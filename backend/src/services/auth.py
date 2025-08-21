"""
Authentication service with Google OAuth integration and JWT handling.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import uuid4

import jwt
import structlog
from google.auth.transport import requests
from google.oauth2 import id_token
from pydantic import ValidationError

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.auth import (
    GoogleOAuthResponse,
    Invitation,
    LoginRequest,
    LoginResponse,
    Session,
    User,
    UserProfile,
    UserRole,
    UserStatus,
)
from ..utils.exceptions import AuthenticationError, NotFoundError, ValidationError as AppValidationError

logger = structlog.get_logger()


class AuthService:
    """Authentication service with Google OAuth and session management."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
    
    async def verify_google_token(self, token: str) -> GoogleOAuthResponse:
        """Verify Google OAuth token and extract user information."""
        try:
            # Verify the token with Google
            id_info = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                self.settings.google_client_id
            )
            
            # Check if token is valid
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise AuthenticationError(
                    message="Invalid token issuer",
                    code="INVALID_TOKEN_ISSUER"
                )
            
            return GoogleOAuthResponse(
                google_id=id_info['sub'],
                email=id_info['email'],
                name=id_info['name'],
                picture=id_info.get('picture'),
                email_verified=id_info.get('email_verified', False)
            )
            
        except ValueError as e:
            logger.error("Google token verification failed", error=str(e))
            raise AuthenticationError(
                message="Invalid Google token",
                code="INVALID_GOOGLE_TOKEN",
                details=[str(e)]
            )
        except Exception as e:
            logger.error("Unexpected error verifying Google token", error=str(e))
            raise AuthenticationError(
                message="Authentication failed",
                code="AUTHENTICATION_FAILED",
                details=[str(e)]
            )
    
    async def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID."""
        try:
            users = await self.firestore.query_documents(
                collection="users",
                model_class=User,
                where_clauses=[("google_id", "==", google_id)]
            )
            return users[0] if users else None
        except Exception as e:
            logger.error("Failed to get user by Google ID", google_id=google_id, error=str(e))
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            users = await self.firestore.query_documents(
                collection="users",
                model_class=User,
                where_clauses=[("email", "==", email)]
            )
            return users[0] if users else None
        except Exception as e:
            logger.error("Failed to get user by email", email=email, error=str(e))
            return None
    
    async def validate_invitation(self, invitation_code: str) -> Invitation:
        """Validate and get invitation by code."""
        try:
            invitations = await self.firestore.query_documents(
                collection="invitations",
                model_class=Invitation,
                where_clauses=[
                    ("invitation_code", "==", invitation_code),
                    ("is_used", "==", False)
                ]
            )
            
            if not invitations:
                raise AuthenticationError(
                    message="Invalid or expired invitation code",
                    code="INVALID_INVITATION"
                )
            
            invitation = invitations[0]
            
            # Check if invitation is expired
            if invitation.expires_at < datetime.utcnow():
                raise AuthenticationError(
                    message="Invitation has expired",
                    code="INVITATION_EXPIRED"
                )
            
            return invitation
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Failed to validate invitation", code=invitation_code, error=str(e))
            raise AuthenticationError(
                message="Failed to validate invitation",
                code="INVITATION_VALIDATION_FAILED",
                details=[str(e)]
            )
    
    async def create_user(
        self,
        google_oauth: GoogleOAuthResponse,
        invitation: Optional[Invitation] = None
    ) -> User:
        """Create a new user account."""
        try:
            user = User(
                google_id=google_oauth.google_id,
                email=google_oauth.email,
                name=google_oauth.name,
                picture=google_oauth.picture,
                status=UserStatus.ACTIVE if invitation else UserStatus.PENDING,
                role=UserRole.USER,
                invited_by=invitation.invited_by if invitation else None,
                invitation_code=invitation.invitation_code if invitation else None
            )
            
            # Save user to database
            await self.firestore.create_document(
                collection="users",
                document_id=user.google_id,
                data=user
            )
            
            # Mark invitation as used if provided
            if invitation:
                invitation.is_used = True
                invitation.used_by = user.google_id
                invitation.used_at = datetime.utcnow()
                
                await self.firestore.update_document(
                    collection="invitations",
                    document_id=str(invitation.id),
                    data=invitation
                )
            
            logger.info(
                "User created successfully",
                user_id=user.google_id,
                email=user.email,
                invited=invitation is not None
            )
            
            return user
            
        except Exception as e:
            logger.error("Failed to create user", email=google_oauth.email, error=str(e))
            raise AuthenticationError(
                message="Failed to create user account",
                code="USER_CREATION_FAILED",
                details=[str(e)]
            )
    
    async def create_session(self, user: User) -> Session:
        """Create a new user session."""
        try:
            session = Session(
                user_id=user.google_id,
                jti=str(uuid4()),
                expires_at=datetime.utcnow() + timedelta(hours=self.settings.session_expire_hours),
                is_active=True
            )
            
            await self.firestore.create_document(
                collection="sessions",
                document_id=str(session.id),
                data=session
            )
            
            logger.info(
                "Session created",
                user_id=user.google_id,
                session_id=str(session.id),
                expires_at=session.expires_at.isoformat()
            )
            
            return session
            
        except Exception as e:
            logger.error("Failed to create session", user_id=user.google_id, error=str(e))
            raise AuthenticationError(
                message="Failed to create session",
                code="SESSION_CREATION_FAILED",
                details=[str(e)]
            )
    
    async def generate_jwt_token(self, user: User, session: Session) -> str:
        """Generate JWT access token."""
        try:
            payload = {
                "sub": user.google_id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "status": user.status.value,
                "jti": session.jti,
                "iat": datetime.utcnow(),
                "exp": session.expires_at,
                "iss": self.settings.app_name,
                "aud": "financial-nomad-api-client"
            }
            
            token = jwt.encode(
                payload,
                self.settings.secret_key,
                algorithm="HS256"
            )
            
            return token
            
        except Exception as e:
            logger.error("Failed to generate JWT token", user_id=user.google_id, error=str(e))
            raise AuthenticationError(
                message="Failed to generate access token",
                code="TOKEN_GENERATION_FAILED",
                details=[str(e)]
            )
    
    async def verify_jwt_token(self, token: str) -> Tuple[User, Session]:
        """Verify JWT token and return user and session."""
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=["HS256"],
                audience="financial-nomad-api-client",
                issuer=self.settings.app_name
            )
            
            # Get user
            user = await self.get_user_by_google_id(payload["sub"])
            if not user:
                raise AuthenticationError(
                    message="User not found",
                    code="USER_NOT_FOUND"
                )
            
            # Get session
            sessions = await self.firestore.query_documents(
                collection="sessions",
                model_class=Session,
                where_clauses=[
                    ("user_id", "==", user.google_id),
                    ("jti", "==", payload["jti"]),
                    ("is_active", "==", True)
                ]
            )
            
            if not sessions:
                raise AuthenticationError(
                    message="Session not found or expired",
                    code="SESSION_NOT_FOUND"
                )
            
            session = sessions[0]
            
            # Check session expiration
            if session.expires_at < datetime.utcnow():
                await self.invalidate_session(session)
                raise AuthenticationError(
                    message="Session has expired",
                    code="SESSION_EXPIRED"
                )
            
            # Update last activity
            session.last_activity = datetime.utcnow()
            await self.firestore.update_document(
                collection="sessions",
                document_id=str(session.id),
                data=session
            )
            
            return user, session
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError(
                message="Token has expired",
                code="TOKEN_EXPIRED"
            )
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(
                message="Invalid token",
                code="INVALID_TOKEN",
                details=[str(e)]
            )
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Failed to verify JWT token", error=str(e))
            raise AuthenticationError(
                message="Token verification failed",
                code="TOKEN_VERIFICATION_FAILED",
                details=[str(e)]
            )
    
    async def login(self, request: LoginRequest) -> LoginResponse:
        """Authenticate user with Google token and return JWT."""
        try:
            # Verify Google token
            google_oauth = await self.verify_google_token(request.google_token)
            
            # Check if user exists
            user = await self.get_user_by_google_id(google_oauth.google_id)
            
            if not user:
                # New user - validate invitation if provided
                invitation = None
                if request.invitation_code:
                    invitation = await self.validate_invitation(request.invitation_code)
                else:
                    # Check if there's an invitation for this email
                    invitations = await self.firestore.query_documents(
                        collection="invitations",
                        model_class=Invitation,
                        where_clauses=[
                            ("email", "==", google_oauth.email),
                            ("is_used", "==", False)
                        ]
                    )
                    if invitations:
                        invitation = invitations[0]
                        # Validate expiration
                        if invitation.expires_at < datetime.utcnow():
                            raise AuthenticationError(
                                message="Invitation has expired",
                                code="INVITATION_EXPIRED"
                            )
                
                if not invitation:
                    raise AuthenticationError(
                        message="Registration requires a valid invitation",
                        code="INVITATION_REQUIRED"
                    )
                
                # Create new user
                user = await self.create_user(google_oauth, invitation)
            
            # Check user status
            if user.status == UserStatus.SUSPENDED:
                raise AuthenticationError(
                    message="Account has been suspended",
                    code="ACCOUNT_SUSPENDED"
                )
            elif user.status == UserStatus.INACTIVE:
                raise AuthenticationError(
                    message="Account is inactive",
                    code="ACCOUNT_INACTIVE"
                )
            
            # Update user login information
            user.last_login = datetime.utcnow()
            user.login_count += 1
            
            await self.firestore.update_document(
                collection="users",
                document_id=user.google_id,
                data=user
            )
            
            # Create session
            session = await self.create_session(user)
            
            # Generate JWT token
            access_token = await self.generate_jwt_token(user, session)
            
            # Prepare response
            user_profile = UserProfile(
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
            
            response = LoginResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=int(self.settings.session_expire_hours * 3600),  # seconds
                user=user_profile
            )
            
            logger.info(
                "User logged in successfully",
                user_id=user.google_id,
                email=user.email,
                is_new_user=user.login_count == 1
            )
            
            return response
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Login failed", error=str(e))
            raise AuthenticationError(
                message="Login failed",
                code="LOGIN_FAILED",
                details=[str(e)]
            )
    
    async def logout(self, session: Session) -> None:
        """Logout user by invalidating session."""
        await self.invalidate_session(session)
        logger.info("User logged out", user_id=session.user_id, session_id=str(session.id))
    
    async def invalidate_session(self, session: Session) -> None:
        """Invalidate a user session."""
        try:
            session.is_active = False
            await self.firestore.update_document(
                collection="sessions",
                document_id=str(session.id),
                data=session
            )
        except Exception as e:
            logger.error("Failed to invalidate session", session_id=str(session.id), error=str(e))
    
    async def invalidate_all_user_sessions(self, user_id: str) -> None:
        """Invalidate all sessions for a user."""
        try:
            sessions = await self.firestore.query_documents(
                collection="sessions",
                model_class=Session,
                where_clauses=[
                    ("user_id", "==", user_id),
                    ("is_active", "==", True)
                ]
            )
            
            for session in sessions:
                await self.invalidate_session(session)
            
            logger.info("All user sessions invalidated", user_id=user_id, count=len(sessions))
            
        except Exception as e:
            logger.error("Failed to invalidate user sessions", user_id=user_id, error=str(e))
    
    async def create_invitation(
        self,
        email: str,
        invited_by: str,
        expires_in_days: int = 7,
        suggested_name: Optional[str] = None,
        message: Optional[str] = None
    ) -> Invitation:
        """Create a new user invitation."""
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_email(email)
            if existing_user:
                raise AppValidationError(
                    message="User with this email already exists",
                    code="USER_ALREADY_EXISTS"
                )
            
            # Check for existing unused invitation
            existing_invitations = await self.firestore.query_documents(
                collection="invitations",
                model_class=Invitation,
                where_clauses=[
                    ("email", "==", email),
                    ("is_used", "==", False)
                ]
            )
            
            if existing_invitations:
                # Update existing invitation
                invitation = existing_invitations[0]
                invitation.invited_by = invited_by
                invitation.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
                invitation.suggested_name = suggested_name
                invitation.message = message
                invitation.invitation_code = secrets.token_urlsafe(32)
                
                await self.firestore.update_document(
                    collection="invitations",
                    document_id=str(invitation.id),
                    data=invitation
                )
            else:
                # Create new invitation
                invitation = Invitation(
                    email=email,
                    invited_by=invited_by,
                    invitation_code=secrets.token_urlsafe(32),
                    expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
                    suggested_name=suggested_name,
                    message=message
                )
                
                await self.firestore.create_document(
                    collection="invitations",
                    document_id=str(invitation.id),
                    data=invitation
                )
            
            logger.info(
                "Invitation created",
                email=email,
                invited_by=invited_by,
                expires_at=invitation.expires_at.isoformat()
            )
            
            return invitation
            
        except AppValidationError:
            raise
        except Exception as e:
            logger.error("Failed to create invitation", email=email, error=str(e))
            raise AppValidationError(
                message="Failed to create invitation",
                code="INVITATION_CREATION_FAILED",
                details=[str(e)]
            )


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service