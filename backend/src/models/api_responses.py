"""
Pydantic models for API responses to improve OpenAPI documentation.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Response model for basic health check."""
    status: str = Field(..., description="Service health status", example="healthy")
    timestamp: str = Field(..., description="Current timestamp in ISO format", example="2024-01-15T10:30:00Z")
    version: str = Field(..., description="Application version", example="1.0.0")
    environment: str = Field(..., description="Current environment", example="production")
    app_name: str = Field(..., description="Application name", example="financial-nomad-api")


class DependencyCheck(BaseModel):
    """Model for individual dependency health check."""
    status: str = Field(..., description="Dependency status", example="healthy")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds", example=45.2)
    error: Optional[str] = Field(None, description="Error message if unhealthy", example="Connection timeout")


class DetailedHealthResponse(BaseModel):
    """Response model for detailed health check."""
    status: str = Field(..., description="Overall service health status", example="healthy")
    timestamp: str = Field(..., description="Current timestamp in ISO format", example="2024-01-15T10:30:00Z")
    version: str = Field(..., description="Application version", example="1.0.0")
    environment: str = Field(..., description="Current environment", example="production")
    checks: Dict[str, Any] = Field(..., description="Detailed dependency checks")


class ReadinessResponse(BaseModel):
    """Response model for readiness probe."""
    status: str = Field(..., description="Readiness status", example="ready")


class LivenessResponse(BaseModel):
    """Response model for liveness probe."""
    status: str = Field(..., description="Liveness status", example="alive")


class ConfigFeatures(BaseModel):
    """Configuration features model."""
    enableAsanaIntegration: bool = Field(..., description="Asana integration enabled", example=True)
    enableExportFeatures: bool = Field(..., description="Export features enabled", example=True)
    enablePwaFeatures: bool = Field(..., description="PWA features enabled", example=True)
    enableOfflineMode: bool = Field(..., description="Offline mode enabled", example=False)


class PublicConfigResponse(BaseModel):
    """Response model for public configuration."""
    googleClientId: Optional[str] = Field(None, description="Google OAuth client ID")
    apiUrl: str = Field(..., description="API base URL", example="/api/v1")
    environment: str = Field(..., description="Current environment", example="production")
    version: str = Field(..., description="Application version", example="1.0.0")
    features: ConfigFeatures = Field(..., description="Available features configuration")


class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str = Field(..., description="Error code", example="VALIDATION_ERROR")
    message: str = Field(..., description="Error message", example="Invalid input data")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorMeta(BaseModel):
    """Error metadata model."""
    timestamp: float = Field(..., description="Error timestamp", example=1705316400.0)
    request_id: str = Field(..., description="Request ID for tracking", example="req_123456789")
    path: str = Field(..., description="API endpoint path", example="/api/v1/accounts")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: ErrorDetail = Field(..., description="Error information")
    meta: ErrorMeta = Field(..., description="Request metadata")


class RootResponse(BaseModel):
    """Response model for root endpoint."""
    message: str = Field(..., description="Welcome message", example="Welcome to financial-nomad-api")
    version: str = Field(..., description="Application version", example="1.0.0")
    docs_url: Optional[str] = Field(None, description="API documentation URL", example="/docs")
    health_check: str = Field(..., description="Health check endpoint", example="/api/v1/health")


# Auth response models
class TokenResponse(BaseModel):
    """Response model for authentication token."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type", example="bearer")
    expires_in: int = Field(..., description="Token expiration in seconds", example=3600)
    refresh_token: Optional[str] = Field(None, description="Refresh token if available")


class UserInfo(BaseModel):
    """User information model."""
    id: str = Field(..., description="User ID", example="user_123456789")
    email: str = Field(..., description="User email", example="user@example.com")
    name: str = Field(..., description="User display name", example="John Doe")
    picture: Optional[str] = Field(None, description="User profile picture URL")
    verified_email: bool = Field(..., description="Email verification status", example=True)


class AuthResponse(BaseModel):
    """Complete authentication response."""
    user: UserInfo = Field(..., description="Authenticated user information")
    tokens: TokenResponse = Field(..., description="Authentication tokens")


# Generic response models
class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Any] = Field(None, description="Response data")


class PaginationInfo(BaseModel):
    """Pagination information model."""
    page: int = Field(..., description="Current page number", example=1)
    per_page: int = Field(..., description="Items per page", example=20)
    total_items: int = Field(..., description="Total number of items", example=150)
    total_pages: int = Field(..., description="Total number of pages", example=8)
    has_next: bool = Field(..., description="Has next page", example=True)
    has_prev: bool = Field(..., description="Has previous page", example=False)


class PaginatedResponse(BaseModel):
    """Generic paginated response model."""
    data: List[Any] = Field(..., description="Response data items")
    pagination: PaginationInfo = Field(..., description="Pagination information")


# Rate limiting response models
class RateLimitHeaders(BaseModel):
    """Rate limiting headers model."""
    limit: int = Field(..., description="Rate limit", example=100)
    remaining: int = Field(..., description="Remaining requests", example=95)
    reset: int = Field(..., description="Rate limit reset timestamp", example=1705316400)


class RateLimitResponse(BaseModel):
    """Rate limit exceeded response."""
    error: str = Field(..., description="Error message", example="Rate limit exceeded")
    retry_after: int = Field(..., description="Retry after seconds", example=60)
    limit_info: RateLimitHeaders = Field(..., description="Rate limit information")