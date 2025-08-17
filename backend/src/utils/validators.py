"""
Custom validators for Pydantic models.
"""

import re
from datetime import date, datetime, timedelta
from typing import Any

from .constants import AMOUNT_SCALE_FACTOR


def validate_email(email: str) -> str:
    """Validate email format."""
    email = email.strip().lower()
    
    # Basic email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise ValueError("Invalid email format")
    
    return email


def validate_amount_centimos(amount: int) -> int:
    """Validate amount in centimos."""
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    # Check for reasonable upper limit (1 billion euros = 100 billion centimos)
    if amount > 100_000_000_000:
        raise ValueError("Amount too large")
    
    return amount


def validate_future_date(date_value: date, max_days_future: int = 1) -> date:
    """Validate that date is not too far in the future."""
    today = date.today()
    max_future_date = today + timedelta(days=max_days_future)
    
    if date_value > max_future_date:
        raise ValueError(f"Date cannot be more than {max_days_future} day(s) in the future")
    
    return date_value


def validate_hex_color(color: str) -> str:
    """Validate hex color format."""
    color = color.strip()
    
    if not color.startswith('#'):
        color = f"#{color}"
    
    hex_pattern = r'^#[0-9A-Fa-f]{6}$'
    
    if not re.match(hex_pattern, color):
        raise ValueError("Invalid hex color format. Use #RRGGBB")
    
    return color.upper()


def validate_phone_number(phone: str) -> str:
    """Validate phone number format."""
    # Remove all non-digit characters
    phone_digits = re.sub(r'\D', '', phone)
    
    # Check length (7-15 digits as per international standards)
    if len(phone_digits) < 7 or len(phone_digits) > 15:
        raise ValueError("Phone number must be between 7 and 15 digits")
    
    return phone_digits


def validate_password_strength(password: str) -> str:
    """Validate password strength."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        raise ValueError("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character")
    
    return password


def validate_slug(slug: str) -> str:
    """Validate URL slug format."""
    slug = slug.strip().lower()
    
    # Check basic format
    slug_pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
    
    if not re.match(slug_pattern, slug):
        raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
    
    if len(slug) < 3 or len(slug) > 50:
        raise ValueError("Slug must be between 3 and 50 characters")
    
    return slug


def validate_bank_last_four_digits(digits: str) -> str:
    """Validate bank card last four digits."""
    digits = digits.strip()
    
    if not re.match(r'^\d{4}$', digits):
        raise ValueError("Must be exactly 4 digits")
    
    return digits


def validate_amount_euros(amount: float) -> int:
    """Convert and validate amount from euros to centimos."""
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    # Convert to centimos
    centimos = int(round(amount * AMOUNT_SCALE_FACTOR))
    
    return validate_amount_centimos(centimos)


def validate_percentage(percentage: float) -> float:
    """Validate percentage value."""
    if percentage < 0 or percentage > 100:
        raise ValueError("Percentage must be between 0 and 100")
    
    return percentage


def validate_timezone(timezone: str) -> str:
    """Validate timezone string."""
    try:
        import zoneinfo
        zoneinfo.ZoneInfo(timezone)
        return timezone
    except Exception:
        # Fallback to basic validation
        if '/' not in timezone:
            raise ValueError("Invalid timezone format")
        return timezone