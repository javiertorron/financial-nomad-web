"""
Category management endpoints.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header, Query

from ..models.auth import User
from ..models.financial import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    CategoryResponse,
    CategorySummary
)
from ..services.category import get_category_service, CategoryService
from ..services.auth import get_auth_service
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError, AuthenticationError

router = APIRouter(prefix="/categories", tags=["categories"])


async def get_current_user(authorization: str = Header(None)) -> User:
    """Get current authenticated user from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format"
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    try:
        auth_service = get_auth_service()
        user, session = await auth_service.verify_jwt_token(token)
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": e.code,
                "message": e.message
            }
        )


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Category",
    description="Create a new financial category for the authenticated user."
)
async def create_category(
    request: CategoryCreateRequest,
    current_user: User = Depends(get_current_user),
    category_service: CategoryService = Depends(get_category_service)
) -> CategoryResponse:
    """Create a new category."""
    try:
        return await category_service.create_category(current_user.id, request)
    except AppValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )


@router.get(
    "/",
    response_model=List[CategorySummary],
    summary="List Categories",
    description="Get a list of categories for the authenticated user with optional filters."
)
async def list_categories(
    category_type: Optional[str] = Query(None, description="Filter by category type (income/expense)"),
    parent_id: Optional[str] = Query(None, description="Filter by parent category ID"),
    active_only: bool = Query(False, description="Show only active categories"),
    current_user: User = Depends(get_current_user),
    category_service: CategoryService = Depends(get_category_service)
) -> List[CategorySummary]:
    """List user categories with optional filters."""
    try:
        return await category_service.list_categories(
            current_user.id, 
            category_type=category_type,
            parent_id=parent_id,
            active_only=active_only
        )
    except AppValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get Category",
    description="Get details of a specific category."
)
async def get_category(
    category_id: str,
    current_user: User = Depends(get_current_user),
    category_service: CategoryService = Depends(get_category_service)
) -> CategoryResponse:
    """Get category by ID."""
    try:
        return await category_service.get_category(current_user.id, category_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": e.code,
                "message": e.message
            }
        )
    except AppValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update Category",
    description="Update an existing category."
)
async def update_category(
    category_id: str,
    request: CategoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    category_service: CategoryService = Depends(get_category_service)
) -> CategoryResponse:
    """Update category."""
    try:
        return await category_service.update_category(current_user.id, category_id, request)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": e.code,
                "message": e.message
            }
        )
    except AppValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Category",
    description="Soft delete a category (marks as inactive). Cannot delete system categories or categories with subcategories."
)
async def delete_category(
    category_id: str,
    current_user: User = Depends(get_current_user),
    category_service: CategoryService = Depends(get_category_service)
) -> None:
    """Delete category (soft delete)."""
    try:
        await category_service.delete_category(current_user.id, category_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": e.code,
                "message": e.message
            }
        )
    except AppValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )