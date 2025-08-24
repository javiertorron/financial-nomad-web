"""
Transaction service for managing financial transactions.
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

import structlog

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.financial import (
    Transaction,
    TransactionCreateRequest,
    TransactionUpdateRequest,
    TransactionResponse,
    TransactionSummary,
    Account,
    Category
)
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError

logger = structlog.get_logger()


class TransactionService:
    """Service for transaction operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
    
    async def create_transaction(self, user_id: str, request: TransactionCreateRequest) -> TransactionResponse:
        """Create a new transaction."""
        try:
            # Validate account exists and belongs to user
            account = await self.firestore.get_document(
                collection=f"accounts/{user_id}/bank_accounts",
                document_id=request.account_id,
                model_class=Account
            )
            if not account:
                raise AppValidationError(
                    message="Account not found",
                    details=[f"Account {request.account_id} does not exist or does not belong to user"]
                )
            
            # Validate category exists and belongs to user (if specified)
            if request.category_id:
                category = await self.firestore.get_document(
                    collection=f"categories/{user_id}/user_categories",
                    document_id=request.category_id,
                    model_class=Category
                )
                if not category:
                    raise AppValidationError(
                        message="Category not found",
                        details=[f"Category {request.category_id} does not exist or does not belong to user"]
                    )
            
            # Validate destination account for transfers
            if request.destination_account_id:
                dest_account = await self.firestore.get_document(
                    collection=f"accounts/{user_id}/bank_accounts",
                    document_id=request.destination_account_id,
                    model_class=Account
                )
                if not dest_account:
                    raise AppValidationError(
                        message="Destination account not found",
                        details=[f"Destination account {request.destination_account_id} does not exist or does not belong to user"]
                    )
            
            # Create transaction model
            transaction = Transaction(
                user_id=user_id,
                account_id=request.account_id,
                category_id=request.category_id,
                amount=request.amount,
                description=request.description,
                transaction_date=request.transaction_date,
                destination_account_id=request.destination_account_id,
                reference_number=request.reference_number,
                notes=request.notes,
                tags=request.tags or []
            )
            
            # Generate transaction ID and save to Firestore
            transaction_id = str(uuid4())
            transaction.id = transaction_id
            
            await self.firestore.create_document(
                collection=f"transactions/{user_id}/user_transactions",
                document_id=transaction_id,
                data=transaction
            )
            
            logger.info(
                "Transaction created successfully",
                user_id=user_id,
                transaction_id=transaction_id,
                amount=str(transaction.amount),
                account_id=transaction.account_id
            )
            
            # Return response
            return TransactionResponse(
                id=transaction.id,
                account_id=transaction.account_id,
                category_id=transaction.category_id,
                amount=transaction.amount,
                description=transaction.description,
                transaction_date=transaction.transaction_date,
                destination_account_id=transaction.destination_account_id,
                reference_number=transaction.reference_number,
                notes=transaction.notes,
                tags=transaction.tags,
                is_active=transaction.is_active,
                created_at=transaction.created_at,
                updated_at=transaction.updated_at
            )
            
        except Exception as e:
            logger.error("Failed to create transaction", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to create transaction",
                details=[str(e)]
            )
    
    async def get_transaction(self, user_id: str, transaction_id: str) -> TransactionResponse:
        """Get transaction by ID."""
        try:
            transaction = await self.firestore.get_document(
                collection=f"transactions/{user_id}/user_transactions",
                document_id=transaction_id,
                model_class=Transaction
            )
            
            if not transaction:
                raise NotFoundError(
                    message="Transaction not found",
                    resource_type="transaction",
                    resource_id=transaction_id
                )
            
            return TransactionResponse(
                id=transaction.id,
                account_id=transaction.account_id,
                category_id=transaction.category_id,
                amount=transaction.amount,
                description=transaction.description,
                transaction_date=transaction.transaction_date,
                destination_account_id=transaction.destination_account_id,
                reference_number=transaction.reference_number,
                notes=transaction.notes,
                tags=transaction.tags,
                is_active=transaction.is_active,
                created_at=transaction.created_at,
                updated_at=transaction.updated_at
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get transaction", user_id=user_id, transaction_id=transaction_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve transaction",
                details=[str(e)]
            )
    
    async def list_transactions(
        self, 
        user_id: str, 
        account_id: Optional[str] = None,
        category_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        active_only: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[TransactionSummary]:
        """List user transactions with optional filters."""
        try:
            where_clauses = []
            
            if account_id:
                where_clauses.append(("account_id", "==", account_id))
            if category_id:
                where_clauses.append(("category_id", "==", category_id))
            if start_date:
                where_clauses.append(("transaction_date", ">=", start_date))
            if end_date:
                where_clauses.append(("transaction_date", "<=", end_date))
            if active_only:
                where_clauses.append(("is_active", "==", True))
            
            transactions = await self.firestore.query_documents(
                collection=f"transactions/{user_id}/user_transactions",
                model_class=Transaction,
                where_clauses=where_clauses,
                order_by=[("transaction_date", "desc")],
                limit=limit,
                offset=offset
            )
            
            return [
                TransactionSummary(
                    id=transaction.id,
                    account_id=transaction.account_id,
                    category_id=transaction.category_id,
                    amount=transaction.amount,
                    description=transaction.description,
                    transaction_date=transaction.transaction_date,
                    destination_account_id=transaction.destination_account_id,
                    is_active=transaction.is_active
                )
                for transaction in transactions
            ]
            
        except Exception as e:
            logger.error("Failed to list transactions", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve transactions",
                details=[str(e)]
            )
    
    async def update_transaction(
        self, 
        user_id: str, 
        transaction_id: str, 
        request: TransactionUpdateRequest
    ) -> TransactionResponse:
        """Update transaction."""
        try:
            # Get existing transaction
            transaction = await self.firestore.get_document(
                collection=f"transactions/{user_id}/user_transactions",
                document_id=transaction_id,
                model_class=Transaction
            )
            
            if not transaction:
                raise NotFoundError(
                    message="Transaction not found",
                    resource_type="transaction",
                    resource_id=transaction_id
                )
            
            # Validate account if being changed
            if request.account_id and request.account_id != transaction.account_id:
                account = await self.firestore.get_document(
                    collection=f"accounts/{user_id}/bank_accounts",
                    document_id=request.account_id,
                    model_class=Account
                )
                if not account:
                    raise AppValidationError(
                        message="Account not found",
                        details=[f"Account {request.account_id} does not exist or does not belong to user"]
                    )
            
            # Validate category if being changed
            if request.category_id and request.category_id != transaction.category_id:
                category = await self.firestore.get_document(
                    collection=f"categories/{user_id}/user_categories",
                    document_id=request.category_id,
                    model_class=Category
                )
                if not category:
                    raise AppValidationError(
                        message="Category not found",
                        details=[f"Category {request.category_id} does not exist or does not belong to user"]
                    )
            
            # Validate destination account if being changed
            if request.destination_account_id and request.destination_account_id != transaction.destination_account_id:
                dest_account = await self.firestore.get_document(
                    collection=f"accounts/{user_id}/bank_accounts",
                    document_id=request.destination_account_id,
                    model_class=Account
                )
                if not dest_account:
                    raise AppValidationError(
                        message="Destination account not found",
                        details=[f"Destination account {request.destination_account_id} does not exist or does not belong to user"]
                    )
            
            # Update fields
            update_data = {}
            if request.account_id is not None:
                update_data["account_id"] = request.account_id
            if request.category_id is not None:
                update_data["category_id"] = request.category_id
            if request.amount is not None:
                update_data["amount"] = request.amount
            if request.description is not None:
                update_data["description"] = request.description
            if request.transaction_date is not None:
                update_data["transaction_date"] = request.transaction_date
            if request.destination_account_id is not None:
                update_data["destination_account_id"] = request.destination_account_id
            if request.reference_number is not None:
                update_data["reference_number"] = request.reference_number
            if request.notes is not None:
                update_data["notes"] = request.notes
            if request.tags is not None:
                update_data["tags"] = request.tags
            if request.is_active is not None:
                update_data["is_active"] = request.is_active
            
            # Update timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            # Apply updates to model
            for field, value in update_data.items():
                setattr(transaction, field, value)
            
            # Save to Firestore
            await self.firestore.update_document(
                collection=f"transactions/{user_id}/user_transactions",
                document_id=transaction_id,
                data=transaction
            )
            
            logger.info(
                "Transaction updated successfully",
                user_id=user_id,
                transaction_id=transaction_id,
                fields_updated=list(update_data.keys())
            )
            
            return TransactionResponse(
                id=transaction.id,
                account_id=transaction.account_id,
                category_id=transaction.category_id,
                amount=transaction.amount,
                description=transaction.description,
                transaction_date=transaction.transaction_date,
                destination_account_id=transaction.destination_account_id,
                reference_number=transaction.reference_number,
                notes=transaction.notes,
                tags=transaction.tags,
                is_active=transaction.is_active,
                created_at=transaction.created_at,
                updated_at=transaction.updated_at
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to update transaction", user_id=user_id, transaction_id=transaction_id, error=str(e))
            raise AppValidationError(
                message="Failed to update transaction",
                details=[str(e)]
            )
    
    async def delete_transaction(self, user_id: str, transaction_id: str) -> None:
        """Soft delete transaction."""
        try:
            # Get existing transaction
            transaction = await self.firestore.get_document(
                collection=f"transactions/{user_id}/user_transactions",
                document_id=transaction_id,
                model_class=Transaction
            )
            
            if not transaction:
                raise NotFoundError(
                    message="Transaction not found",
                    resource_type="transaction",
                    resource_id=transaction_id
                )
            
            # Soft delete
            transaction.soft_delete()
            
            # Save to Firestore
            await self.firestore.update_document(
                collection=f"transactions/{user_id}/user_transactions",
                document_id=transaction_id,
                data=transaction
            )
            
            logger.info(
                "Transaction deleted successfully",
                user_id=user_id,
                transaction_id=transaction_id,
                amount=str(transaction.amount)
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete transaction", user_id=user_id, transaction_id=transaction_id, error=str(e))
            raise AppValidationError(
                message="Failed to delete transaction",
                details=[str(e)]
            )


# Global service instance
_transaction_service: Optional[TransactionService] = None


def get_transaction_service() -> TransactionService:
    """Get the global transaction service instance."""
    global _transaction_service
    if _transaction_service is None:
        _transaction_service = TransactionService()
    return _transaction_service