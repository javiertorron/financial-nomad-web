"""
Account service for managing financial accounts.
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

import structlog

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.financial import (
    Account,
    AccountCreateRequest,
    AccountUpdateRequest,
    AccountResponse,
    AccountSummary
)
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError

logger = structlog.get_logger()


class AccountService:
    """Service for account operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
    
    async def create_account(self, user_id: str, request: AccountCreateRequest) -> AccountResponse:
        """Create a new account."""
        try:
            # Create account model
            account = Account(
                user_id=user_id,
                name=request.name,
                account_type=request.account_type,
                balance=request.balance,
                currency=request.currency.upper(),
                description=request.description,
                color=request.color,
                icon=request.icon
            )
            
            # Generate account ID and save to Firestore
            account_id = str(uuid4())
            account.id = account_id
            
            await self.firestore.create_document(
                collection=f"accounts/{user_id}/bank_accounts",
                document_id=account_id,
                data=account
            )
            
            logger.info(
                "Account created successfully",
                user_id=user_id,
                account_id=account_id,
                account_name=account.name
            )
            
            # Return response
            return AccountResponse(
                id=account.id,
                name=account.name,
                account_type=account.account_type,
                balance=account.balance,
                currency=account.currency,
                description=account.description,
                is_active=account.is_active,
                color=account.color,
                icon=account.icon,
                created_at=account.created_at,
                updated_at=account.updated_at
            )
            
        except Exception as e:
            logger.error("Failed to create account", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to create account",
                details=[str(e)]
            )
    
    async def get_account(self, user_id: str, account_id: str) -> AccountResponse:
        """Get account by ID."""
        try:
            account = await self.firestore.get_document(
                collection=f"accounts/{user_id}/bank_accounts",
                document_id=account_id,
                model_class=Account
            )
            
            if not account:
                raise NotFoundError(
                    message="Account not found",
                    resource_type="account",
                    resource_id=account_id
                )
            
            return AccountResponse(
                id=account.id,
                name=account.name,
                account_type=account.account_type,
                balance=account.balance,
                currency=account.currency,
                description=account.description,
                is_active=account.is_active,
                color=account.color,
                icon=account.icon,
                created_at=account.created_at,
                updated_at=account.updated_at
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get account", user_id=user_id, account_id=account_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve account",
                details=[str(e)]
            )
    
    async def list_accounts(self, user_id: str, active_only: bool = False) -> List[AccountSummary]:
        """List user accounts."""
        try:
            where_clauses = []
            if active_only:
                where_clauses.append(("is_active", "==", True))
            
            accounts = await self.firestore.query_documents(
                collection=f"accounts/{user_id}/bank_accounts",
                model_class=Account,
                where_clauses=where_clauses,
                order_by="name"
            )
            
            return [
                AccountSummary(
                    id=account.id,
                    name=account.name,
                    account_type=account.account_type,
                    balance=account.balance,
                    currency=account.currency,
                    description=account.description,
                    is_active=account.is_active,
                    color=account.color,
                    icon=account.icon
                )
                for account in accounts
            ]
            
        except Exception as e:
            logger.error("Failed to list accounts", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve accounts",
                details=[str(e)]
            )
    
    async def update_account(
        self, 
        user_id: str, 
        account_id: str, 
        request: AccountUpdateRequest
    ) -> AccountResponse:
        """Update account."""
        try:
            # Get existing account
            account = await self.firestore.get_document(
                collection=f"accounts/{user_id}/bank_accounts",
                document_id=account_id,
                model_class=Account
            )
            
            if not account:
                raise NotFoundError(
                    message="Account not found",
                    resource_type="account",
                    resource_id=account_id
                )
            
            # Update fields
            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.balance is not None:
                update_data["balance"] = request.balance
            if request.description is not None:
                update_data["description"] = request.description
            if request.is_active is not None:
                update_data["is_active"] = request.is_active
            if request.color is not None:
                update_data["color"] = request.color
            if request.icon is not None:
                update_data["icon"] = request.icon
            
            # Update timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            # Apply updates to model
            for field, value in update_data.items():
                setattr(account, field, value)
            
            # Convert to dict and handle Decimal conversion for Firestore
            account_data = account.dict()
            if 'balance' in account_data:
                account_data['balance'] = float(account_data['balance'])
            
            # Save to Firestore
            await self.firestore.update_document(
                collection=f"accounts/{user_id}/bank_accounts",
                document_id=account_id,
                data=account_data
            )
            
            logger.info(
                "Account updated successfully",
                user_id=user_id,
                account_id=account_id,
                fields_updated=list(update_data.keys())
            )
            
            return AccountResponse(
                id=account.id,
                name=account.name,
                account_type=account.account_type,
                balance=account.balance,
                currency=account.currency,
                description=account.description,
                is_active=account.is_active,
                color=account.color,
                icon=account.icon,
                created_at=account.created_at,
                updated_at=account.updated_at
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to update account", user_id=user_id, account_id=account_id, error=str(e))
            raise AppValidationError(
                message="Failed to update account",
                details=[str(e)]
            )
    
    async def delete_account(self, user_id: str, account_id: str) -> None:
        """Soft delete account."""
        try:
            # Get existing account
            account = await self.firestore.get_document(
                collection=f"accounts/{user_id}/bank_accounts",
                document_id=account_id,
                model_class=Account
            )
            
            if not account:
                raise NotFoundError(
                    message="Account not found",
                    resource_type="account",
                    resource_id=account_id
                )
            
            # Soft delete
            account.soft_delete()
            
            # Convert to dict and handle Decimal conversion
            account_data = account.dict()
            if 'balance' in account_data:
                account_data['balance'] = float(account_data['balance'])
            
            # Save to Firestore
            await self.firestore.update_document(
                collection=f"accounts/{user_id}/bank_accounts",
                document_id=account_id,
                data=account_data
            )
            
            logger.info(
                "Account deleted successfully",
                user_id=user_id,
                account_id=account_id,
                account_name=account.name
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete account", user_id=user_id, account_id=account_id, error=str(e))
            raise AppValidationError(
                message="Failed to delete account",
                details=[str(e)]
            )


# Global service instance
_account_service: Optional[AccountService] = None


def get_account_service() -> AccountService:
    """Get the global account service instance."""
    global _account_service
    if _account_service is None:
        _account_service = AccountService()
    return _account_service