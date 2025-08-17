"""
FastAPI application entry point.
"""

import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog

from src.config import settings
from src.routers import health, auth
from src.middleware.error_handler import ErrorHandlerMiddleware
from src.middleware.logging import LoggingMiddleware
from src.middleware.security import SecurityHeadersMiddleware, RateLimitingMiddleware
from src.utils.exceptions import AppException
from src.infrastructure import cleanup_firestore


# Configure structured logging
def configure_logging():
    """Configure structured logging."""
    logging.basicConfig(
        format="%(message)s",
        stream=None,
        level=getattr(logging, settings.log_level),
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    configure_logging()
    logger = structlog.get_logger()
    
    logger.info(
        "Application starting up",
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        debug=settings.debug
    )
    
    # Initialize services on startup
    logger.info("Initializing services...")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")
    
    # Cleanup resources
    await cleanup_firestore()
    logger.info("Resources cleaned up")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Financial Nomad API - Personal finance management with Asana integration",
        debug=settings.debug,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        lifespan=lifespan
    )
    
    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.debug else [
            "api.financial-nomad.com",
            "localhost",
            "127.0.0.1"
        ]
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"] if settings.debug else settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type", 
            "X-Request-ID",
            "X-Forwarded-For",
            "X-Real-IP"
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ]
    )
    
    # Custom middleware (order matters - last added is executed first)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate limiting (disabled in testing)
    if not settings.is_testing:
        app.add_middleware(RateLimitingMiddleware)
    
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    
    # Exception handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle application exceptions."""
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
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "path": str(request.url.path)
                }
            }
        )
    
    # Include routers
    app.include_router(
        health.router,
        prefix=settings.api_prefix,
        tags=["health"]
    )
    
    app.include_router(
        auth.router,
        prefix=f"{settings.api_prefix}/auth",
        tags=["authentication"]
    )
    
    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        """Root endpoint."""
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": settings.version,
            "docs_url": settings.docs_url,
            "health_check": f"{settings.api_prefix}/health"
        }
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )