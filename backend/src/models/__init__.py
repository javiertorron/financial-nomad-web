"""
Pydantic models for the Financial Nomad API.
"""
from .auth import (
    Invitation,
    InvitationRequest,
    InvitationResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    Session,
    User,
    UserPreferencesUpdate,
    UserProfile,
    UserRole,
    UserStatus,
)
from .base import IdentifiedModel, SoftDeleteModel, TimestampedModel, UserOwnedModel
from .financial import (
    Account,
    AccountSummary,
    AccountType,
    Budget,
    Category,
    CategorySummary,
    CategoryType,
    RecurringFrequency,
    RecurringTransaction,
    Transaction,
    TransactionSummary,
    TransactionType,
)

__all__ = [
    # Base models
    "TimestampedModel",
    "IdentifiedModel", 
    "SoftDeleteModel",
    "UserOwnedModel",
    # Auth models
    "User",
    "UserRole",
    "UserStatus",
    "UserProfile",
    "UserPreferencesUpdate",
    "Invitation",
    "InvitationRequest",
    "InvitationResponse",
    "Session",
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RegisterResponse",
    # Financial models
    "Account",
    "AccountType",
    "AccountSummary",
    "Category",
    "CategoryType",
    "CategorySummary",
    "Transaction",
    "TransactionType",
    "TransactionSummary",
    "RecurringTransaction",
    "RecurringFrequency",
    "Budget",
]