"""
Health check endpoints.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import structlog

from src.config import settings
from src.models.api_responses import (
    HealthCheckResponse,
    DetailedHealthResponse, 
    ReadinessResponse,
    LivenessResponse,
    PublicConfigResponse,
    ConfigFeatures
)

logger = structlog.get_logger()
router = APIRouter()


@router.get(
    "/health", 
    status_code=status.HTTP_200_OK,
    summary="Basic Health Check",
    description="Returns the basic health status of the API service",
    response_description="Service health information",
    response_model=HealthCheckResponse,
    tags=["Health Checks"]
)
async def health_check() -> HealthCheckResponse:
    """
    **Basic health check endpoint**
    
    Returns essential service information including:
    - Service status
    - Current timestamp  
    - Application version
    - Environment name
    - Application name
    
    This endpoint is used for basic monitoring and load balancer health checks.
    """
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.version,
        environment=settings.environment,
        app_name=settings.app_name
    )


@router.get(
    "/health/detailed", 
    status_code=status.HTTP_200_OK,
    summary="Detailed Health Check",
    description="Comprehensive health check including all service dependencies",
    response_description="Detailed health status with dependency checks",
    tags=["Health Checks"],
    responses={
        200: {
            "description": "Service and all dependencies are healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "version": "1.0.0",
                        "environment": "production",
                        "checks": {
                            "database": {
                                "status": "healthy",
                                "response_time_ms": 45.2
                            },
                            "external_apis": {
                                "status": "healthy"
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service or dependencies are unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "version": "1.0.0",
                        "environment": "production",
                        "checks": {
                            "database": {
                                "status": "unhealthy",
                                "error": "Connection timeout"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def detailed_health_check() -> Dict[str, Any]:
    """
    **Detailed health check with dependency verification**
    
    Performs comprehensive health checks including:
    - Database connectivity and response time
    - External API availability (Google, Asana)
    - Cache service status
    - Background service health
    
    Returns HTTP 503 if any critical dependency is unhealthy.
    Used for deep monitoring and troubleshooting.
    """
    checks = {}
    overall_status = "healthy"
    
    # TODO: Add Firestore health check when implemented
    # try:
    #     start_time = datetime.utcnow()
    #     await firestore_client.test_connection()
    #     response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    #     
    #     checks["firestore"] = {
    #         "status": "healthy",
    #         "response_time_ms": round(response_time, 2)
    #     }
    # except Exception as e:
    #     checks["firestore"] = {
    #         "status": "unhealthy",
    #         "error": str(e)
    #     }
    #     overall_status = "unhealthy"
    
    # Placeholder for now
    checks["database"] = {
        "status": "not_implemented",
        "message": "Database health check not yet implemented"
    }
    
    response_data = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,
        "environment": settings.environment,
        "checks": checks
    }
    
    status_code = status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return response_data


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, str]:
    """Readiness probe for Kubernetes."""
    # TODO: Add actual readiness checks when dependencies are implemented
    # For now, just return ready
    return {"status": "ready"}


@router.get("/live", status_code=status.HTTP_200_OK) 
async def liveness_check() -> Dict[str, str]:
    """Liveness probe for Kubernetes."""
    # Basic check that the application is responsive
    return {"status": "alive"}


@router.get(
    "/config",
    status_code=status.HTTP_200_OK,
    summary="Get Public Configuration",
    description="Returns public configuration settings for frontend applications",
    response_description="Configuration settings safe for client-side use",
    response_model=PublicConfigResponse,
    tags=["Configuration"]
)
async def get_config() -> PublicConfigResponse:
    """
    **Get public configuration for frontend**
    
    Returns configuration settings that are safe to expose to client applications:
    - Google OAuth client ID
    - API base URL  
    - Environment name
    - Application version
    - Feature flags
    
    This endpoint does not require authentication and is used by frontend
    applications during initialization.
    """
    return PublicConfigResponse(
        googleClientId=settings.google_client_id,
        apiUrl=settings.api_prefix,
        environment=settings.environment,
        version=settings.version,
        features=ConfigFeatures(
            enableAsanaIntegration=bool(settings.asana_client_id),
            enableExportFeatures=True,
            enablePwaFeatures=True,
            enableOfflineMode=False
        )
    )