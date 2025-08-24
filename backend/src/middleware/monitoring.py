"""
Advanced monitoring and observability middleware for Financial Nomad.
"""
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from ..config import get_settings

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'financial_nomad_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'financial_nomad_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'financial_nomad_active_requests',
    'Number of active HTTP requests'
)

DATABASE_OPERATIONS = Counter(
    'financial_nomad_database_operations_total',
    'Total number of database operations',
    ['operation', 'collection', 'status']
)

EXTERNAL_API_CALLS = Counter(
    'financial_nomad_external_api_calls_total',
    'Total number of external API calls',
    ['service', 'status']
)

CACHE_OPERATIONS = Counter(
    'financial_nomad_cache_operations_total',
    'Total number of cache operations',
    ['operation', 'status']
)

# Application metrics
USER_SESSIONS = Gauge(
    'financial_nomad_active_user_sessions',
    'Number of active user sessions'
)

BACKUP_OPERATIONS = Counter(
    'financial_nomad_backup_operations_total',
    'Total number of backup operations',
    ['type', 'status']
)

EXPORT_OPERATIONS = Counter(
    'financial_nomad_export_operations_total',
    'Total number of export operations',
    ['format', 'type', 'status']
)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for request monitoring and observability."""
    
    def __init__(self, app, settings=None):
        super().__init__(app)
        self.settings = settings or get_settings()
        self.active_requests: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        ACTIVE_REQUESTS.inc()
        
        # Store request info for monitoring
        self.active_requests[request_id] = {
            'method': request.method,
            'url': str(request.url),
            'start_time': start_time,
            'user_id': getattr(request.state, 'user_id', None)
        }
        
        # Extract endpoint pattern for metrics
        endpoint_pattern = self._extract_endpoint_pattern(request)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint_pattern,
                status_code=response.status_code
            ).inc()
            
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=endpoint_pattern
            ).observe(duration)
            
            # Log request
            await self._log_request(request, response, duration)
            
            # Track business metrics
            await self._track_business_metrics(request, response, duration)
            
            # Add monitoring headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            return response
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint_pattern,
                status_code=500
            ).inc()
            
            # Log error
            logger.error(
                "Request processing failed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                duration=duration,
                error=str(e),
                exc_info=True
            )
            
            raise
            
        finally:
            # Cleanup
            ACTIVE_REQUESTS.dec()
            if request_id in self.active_requests:
                del self.active_requests[request_id]
    
    def _extract_endpoint_pattern(self, request: Request) -> str:
        """Extract endpoint pattern for consistent metrics labeling."""
        path = request.url.path
        
        # Common patterns for path normalization
        patterns = [
            (r'/api/v1/transactions/[^/]+', '/api/v1/transactions/{id}'),
            (r'/api/v1/accounts/[^/]+', '/api/v1/accounts/{id}'),
            (r'/api/v1/categories/[^/]+', '/api/v1/categories/{id}'),
            (r'/api/v1/budgets/[^/]+', '/api/v1/budgets/{id}'),
            (r'/api/v1/backup/exports/[^/]+', '/api/v1/backup/exports/{id}'),
            (r'/api/v1/asana/tasks/[^/]+', '/api/v1/asana/tasks/{id}'),
        ]
        
        import re
        for pattern, replacement in patterns:
            if re.search(pattern, path):
                return replacement
        
        return path
    
    async def _log_request(self, request: Request, response: Response, duration: float):
        """Log request with structured logging."""
        user_id = getattr(request.state, 'user_id', None)
        
        log_data = {
            'request_id': request.state.request_id,
            'method': request.method,
            'url': str(request.url),
            'status_code': response.status_code,
            'duration_seconds': round(duration, 3),
            'user_id': user_id,
            'user_agent': request.headers.get('user-agent'),
            'ip_address': self._get_client_ip(request),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add response size if available
        content_length = response.headers.get('content-length')
        if content_length:
            log_data['response_size_bytes'] = int(content_length)
        
        # Log at appropriate level based on status code
        if response.status_code >= 500:
            logger.error("HTTP request completed with server error", **log_data)
        elif response.status_code >= 400:
            logger.warning("HTTP request completed with client error", **log_data)
        elif duration > 2.0:  # Slow request threshold
            logger.warning("Slow HTTP request detected", **log_data)
        else:
            logger.info("HTTP request completed", **log_data)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxy headers."""
        # Check for proxy headers first
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else 'unknown'
    
    async def _track_business_metrics(self, request: Request, response: Response, duration: float):
        """Track business metrics for analytics."""
        try:
            from src.services.business_metrics import get_business_metrics_collector
            business_collector = get_business_metrics_collector()
            
            user_id = getattr(request.state, 'user_id', None)
            
            # Track API usage
            business_collector.track_api_usage(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time=duration,
                user_id=user_id
            )
            
            # Track user session if authenticated
            if user_id and hasattr(request.state, 'session_data'):
                session_data = getattr(request.state, 'session_data', {})
                business_collector.track_user_session(user_id, session_data)
            
        except Exception as e:
            logger.warning("Failed to track business metrics", error=str(e))
    
    def get_active_requests_info(self) -> Dict[str, Any]:
        """Get information about currently active requests."""
        return {
            'count': len(self.active_requests),
            'requests': list(self.active_requests.values())
        }


