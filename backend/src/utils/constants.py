"""
Application constants.
"""

from enum import Enum


class UserRole(str, Enum):
    """User roles in the system."""
    USER = "user"
    ADMIN = "admin"


class Language(str, Enum):
    """Supported languages."""
    ES = "es"
    EN = "en"


class Currency(str, Enum):
    """Supported currencies."""
    EUR = "EUR"
    USD = "USD"


class TransactionType(str, Enum):
    """Transaction types."""
    INCOME = "income"
    EXPENSE = "expense"


class AccountType(str, Enum):
    """Account types."""
    BANK = "bank"
    CASH = "cash"
    CARD = "card"


class InvitationStatus(str, Enum):
    """Invitation statuses."""
    PENDING = "pending"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    REVOKED = "revoked"


# API Response constants
API_RESPONSE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}

# Pagination constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Rate limiting constants
DEFAULT_RATE_LIMIT = 100  # requests per minute

# Session constants
DEFAULT_SESSION_EXPIRE_HOURS = 24
MAX_SESSION_EXPIRE_HOURS = 168  # 7 days

# Validation constants
MIN_PASSWORD_LENGTH = 8
MAX_DESCRIPTION_LENGTH = 200
MAX_NAME_LENGTH = 100

# File upload constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

# Currency formatting
CURRENCY_DECIMALS = 2
AMOUNT_SCALE_FACTOR = 100  # Store amounts in centimos