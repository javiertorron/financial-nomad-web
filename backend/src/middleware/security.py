"""
Security middleware for the application.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to the response."""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Only add HSTS in production with HTTPS
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy (basic)
        if not settings.debug:
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
            response.headers["Content-Security-Policy"] = csp
        
        return response


class RateLimitingMiddleware:
    """Simple in-memory rate limiting middleware."""
    
    def __init__(self, app: Callable):
        self.app = app
        self.request_counts = {}
        self.last_reset = {}
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting based on client IP."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Reset counters every minute
        if client_ip not in self.last_reset or current_time - self.last_reset[client_ip] > 60:
            self.request_counts[client_ip] = 0
            self.last_reset[client_ip] = current_time
        
        # Increment request count
        self.request_counts[client_ip] += 1
        
        # Check rate limit
        if self.request_counts[client_ip] > settings.rate_limit_per_minute:
            from src.utils.exceptions import RateLimitError
            raise RateLimitError("Rate limit exceeded", retry_after=60)
        
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, settings.rate_limit_per_minute - self.request_counts[client_ip])
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(self.last_reset[client_ip] + 60))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"