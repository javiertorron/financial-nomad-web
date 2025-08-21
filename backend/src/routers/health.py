"""
Health check endpoints.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status
import structlog

from src.config import settings

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,
        "environment": settings.environment,
        "app_name": settings.app_name
    }


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with dependency checks."""
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


@router.get("/config", status_code=status.HTTP_200_OK)
async def get_config() -> Dict[str, Any]:
    """Get public configuration for frontend."""
    return {
        "googleClientId": settings.google_client_id,
        "apiUrl": f"/api/v1",
        "environment": settings.environment,
        "version": settings.version,
        "features": {
            "enableAsanaIntegration": True,
            "enableExportFeatures": True,
            "enablePwaFeatures": True,
            "enableOfflineMode": False
        }
    }