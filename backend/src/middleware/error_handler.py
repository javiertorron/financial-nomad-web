"""
Error handling middleware for the application.
"""

import time
import traceback
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog

from src.utils.exceptions import AppException

logger = structlog.get_logger()


class ErrorHandlerMiddleware:
    """Middleware to handle exceptions and format error responses."""
    
    def __init__(self, app: Callable):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle any exceptions."""
        # Generate request ID if not present
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        
        try:
            # Add request ID to request state
            request.state.request_id = request_id
            
            # Process the request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers["x-request-id"] = request_id
            
            return response
            
        except AppException as exc:
            # Handle our custom exceptions
            logger.warning(
                "Application exception occurred",
                request_id=request_id,
                error_code=exc.code,
                error_message=exc.message,
                status_code=exc.status_code,
                path=request.url.path,
                method=request.method
            )
            
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details
                    },
                    "meta": {
                        "timestamp": time.time(),
                        "request_id": request_id,
                        "path": str(request.url.path)
                    }
                },
                headers={"x-request-id": request_id}
            )
            
        except Exception as exc:
            # Handle unexpected exceptions
            logger.error(
                "Unexpected exception occurred",
                request_id=request_id,
                error_type=type(exc).__name__,
                error_message=str(exc),
                traceback=traceback.format_exc(),
                path=request.url.path,
                method=request.method
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "details": []
                    },
                    "meta": {
                        "timestamp": time.time(),
                        "request_id": request_id,
                        "path": str(request.url.path)
                    }
                },
                headers={"x-request-id": request_id}
            )