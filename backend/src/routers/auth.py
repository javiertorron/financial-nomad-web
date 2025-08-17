"""
Authentication endpoints with Google OAuth integration.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.auth import (
    LoginRequest,
    LoginResponse,
    UserProfile,
    UserPreferencesUpdate,
    InvitationRequest,
    InvitationResponse,
)
from ..services import get_auth_service, AuthService
from ..utils.exceptions import AuthenticationError, NotFoundError, ValidationError

router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> tuple:
    """Get current authenticated user from JWT token."""
    try:
        token = credentials.credentials
        user, session = await auth_service.verify_jwt_token(token)
        return user, session
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/login", status_code=status.HTTP_200_OK, response_model=LoginResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> LoginResponse:
    """
    Authenticate user with Google OAuth token.
    
    For new users, an invitation code is required unless there's
    an existing invitation for the email address.
    """
    try:
        return await auth_service.login(request)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: tuple = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> None:
    """Logout current user by invalidating session."""
    user, session = current_user
    await auth_service.logout(session)


@router.get("/profile", status_code=status.HTTP_200_OK, response_model=UserProfile)
async def get_profile(
    current_user: tuple = Depends(get_current_user)
) -> UserProfile:
    """Get current user profile."""
    user, _ = current_user
    
    return UserProfile(
        id=user.google_id,
        email=user.email,
        name=user.name,
        picture=user.picture,
        role=user.role,
        status=user.status,
        locale=user.locale,
        timezone=user.timezone,
        currency=user.currency,
        last_login=user.last_login,
        has_asana_integration=bool(user.asana_access_token)
    )


@router.put("/profile", status_code=status.HTTP_200_OK, response_model=UserProfile)
async def update_profile(
    preferences: UserPreferencesUpdate,
    current_user: tuple = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserProfile:
    """Update user preferences."""
    user, _ = current_user
    
    # Update user preferences
    if preferences.locale is not None:
        user.locale = preferences.locale
    if preferences.timezone is not None:
        user.timezone = preferences.timezone
    if preferences.currency is not None:
        user.currency = preferences.currency
    
    user.update_timestamp()
    
    # Save to database
    firestore = auth_service.firestore
    await firestore.update_document(
        collection="users",
        document_id=user.google_id,
        data=user
    )
    
    return UserProfile(
        id=user.google_id,
        email=user.email,
        name=user.name,
        picture=user.picture,
        role=user.role,
        status=user.status,
        locale=user.locale,
        timezone=user.timezone,
        currency=user.currency,
        last_login=user.last_login,
        has_asana_integration=bool(user.asana_access_token)
    )


@router.post("/invite", status_code=status.HTTP_201_CREATED, response_model=InvitationResponse)
async def create_invitation(
    request: InvitationRequest,
    current_user: tuple = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> InvitationResponse:
    """
    Create a new user invitation.
    
    Only authenticated users can send invitations.
    """
    user, _ = current_user
    
    try:
        invitation = await auth_service.create_invitation(
            email=request.email,
            invited_by=user.google_id,
            expires_in_days=request.expires_in_days,
            suggested_name=request.suggested_name,
            message=request.message
        )
        
        return InvitationResponse(
            id=str(invitation.id),
            email=invitation.email,
            invitation_code=invitation.invitation_code,
            expires_at=invitation.expires_at,
            invited_by_name=user.name
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all_sessions(
    current_user: tuple = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> None:
    """Logout from all sessions (invalidate all user sessions)."""
    user, _ = current_user
    await auth_service.invalidate_all_user_sessions(user.google_id)


@router.get("/verify", status_code=status.HTTP_200_OK)
async def verify_token(
    current_user: tuple = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Verify if the current token is valid.
    
    This endpoint can be used by the frontend to check
    if the user is still authenticated.
    """
    user, session = current_user
    
    return {
        "valid": True,
        "user_id": user.google_id,
        "email": user.email,
        "expires_at": session.expires_at.isoformat()
    }