"""
Import/Export service for transactions.
"""
import yaml
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from uuid import uuid4

import structlog

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.financial import (
    Account,
    Category,
    Transaction,
    CategoryType,
    CategoryCreateRequest
)
from ..models.import_models import (
    YAMLImportRequest,
    YAMLImportResponse,
    YAMLExportRequest, 
    YAMLExportResponse,
    ImportSummary,
    ImportValidationError,
    TransactionExportItem,
    YAMLTransactionItem
)
from ..services.category import get_category_service
from ..services.transaction import get_transaction_service
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError

logger = structlog.get_logger()


class ImportExportService:
    """Service for importing and exporting transactions."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
        self.category_service = get_category_service()
        self.transaction_service = get_transaction_service()
    
    async def import_yaml_transactions(self, user_id: str, request: YAMLImportRequest) -> YAMLImportResponse:
        """Import transactions from YAML data."""
        try:
            # Get user accounts and categories for validation
            accounts = await self._get_user_accounts(user_id)
            categories = await self._get_user_categories(user_id)
            
            # Create lookup dictionaries
            account_lookup = {acc.name.lower(): acc for acc in accounts}
            category_lookup = {cat.name.lower(): cat for cat in categories}
            
            summary = ImportSummary(
                total_transactions=len(request.transactions),
                successful_imports=0,
                failed_imports=0,
                created_categories=0,
                errors=[]
            )
            
            created_transaction_ids = []
            created_categories = []
            
            # Process each transaction
            for idx, yaml_transaction in enumerate(request.transactions):
                try:
                    # Validate and prepare transaction
                    validation_result = await self._validate_yaml_transaction(
                        yaml_transaction, account_lookup, category_lookup, 
                        request.create_missing_categories, request.default_category_type,
                        user_id, idx
                    )
                    
                    if not validation_result['valid']:
                        summary.errors.extend(validation_result['errors'])
                        summary.failed_imports += 1
                        continue
                    
                    # Track newly created category
                    if validation_result.get('created_category'):
                        created_categories.append(validation_result['created_category'])
                        category_lookup[validation_result['created_category'].name.lower()] = validation_result['created_category']
                        summary.created_categories += 1
                    
                    # If dry run, don't create transactions
                    if request.dry_run:
                        summary.successful_imports += 1
                        continue
                    
                    # Create the transaction
                    transaction_data = validation_result['transaction_data']
                    transaction = Transaction(**transaction_data)
                    transaction_id = str(uuid4())
                    transaction.id = transaction_id
                    
                    await self.firestore.create_document(
                        collection=f"transactions/{user_id}/user_transactions",
                        document_id=transaction_id,
                        data=transaction
                    )
                    
                    created_transaction_ids.append(transaction_id)
                    summary.successful_imports += 1
                    
                    logger.info(
                        "Transaction imported from YAML",
                        user_id=user_id,
                        transaction_id=transaction_id,
                        amount=str(yaml_transaction.amount),
                        description=yaml_transaction.description
                    )
                    
                except Exception as e:
                    logger.error("Failed to import transaction", 
                               user_id=user_id, row_index=idx, error=str(e))
                    summary.errors.append(ImportValidationError(
                        row_index=idx,
                        field=None,
                        error=f"Failed to create transaction: {str(e)}",
                        transaction=yaml_transaction.dict()
                    ))
                    summary.failed_imports += 1
            
            # Determine success
            success = summary.failed_imports == 0
            
            # Create response message
            if request.dry_run:
                message = f"Dry run completed. {summary.successful_imports} transactions would be imported successfully"
                if summary.failed_imports > 0:
                    message += f", {summary.failed_imports} would fail"
                if summary.created_categories > 0:
                    message += f", {summary.created_categories} categories would be created"
            else:
                message = f"Import completed. {summary.successful_imports} transactions imported successfully"
                if summary.failed_imports > 0:
                    message += f", {summary.failed_imports} failed"
                if summary.created_categories > 0:
                    message += f", {summary.created_categories} categories created"
            
            logger.info(
                "YAML import completed",
                user_id=user_id,
                total=summary.total_transactions,
                successful=summary.successful_imports,
                failed=summary.failed_imports,
                dry_run=request.dry_run
            )
            
            return YAMLImportResponse(
                success=success,
                summary=summary,
                message=message,
                created_transaction_ids=created_transaction_ids
            )
            
        except Exception as e:
            logger.error("Failed to import YAML transactions", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to import transactions from YAML",
                details=[str(e)]
            )
    
    async def export_yaml_transactions(self, user_id: str, request: YAMLExportRequest) -> YAMLExportResponse:
        """Export transactions to YAML format."""
        try:
            # Get user accounts and categories for name resolution
            accounts = await self._get_user_accounts(user_id)
            categories = await self._get_user_categories(user_id)
            
            # Create lookup dictionaries
            account_lookup = {acc.id: acc.name for acc in accounts}
            category_lookup = {cat.id: cat.name for cat in categories}
            
            # Get transactions with filters
            transactions = await self.transaction_service.list_transactions(
                user_id=user_id,
                account_id=request.account_id,
                category_id=request.category_id,
                start_date=request.start_date,
                end_date=request.end_date,
                active_only=not request.include_inactive,
                limit=None,  # Export all matching transactions
                offset=None
            )
            
            # Convert to export format
            export_items = []
            for transaction in transactions:
                # Get full transaction details
                full_transaction = await self.transaction_service.get_transaction(user_id, transaction.id)
                
                export_item = TransactionExportItem(
                    account_name=account_lookup.get(full_transaction.account_id, "Unknown Account"),
                    category_name=category_lookup.get(full_transaction.category_id) if full_transaction.category_id else None,
                    amount=str(full_transaction.amount) if request.format_amounts else f"{float(full_transaction.amount):.2f}",
                    description=full_transaction.description,
                    date=full_transaction.transaction_date,
                    destination_account_name=account_lookup.get(full_transaction.destination_account_id) if full_transaction.destination_account_id else None,
                    reference_number=full_transaction.reference_number,
                    notes=full_transaction.notes,
                    tags=full_transaction.tags or []
                )
                export_items.append(export_item)
            
            # Convert to YAML
            yaml_data = {
                'transactions': [item.dict(exclude_none=True) for item in export_items]
            }
            
            yaml_content = yaml.dump(
                yaml_data,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                indent=2
            )
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"transactions_export_{timestamp}.yaml"
            
            logger.info(
                "YAML export completed",
                user_id=user_id,
                transaction_count=len(export_items)
            )
            
            return YAMLExportResponse(
                yaml_content=yaml_content,
                transaction_count=len(export_items),
                filename=filename
            )
            
        except Exception as e:
            logger.error("Failed to export YAML transactions", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to export transactions to YAML",
                details=[str(e)]
            )
    
    async def _get_user_accounts(self, user_id: str) -> List[Account]:
        """Get all user accounts."""
        try:
            accounts = await self.firestore.query_documents(
                collection=f"accounts/{user_id}/bank_accounts",
                model_class=Account,
                where_clauses=[("is_active", "==", True)],
                order_by=[("name", "asc")]
            )
            return accounts
        except Exception as e:
            logger.error("Failed to get user accounts", user_id=user_id, error=str(e))
            return []
    
    async def _get_user_categories(self, user_id: str) -> List[Category]:
        """Get all user categories."""
        try:
            categories = await self.firestore.query_documents(
                collection=f"categories/{user_id}/user_categories",
                model_class=Category,
                where_clauses=[("is_active", "==", True)],
                order_by=[("name", "asc")]
            )
            return categories
        except Exception as e:
            logger.error("Failed to get user categories", user_id=user_id, error=str(e))
            return []
    
    async def _validate_yaml_transaction(
        self, 
        yaml_transaction: YAMLTransactionItem,
        account_lookup: Dict[str, Account],
        category_lookup: Dict[str, Category],
        create_missing_categories: bool,
        default_category_type: str,
        user_id: str,
        row_index: int
    ) -> dict:
        """Validate a single YAML transaction and prepare for import."""
        errors = []
        created_category = None
        
        # Validate account exists
        account = account_lookup.get(yaml_transaction.account_name.lower())
        if not account:
            errors.append(ImportValidationError(
                row_index=row_index,
                field="account_name",
                error=f"Account '{yaml_transaction.account_name}' not found",
                transaction=yaml_transaction.dict()
            ))
            return {'valid': False, 'errors': errors}
        
        # Validate destination account (for transfers)
        destination_account = None
        if yaml_transaction.destination_account_name:
            destination_account = account_lookup.get(yaml_transaction.destination_account_name.lower())
            if not destination_account:
                errors.append(ImportValidationError(
                    row_index=row_index,
                    field="destination_account_name",
                    error=f"Destination account '{yaml_transaction.destination_account_name}' not found",
                    transaction=yaml_transaction.dict()
                ))
                return {'valid': False, 'errors': errors}
        
        # Validate/create category
        category = None
        if yaml_transaction.category_name:
            category = category_lookup.get(yaml_transaction.category_name.lower())
            if not category and create_missing_categories:
                try:
                    # Create new category
                    category_request = CategoryCreateRequest(
                        name=yaml_transaction.category_name,
                        category_type=CategoryType(default_category_type)
                    )
                    category_response = await self.category_service.create_category(user_id, category_request)
                    
                    # Convert response back to Category model for lookup
                    created_category = Category(
                        id=category_response.id,
                        user_id=user_id,
                        name=category_response.name,
                        category_type=category_response.category_type,
                        is_system=category_response.is_system,
                        is_active=category_response.is_active,
                        created_at=category_response.created_at,
                        updated_at=category_response.updated_at
                    )
                    category = created_category
                    
                    logger.info(
                        "Created new category during YAML import",
                        user_id=user_id,
                        category_name=yaml_transaction.category_name,
                        category_type=default_category_type
                    )
                    
                except Exception as e:
                    errors.append(ImportValidationError(
                        row_index=row_index,
                        field="category_name",
                        error=f"Failed to create category '{yaml_transaction.category_name}': {str(e)}",
                        transaction=yaml_transaction.dict()
                    ))
                    return {'valid': False, 'errors': errors}
            
            elif not category:
                errors.append(ImportValidationError(
                    row_index=row_index,
                    field="category_name",
                    error=f"Category '{yaml_transaction.category_name}' not found and create_missing_categories is disabled",
                    transaction=yaml_transaction.dict()
                ))
                return {'valid': False, 'errors': errors}
        
        # Prepare transaction data
        transaction_data = {
            "user_id": user_id,
            "account_id": account.id,
            "category_id": category.id if category else None,
            "amount": yaml_transaction.amount,
            "description": yaml_transaction.description,
            "transaction_date": yaml_transaction.date,
            "destination_account_id": destination_account.id if destination_account else None,
            "reference_number": yaml_transaction.reference_number,
            "notes": yaml_transaction.notes,
            "tags": yaml_transaction.tags or []
        }
        
        return {
            'valid': True,
            'errors': [],
            'transaction_data': transaction_data,
            'created_category': created_category
        }


# Global service instance
_import_export_service: Optional[ImportExportService] = None


def get_import_export_service() -> ImportExportService:
    """Get the global import/export service instance."""
    global _import_export_service
    if _import_export_service is None:
        _import_export_service = ImportExportService()
    return _import_export_service