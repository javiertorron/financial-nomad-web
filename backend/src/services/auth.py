"""
Authentication service with email/password authentication and JWT handling.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import uuid4

import jwt
import structlog
from passlib.context import CryptContext
from pydantic import ValidationError

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.auth import (
    Invitation,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    Session,
    User,
    UserProfile,
    UserRole,
    UserStatus,
)
from ..utils.exceptions import AuthenticationError, NotFoundError, ValidationError as AppValidationError

logger = structlog.get_logger()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service with email/password and session management."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            user = await self.firestore.get_document(
                collection="users",
                document_id=user_id,
                model_class=User
            )
            return user
        except Exception as e:
            logger.error("Failed to get user by ID", user_id=user_id, error=str(e))
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
    
    async def validate_invitation(self, invitation_code: str, email: str) -> Invitation:
        """Validate invitation by code and email."""
        try:
            invitations = await self.firestore.query_documents(
                collection="invitations",
                model_class=Invitation,
                where_clauses=[
                    ("invitation_code", "==", invitation_code),
                    ("email", "==", email),
                    ("is_used", "==", False)
                ]
            )
            
            if not invitations:
                raise AuthenticationError(
                    message="Invalid invitation code for this email",
                    code="INVALID_INVITATION"
                )
            
            invitation = invitations[0]
            
            # Check if invitation is expired (ensure timezone consistency)
            now = datetime.utcnow()
            expires_at = invitation.expires_at.replace(tzinfo=None) if invitation.expires_at.tzinfo else invitation.expires_at
            if expires_at < now:
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
        email: str,
        password: str,
        name: str,
        invitation: Invitation
    ) -> User:
        """Create a new user account."""
        try:
            # Hash password
            password_hash = self.hash_password(password)
            
            user = User(
                email=email,
                password_hash=password_hash,
                name=name,
                status=UserStatus.ACTIVE,
                role=UserRole.USER,
                invited_by=invitation.invited_by,
                invitation_code=invitation.invitation_code
            )
            
            # Generate user ID and save user to database
            user_id = str(uuid4())
            await self.firestore.create_document(
                collection="users",
                document_id=user_id,
                data=user
            )
            # Set the ID for return
            user.id = user_id
            
            # Mark invitation as used
            invitation.is_used = True
            invitation.used_by = user_id
            invitation.used_at = datetime.utcnow()
            
            await self.firestore.update_document(
                collection="invitations",
                document_id=str(invitation.id),
                data=invitation
            )
            
            logger.info(
                "User created successfully",
                user_id=user_id,
                email=user.email
            )
            
            return user
            
        except Exception as e:
            logger.error("Failed to create user", email=email, error=str(e))
            raise AuthenticationError(
                message="Failed to create user account",
                code="USER_CREATION_FAILED",
                details=[str(e)]
            )
    
    async def create_master_user(self) -> User:
        """Create the master admin user."""
        try:
            master_email = "javier.torron.diaz@gmail.com"
            master_password = "fI07.08511982#"
            
            # Check if master user already exists
            existing_user = await self.get_user_by_email(master_email)
            if existing_user:
                logger.info("Master user already exists")
                return existing_user
            
            # Hash password
            password_hash = self.hash_password(master_password)
            
            user = User(
                email=master_email,
                password_hash=password_hash,
                name="Javier Torrón",
                status=UserStatus.ACTIVE,
                role=UserRole.ADMIN
            )
            
            # Generate user ID and save user to database
            user_id = str(uuid4())
            await self.firestore.create_document(
                collection="users",
                document_id=user_id,
                data=user
            )
            # Set the ID for return
            user.id = user_id
            
            logger.info(
                "Master user created successfully",
                user_id=user_id,
                email=user.email
            )
            
            return user
            
        except Exception as e:
            logger.error("Failed to create master user", error=str(e))
            raise AuthenticationError(
                message="Failed to create master user",
                code="MASTER_USER_CREATION_FAILED",
                details=[str(e)]
            )
    
    async def create_session(self, user: User) -> Session:
        """Create a new user session."""
        try:
            session = Session(
                user_id=str(user.id),
                jti=str(uuid4()),
                expires_at=datetime.utcnow() + timedelta(hours=24),  # 24 hour sessions
                is_active=True
            )
            
            await self.firestore.create_document(
                collection="sessions",
                document_id=str(session.id),
                data=session
            )
            
            logger.info(
                "Session created",
                user_id=str(user.id),
                session_id=str(session.id),
                expires_at=session.expires_at.isoformat()
            )
            
            return session
            
        except Exception as e:
            logger.error("Failed to create session", user_id=str(user.id), error=str(e))
            raise AuthenticationError(
                message="Failed to create session",
                code="SESSION_CREATION_FAILED",
                details=[str(e)]
            )
    
    async def generate_jwt_token(self, user: User, session: Session) -> str:
        """Generate JWT access token."""
        try:
            # Ensure all datetime objects are timezone-aware UTC
            now = datetime.utcnow()
            expires_at = session.expires_at.replace(tzinfo=None) if session.expires_at.tzinfo else session.expires_at
            
            payload = {
                "sub": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "status": user.status.value,
                "jti": session.jti,
                "iat": now,
                "exp": expires_at,
                "iss": self.settings.app_name,
                "aud": "financial-nomad-api-client"
            }
            
            token = jwt.encode(
                payload,
                self.settings.jwt_secret_key,
                algorithm="HS256"
            )
            
            return token
            
        except Exception as e:
            logger.error("Failed to generate JWT token", user_id=str(user.id), error=str(e))
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
                self.settings.jwt_secret_key,
                algorithms=["HS256"],
                audience="financial-nomad-api-client",
                issuer=self.settings.app_name
            )
            
            # Get user
            user = await self.get_user_by_id(payload["sub"])
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
                    ("user_id", "==", str(user.id)),
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
            
            # Check session expiration (ensure timezone consistency)
            now = datetime.utcnow()
            expires_at = session.expires_at.replace(tzinfo=None) if session.expires_at.tzinfo else session.expires_at
            if expires_at < now:
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
    
    async def register(self, request: RegisterRequest) -> RegisterResponse:
        """Register a new user with email/password."""
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_email(request.email)
            if existing_user:
                raise AuthenticationError(
                    message="User with this email already exists",
                    code="USER_ALREADY_EXISTS"
                )
            
            # Validate invitation
            invitation = await self.validate_invitation(request.invitation_code, request.email)
            
            # Create user
            user = await self.create_user(
                email=request.email,
                password=request.password,
                name=request.name,
                invitation=invitation
            )
            
            logger.info(
                "User registered successfully",
                user_id=str(user.id),
                email=user.email
            )
            
            return RegisterResponse(
                message="User registered successfully",
                user_id=str(user.id)
            )
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Registration failed", email=request.email, error=str(e))
            raise AuthenticationError(
                message="Registration failed",
                code="REGISTRATION_FAILED",
                details=[str(e)]
            )
    
    async def login(self, request: LoginRequest) -> LoginResponse:
        """Authenticate user with email/password and return JWT."""
        try:
            # Get user by email
            user = await self.get_user_by_email(request.email)
            if not user:
                raise AuthenticationError(
                    message="Invalid email or password",
                    code="INVALID_CREDENTIALS"
                )
            
            # Verify password
            if not self.verify_password(request.password, user.password_hash):
                raise AuthenticationError(
                    message="Invalid email or password",
                    code="INVALID_CREDENTIALS"
                )
            
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
                document_id=str(user.id),
                data=user
            )
            
            # Create session
            session = await self.create_session(user)
            
            # Generate JWT token
            access_token = await self.generate_jwt_token(user, session)
            
            # Prepare response
            user_profile = UserProfile(
                id=str(user.id),
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
                expires_in=24 * 3600,  # 24 hours in seconds
                user=user_profile
            )
            
            logger.info(
                "User logged in successfully",
                user_id=str(user.id),
                email=user.email
            )
            
            return response
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Login failed", email=request.email, error=str(e))
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