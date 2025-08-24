"""
Transaction management endpoints.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header, Query

from ..models.auth import User
from ..models.financial import (
    TransactionCreateRequest,
    TransactionUpdateRequest,
    TransactionResponse,
    TransactionSummary
)
from ..services.transaction import get_transaction_service, TransactionService
from ..services.auth import get_auth_service
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError, AuthenticationError

router = APIRouter(prefix="/transactions", tags=["transactions"])


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
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Transaction",
    description="Create a new financial transaction for the authenticated user."
)
async def create_transaction(
    request: TransactionCreateRequest,
    current_user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> TransactionResponse:
    """Create a new transaction."""
    try:
        return await transaction_service.create_transaction(current_user.id, request)
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
    response_model=List[TransactionSummary],
    summary="List Transactions",
    description="Get a list of transactions for the authenticated user with optional filters."
)
async def list_transactions(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    start_date: Optional[datetime] = Query(None, description="Filter transactions from this date (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="Filter transactions until this date (inclusive)"),
    active_only: bool = Query(False, description="Show only active transactions"),
    limit: Optional[int] = Query(50, ge=1, le=1000, description="Maximum number of transactions to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of transactions to skip"),
    current_user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> List[TransactionSummary]:
    """List user transactions with optional filters."""
    try:
        return await transaction_service.list_transactions(
            current_user.id,
            account_id=account_id,
            category_id=category_id,
            start_date=start_date,
            end_date=end_date,
            active_only=active_only,
            limit=limit,
            offset=offset
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
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get Transaction",
    description="Get details of a specific transaction."
)
async def get_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> TransactionResponse:
    """Get transaction by ID."""
    try:
        return await transaction_service.get_transaction(current_user.id, transaction_id)
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
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Update Transaction",
    description="Update an existing transaction."
)
async def update_transaction(
    transaction_id: str,
    request: TransactionUpdateRequest,
    current_user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> TransactionResponse:
    """Update transaction."""
    try:
        return await transaction_service.update_transaction(current_user.id, transaction_id, request)
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
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Transaction",
    description="Soft delete a transaction (marks as inactive)."
)
async def delete_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service)
) -> None:
    """Delete transaction (soft delete)."""
    try:
        await transaction_service.delete_transaction(current_user.id, transaction_id)
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