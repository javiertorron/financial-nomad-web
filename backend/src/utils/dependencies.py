"""
Dependency injection utilities for FastAPI.
"""
from typing import Annotated
from fastapi import Depends

from ..models.auth import User, Session
from ..routers.auth import get_current_user

# Type aliases for dependency injection
CurrentUser = Annotated[tuple[User, Session], Depends(get_current_user)]