"""
Tests for custom validators.
"""

import pytest
from datetime import date, timedelta

from src.utils.validators import (
    validate_email,
    validate_amount_centimos,
    validate_future_date,
    validate_hex_color,
    validate_bank_last_four_digits,
    validate_amount_euros,
    validate_percentage
)


@pytest.mark.unit
class TestValidators:
    """Test custom validators."""
    
    def test_validate_email_valid_formats(self):
        """Test email validation with valid formats."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@456.com",
            "Test@Example.COM"  # Case insensitive
        ]
        
        for email in valid_emails:
            result = validate_email(email)
            assert result == email.strip().lower()
    
    def test_validate_email_invalid_formats(self):
        """Test email validation with invalid formats."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user@.com",
            "user@domain",
            "user space@example.com",
            ""
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email format"):
                validate_email(email)
    
    def test_validate_amount_centimos_valid(self):
        """Test amount validation with valid values."""
        valid_amounts = [1, 100, 1000, 999999999]
        
        for amount in valid_amounts:
            result = validate_amount_centimos(amount)
            assert result == amount
    
    def test_validate_amount_centimos_invalid(self):
        """Test amount validation with invalid values."""
        invalid_amounts = [0, -1, -1000, 100_000_000_001]
        
        for amount in invalid_amounts:
            with pytest.raises(ValueError):
                validate_amount_centimos(amount)
    
    def test_validate_future_date_valid(self):
        """Test future date validation with valid dates."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        # Past and today should be valid
        assert validate_future_date(yesterday) == yesterday
        assert validate_future_date(today) == today
        
        # Tomorrow should be valid with default 1 day limit
        assert validate_future_date(tomorrow) == tomorrow
    
    def test_validate_future_date_invalid(self):
        """Test future date validation with invalid dates."""
        today = date.today()
        day_after_tomorrow = today + timedelta(days=2)
        
        # Day after tomorrow should be invalid with default 1 day limit
        with pytest.raises(ValueError, match="Date cannot be more than 1 day"):
            validate_future_date(day_after_tomorrow)
    
    def test_validate_future_date_custom_limit(self):
        """Test future date validation with custom limit."""
        today = date.today()
        next_week = today + timedelta(days=7)
        next_month = today + timedelta(days=31)
        
        # Next week should be valid with 30 day limit
        assert validate_future_date(next_week, max_days_future=30) == next_week
        
        # Next month should be invalid with 30 day limit
        with pytest.raises(ValueError, match="Date cannot be more than 30 day"):
            validate_future_date(next_month, max_days_future=30)
    
    def test_validate_hex_color_valid(self):
        """Test hex color validation with valid colors."""
        valid_colors = [
            "#FF0000",
            "#00FF00", 
            "#0000FF",
            "#123456",
            "#ABCDEF",
            "FF0000",  # Without #
            "#ff0000",  # Lowercase
            "ff0000"   # Lowercase without #
        ]
        
        for color in valid_colors:
            result = validate_hex_color(color)
            assert result.startswith("#")
            assert len(result) == 7
            assert result.isupper()
    
    def test_validate_hex_color_invalid(self):
        """Test hex color validation with invalid colors."""
        invalid_colors = [
            "#FFF",      # Too short
            "#GGGGGG",   # Invalid hex characters
            "#1234567",  # Too long
            "red",       # Color name
            ""           # Empty
        ]
        
        for color in invalid_colors:
            with pytest.raises(ValueError, match="Invalid hex color format"):
                validate_hex_color(color)
    
    def test_validate_bank_last_four_digits_valid(self):
        """Test bank digits validation with valid values."""
        valid_digits = ["1234", "0000", "9999", " 1234 "]
        
        for digits in valid_digits:
            result = validate_bank_last_four_digits(digits)
            assert len(result) == 4
            assert result.isdigit()
    
    def test_validate_bank_last_four_digits_invalid(self):
        """Test bank digits validation with invalid values."""
        invalid_digits = ["123", "12345", "ABCD", "12a4", ""]
        
        for digits in invalid_digits:
            with pytest.raises(ValueError, match="Must be exactly 4 digits"):
                validate_bank_last_four_digits(digits)
    
    def test_validate_amount_euros_valid(self):
        """Test euro amount validation and conversion."""
        test_cases = [
            (1.0, 100),
            (10.50, 1050),
            (100.99, 10099),
            (0.01, 1)
        ]
        
        for euros, expected_centimos in test_cases:
            result = validate_amount_euros(euros)
            assert result == expected_centimos
    
    def test_validate_amount_euros_invalid(self):
        """Test euro amount validation with invalid values."""
        invalid_amounts = [0, -1.0, -10.50]
        
        for amount in invalid_amounts:
            with pytest.raises(ValueError, match="Amount must be positive"):
                validate_amount_euros(amount)
    
    def test_validate_percentage_valid(self):
        """Test percentage validation with valid values."""
        valid_percentages = [0, 0.5, 25.5, 50, 100]
        
        for percentage in valid_percentages:
            result = validate_percentage(percentage)
            assert result == percentage
    
    def test_validate_percentage_invalid(self):
        """Test percentage validation with invalid values."""
        invalid_percentages = [-1, -0.1, 100.1, 150]
        
        for percentage in invalid_percentages:
            with pytest.raises(ValueError, match="Percentage must be between 0 and 100"):
                validate_percentage(percentage)