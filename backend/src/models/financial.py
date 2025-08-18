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
    parent_id: Optional[UUID] = Field(None, description="Parent category for subcategories")
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)
    
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
    account_id: UUID = Field(..., description="Source/destination account")
    to_account_id: Optional[UUID] = Field(None, description="Destination account for transfers")
    
    # Categorization
    category_id: UUID = Field(..., description="Transaction category")
    subcategory_id: Optional[UUID] = Field(None, description="Transaction subcategory")
    
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
    account_id: UUID
    to_account_id: Optional[UUID] = None
    category_id: UUID
    subcategory_id: Optional[UUID] = None
    
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
    category_id: UUID
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
    id: UUID
    name: str
    account_type: AccountType
    balance: Decimal
    currency: str
    is_active: bool
    color: Optional[str]
    icon: Optional[str]


class TransactionSummary(BaseModel):
    """Transaction summary for listings."""
    id: UUID
    amount: Decimal
    description: str
    transaction_type: TransactionType
    transaction_date: datetime
    account_name: str
    category_name: str
    is_confirmed: bool


class CategorySummary(BaseModel):
    """Category summary for listings."""
    id: UUID
    name: str
    category_type: CategoryType
    parent_name: Optional[str]
    monthly_budget: Optional[Decimal]
    is_active: bool
    color: Optional[str]
    icon: Optional[str]