"""
Financial domain models: Account, Category, Transaction, etc.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .base import UserOwnedModel


class AccountType(str, Enum):
    """Types of financial accounts."""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    INVESTMENT = "investment"
    LOAN = "loan"
    OTHER = "other"


class CategoryType(str, Enum):
    """Types of transaction categories."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class TransactionType(str, Enum):
    """Types of transactions."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class RecurringFrequency(str, Enum):
    """Frequency for recurring transactions."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class Account(UserOwnedModel):
    """Financial account model."""
    
    name: str = Field(..., min_length=1, max_length=100)
    account_type: AccountType
    balance: Decimal = Field(default=Decimal("0.00"))
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)
    
    # Display settings
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    
    @validator("currency")
    def validate_currency(cls, v):
        """Validate currency code."""
        return v.upper()
    
    @validator("balance")
    def validate_balance(cls, v):
        """Validate balance precision."""
        if v.as_tuple().exponent < -2:
            raise ValueError("Balance cannot have more than 2 decimal places")
        return v


class Category(UserOwnedModel):
    """Transaction category model."""
    
    name: str = Field(..., min_length=1, max_length=100)
    category_type: CategoryType
    parent_id: Optional[str] = Field(None, description="Parent category for subcategories")
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)
    is_system: bool = Field(default=False, description="System-managed category that cannot be deleted by users")
    
    # Display settings
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    
    # Budget settings
    monthly_budget: Optional[Decimal] = Field(None, gt=0)
    
    @validator("monthly_budget")
    def validate_monthly_budget(cls, v):
        """Validate monthly budget precision."""
        if v and v.as_tuple().exponent < -2:
            raise ValueError("Monthly budget cannot have more than 2 decimal places")
        return v


class Transaction(UserOwnedModel):
    """Financial transaction model."""
    
    # Basic transaction data
    amount: Decimal = Field(...)
    description: str = Field(..., min_length=1, max_length=200)
    transaction_type: TransactionType
    transaction_date: datetime
    
    # Account relationships
    account_id: str = Field(..., description="Source/destination account")
    destination_account_id: Optional[str] = Field(None, description="Destination account for transfers")
    
    # Categorization
    category_id: str = Field(..., description="Transaction category")
    subcategory_id: Optional[str] = Field(None, description="Transaction subcategory")
    
    # Additional metadata
    reference: Optional[str] = Field(None, max_length=100, description="External reference number")
    notes: Optional[str] = Field(None, max_length=1000)
    tags: List[str] = Field(default_factory=list, max_items=10)
    
    # Import metadata
    import_id: Optional[str] = Field(None, description="ID from imported data")
    import_source: Optional[str] = Field(None, description="Source of imported data")
    
    # Status
    is_confirmed: bool = Field(default=True)
    is_reconciled: bool = Field(default=False)
    is_active: bool = Field(default=True, description="Whether the transaction is active (not deleted)")
    
    @validator("amount")
    def validate_amount(cls, v):
        """Validate amount precision and sign."""
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than 2 decimal places")
        if v == 0:
            raise ValueError("Amount cannot be zero")
        return v
    
    @validator("tags")
    def validate_tags(cls, v):
        """Validate tags format."""
        for tag in v:
            if not tag.strip() or len(tag) > 50:
                raise ValueError("Tags must be non-empty and max 50 characters")
        return [tag.strip().lower() for tag in v]