class MetricsCollector:
    """Collector for application-specific metrics."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def record_database_operation(self, operation: str, collection: str, status: str = 'success'):
        """Record database operation metrics."""
        DATABASE_OPERATIONS.labels(
            operation=operation,
            collection=collection,
            status=status
        ).inc()
    
    def record_external_api_call(self, service: str, status: str = 'success'):
        """Record external API call metrics."""
        EXTERNAL_API_CALLS.labels(
            service=service,
            status=status
        ).inc()
    
    def record_cache_operation(self, operation: str, status: str = 'hit'):
        """Record cache operation metrics."""
        CACHE_OPERATIONS.labels(
            operation=operation,
            status=status
        ).inc()
    
    def record_backup_operation(self, backup_type: str, status: str = 'success'):
        """Record backup operation metrics."""
        BACKUP_OPERATIONS.labels(
            type=backup_type,
            status=status
        ).inc()
    
    def record_export_operation(self, format_type: str, export_type: str, status: str = 'success'):
        """Record export operation metrics."""
        EXPORT_OPERATIONS.labels(
            format=format_type,
            type=export_type,
            status=status
        ).inc()
    
    def update_active_sessions(self, count: int):
        """Update active user sessions gauge."""
        USER_SESSIONS.set(count)


class HealthChecker:
    """Advanced health checking for dependencies."""
    
    def __init__(self):
        self.settings = get_settings()
        self._last_check = {}
        self._check_intervals = {
            'firestore': 30,  # seconds
            'external_apis': 60,
            'storage': 45
        }
    
    async def check_firestore_health(self) -> Dict[str, Any]:
        """Check Firestore connectivity and performance."""
        try:
            from ..infrastructure import get_firestore
            firestore = get_firestore()
            
            start_time = time.time()
            
            # Simple read operation to test connectivity
            test_doc = await firestore.get_document(
                collection="health_checks",
                document_id="test",
                model_class=None
            )
            
            duration = time.time() - start_time
            
            return {
                'status': 'healthy',
                'response_time_ms': round(duration * 1000, 2),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Firestore health check failed", error=str(e))
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def check_external_apis_health(self) -> Dict[str, Any]:
        """Check external API dependencies."""
        results = {}
        
        # Check Google Drive API (if configured)
        if hasattr(self.settings, 'google_client_id') and self.settings.google_client_id:
            results['google_drive'] = await self._check_google_api()
        
        # Check Asana API (basic connectivity)
        results['asana'] = await self._check_asana_api()
        
        return results
    
    async def _check_google_api(self) -> Dict[str, Any]:
        """Check Google API connectivity."""
        try:
            import httpx
            
            # Simple check to Google's discovery document
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://www.googleapis.com/discovery/v1/apis/drive/v3/rest"
                )
                
                if response.status_code == 200:
                    return {
                        'status': 'healthy',
                        'response_time_ms': response.elapsed.total_seconds() * 1000
                    }
                else:
                    return {
                        'status': 'degraded',
                        'status_code': response.status_code
                    }
                    
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _check_asana_api(self) -> Dict[str, Any]:
        """Check Asana API connectivity."""
        try:
            import httpx
            
            # Check Asana API status endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://app.asana.com/api/1.0/users/me")
                
                # We expect 401 (unauthorized) as we're not sending auth
                # This confirms the API is reachable
                if response.status_code == 401:
                    return {
                        'status': 'healthy',
                        'response_time_ms': response.elapsed.total_seconds() * 1000
                    }
                else:
                    return {
                        'status': 'degraded',
                        'status_code': response.status_code
                    }
                    
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        health_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy'
        }
        
        # Check all dependencies
        checks = await asyncio.gather(
            self.check_firestore_health(),
            self.check_external_apis_health(),
            return_exceptions=True
        )
        
        health_data['firestore'] = checks[0] if not isinstance(checks[0], Exception) else {
            'status': 'unhealthy',
            'error': str(checks[0])
        }
        
        health_data['external_apis'] = checks[1] if not isinstance(checks[1], Exception) else {
            'status': 'unhealthy',
            'error': str(checks[1])
        }
        
        # Determine overall status
        if any(
            check.get('status') == 'unhealthy' 
            for check in [health_data['firestore']] + list(health_data['external_apis'].values())
        ):
            health_data['overall_status'] = 'unhealthy'
        elif any(
            check.get('status') == 'degraded'
            for check in [health_data['firestore']] + list(health_data['external_apis'].values())
        ):
            health_data['overall_status'] = 'degraded'
        
        return health_data


# Global instances
metrics_collector = MetricsCollector()
health_checker = HealthChecker()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return metrics_collector


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    return health_checker


async def get_prometheus_metrics() -> str:
    """Generate Prometheus metrics."""
    return generate_latest().decode('utf-8')