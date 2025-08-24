"""
Budget service for managing financial budgets.
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from decimal import Decimal

import structlog

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.financial import (
    Budget,
    BudgetCreateRequest,
    BudgetUpdateRequest,
    BudgetResponse,
    BudgetSummary,
    Category,
    Transaction,
    TransactionType
)
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError, BusinessLogicError

logger = structlog.get_logger()


class BudgetService:
    """Service for budget operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
    
    async def create_budget(self, user_id: str, request: BudgetCreateRequest) -> BudgetResponse:
        """Create a new budget."""
        try:
            # Validate category exists
            category = await self.firestore.get_document(
                collection=f"categories/{user_id}/user_categories",
                document_id=request.category_id,
                model_class=Category
            )
            
            if not category:
                raise NotFoundError(
                    message="Category not found",
                    resource_type="category",
                    resource_id=request.category_id
                )
            
            # Check for existing active budget for the same category and overlapping period
            existing_budgets = await self.firestore.query_documents(
                collection=f"budgets/{user_id}/user_budgets",
                model_class=Budget,
                where_clauses=[
                    ("category_id", "==", request.category_id),
                    ("is_active", "==", True)
                ]
            )
            
            for existing in existing_budgets:
                if self._periods_overlap(request.period_start, request.period_end, 
                                       existing.period_start, existing.period_end):
                    raise BusinessLogicError(
                        message="Active budget already exists for this category in overlapping period",
                        details=[f"Existing budget: {existing.name}"]
                    )
            
            # Create budget
            budget = Budget(
                user_id=user_id,
                name=request.name,
                category_id=request.category_id,
                amount=request.amount,
                period_start=request.period_start,
                period_end=request.period_end,
                alert_threshold=request.alert_threshold
            )
            
            # Generate budget ID and save
            budget_id = str(uuid4())
            budget.id = budget_id
            
            await self.firestore.create_document(
                collection=f"budgets/{user_id}/user_budgets",
                document_id=budget_id,
                data=budget
            )
            
            logger.info(
                "Budget created successfully",
                user_id=user_id,
                budget_id=budget_id,
                category_id=request.category_id,
                amount=float(budget.amount)
            )
            
            return BudgetResponse(
                id=budget.id,
                name=budget.name,
                category_id=budget.category_id,
                amount=budget.amount,
                period_start=budget.period_start,
                period_end=budget.period_end,
                spent_amount=budget.spent_amount,
                is_active=budget.is_active,
                alert_threshold=budget.alert_threshold,
                alert_sent=budget.alert_sent,
                created_at=budget.created_at,
                updated_at=budget.updated_at
            )
            
        except (NotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error("Failed to create budget", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to create budget",
                details=[str(e)]
            )
    
    async def get_budget(self, user_id: str, budget_id: str) -> BudgetResponse:
        """Get budget by ID."""
        try:
            budget = await self.firestore.get_document(
                collection=f"budgets/{user_id}/user_budgets",
                document_id=budget_id,
                model_class=Budget
            )
            
            if not budget:
                raise NotFoundError(
                    message="Budget not found",
                    resource_type="budget",
                    resource_id=budget_id
                )
            
            return BudgetResponse(
                id=budget.id,
                name=budget.name,
                category_id=budget.category_id,
                amount=budget.amount,
                period_start=budget.period_start,
                period_end=budget.period_end,
                spent_amount=budget.spent_amount,
                is_active=budget.is_active,
                alert_threshold=budget.alert_threshold,
                alert_sent=budget.alert_sent,
                created_at=budget.created_at,
                updated_at=budget.updated_at
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get budget", user_id=user_id, budget_id=budget_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve budget",
                details=[str(e)]
            )
    
    async def list_budgets(self, user_id: str, active_only: bool = False, 
                          category_id: Optional[str] = None) -> List[BudgetSummary]:
        """List user budgets."""
        try:
            where_clauses = []
            if active_only:
                where_clauses.append(("is_active", "==", True))
            if category_id:
                where_clauses.append(("category_id", "==", category_id))
            
            budgets = await self.firestore.query_documents(
                collection=f"budgets/{user_id}/user_budgets",
                model_class=Budget,
                where_clauses=where_clauses,
                order_by="period_start"
            )
            
            # Get category names for summaries
            categories = await self.firestore.query_documents(
                collection=f"categories/{user_id}/user_categories",
                model_class=Category
            )
            category_map = {cat.id: cat.name for cat in categories}
            
            budget_summaries = []
            for budget in budgets:
                # Recalculate spent amount
                await self._update_budget_spent_amount(user_id, budget)
                
                budget_summaries.append(BudgetSummary(
                    id=budget.id,
                    name=budget.name,
                    category_id=budget.category_id,
                    category_name=category_map.get(budget.category_id, "Unknown"),
                    amount=budget.amount,
                    spent_amount=budget.spent_amount,
                    percentage_used=budget.percentage_used,
                    remaining_amount=budget.remaining_amount,
                    period_start=budget.period_start,
                    period_end=budget.period_end,
                    is_active=budget.is_active,
                    alert_threshold=budget.alert_threshold
                ))
            
            return budget_summaries
            
        except Exception as e:
            logger.error("Failed to list budgets", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve budgets",
                details=[str(e)]
            )
    
    async def update_budget(self, user_id: str, budget_id: str, 
                           request: BudgetUpdateRequest) -> BudgetResponse:
        """Update budget."""
        try:
            # Get existing budget
            budget = await self.firestore.get_document(
                collection=f"budgets/{user_id}/user_budgets",
                document_id=budget_id,
                model_class=Budget
            )
            
            if not budget:
                raise NotFoundError(
                    message="Budget not found",
                    resource_type="budget",
                    resource_id=budget_id
                )
            
            # Update fields
            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.amount is not None:
                update_data["amount"] = request.amount
            if request.period_start is not None:
                update_data["period_start"] = request.period_start
            if request.period_end is not None:
                update_data["period_end"] = request.period_end
            if request.is_active is not None:
                update_data["is_active"] = request.is_active
            if request.alert_threshold is not None:
                update_data["alert_threshold"] = request.alert_threshold
            
            # Validate period if being updated
            period_start = request.period_start or budget.period_start
            period_end = request.period_end or budget.period_end
            if period_end <= period_start:
                raise BusinessLogicError(
                    message="Period end must be after period start"
                )
            
            # Update timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            # Apply updates to model
            for field, value in update_data.items():
                setattr(budget, field, value)
            
            # Convert to dict for Firestore
            budget_data = budget.dict()
            if 'amount' in budget_data:
                budget_data['amount'] = float(budget_data['amount'])
            if 'spent_amount' in budget_data:
                budget_data['spent_amount'] = float(budget_data['spent_amount'])
            if 'alert_threshold' in budget_data and budget_data['alert_threshold'] is not None:
                budget_data['alert_threshold'] = float(budget_data['alert_threshold'])
            
            # Save to Firestore
            await self.firestore.update_document(
                collection=f"budgets/{user_id}/user_budgets",
                document_id=budget_id,
                data=budget_data
            )
            
            logger.info(
                "Budget updated successfully",
                user_id=user_id,
                budget_id=budget_id,
                fields_updated=list(update_data.keys())
            )
            
            return BudgetResponse(
                id=budget.id,
                name=budget.name,
                category_id=budget.category_id,
                amount=budget.amount,
                period_start=budget.period_start,
                period_end=budget.period_end,
                spent_amount=budget.spent_amount,
                is_active=budget.is_active,
                alert_threshold=budget.alert_threshold,
                alert_sent=budget.alert_sent,
                created_at=budget.created_at,
                updated_at=budget.updated_at
            )
            
        except (NotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error("Failed to update budget", user_id=user_id, budget_id=budget_id, error=str(e))
            raise AppValidationError(
                message="Failed to update budget",
                details=[str(e)]
            )
    
    async def delete_budget(self, user_id: str, budget_id: str) -> None:
        """Soft delete budget."""
        try:
            budget = await self.firestore.get_document(
                collection=f"budgets/{user_id}/user_budgets",
                document_id=budget_id,
                model_class=Budget
            )
            
            if not budget:
                raise NotFoundError(
                    message="Budget not found",
                    resource_type="budget",
                    resource_id=budget_id
                )
            
            # Soft delete
            budget.soft_delete()
            
            # Convert to dict for Firestore
            budget_data = budget.dict()
            if 'amount' in budget_data:
                budget_data['amount'] = float(budget_data['amount'])
            if 'spent_amount' in budget_data:
                budget_data['spent_amount'] = float(budget_data['spent_amount'])
            if 'alert_threshold' in budget_data and budget_data['alert_threshold'] is not None:
                budget_data['alert_threshold'] = float(budget_data['alert_threshold'])
            
            # Save to Firestore
            await self.firestore.update_document(
                collection=f"budgets/{user_id}/user_budgets",
                document_id=budget_id,
                data=budget_data
            )
            
            logger.info(
                "Budget deleted successfully",
                user_id=user_id,
                budget_id=budget_id,
                budget_name=budget.name
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete budget", user_id=user_id, budget_id=budget_id, error=str(e))
            raise AppValidationError(
                message="Failed to delete budget",
                details=[str(e)]
            )
    
    async def _update_budget_spent_amount(self, user_id: str, budget: Budget) -> None:
        """Update budget spent amount based on transactions in the period."""
        try:
            # Get transactions for the category in the budget period
            transactions = await self.firestore.query_documents(
                collection=f"transactions/{user_id}/user_transactions",
                model_class=Transaction,
                where_clauses=[
                    ("category_id", "==", budget.category_id),
                    ("transaction_date", ">=", budget.period_start),
                    ("transaction_date", "<=", budget.period_end),
                    ("transaction_type", "==", TransactionType.EXPENSE)
                ]
            )
            
            # Calculate total spent (absolute value for expenses)
            total_spent = Decimal("0.00")
            for transaction in transactions:
                if transaction.amount < 0:  # Expenses are negative
                    total_spent += abs(transaction.amount)
            
            # Update budget if spent amount changed
            if budget.spent_amount != total_spent:
                budget.spent_amount = total_spent
                
                # Convert to dict for Firestore
                budget_data = budget.dict()
                if 'amount' in budget_data:
                    budget_data['amount'] = float(budget_data['amount'])
                if 'spent_amount' in budget_data:
                    budget_data['spent_amount'] = float(budget_data['spent_amount'])
                if 'alert_threshold' in budget_data and budget_data['alert_threshold'] is not None:
                    budget_data['alert_threshold'] = float(budget_data['alert_threshold'])
                
                await self.firestore.update_document(
                    collection=f"budgets/{user_id}/user_budgets",
                    document_id=budget.id,
                    data=budget_data
                )
                
        except Exception as e:
            logger.warning("Failed to update budget spent amount", 
                         budget_id=budget.id, error=str(e))
    
    def _periods_overlap(self, start1: datetime, end1: datetime, 
                        start2: datetime, end2: datetime) -> bool:
        """Check if two date periods overlap."""
        return start1 <= end2 and start2 <= end1


# Global service instance
_budget_service: Optional[BudgetService] = None


def get_budget_service() -> BudgetService:
    """Get the global budget service instance."""
    global _budget_service
    if _budget_service is None:
        _budget_service = BudgetService()
    return _budget_service