"""
Recurring transaction service for managing recurring financial transactions.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4
from decimal import Decimal

import structlog

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.financial import (
    RecurringTransaction,
    RecurringTransactionCreateRequest,
    RecurringTransactionUpdateRequest,
    RecurringTransactionResponse,
    RecurringTransactionSummary,
    Account,
    Category,
    Transaction,
    RecurringFrequency,
    TransactionType
)
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError, BusinessLogicError

logger = structlog.get_logger()


class RecurringTransactionService:
    """Service for recurring transaction operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
    
    async def create_recurring_transaction(
        self, user_id: str, request: RecurringTransactionCreateRequest
    ) -> RecurringTransactionResponse:
        """Create a new recurring transaction."""
        try:
            # Validate account exists
            account = await self.firestore.get_document(
                collection=f"accounts/{user_id}/bank_accounts",
                document_id=request.account_id,
                model_class=Account
            )
            
            if not account:
                raise NotFoundError(
                    message="Account not found",
                    resource_type="account",
                    resource_id=request.account_id
                )
            
            # Validate destination account if transfer
            to_account = None
            if request.to_account_id:
                to_account = await self.firestore.get_document(
                    collection=f"accounts/{user_id}/bank_accounts",
                    document_id=request.to_account_id,
                    model_class=Account
                )
                
                if not to_account:
                    raise NotFoundError(
                        message="Destination account not found",
                        resource_type="account",
                        resource_id=request.to_account_id
                    )
            
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
            
            # Calculate next execution date
            next_execution = self._calculate_next_execution(
                request.start_date, request.frequency
            )
            
            # Create recurring transaction
            recurring_transaction = RecurringTransaction(
                user_id=user_id,
                name=request.name,
                amount=request.amount,
                description=request.description,
                transaction_type=request.transaction_type,
                account_id=request.account_id,
                to_account_id=request.to_account_id,
                category_id=request.category_id,
                subcategory_id=request.subcategory_id,
                frequency=request.frequency,
                start_date=request.start_date,
                end_date=request.end_date,
                next_execution=next_execution,
                notes=request.notes,
                tags=request.tags or []
            )
            
            # Generate ID and save
            recurring_id = str(uuid4())
            recurring_transaction.id = recurring_id
            
            await self.firestore.create_document(
                collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                document_id=recurring_id,
                data=recurring_transaction
            )
            
            logger.info(
                "Recurring transaction created successfully",
                user_id=user_id,
                recurring_id=recurring_id,
                name=request.name,
                frequency=request.frequency.value
            )
            
            return RecurringTransactionResponse(
                id=recurring_transaction.id,
                name=recurring_transaction.name,
                amount=recurring_transaction.amount,
                description=recurring_transaction.description,
                transaction_type=recurring_transaction.transaction_type,
                account_id=recurring_transaction.account_id,
                to_account_id=recurring_transaction.to_account_id,
                category_id=recurring_transaction.category_id,
                subcategory_id=recurring_transaction.subcategory_id,
                frequency=recurring_transaction.frequency,
                start_date=recurring_transaction.start_date,
                end_date=recurring_transaction.end_date,
                next_execution=recurring_transaction.next_execution,
                is_active=recurring_transaction.is_active,
                last_executed=recurring_transaction.last_executed,
                notes=recurring_transaction.notes,
                tags=recurring_transaction.tags,
                created_at=recurring_transaction.created_at,
                updated_at=recurring_transaction.updated_at
            )
            
        except (NotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error("Failed to create recurring transaction", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to create recurring transaction",
                details=[str(e)]
            )
    
    async def get_recurring_transaction(
        self, user_id: str, recurring_id: str
    ) -> RecurringTransactionResponse:
        """Get recurring transaction by ID."""
        try:
            recurring = await self.firestore.get_document(
                collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                document_id=recurring_id,
                model_class=RecurringTransaction
            )
            
            if not recurring:
                raise NotFoundError(
                    message="Recurring transaction not found",
                    resource_type="recurring_transaction",
                    resource_id=recurring_id
                )
            
            return RecurringTransactionResponse(
                id=recurring.id,
                name=recurring.name,
                amount=recurring.amount,
                description=recurring.description,
                transaction_type=recurring.transaction_type,
                account_id=recurring.account_id,
                to_account_id=recurring.to_account_id,
                category_id=recurring.category_id,
                subcategory_id=recurring.subcategory_id,
                frequency=recurring.frequency,
                start_date=recurring.start_date,
                end_date=recurring.end_date,
                next_execution=recurring.next_execution,
                is_active=recurring.is_active,
                last_executed=recurring.last_executed,
                notes=recurring.notes,
                tags=recurring.tags,
                created_at=recurring.created_at,
                updated_at=recurring.updated_at
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get recurring transaction", 
                        user_id=user_id, recurring_id=recurring_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve recurring transaction",
                details=[str(e)]
            )
    
    async def list_recurring_transactions(
        self, user_id: str, active_only: bool = False
    ) -> List[RecurringTransactionSummary]:
        """List user recurring transactions."""
        try:
            where_clauses = []
            if active_only:
                where_clauses.append(("is_active", "==", True))
            
            recurring_transactions = await self.firestore.query_documents(
                collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                model_class=RecurringTransaction,
                where_clauses=where_clauses,
                order_by="next_execution"
            )
            
            # Get account and category names for summaries
            accounts = await self.firestore.query_documents(
                collection=f"accounts/{user_id}/bank_accounts",
                model_class=Account
            )
            categories = await self.firestore.query_documents(
                collection=f"categories/{user_id}/user_categories",
                model_class=Category
            )
            
            account_map = {acc.id: acc.name for acc in accounts}
            category_map = {cat.id: cat.name for cat in categories}
            
            summaries = []
            for recurring in recurring_transactions:
                summaries.append(RecurringTransactionSummary(
                    id=recurring.id,
                    name=recurring.name,
                    amount=recurring.amount,
                    description=recurring.description,
                    transaction_type=recurring.transaction_type,
                    frequency=recurring.frequency,
                    account_name=account_map.get(recurring.account_id, "Unknown"),
                    category_name=category_map.get(recurring.category_id, "Unknown"),
                    next_execution=recurring.next_execution,
                    is_active=recurring.is_active
                ))
            
            return summaries
            
        except Exception as e:
            logger.error("Failed to list recurring transactions", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve recurring transactions",
                details=[str(e)]
            )
    
    async def update_recurring_transaction(
        self, user_id: str, recurring_id: str, request: RecurringTransactionUpdateRequest
    ) -> RecurringTransactionResponse:
        """Update recurring transaction."""
        try:
            # Get existing recurring transaction
            recurring = await self.firestore.get_document(
                collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                document_id=recurring_id,
                model_class=RecurringTransaction
            )
            
            if not recurring:
                raise NotFoundError(
                    message="Recurring transaction not found",
                    resource_type="recurring_transaction",
                    resource_id=recurring_id
                )
            
            # Update fields
            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.amount is not None:
                update_data["amount"] = request.amount
            if request.description is not None:
                update_data["description"] = request.description
            if request.account_id is not None:
                update_data["account_id"] = request.account_id
            if request.to_account_id is not None:
                update_data["to_account_id"] = request.to_account_id
            if request.category_id is not None:
                update_data["category_id"] = request.category_id
            if request.subcategory_id is not None:
                update_data["subcategory_id"] = request.subcategory_id
            if request.frequency is not None:
                update_data["frequency"] = request.frequency
                # Recalculate next execution if frequency changed
                update_data["next_execution"] = self._calculate_next_execution(
                    recurring.start_date, request.frequency
                )
            if request.start_date is not None:
                update_data["start_date"] = request.start_date
            if request.end_date is not None:
                update_data["end_date"] = request.end_date
            if request.is_active is not None:
                update_data["is_active"] = request.is_active
            if request.notes is not None:
                update_data["notes"] = request.notes
            if request.tags is not None:
                update_data["tags"] = request.tags
            
            # Update timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            # Apply updates to model
            for field, value in update_data.items():
                setattr(recurring, field, value)
            
            # Convert to dict for Firestore
            recurring_data = recurring.dict()
            if 'amount' in recurring_data:
                recurring_data['amount'] = float(recurring_data['amount'])
            
            # Save to Firestore
            await self.firestore.update_document(
                collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                document_id=recurring_id,
                data=recurring_data
            )
            
            logger.info(
                "Recurring transaction updated successfully",
                user_id=user_id,
                recurring_id=recurring_id,
                fields_updated=list(update_data.keys())
            )
            
            return RecurringTransactionResponse(
                id=recurring.id,
                name=recurring.name,
                amount=recurring.amount,
                description=recurring.description,
                transaction_type=recurring.transaction_type,
                account_id=recurring.account_id,
                to_account_id=recurring.to_account_id,
                category_id=recurring.category_id,
                subcategory_id=recurring.subcategory_id,
                frequency=recurring.frequency,
                start_date=recurring.start_date,
                end_date=recurring.end_date,
                next_execution=recurring.next_execution,
                is_active=recurring.is_active,
                last_executed=recurring.last_executed,
                notes=recurring.notes,
                tags=recurring.tags,
                created_at=recurring.created_at,
                updated_at=recurring.updated_at
            )
            
        except (NotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error("Failed to update recurring transaction", 
                        user_id=user_id, recurring_id=recurring_id, error=str(e))
            raise AppValidationError(
                message="Failed to update recurring transaction",
                details=[str(e)]
            )
    
    async def delete_recurring_transaction(self, user_id: str, recurring_id: str) -> None:
        """Soft delete recurring transaction."""
        try:
            recurring = await self.firestore.get_document(
                collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                document_id=recurring_id,
                model_class=RecurringTransaction
            )
            
            if not recurring:
                raise NotFoundError(
                    message="Recurring transaction not found",
                    resource_type="recurring_transaction",
                    resource_id=recurring_id
                )
            
            # Soft delete
            recurring.soft_delete()
            
            # Convert to dict for Firestore
            recurring_data = recurring.dict()
            if 'amount' in recurring_data:
                recurring_data['amount'] = float(recurring_data['amount'])
            
            # Save to Firestore
            await self.firestore.update_document(
                collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                document_id=recurring_id,
                data=recurring_data
            )
            
            logger.info(
                "Recurring transaction deleted successfully",
                user_id=user_id,
                recurring_id=recurring_id,
                name=recurring.name
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete recurring transaction", 
                        user_id=user_id, recurring_id=recurring_id, error=str(e))
            raise AppValidationError(
                message="Failed to delete recurring transaction",
                details=[str(e)]
            )
    
    async def execute_due_recurring_transactions(self, user_id: str) -> List[str]:
        """Execute recurring transactions that are due."""
        try:
            now = datetime.utcnow()
            
            # Find due recurring transactions
            due_transactions = await self.firestore.query_documents(
                collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                model_class=RecurringTransaction,
                where_clauses=[
                    ("is_active", "==", True),
                    ("next_execution", "<=", now)
                ]
            )
            
            executed_transaction_ids = []
            
            for recurring in due_transactions:
                try:
                    # Create the actual transaction
                    transaction = Transaction(
                        user_id=user_id,
                        amount=recurring.amount,
                        description=f"{recurring.description} (auto)",
                        transaction_type=recurring.transaction_type,
                        transaction_date=now,
                        account_id=recurring.account_id,
                        to_account_id=recurring.to_account_id,
                        category_id=recurring.category_id,
                        subcategory_id=recurring.subcategory_id,
                        notes=f"Auto-generated from recurring: {recurring.name}",
                        tags=recurring.tags + ["auto-recurring"]
                    )
                    
                    transaction_id = str(uuid4())
                    transaction.id = transaction_id
                    
                    await self.firestore.create_document(
                        collection=f"transactions/{user_id}/user_transactions",
                        document_id=transaction_id,
                        data=transaction
                    )
                    
                    # Update recurring transaction
                    recurring.last_executed = now
                    recurring.next_execution = self._calculate_next_execution(
                        now, recurring.frequency
                    )
                    
                    # Check if recurring should be deactivated
                    if (recurring.end_date and 
                        recurring.next_execution > recurring.end_date):
                        recurring.is_active = False
                    
                    recurring.updated_at = now
                    
                    # Convert to dict for Firestore
                    recurring_data = recurring.dict()
                    if 'amount' in recurring_data:
                        recurring_data['amount'] = float(recurring_data['amount'])
                    
                    await self.firestore.update_document(
                        collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                        document_id=recurring.id,
                        data=recurring_data
                    )
                    
                    executed_transaction_ids.append(transaction_id)
                    
                    logger.info(
                        "Recurring transaction executed",
                        user_id=user_id,
                        recurring_id=recurring.id,
                        transaction_id=transaction_id,
                        amount=float(recurring.amount)
                    )
                    
                except Exception as e:
                    logger.error(
                        "Failed to execute recurring transaction",
                        user_id=user_id,
                        recurring_id=recurring.id,
                        error=str(e)
                    )
            
            return executed_transaction_ids
            
        except Exception as e:
            logger.error("Failed to execute recurring transactions", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to execute recurring transactions",
                details=[str(e)]
            )
    
    def _calculate_next_execution(self, current_date: datetime, frequency: RecurringFrequency) -> datetime:
        """Calculate the next execution date based on frequency."""
        if frequency == RecurringFrequency.DAILY:
            return current_date + timedelta(days=1)
        elif frequency == RecurringFrequency.WEEKLY:
            return current_date + timedelta(weeks=1)
        elif frequency == RecurringFrequency.BIWEEKLY:
            return current_date + timedelta(weeks=2)
        elif frequency == RecurringFrequency.MONTHLY:
            # Handle month boundaries
            if current_date.month == 12:
                return current_date.replace(year=current_date.year + 1, month=1)
            else:
                return current_date.replace(month=current_date.month + 1)
        elif frequency == RecurringFrequency.QUARTERLY:
            # Handle quarter boundaries
            new_month = current_date.month + 3
            if new_month > 12:
                return current_date.replace(year=current_date.year + 1, month=new_month - 12)
            else:
                return current_date.replace(month=new_month)
        elif frequency == RecurringFrequency.YEARLY:
            return current_date.replace(year=current_date.year + 1)
        else:
            # Default to monthly
            return current_date.replace(month=current_date.month + 1)


# Global service instance
_recurring_transaction_service: Optional[RecurringTransactionService] = None


def get_recurring_transaction_service() -> RecurringTransactionService:
    """Get the global recurring transaction service instance."""
    global _recurring_transaction_service
    if _recurring_transaction_service is None:
        _recurring_transaction_service = RecurringTransactionService()
    return _recurring_transaction_service