class RecurringTransaction(UserOwnedModel):
    """Recurring transaction template."""
    
    # Template data
    name: str = Field(..., min_length=1, max_length=100)
    amount: Decimal = Field(...)
    description: str = Field(..., min_length=1, max_length=200)
    transaction_type: TransactionType
    
    # Accounts and categories
    account_id: str
    to_account_id: Optional[str] = None
    category_id: str
    subcategory_id: Optional[str] = None
    
    # Recurrence settings
    frequency: RecurringFrequency
    start_date: datetime
    end_date: Optional[datetime] = None
    next_execution: datetime
    
    # Status
    is_active: bool = Field(default=True)
    last_executed: Optional[datetime] = None
    
    # Additional metadata
    notes: Optional[str] = Field(None, max_length=1000)
    tags: List[str] = Field(default_factory=list, max_items=10)
    
    @validator("amount")
    def validate_amount(cls, v):
        """Validate amount precision."""
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than 2 decimal places")
        if v == 0:
            raise ValueError("Amount cannot be zero")
        return v
    
    @validator("end_date")
    def validate_end_date(cls, v, values):
        """Validate end date is after start date."""
        if v and "start_date" in values and v <= values["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class Budget(UserOwnedModel):
    """Budget model for categories."""
    
    name: str = Field(..., min_length=1, max_length=100)
    category_id: str
    amount: Decimal = Field(..., gt=0)
    period_start: datetime
    period_end: datetime
    
    # Status tracking
    spent_amount: Decimal = Field(default=Decimal("0.00"))
    is_active: bool = Field(default=True)
    
    # Alerts
    alert_threshold: Optional[Decimal] = Field(None, ge=0, le=100)  # Percentage
    alert_sent: bool = Field(default=False)
    
    @property
    def remaining_amount(self) -> Decimal:
        """Calculate remaining budget amount."""
        return self.amount - self.spent_amount
    
    @property
    def percentage_used(self) -> Decimal:
        """Calculate percentage of budget used."""
        if self.amount == 0:
            return Decimal("0")
        return (self.spent_amount / self.amount) * 100
    
    @validator("period_end")
    def validate_period_end(cls, v, values):
        """Validate period end is after start."""
        if "period_start" in values and v <= values["period_start"]:
            raise ValueError("Period end must be after period start")
        return v


# DTOs for API responses
class AccountSummary(BaseModel):
    """Account summary for listings."""
    id: str
    name: str
    account_type: AccountType
    balance: Decimal
    currency: str
    description: Optional[str]
    is_active: bool
    color: Optional[str]
    icon: Optional[str]


class TransactionSummary(BaseModel):
    """Transaction summary for listings."""
    id: str
    amount: Decimal
    description: str
    transaction_type: Optional[TransactionType] = None
    transaction_date: datetime
    account_name: Optional[str] = None
    category_name: Optional[str] = None
    is_confirmed: bool = True
    destination_account_id: Optional[str] = None
    is_active: bool = True


class CategorySummary(BaseModel):
    """Category summary for listings."""
    id: str
    name: str
    category_type: CategoryType
    parent_name: Optional[str] = None
    monthly_budget: Optional[Decimal] = None
    is_active: bool
    is_system: bool
    color: Optional[str] = None
    icon: Optional[str] = None


# DTOs for API requests
class AccountCreateRequest(BaseModel):
    """Request to create a new account."""
    name: str = Field(..., min_length=1, max_length=100)
    account_type: AccountType
    balance: Decimal = Field(default=Decimal("0.00"))
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)


class AccountUpdateRequest(BaseModel):
    """Request to update an account."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    balance: Optional[Decimal] = None
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)


class CategoryCreateRequest(BaseModel):
    """Request to create a new category."""
    name: str = Field(..., min_length=1, max_length=100)
    category_type: CategoryType
    parent_id: Optional[str] = Field(None, description="Parent category for subcategories")
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    monthly_budget: Optional[Decimal] = Field(None, gt=0)


class CategoryUpdateRequest(BaseModel):
    """Request to update a category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parent_id: Optional[str] = Field(None, description="Parent category for subcategories")
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    monthly_budget: Optional[Decimal] = Field(None, gt=0)


class TransactionCreateRequest(BaseModel):
    """Request to create a new transaction."""
    amount: Decimal = Field(..., description="Transaction amount (positive for income, negative for expense)")
    description: str = Field(..., min_length=1, max_length=200)
    transaction_type: TransactionType
    transaction_date: datetime
    account_id: str = Field(..., description="Source/destination account")
    destination_account_id: Optional[str] = Field(None, description="Destination account for transfers")
    category_id: str = Field(..., description="Transaction category")
    subcategory_id: Optional[str] = Field(None, description="Transaction subcategory")
    reference: Optional[str] = Field(None, max_length=100, description="External reference number")
    notes: Optional[str] = Field(None, max_length=1000)
    tags: List[str] = Field(default_factory=list, max_items=10)
    is_confirmed: bool = Field(default=True)


class TransactionUpdateRequest(BaseModel):
    """Request to update a transaction."""
    amount: Optional[Decimal] = None
    description: Optional[str] = Field(None, min_length=1, max_length=200)
    transaction_date: Optional[datetime] = None
    account_id: Optional[str] = Field(None, description="Source/destination account")
    destination_account_id: Optional[str] = Field(None, description="Destination account for transfers")
    category_id: Optional[str] = Field(None, description="Transaction category")
    subcategory_id: Optional[str] = Field(None, description="Transaction subcategory")
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = Field(None, max_items=10)
    is_confirmed: Optional[bool] = None
    is_reconciled: Optional[bool] = None


