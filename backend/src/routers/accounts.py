"""
Account management endpoints.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Header

from ..models.auth import User
from ..models.financial import (
    AccountCreateRequest,
    AccountUpdateRequest,
    AccountResponse,
    AccountSummary
)
from ..services.account import get_account_service, AccountService
from ..services.auth import get_auth_service
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError, AuthenticationError

router = APIRouter(prefix="/accounts", tags=["accounts"])


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
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Account",
    description="Create a new financial account for the authenticated user."
)
async def create_account(
    request: AccountCreateRequest,
    current_user: User = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service)
) -> AccountResponse:
    """Create a new account."""
    try:
        return await account_service.create_account(current_user.id, request)
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
    response_model=List[AccountSummary],
    summary="List Accounts",
    description="Get a list of accounts for the authenticated user."
)
async def list_accounts(
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service)
) -> List[AccountSummary]:
    """List user accounts."""
    try:
        return await account_service.list_accounts(current_user.id, active_only)
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
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get Account",
    description="Get details of a specific account."
)
async def get_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service)
) -> AccountResponse:
    """Get account by ID."""
    try:
        return await account_service.get_account(current_user.id, account_id)
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
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update Account",
    description="Update an existing account."
)
async def update_account(
    account_id: str,
    request: AccountUpdateRequest,
    current_user: User = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service)
) -> AccountResponse:
    """Update account."""
    try:
        return await account_service.update_account(current_user.id, account_id, request)
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
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Account",
    description="Soft delete an account (marks as inactive)."
)
async def delete_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service)
) -> None:
    """Delete account (soft delete)."""
    try:
        await account_service.delete_account(current_user.id, account_id)
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