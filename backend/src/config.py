"""
Configuration module using Pydantic Settings.
Handles all environment variables and app configuration.
"""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # App settings
    app_name: str = Field(default="financial-nomad-api", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="production", description="Environment name")
    
    # Security
    secret_key: str = Field(..., description="Secret key for JWT tokens")
    google_client_id: str = Field(..., description="Google OAuth client ID")
    session_expire_hours: int = Field(default=24, ge=1, le=168, description="Session expiration in hours")
    
    # Database
    firestore_project_id: str = Field(..., description="Firestore project ID")
    firestore_database: str = Field(default="(default)", description="Firestore database name")
    use_firestore_emulator: bool = Field(default=False, description="Use Firestore emulator")
    firestore_emulator_host: str = Field(default="localhost:8081", description="Firestore emulator host")
    google_credentials_path: Optional[str] = Field(default=None, description="Path to Google credentials JSON file")
    
    # API
    api_prefix: str = Field(default="/api/v1", description="API path prefix")
    cors_origins: List[str] = Field(default=[], description="CORS allowed origins")
    rate_limit_per_minute: int = Field(default=100, ge=1, description="Rate limit per minute")
    
    # External APIs
    google_auth_url: str = Field(
        default="https://oauth2.googleapis.com/tokeninfo",
        description="Google token verification URL"
    )
    
    # Monitoring and logging
    log_level: str = Field(default="INFO", description="Logging level")
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, ge=1, le=65535, description="Server port")
    workers: int = Field(default=1, ge=1, description="Number of worker processes")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Handle string format like "['http://localhost:3000', 'http://localhost:4200']"
            if v.startswith("[") and v.endswith("]"):
                import ast
                try:
                    return ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    return []
            # Handle comma-separated string
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v or []
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment."""
        valid_envs = ["development", "testing", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid environment. Must be one of: {valid_envs}")
        return v.lower()
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == "testing"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    @property
    def docs_url(self) -> Optional[str]:
        """Get docs URL based on environment."""
        return "/docs" if self.debug or self.is_development else None
    
    @property
    def redoc_url(self) -> Optional[str]:
        """Get ReDoc URL based on environment."""
        return "/redoc" if self.debug or self.is_development else None
    
    @property
    def openapi_url(self) -> Optional[str]:
        """Get OpenAPI URL based on environment."""
        return "/openapi.json" if self.debug or self.is_development else None


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance. Useful for dependency injection."""
    return settings