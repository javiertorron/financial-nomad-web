"""
Authentication and user models.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from .base import IdentifiedModel


class UserRole(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User(IdentifiedModel):
    """User model with email/password authentication."""
    
    # Authentication data
    email: EmailStr
    password_hash: str = Field(..., description="Bcrypt hashed password")
    name: str = Field(..., min_length=1, max_length=100)
    picture: Optional[str] = Field(None, description="Profile picture URL")
    
    # System data
    role: UserRole = Field(default=UserRole.USER)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    
    # Preferences
    locale: str = Field(default="es-ES", max_length=5)
    timezone: str = Field(default="Europe/Madrid", max_length=50)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    
    # Access control
    last_login: Optional[datetime] = None
    login_count: int = Field(default=0)
    
    # Invitation system
    invited_by: Optional[str] = Field(None, description="User ID who sent invitation")
    invitation_code: Optional[str] = Field(None, description="Invitation code used")
    
    # Asana integration (optional)
    asana_access_token: Optional[str] = Field(None, description="Encrypted Asana token")
    asana_refresh_token: Optional[str] = Field(None, description="Encrypted Asana refresh token")
    asana_workspace_id: Optional[str] = Field(None, description="Selected Asana workspace")
    
    model_config = ConfigDict(
        # For Pydantic v2, use model_config instead of Config class
        extra="forbid"
    )


class Invitation(IdentifiedModel):
    """User invitation model."""
    
    email: EmailStr
    invited_by: str = Field(..., description="User ID who sent invitation")
    invitation_code: str = Field(..., description="Unique invitation code")
    
    # Status
    is_used: bool = Field(default=False)
    used_by: Optional[str] = Field(None, description="User ID who used invitation")
    used_at: Optional[datetime] = None
    
    # Expiration
    expires_at: datetime
    
    # Optional user data
    suggested_name: Optional[str] = Field(None, max_length=100)
    message: Optional[str] = Field(None, max_length=500)


class Session(IdentifiedModel):
    """User session model for JWT tracking."""
    
    user_id: str = Field(..., description="User ID")
    jti: str = Field(..., description="JWT ID for token tracking")
    
    # Session metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Session lifecycle
    expires_at: datetime
    is_active: bool = Field(default=True)
    last_activity: datetime = Field(default_factory=datetime.utcnow)


# DTOs for API requests/responses
class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=100)
    invitation_code: str = Field(..., description="Required invitation code")


class LoginRequest(BaseModel):
    """Login request with email/password."""
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    """Login response with JWT and user data."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserProfile"


class UserProfile(BaseModel):
    """User profile for API responses."""
    id: str
    email: EmailStr
    name: str
    picture: Optional[str]
    role: UserRole
    status: UserStatus
    locale: str
    timezone: str
    currency: str
    last_login: Optional[datetime]
    has_asana_integration: bool = Field(default=False)


class RegisterResponse(BaseModel):
    """Registration response."""
    message: str
    user_id: str


class UserPreferencesUpdate(BaseModel):
    """User preferences update request."""
    locale: Optional[str] = Field(None, max_length=5)
    timezone: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)


class InvitationRequest(BaseModel):
    """Request to create a new invitation."""
    email: EmailStr
    suggested_name: Optional[str] = Field(None, max_length=100)
    message: Optional[str] = Field(None, max_length=500)
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationResponse(BaseModel):
    """Response with invitation details."""
    id: str
    email: EmailStr
    invitation_code: str
    expires_at: datetime
    invited_by_name: str


# Update forward references for Pydantic v2
LoginResponse.model_rebuild()