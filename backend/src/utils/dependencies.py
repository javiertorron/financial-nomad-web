"""
Dependency injection utilities for FastAPI.
"""
import sys
from typing import Dict, Any, Optional, Tuple
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import structlog

from ..models.auth import User, Session
from ..config import settings

# Python 3.8 compatibility
if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

logger = structlog.get_logger()
security = HTTPBearer(auto_error=False)

# Import here to avoid circular imports
def get_current_user_dependency():
    from ..routers.auth import get_current_user
    return get_current_user

async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current user from JWT token, but don't raise error if not authenticated.
    Returns None if no valid authentication is provided.
    """
    if not credentials:
        return None
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=["HS256"]
        )
        
        user_id = payload.get("sub")
        if not user_id:
            return None
            
        # Return basic user info from token
        return {
            "id": user_id,
            "email": payload.get("email"),
            "name": payload.get("name"),
            "authenticated": True
        }
        
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token", error=str(e))
        return None
    except Exception as e:
        logger.error("Error validating token", error=str(e))
        return None

# Type aliases for dependency injection  
if sys.version_info >= (3, 9):
    CurrentUser = Annotated[Tuple[User, Session], Depends(get_current_user_dependency)]
    OptionalCurrentUser = Annotated[Optional[Dict[str, Any]], Depends(get_current_user_optional)]
else:
    # Python 3.8 compatibility - use Tuple instead of tuple
    from typing import Tuple
    CurrentUser = Annotated[Tuple[User, Session], Depends(get_current_user_dependency)]
    OptionalCurrentUser = Annotated[Optional[Dict[str, Any]], Depends(get_current_user_optional)]