"""
Rate limiting and throttling middleware for Financial Nomad.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from collections import defaultdict, deque
import hashlib

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from ..config import get_settings
from .monitoring import metrics_collector

logger = structlog.get_logger()

# Rate limiting metrics - we'll define these after importing prometheus_client
from prometheus_client import Counter

RATE_LIMIT_EXCEEDED = Counter(
    'financial_nomad_rate_limit_exceeded_total',
    'Total number of rate limit exceeded events',
    ['endpoint', 'limit_type']
)

RATE_LIMIT_REQUESTS = Counter(
    'financial_nomad_rate_limited_requests_total',
    'Total number of rate limited requests',
    ['endpoint', 'user_id']
)


class RateLimitRule:
    """Rate limiting rule configuration."""
    
    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        burst_limit: Optional[int] = None,
        key_func: Optional[Callable[[Request], str]] = None
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit or max_requests
        self.key_func = key_func or self._default_key_func
    
    def _default_key_func(self, request: Request) -> str:
        """Default key function using IP address."""
        return self._get_client_ip(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxy headers."""
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else 'unknown'


class TokenBucket:
    """Token bucket algorithm for rate limiting."""
    
    def __init__(self, max_tokens: int, refill_rate: float):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = max_tokens
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket."""
        async with self.lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current bucket status."""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            current_tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
            
            return {
                'available_tokens': int(current_tokens),
                'max_tokens': self.max_tokens,
                'refill_rate': self.refill_rate,
                'last_refill': self.last_refill
            }