class TransactionResponse(BaseModel):
    """Complete transaction response."""
    id: str
    amount: Decimal
    description: str
    transaction_type: TransactionType
    transaction_date: datetime
    account_id: str
    to_account_id: Optional[str]
    category_id: str
    subcategory_id: Optional[str]
    reference: Optional[str]
    notes: Optional[str]
    tags: List[str]
    is_confirmed: bool
    is_reconciled: bool
    created_at: datetime
    updated_at: datetime
    

class AccountResponse(BaseModel):
    """Complete account response."""
    id: str
    name: str
    account_type: AccountType
    balance: Decimal
    currency: str
    description: Optional[str]
    is_active: bool
    color: Optional[str]
    icon: Optional[str]
    created_at: datetime
    updated_at: datetime


class CategoryResponse(BaseModel):
    """Complete category response."""
    id: str
    name: str
    category_type: CategoryType
    parent_id: Optional[str]
    description: Optional[str]
    is_active: bool
    color: Optional[str]
    icon: Optional[str]
    monthly_budget: Optional[Decimal]
    created_at: datetime
    updated_at: datetime


# DTOs for Budgets
class BudgetSummary(BaseModel):
    """Budget summary for listings."""
    id: str
    name: str
    category_id: str
    category_name: str
    amount: Decimal
    spent_amount: Decimal
    percentage_used: Decimal
    remaining_amount: Decimal
    period_start: datetime
    period_end: datetime
    is_active: bool
    alert_threshold: Optional[Decimal]


class BudgetResponse(BaseModel):
    """Complete budget response."""
    id: str
    name: str
    category_id: str
    amount: Decimal
    period_start: datetime
    period_end: datetime
    spent_amount: Decimal
    is_active: bool
    alert_threshold: Optional[Decimal]
    alert_sent: bool
    created_at: datetime
    updated_at: datetime


class BudgetCreateRequest(BaseModel):
    """Request to create a new budget."""
    name: str = Field(..., min_length=1, max_length=100)
    category_id: str
    amount: Decimal = Field(..., gt=0)
    period_start: datetime
    period_end: datetime
    alert_threshold: Optional[Decimal] = Field(None, ge=0, le=100)
    
    @validator("period_end")
    def validate_period_end(cls, v, values):
        """Validate period end is after start."""
        if "period_start" in values and v <= values["period_start"]:
            raise ValueError("Period end must be after period start")
        return v


class BudgetUpdateRequest(BaseModel):
    """Request to update a budget."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    amount: Optional[Decimal] = Field(None, gt=0)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    is_active: Optional[bool] = None
    alert_threshold: Optional[Decimal] = Field(None, ge=0, le=100)


# DTOs for Recurring Transactions
class RecurringTransactionSummary(BaseModel):
    """Recurring transaction summary for listings."""
    id: str
    name: str
    amount: Decimal
    description: str
    transaction_type: TransactionType
    frequency: RecurringFrequency
    account_name: str
    category_name: str
    next_execution: datetime
    is_active: bool


class RecurringTransactionResponse(BaseModel):
    """Complete recurring transaction response."""
    id: str
    name: str
    amount: Decimal
    description: str
    transaction_type: TransactionType
    account_id: str
    to_account_id: Optional[str]
    category_id: str
    subcategory_id: Optional[str]
    frequency: RecurringFrequency
    start_date: datetime
    end_date: Optional[datetime]
    next_execution: datetime
    is_active: bool
    last_executed: Optional[datetime]
    notes: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime


class RecurringTransactionCreateRequest(BaseModel):
    """Request to create a recurring transaction."""
    name: str = Field(..., min_length=1, max_length=100)
    amount: Decimal = Field(..., description="Transaction amount")
    description: str = Field(..., min_length=1, max_length=200)
    transaction_type: TransactionType
    account_id: str
    to_account_id: Optional[str] = None
    category_id: str
    subcategory_id: Optional[str] = None
    frequency: RecurringFrequency
    start_date: datetime
    end_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)
    tags: List[str] = Field(default_factory=list, max_items=10)
    
    @validator("end_date")
    def validate_end_date(cls, v, values):
        """Validate end date is after start date."""
        if v and "start_date" in values and v <= values["start_date"]:
            raise ValueError("End date must be after start date")
        return v


class RecurringTransactionUpdateRequest(BaseModel):
    """Request to update a recurring transaction."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    amount: Optional[Decimal] = None
    description: Optional[str] = Field(None, min_length=1, max_length=200)
    account_id: Optional[str] = None
    to_account_id: Optional[str] = None
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    frequency: Optional[RecurringFrequency] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = Field(None, max_items=10)