"""
Custom exceptions for the application.
All business logic and technical exceptions are defined here.
"""

from typing import Any, Dict, List, Optional


class AppException(Exception):
    """Base exception for all application exceptions."""
    
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
        details: Optional[List[str]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []
        super().__init__(self.message)


class ValidationError(AppException):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details
        )


class AuthenticationError(AppException):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details
        )


class AuthorizationError(AppException):
    """Raised when authorization fails."""
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details
        )


class NotFoundError(AppException):
    """Raised when a resource is not found."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: str = "resource",
        resource_id: Optional[str] = None
    ):
        if resource_id:
            message = f"{resource_type.title()} with ID '{resource_id}' not found"
        
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=[f"Resource type: {resource_type}"]
        )


class ConflictError(AppException):
    """Raised when a resource conflict occurs."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            code="CONFLICT_ERROR",
            status_code=409,
            details=details
        )


class BusinessLogicError(AppException):
    """Raised when business logic rules are violated."""
    
    def __init__(
        self,
        message: str = "Business logic error",
        details: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            code="BUSINESS_LOGIC_ERROR",
            status_code=422,
            details=details
        )


class DatabaseError(AppException):
    """Raised when database operations fail."""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


class ExternalServiceError(AppException):
    """Raised when external service calls fail."""
    
    def __init__(
        self,
        message: str = "External service error",
        service_name: str = "unknown",
        details: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details=details or [f"Service: {service_name}"]
        )


class RateLimitError(AppException):
    """Raised when rate limits are exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ):
        details = []
        if retry_after:
            details.append(f"Retry after: {retry_after} seconds")
        
        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            status_code=429,
            details=details
        )