class SlidingWindowCounter:
    """Sliding window counter for rate limiting."""
    
    def __init__(self, window_size: int, max_requests: int):
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = deque()
        self.lock = asyncio.Lock()
    
    async def is_allowed(self) -> bool:
        """Check if request is allowed under current rate limit."""
        async with self.lock:
            now = time.time()
            
            # Remove old requests outside the window
            while self.requests and self.requests[0] <= now - self.window_size:
                self.requests.popleft()
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            else:
                return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current window status."""
        async with self.lock:
            now = time.time()
            
            # Clean old requests
            while self.requests and self.requests[0] <= now - self.window_size:
                self.requests.popleft()
            
            return {
                'current_requests': len(self.requests),
                'max_requests': self.max_requests,
                'window_size': self.window_size,
                'requests_remaining': self.max_requests - len(self.requests)
            }


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Advanced rate limiting middleware with multiple strategies."""
    
    def __init__(self, app, settings=None):
        super().__init__(app)
        self.settings = settings or get_settings()
        
        # Storage for rate limiting data
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.sliding_windows: Dict[str, SlidingWindowCounter] = {}
        
        # Rate limit rules per endpoint pattern
        self.rules = self._setup_rate_limit_rules()
        
        # Global rate limiting
        self.global_limiter = TokenBucket(
            max_tokens=1000,  # 1000 requests
            refill_rate=10.0  # 10 requests per second
        )
        
        # Cleanup task
        self.cleanup_task = None
        self._start_cleanup_task()
    
    def _setup_rate_limit_rules(self) -> Dict[str, RateLimitRule]:
        """Setup rate limiting rules for different endpoints."""
        return {
            # Authentication endpoints - more restrictive
            '/api/v1/auth/login': RateLimitRule(
                max_requests=5,
                window_seconds=300,  # 5 requests per 5 minutes
                key_func=lambda req: self._get_client_ip(req)
            ),
            '/api/v1/auth/register': RateLimitRule(
                max_requests=3,
                window_seconds=3600,  # 3 requests per hour
                key_func=lambda req: self._get_client_ip(req)
            ),
            
            # Backup and export endpoints - moderate limits
            '/api/v1/backup/trigger': RateLimitRule(
                max_requests=10,
                window_seconds=3600,  # 10 backups per hour
                key_func=lambda req: getattr(req.state, 'user_id', 'anonymous')
            ),
            '/api/v1/backup/export': RateLimitRule(
                max_requests=20,
                window_seconds=3600,  # 20 exports per hour
                key_func=lambda req: getattr(req.state, 'user_id', 'anonymous')
            ),
            
            # External API integration endpoints
            '/api/v1/asana': RateLimitRule(
                max_requests=100,
                window_seconds=3600,  # 100 requests per hour
                key_func=lambda req: getattr(req.state, 'user_id', 'anonymous')
            ),
            
            # General API endpoints
            'default': RateLimitRule(
                max_requests=1000,
                window_seconds=3600,  # 1000 requests per hour per user
                key_func=lambda req: getattr(req.state, 'user_id', self._get_client_ip(req))
            )
        }
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and metrics
        if request.url.path in ['/health', '/metrics', '/api/v1/health']:
            return await call_next(request)
        
        # Apply global rate limiting first
        if not await self.global_limiter.consume():
            logger.warning(
                "Global rate limit exceeded",
                path=request.url.path,
                client_ip=self._get_client_ip(request)
            )
            return self._rate_limit_response("Global rate limit exceeded")
        
        # Find applicable rule
        rule = self._find_rule_for_path(request.url.path)
        rate_limit_key = f"{request.url.path}:{rule.key_func(request)}"
        
        # Check rate limit
        if not await self._check_rate_limit(rate_limit_key, rule, request):
            endpoint_pattern = self._extract_endpoint_pattern(request.url.path)
            
            RATE_LIMIT_EXCEEDED.labels(
                endpoint=endpoint_pattern,
                limit_type='user'
            ).inc()
            
            user_id = getattr(request.state, 'user_id', 'anonymous')
            RATE_LIMIT_REQUESTS.labels(
                endpoint=endpoint_pattern,
                user_id=user_id
            ).inc()
            
            logger.warning(
                "Rate limit exceeded",
                path=request.url.path,
                user_id=user_id,
                rate_limit_key=rate_limit_key,
                rule_max_requests=rule.max_requests,
                rule_window_seconds=rule.window_seconds
            )
            
            return self._rate_limit_response(
                f"Rate limit exceeded: {rule.max_requests} requests per {rule.window_seconds} seconds"
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        await self._add_rate_limit_headers(response, rate_limit_key, rule)
        
        return response
    
    def _find_rule_for_path(self, path: str) -> RateLimitRule:
        """Find the most specific rate limit rule for a path."""
        # Check for exact matches first
        for rule_path, rule in self.rules.items():
            if rule_path == path:
                return rule
        
        # Check for prefix matches
        for rule_path, rule in self.rules.items():
            if path.startswith(rule_path) and rule_path != 'default':
                return rule
        
        # Return default rule
        return self.rules['default']
    
    async def _check_rate_limit(self, key: str, rule: RateLimitRule, request: Request) -> bool:
        """Check if request is within rate limit."""
        # Use sliding window for most cases
        if key not in self.sliding_windows:
            self.sliding_windows[key] = SlidingWindowCounter(
                window_size=rule.window_seconds,
                max_requests=rule.max_requests
            )
        
        return await self.sliding_windows[key].is_allowed()
    
    def _rate_limit_response(self, message: str) -> Response:
        """Create rate limit exceeded response."""
        return Response(
            content=f'{{"detail": "{message}"}}',
            status_code=429,
            media_type="application/json",
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": "Various",
                "X-RateLimit-Reset": str(int(time.time()) + 60)
            }
        )
    
    async def _add_rate_limit_headers(self, response: Response, key: str, rule: RateLimitRule):
        """Add rate limit information to response headers."""
        if key in self.sliding_windows:
            status = await self.sliding_windows[key].get_status()
            response.headers["X-RateLimit-Limit"] = str(rule.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(status['requests_remaining'])
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + rule.window_seconds)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxy headers."""
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else 'unknown'
    
    def _extract_endpoint_pattern(self, path: str) -> str:
        """Extract endpoint pattern for consistent metrics labeling."""
        patterns = [
            (r'/api/v1/transactions/[^/]+', '/api/v1/transactions/{id}'),
            (r'/api/v1/accounts/[^/]+', '/api/v1/accounts/{id}'),
            (r'/api/v1/categories/[^/]+', '/api/v1/categories/{id}'),
            (r'/api/v1/budgets/[^/]+', '/api/v1/budgets/{id}'),
            (r'/api/v1/backup/exports/[^/]+', '/api/v1/backup/exports/{id}'),
        ]
        
        import re
        for pattern, replacement in patterns:
            if re.search(pattern, path):
                return replacement
        
        return path
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_old_entries())
    
    async def _cleanup_old_entries(self):
        """Periodically clean up old rate limiting entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                now = time.time()
                
                # Cleanup old sliding windows
                keys_to_remove = []
                for key, window in self.sliding_windows.items():
                    status = await window.get_status()
                    # Remove if no recent activity
                    if status['current_requests'] == 0:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.sliding_windows[key]
                
                # Cleanup old token buckets
                keys_to_remove = []
                for key, bucket in self.token_buckets.items():
                    status = await bucket.get_status()
                    # Remove if bucket is full and hasn't been used recently
                    if (status['available_tokens'] == status['max_tokens'] and 
                        now - status['last_refill'] > 3600):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.token_buckets[key]
                
                logger.debug(
                    "Rate limiting cleanup completed",
                    sliding_windows_removed=len(keys_to_remove),
                    active_windows=len(self.sliding_windows),
                    active_buckets=len(self.token_buckets)
                )
                
            except Exception as e:
                logger.error("Rate limiting cleanup failed", error=str(e))
    
    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limiting status for monitoring."""
        global_status = await self.global_limiter.get_status()
        
        return {
            'global_limiter': global_status,
            'active_sliding_windows': len(self.sliding_windows),
            'active_token_buckets': len(self.token_buckets),
            'rules_count': len(self.rules),
            'cleanup_task_running': self.cleanup_task is not None and not self.cleanup_task.done()
        }


class IPWhitelist:
    """IP whitelist middleware for admin endpoints."""
    
    def __init__(self, whitelisted_ips: List[str] = None):
        self.whitelisted_ips = set(whitelisted_ips or [])
        # Add common development IPs
        self.whitelisted_ips.update(['127.0.0.1', 'localhost', '::1'])
    
    def is_whitelisted(self, request: Request) -> bool:
        """Check if request IP is whitelisted."""
        client_ip = self._get_client_ip(request)
        return client_ip in self.whitelisted_ips
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxy headers."""
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else 'unknown'


# Global instances
rate_limiter = None
ip_whitelist = IPWhitelist()


def get_rate_limiter(settings=None) -> RateLimitingMiddleware:
    """Get or create rate limiter instance."""
    global rate_limiter
    if rate_limiter is None:
        # This would be created during app startup
        pass
    return rate_limiter


def get_ip_whitelist() -> IPWhitelist:
    """Get IP whitelist instance."""
    return ip_whitelist