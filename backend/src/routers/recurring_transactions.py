"""
Recurring transaction management endpoints for Financial Nomad API.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
import structlog

from ..models.financial import (
    RecurringTransactionCreateRequest,
    RecurringTransactionUpdateRequest,
    RecurringTransactionResponse,
    RecurringTransactionSummary
)
from ..models.auth import User
from ..services.recurring_transaction import RecurringTransactionService, get_recurring_transaction_service
from ..routers.auth import get_current_user
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError, BusinessLogicError

logger = structlog.get_logger()

router = APIRouter(
    prefix="/recurring-transactions",
    tags=["recurring-transactions"]
)


@router.post("/", response_model=RecurringTransactionResponse)
async def create_recurring_transaction(
    request: RecurringTransactionCreateRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    service: RecurringTransactionService = Depends(get_recurring_transaction_service)
) -> RecurringTransactionResponse:
    """Create a new recurring transaction."""
    try:
        current_user, _ = current_user_tuple
        recurring = await service.create_recurring_transaction(current_user.id, request)
        return recurring
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error creating recurring transaction", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{recurring_id}", response_model=RecurringTransactionResponse)
async def get_recurring_transaction(
    recurring_id: str,
    current_user_tuple: tuple = Depends(get_current_user),
    service: RecurringTransactionService = Depends(get_recurring_transaction_service)
) -> RecurringTransactionResponse:
    """Get recurring transaction by ID."""
    try:
        current_user, _ = current_user_tuple
        recurring = await service.get_recurring_transaction(current_user.id, recurring_id)
        return recurring
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error retrieving recurring transaction", 
                    user_id=current_user.id, recurring_id=recurring_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[RecurringTransactionSummary])
async def list_recurring_transactions(
    current_user_tuple: tuple = Depends(get_current_user),
    service: RecurringTransactionService = Depends(get_recurring_transaction_service),
    active_only: bool = Query(False, description="Filter only active recurring transactions")
) -> List[RecurringTransactionSummary]:
    """List user recurring transactions."""
    try:
        current_user, _ = current_user_tuple
        recurring_transactions = await service.list_recurring_transactions(
            current_user.id, 
            active_only=active_only
        )
        return recurring_transactions
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error listing recurring transactions", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{recurring_id}", response_model=RecurringTransactionResponse)
async def update_recurring_transaction(
    recurring_id: str,
    request: RecurringTransactionUpdateRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    service: RecurringTransactionService = Depends(get_recurring_transaction_service)
) -> RecurringTransactionResponse:
    """Update recurring transaction."""
    try:
        current_user, _ = current_user_tuple
        recurring = await service.update_recurring_transaction(current_user.id, recurring_id, request)
        return recurring
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error updating recurring transaction", 
                    user_id=current_user.id, recurring_id=recurring_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{recurring_id}")
async def delete_recurring_transaction(
    recurring_id: str,
    current_user_tuple: tuple = Depends(get_current_user),
    service: RecurringTransactionService = Depends(get_recurring_transaction_service)
):
    """Delete recurring transaction (soft delete)."""
    try:
        current_user, _ = current_user_tuple
        await service.delete_recurring_transaction(current_user.id, recurring_id)
        return {"message": "Recurring transaction deleted successfully"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error deleting recurring transaction", 
                    user_id=current_user.id, recurring_id=recurring_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/execute")
async def execute_due_recurring_transactions(
    background_tasks: BackgroundTasks,
    current_user_tuple: tuple = Depends(get_current_user),
    service: RecurringTransactionService = Depends(get_recurring_transaction_service)
):
    """Execute recurring transactions that are due."""
    try:
        current_user, _ = current_user_tuple
        
        # Run in background to avoid blocking the request
        def execute_transactions():
            import asyncio
            
            async def _execute():
                try:
                    return await service.execute_due_recurring_transactions(current_user.id)
                except Exception as e:
                    logger.error("Background execution failed", user_id=current_user.id, error=str(e))
                    return []
            
            return asyncio.run(_execute())
        
        background_tasks.add_task(execute_transactions)
        
        return {"message": "Recurring transactions execution started"}
        
    except Exception as e:
        logger.error("Unexpected error executing recurring transactions", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")