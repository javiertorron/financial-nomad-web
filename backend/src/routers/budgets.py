"""
Budget management endpoints for Financial Nomad API.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
import structlog

from ..models.financial import (
    BudgetCreateRequest,
    BudgetUpdateRequest,
    BudgetResponse,
    BudgetSummary
)
from ..models.auth import User
from ..services.budget import BudgetService, get_budget_service
from ..routers.auth import get_current_user
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError, BusinessLogicError

logger = structlog.get_logger()

router = APIRouter(
    prefix="/budgets",
    tags=["budgets"]
)


@router.post("/", response_model=BudgetResponse)
async def create_budget(
    request: BudgetCreateRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    budget_service: BudgetService = Depends(get_budget_service)
) -> BudgetResponse:
    """Create a new budget."""
    try:
        current_user, _ = current_user_tuple
        budget = await budget_service.create_budget(current_user.id, request)
        return budget
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error creating budget", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str,
    current_user_tuple: tuple = Depends(get_current_user),
    budget_service: BudgetService = Depends(get_budget_service)
) -> BudgetResponse:
    """Get budget by ID."""
    try:
        current_user, _ = current_user_tuple
        budget = await budget_service.get_budget(current_user.id, budget_id)
        return budget
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error retrieving budget", 
                    user_id=current_user.id, budget_id=budget_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[BudgetSummary])
async def list_budgets(
    current_user_tuple: tuple = Depends(get_current_user),
    budget_service: BudgetService = Depends(get_budget_service),
    active_only: bool = Query(False, description="Filter only active budgets"),
    category_id: Optional[str] = Query(None, description="Filter by category ID")
) -> List[BudgetSummary]:
    """List user budgets."""
    try:
        current_user, _ = current_user_tuple
        budgets = await budget_service.list_budgets(
            current_user.id, 
            active_only=active_only,
            category_id=category_id
        )
        return budgets
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error listing budgets", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    request: BudgetUpdateRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    budget_service: BudgetService = Depends(get_budget_service)
) -> BudgetResponse:
    """Update budget."""
    try:
        current_user, _ = current_user_tuple
        budget = await budget_service.update_budget(current_user.id, budget_id, request)
        return budget
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error updating budget", 
                    user_id=current_user.id, budget_id=budget_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{budget_id}")
async def delete_budget(
    budget_id: str,
    current_user_tuple: tuple = Depends(get_current_user),
    budget_service: BudgetService = Depends(get_budget_service)
):
    """Delete budget (soft delete)."""
    try:
        current_user, _ = current_user_tuple
        await budget_service.delete_budget(current_user.id, budget_id)
        return {"message": "Budget deleted successfully"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error deleting budget", 
                    user_id=current_user.id, budget_id=budget_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")