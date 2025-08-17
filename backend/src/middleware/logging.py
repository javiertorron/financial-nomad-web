"""
Logging middleware for request/response logging.
"""

import time
from typing import Callable

from fastapi import Request, Response
import structlog

logger = structlog.get_logger()


class LoggingMiddleware:
    """Middleware to log HTTP requests and responses."""
    
    def __init__(self, app: Callable):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Log request and response information."""
        start_time = time.time()
        
        # Extract useful request information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log request start
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=f"{process_time:.4f}s",
            client_ip=client_ip,
            request_id=request_id
        )
        
        # Add processing time header
        response.headers["x-process-time"] = f"{process_time:.4f}"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"