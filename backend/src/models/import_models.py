"""
Models for import/export functionality.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class YAMLTransactionItem(BaseModel):
    """Single transaction item from YAML import."""
    account_name: str = Field(..., min_length=1, max_length=100, description="Account name (will be matched to existing account)")
    category_name: Optional[str] = Field(None, max_length=100, description="Category name (will be matched to existing category)")
    amount: Decimal = Field(..., description="Transaction amount (positive for income, negative for expense)")
    description: str = Field(..., min_length=1, max_length=255, description="Transaction description")
    date: datetime = Field(..., description="Transaction date")
    destination_account_name: Optional[str] = Field(None, max_length=100, description="Destination account name for transfers")
    reference_number: Optional[str] = Field(None, max_length=50, description="Reference number")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")
    tags: Optional[List[str]] = Field(default_factory=list, description="Transaction tags")

    @validator('amount')
    def validate_amount(cls, v):
        if v == 0:
            raise ValueError('Amount cannot be zero')
        return v

    @validator('tags')
    def validate_tags(cls, v):
        if v is None:
            return []
        if len(v) > 10:
            raise ValueError('Maximum 10 tags allowed per transaction')
        for tag in v:
            if len(tag) > 50:
                raise ValueError('Tag length cannot exceed 50 characters')
        return v


class YAMLImportRequest(BaseModel):
    """Request for importing transactions from YAML."""
    transactions: List[YAMLTransactionItem] = Field(..., min_items=1, max_items=1000, description="List of transactions to import")
    dry_run: bool = Field(default=False, description="If true, validate import without creating transactions")
    create_missing_categories: bool = Field(default=False, description="Create categories that don't exist")
    default_category_type: str = Field(default="expense", description="Default category type for created categories")

    @validator('default_category_type')
    def validate_category_type(cls, v):
        if v not in ['income', 'expense', 'transfer']:
            raise ValueError('default_category_type must be income, expense, or transfer')
        return v


class ImportValidationError(BaseModel):
    """Validation error for a single transaction."""
    row_index: int = Field(..., description="Index of the transaction in the import list")
    field: Optional[str] = Field(None, description="Field that caused the error")
    error: str = Field(..., description="Error message")
    transaction: Optional[dict] = Field(None, description="Transaction data that caused the error")


class ImportSummary(BaseModel):
    """Summary of import operation."""
    total_transactions: int = Field(..., description="Total number of transactions in import")
    successful_imports: int = Field(..., description="Number of successfully imported transactions")
    failed_imports: int = Field(..., description="Number of failed imports")
    created_categories: int = Field(default=0, description="Number of new categories created")
    errors: List[ImportValidationError] = Field(default_factory=list, description="List of validation errors")


class YAMLImportResponse(BaseModel):
    """Response from YAML import operation."""
    success: bool = Field(..., description="Whether the import operation was successful")
    summary: ImportSummary = Field(..., description="Import operation summary")
    message: str = Field(..., description="Human-readable message about the import")
    created_transaction_ids: List[str] = Field(default_factory=list, description="IDs of successfully created transactions")


class TransactionExportItem(BaseModel):
    """Transaction item for export to YAML."""
    account_name: str
    category_name: Optional[str]
    amount: str  # Export as string to preserve formatting
    description: str
    date: datetime
    destination_account_name: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class YAMLExportRequest(BaseModel):
    """Request for exporting transactions to YAML."""
    account_id: Optional[str] = Field(None, description="Filter by account ID")
    category_id: Optional[str] = Field(None, description="Filter by category ID")
    start_date: Optional[datetime] = Field(None, description="Export transactions from this date")
    end_date: Optional[datetime] = Field(None, description="Export transactions until this date")
    include_inactive: bool = Field(default=False, description="Include inactive/deleted transactions")
    format_amounts: bool = Field(default=True, description="Format amounts with proper decimal places")


class YAMLExportResponse(BaseModel):
    """Response from YAML export operation."""
    yaml_content: str = Field(..., description="YAML content as string")
    transaction_count: int = Field(..., description="Number of transactions exported")
    filename: str = Field(..., description="Suggested filename for the export")