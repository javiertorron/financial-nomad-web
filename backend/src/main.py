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
from src.routers import health, auth, accounts, categories, transactions, import_export, budgets, recurring_transactions, asana, backup_export, monitoring, frontend, performance, business_intelligence, feature_flags, admin_tools, resilience, notifications, reports, analytics, webhooks, graphql, audit, cache, migrations
from src.middleware.error_handler import ErrorHandlerMiddleware
from src.middleware.logging import LoggingMiddleware
from src.middleware.security import SecurityHeadersMiddleware, RateLimitingMiddleware as SimpleLimiter
from src.middleware.monitoring import MonitoringMiddleware
from src.middleware.rate_limiting import RateLimitingMiddleware as AdvancedLimiter
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
    
    # Initialize cache service
    from src.services.caching import get_cache_service
    cache_service = get_cache_service()
    logger.info("Cache service initialized")
    
    # Initialize query optimizer
    from src.services.query_optimizer import get_query_optimizer
    query_optimizer = get_query_optimizer()
    logger.info("Query optimizer initialized")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")
    
    # Cleanup resources
    await cleanup_firestore()
    logger.info("Resources cleaned up")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Financial Nomad API",
        version=settings.version,
        description="""
**Financial Nomad API** - Personal finance management with Asana integration

## Features

- 📊 **Financial Management**: Complete CRUD for accounts, transactions, categories and budgets
- 📈 **Analytics**: Advanced reporting and financial insights 
- 🔗 **Asana Integration**: Sync tasks and projects between Asana and financial tracking
- 💾 **Backup & Export**: Full data export to JSON/CSV with Google Drive integration
- 🔐 **OAuth Authentication**: Secure authentication via Google OAuth
- 🚀 **Performance**: Redis caching, query optimization and rate limiting
- 📊 **Monitoring**: Prometheus metrics and health checks
        
## Authentication

All endpoints require authentication via **Bearer Token**. Get your token from `/auth/login`.

## Rate Limiting

API requests are rate limited to ensure fair usage:
- **100 requests/minute** for authenticated users
- **10 requests/minute** for unauthenticated requests
        
## Support

- 📧 Email: support@financial-nomad.com
- 📖 Documentation: [API Docs](https://api.financial-nomad.com/docs)
        """,
        debug=settings.debug,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        lifespan=lifespan,
        contact={
            "name": "Financial Nomad Team",
            "email": "support@financial-nomad.com",
            "url": "https://financial-nomad.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        servers=[
            {
                "url": "https://api.financial-nomad.com",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.financial-nomad.com", 
                "description": "Staging server"
            },
            {
                "url": "http://localhost:8080",
                "description": "Local development server"
            }
        ]
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
    
    # CORS middleware - Configure allowed origins based on environment
    cors_origins = settings.get_cors_origins_list()
    if settings.debug and not cors_origins:
        # Default CORS for development
        cors_origins = [
            "http://localhost:3000",
            "http://localhost:4200", 
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:4200",
            "http://127.0.0.1:8080"
        ]
    elif not cors_origins and not settings.debug:
        # Production should have explicit origins
        cors_origins = []
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Authorization",
            "Content-Type", 
            "X-Request-ID",
            "X-Forwarded-For",
            "X-Real-IP",
            "User-Agent",
            "Accept",
            "Accept-Language",
            "Accept-Encoding",
            "Origin",
            "Referer"
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time",
            "X-RateLimit-Limit", 
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Total-Count",
            "X-Page",
            "X-Per-Page"
        ]
    )
    
    # Custom middleware (order matters - last added is executed first)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Monitoring middleware (should be early in chain)
    app.add_middleware(MonitoringMiddleware, settings=settings)
    
    # Rate limiting (disabled in testing)
    if not settings.is_testing:
        # Use the advanced rate limiter for production
        # app.add_middleware(AdvancedLimiter, settings=settings)
        # For now, use the simple limiter to avoid complexity
        app.add_middleware(SimpleLimiter)
    
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
    
    app.include_router(
        accounts.router,
        prefix=settings.api_prefix,
        tags=["accounts"]
    )
    
    app.include_router(
        categories.router,
        prefix=settings.api_prefix,
        tags=["categories"]
    )
    
    app.include_router(
        transactions.router,
        prefix=settings.api_prefix,
        tags=["transactions"]
    )
    
    app.include_router(
        import_export.router,
        prefix=settings.api_prefix,
        tags=["import-export"]
    )
    
    app.include_router(
        budgets.router,
        prefix=settings.api_prefix,
        tags=["budgets"]
    )
    
    app.include_router(
        recurring_transactions.router,
        prefix=settings.api_prefix,
        tags=["recurring-transactions"]
    )
    
    app.include_router(
        asana.router,
        prefix=settings.api_prefix,
        tags=["asana-integration"]
    )
    
    app.include_router(
        backup_export.router,
        prefix=settings.api_prefix,
        tags=["backup-export"]
    )
    
    app.include_router(
        monitoring.router,
        prefix=settings.api_prefix,
        tags=["monitoring"]
    )
    
    app.include_router(
        frontend.router,
        prefix=f"{settings.api_prefix}/frontend",
        tags=["frontend-integration"]
    )
    
    app.include_router(
        performance.router,
        prefix=f"{settings.api_prefix}/performance",
        tags=["performance-optimization"]
    )
    
    app.include_router(
        business_intelligence.router,
        prefix=f"{settings.api_prefix}/bi",
        tags=["business-intelligence"]
    )
    
    app.include_router(
        feature_flags.router,
        prefix=f"{settings.api_prefix}/features",
        tags=["feature-flags"]
    )
    
    app.include_router(
        admin_tools.router,
        prefix=f"{settings.api_prefix}/admin",
        tags=["admin-tools"]
    )
    
    app.include_router(
        resilience.router,
        prefix=f"{settings.api_prefix}/resilience",
        tags=["resilience"]
    )
    
    app.include_router(
        notifications.router,
        prefix=f"{settings.api_prefix}/notifications",
        tags=["notifications"]
    )
    
    app.include_router(
        reports.router,
        prefix=f"{settings.api_prefix}/reports",
        tags=["reports"]
    )
    
    app.include_router(
        analytics.router,
        prefix=f"{settings.api_prefix}/analytics",
        tags=["analytics"]
    )
    
    app.include_router(
        webhooks.router,
        prefix=f"{settings.api_prefix}/webhooks",
        tags=["webhooks"]
    )
    
    app.include_router(
        graphql.router,
        prefix=f"{settings.api_prefix}/graphql",
        tags=["graphql"]
    )
    
    app.include_router(
        audit.router,
        prefix=f"{settings.api_prefix}/audit",
        tags=["audit"]
    )
    
    app.include_router(
        cache.router,
        prefix=f"{settings.api_prefix}/cache",
        tags=["cache"]
    )
    
    app.include_router(
        migrations.router,
        prefix=f"{settings.api_prefix}/migrations",
        tags=["migrations"]
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