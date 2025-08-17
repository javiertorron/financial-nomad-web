"""
Tests for custom exceptions.
"""

import pytest

from src.utils.exceptions import (
    AppException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    BusinessLogicError,
    DatabaseError,
    ExternalServiceError,
    RateLimitError
)


@pytest.mark.unit
class TestExceptions:
    """Test custom exceptions."""
    
    def test_app_exception_base(self):
        """Test base AppException."""
        exc = AppException(
            message="Test error",
            code="TEST_ERROR",
            status_code=400,
            details=["Detail 1", "Detail 2"]
        )
        
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.code == "TEST_ERROR"
        assert exc.status_code == 400
        assert exc.details == ["Detail 1", "Detail 2"]
    
    def test_app_exception_defaults(self):
        """Test AppException with default values."""
        exc = AppException("Simple error")
        
        assert exc.message == "Simple error"
        assert exc.code == "UNKNOWN_ERROR"
        assert exc.status_code == 500
        assert exc.details == []
    
    def test_validation_error(self):
        """Test ValidationError."""
        exc = ValidationError("Invalid input", details=["Field required"])
        
        assert exc.message == "Invalid input"
        assert exc.code == "VALIDATION_ERROR"
        assert exc.status_code == 422
        assert exc.details == ["Field required"]
    
    def test_validation_error_defaults(self):
        """Test ValidationError with defaults."""
        exc = ValidationError()
        
        assert exc.message == "Validation error"
        assert exc.code == "VALIDATION_ERROR"
        assert exc.status_code == 422
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        exc = AuthenticationError("Token expired")
        
        assert exc.message == "Token expired"
        assert exc.code == "AUTHENTICATION_ERROR"
        assert exc.status_code == 401
    
    def test_authentication_error_defaults(self):
        """Test AuthenticationError with defaults."""
        exc = AuthenticationError()
        
        assert exc.message == "Authentication failed"
        assert exc.code == "AUTHENTICATION_ERROR"
        assert exc.status_code == 401
    
    def test_authorization_error(self):
        """Test AuthorizationError."""
        exc = AuthorizationError("Admin required")
        
        assert exc.message == "Admin required"
        assert exc.code == "AUTHORIZATION_ERROR"
        assert exc.status_code == 403
    
    def test_authorization_error_defaults(self):
        """Test AuthorizationError with defaults."""
        exc = AuthorizationError()
        
        assert exc.message == "Insufficient permissions"
        assert exc.code == "AUTHORIZATION_ERROR"
        assert exc.status_code == 403
    
    def test_not_found_error(self):
        """Test NotFoundError."""
        exc = NotFoundError("User not found", "user", "123")
        
        assert exc.message == "User with ID '123' not found"
        assert exc.code == "NOT_FOUND"
        assert exc.status_code == 404
        assert "Resource type: user" in exc.details
    
    def test_not_found_error_without_id(self):
        """Test NotFoundError without resource ID."""
        exc = NotFoundError("Custom message", "transaction")
        
        assert exc.message == "Custom message"
        assert exc.code == "NOT_FOUND"
        assert exc.status_code == 404
        assert "Resource type: transaction" in exc.details
    
    def test_not_found_error_defaults(self):
        """Test NotFoundError with defaults."""
        exc = NotFoundError()
        
        assert exc.message == "Resource not found"
        assert exc.code == "NOT_FOUND"
        assert exc.status_code == 404
        assert "Resource type: resource" in exc.details
    
    def test_conflict_error(self):
        """Test ConflictError."""
        exc = ConflictError("Email already exists")
        
        assert exc.message == "Email already exists"
        assert exc.code == "CONFLICT_ERROR"
        assert exc.status_code == 409
    
    def test_business_logic_error(self):
        """Test BusinessLogicError."""
        exc = BusinessLogicError("Cannot delete account with transactions")
        
        assert exc.message == "Cannot delete account with transactions"
        assert exc.code == "BUSINESS_LOGIC_ERROR"
        assert exc.status_code == 422
    
    def test_database_error(self):
        """Test DatabaseError."""
        exc = DatabaseError("Connection failed")
        
        assert exc.message == "Connection failed"
        assert exc.code == "DATABASE_ERROR"
        assert exc.status_code == 500
    
    def test_external_service_error(self):
        """Test ExternalServiceError."""
        exc = ExternalServiceError("Google API error", "google", ["Timeout"])
        
        assert exc.message == "Google API error"
        assert exc.code == "EXTERNAL_SERVICE_ERROR"
        assert exc.status_code == 502
        assert "Timeout" in exc.details
        assert "Service: google" in exc.details
    
    def test_external_service_error_defaults(self):
        """Test ExternalServiceError with defaults."""
        exc = ExternalServiceError()
        
        assert exc.message == "External service error"
        assert exc.code == "EXTERNAL_SERVICE_ERROR"
        assert exc.status_code == 502
        assert "Service: unknown" in exc.details
    
    def test_rate_limit_error(self):
        """Test RateLimitError."""
        exc = RateLimitError("Too many requests", retry_after=60)
        
        assert exc.message == "Too many requests"
        assert exc.code == "RATE_LIMIT_ERROR"
        assert exc.status_code == 429
        assert "Retry after: 60 seconds" in exc.details
    
    def test_rate_limit_error_without_retry_after(self):
        """Test RateLimitError without retry_after."""
        exc = RateLimitError()
        
        assert exc.message == "Rate limit exceeded"
        assert exc.code == "RATE_LIMIT_ERROR"
        assert exc.status_code == 429
        assert exc.details == []