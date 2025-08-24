"""
Frontend integration endpoints.
Provides configuration and integration points for the Angular frontend.
"""

from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import BaseModel, Field
import structlog

from src.config import settings
from src.models.api_responses import PublicConfigResponse, ConfigFeatures
from src.utils.dependencies import get_current_user_optional

logger = structlog.get_logger()
router = APIRouter()


class ServerInfo(BaseModel):
    """Server information model."""
    server_time: str = Field(..., description="Current server time", example="2024-01-15T10:30:00Z")
    timezone: str = Field(..., description="Server timezone", example="UTC")
    uptime_seconds: float = Field(..., description="Server uptime in seconds", example=3600.0)
    version: str = Field(..., description="API version", example="1.0.0")
    environment: str = Field(..., description="Environment name", example="production")


class FeatureFlag(BaseModel):
    """Feature flag model."""
    key: str = Field(..., description="Feature key", example="enable_asana_integration")
    enabled: bool = Field(..., description="Feature enabled status", example=True)
    description: str = Field(..., description="Feature description", example="Enable Asana task integration")
    requires_auth: bool = Field(..., description="Feature requires authentication", example=True)


class FrontendConfig(BaseModel):
    """Complete frontend configuration."""
    api: PublicConfigResponse = Field(..., description="API configuration")
    server: ServerInfo = Field(..., description="Server information")
    features: List[FeatureFlag] = Field(..., description="Available feature flags")
    cors_origins: List[str] = Field(..., description="Allowed CORS origins")
    rate_limits: Dict[str, int] = Field(..., description="Rate limit information")


# Global variable to track server start time
import time
_server_start_time = time.time()


@router.get(
    "/info",
    status_code=status.HTTP_200_OK,
    summary="Get Server Information",
    description="Returns current server information including time, uptime, and version",
    response_description="Server status information",
    response_model=ServerInfo,
    tags=["Frontend Integration"]
)
async def get_server_info() -> ServerInfo:
    """
    **Get server information for frontend synchronization**
    
    Provides essential server information including:
    - Current server time for synchronization
    - Server timezone information
    - Server uptime
    - API version information
    - Environment details
    
    This endpoint helps frontend applications synchronize with server state
    and display relevant system information.
    """
    current_time = time.time()
    uptime = current_time - _server_start_time
    
    return ServerInfo(
        server_time=datetime.utcnow().isoformat() + "Z",
        timezone="UTC",
        uptime_seconds=round(uptime, 2),
        version=settings.version,
        environment=settings.environment
    )


@router.get(
    "/features",
    status_code=status.HTTP_200_OK,
    summary="Get Feature Flags",
    description="Returns available feature flags for the current environment",
    response_description="List of available features with their status",
    response_model=List[FeatureFlag],
    tags=["Frontend Integration"]
)
async def get_feature_flags(
    current_user: Dict[str, Any] = Depends(get_current_user_optional)
) -> List[FeatureFlag]:
    """
    **Get feature flags for frontend feature toggling**
    
    Returns a list of available features with their current status.
    Some features may require authentication to be enabled.
    
    Feature flags help frontend applications:
    - Show/hide UI components based on availability
    - Enable/disable functionality based on server capabilities
    - Adapt to different environments and configurations
    """
    user_authenticated = current_user is not None
    
    features = [
        FeatureFlag(
            key="asana_integration",
            enabled=bool(settings.asana_client_id),
            description="Asana task integration and synchronization",
            requires_auth=True
        ),
        FeatureFlag(
            key="google_drive_backup",
            enabled=bool(settings.google_client_secret),
            description="Backup data to Google Drive",
            requires_auth=True
        ),
        FeatureFlag(
            key="export_features",
            enabled=True,
            description="Data export to JSON/CSV formats",
            requires_auth=True
        ),
        FeatureFlag(
            key="advanced_analytics",
            enabled=not settings.is_testing,
            description="Advanced financial analytics and reporting",
            requires_auth=True
        ),
        FeatureFlag(
            key="real_time_sync",
            enabled=settings.is_production,
            description="Real-time data synchronization",
            requires_auth=True
        ),
        FeatureFlag(
            key="offline_mode",
            enabled=False,  # Not yet implemented
            description="Offline functionality with local storage",
            requires_auth=False
        ),
        FeatureFlag(
            key="pwa_features",
            enabled=True,
            description="Progressive Web App features",
            requires_auth=False
        ),
        FeatureFlag(
            key="debug_mode",
            enabled=settings.debug and user_authenticated,
            description="Debug information and developer tools",
            requires_auth=True
        )
    ]
    
    return features


@router.get(
    "/config/complete",
    status_code=status.HTTP_200_OK,
    summary="Get Complete Frontend Configuration",
    description="Returns comprehensive configuration for frontend initialization",
    response_description="Complete configuration including server info and feature flags",
    response_model=FrontendConfig,
    tags=["Frontend Integration"]
)
async def get_complete_config(
    current_user: Dict[str, Any] = Depends(get_current_user_optional)
) -> FrontendConfig:
    """
    **Get complete configuration for frontend initialization**
    
    This endpoint provides all necessary configuration data for frontend
    applications in a single request, including:
    - API configuration (OAuth, URLs, version)
    - Server information (time, uptime, environment)
    - Feature flags (what's available and enabled)
    - CORS configuration
    - Rate limiting information
    
    This is the recommended endpoint for frontend application initialization
    as it reduces the number of requests needed during app startup.
    """
    # Get all components
    api_config = PublicConfigResponse(
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
    
    server_info = await get_server_info()
    features = await get_feature_flags(current_user)
    cors_origins = settings.get_cors_origins_list()
    
    return FrontendConfig(
        api=api_config,
        server=server_info,
        features=features,
        cors_origins=cors_origins,
        rate_limits={
            "authenticated": settings.rate_limit_per_minute,
            "unauthenticated": 10,
            "window_minutes": 1
        }
    )


@router.get(
    "/version",
    status_code=status.HTTP_200_OK,
    summary="Get API Version",
    description="Returns the current API version information",
    tags=["Frontend Integration"]
)
async def get_version() -> Dict[str, str]:
    """
    **Get API version for compatibility checking**
    
    Returns version information that frontend applications can use
    to verify compatibility and display version information.
    """
    return {
        "version": settings.version,
        "api_version": "v1",
        "environment": settings.environment,
        "build_date": "2024-01-15",  # This could be injected during build
    }


@router.options(
    "/{path:path}",
    status_code=status.HTTP_200_OK,
    summary="CORS Preflight Handler",
    description="Handles CORS preflight requests for all frontend endpoints",
    tags=["Frontend Integration"],
    include_in_schema=False
)
async def handle_preflight(path: str):
    """
    **Handle CORS preflight requests**
    
    This endpoint handles OPTIONS requests for CORS preflight checks.
    It's automatically called by browsers before making actual requests
    to ensure the frontend is allowed to access the API.
    """
    return {"status": "ok"}