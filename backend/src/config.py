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
        case_sensitive=False,
        extra="ignore"
    )
    
    # App settings
    app_name: str = Field(default="financial-nomad-api", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="production", description="Environment name")
    
    # Security
    jwt_secret_key: str = Field(..., description="Secret key for JWT tokens")
    session_expire_hours: int = Field(default=24, ge=1, le=168, description="Session expiration in hours")
    
    # Database
    firestore_project_id: str = Field(..., description="Firestore project ID")
    firestore_database: str = Field(default="(default)", description="Firestore database name")
    use_firestore_emulator: bool = Field(default=False, description="Use Firestore emulator")
    firestore_emulator_host: str = Field(default="localhost:8081", description="Firestore emulator host")
    google_credentials_path: Optional[str] = Field(default=None, description="Path to Google credentials JSON file")
    
    # API
    api_prefix: str = Field(default="/api/v1", description="API path prefix")
    cors_origins: str = Field(default="", description="CORS allowed origins (comma-separated)")
    rate_limit_per_minute: int = Field(default=100, ge=1, description="Rate limit per minute")
    
    # External APIs
    google_auth_url: str = Field(
        default="https://oauth2.googleapis.com/tokeninfo",
        description="Google token verification URL"
    )
    
    # Asana integration
    asana_client_id: Optional[str] = Field(default=None, description="Asana OAuth client ID")
    asana_client_secret: Optional[str] = Field(default=None, description="Asana OAuth client secret")
    asana_redirect_uri: Optional[str] = Field(
        default=None, 
        description="Asana OAuth redirect URI"
    )
    asana_encryption_key: Optional[str] = Field(
        default=None, 
        description="Key for encrypting Asana tokens"
    )
    
    # Google Drive integration
    google_client_id: Optional[str] = Field(default=None, description="Google OAuth client ID")
    google_client_secret: Optional[str] = Field(default=None, description="Google OAuth client secret")
    google_redirect_uri: Optional[str] = Field(
        default=None,
        description="Google OAuth redirect URI"
    )
    drive_encryption_key: Optional[str] = Field(
        default=None,
        description="Key for encrypting Drive tokens"
    )
    
    # Backup and export settings
    backup_encryption_key: Optional[str] = Field(
        default=None,
        description="Key for encrypting backup files"
    )
    backup_retention_days: int = Field(default=90, ge=1, le=365, description="Default backup retention in days")
    export_temp_dir: Optional[str] = Field(default=None, description="Temporary directory for exports")
    max_export_size_mb: int = Field(default=500, ge=1, le=2048, description="Maximum export file size in MB")
    
    # Monitoring and logging
    log_level: str = Field(default="INFO", description="Logging level")
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, ge=1, le=65535, description="Server port")
    workers: int = Field(default=1, ge=1, description="Number of worker processes")
    
    # Email and notification settings
    smtp_server: Optional[str] = Field(default=None, description="SMTP server for email notifications")
    smtp_port: Optional[int] = Field(default=587, description="SMTP port")
    smtp_username: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    from_email: Optional[str] = Field(default=None, description="From email address")
    from_name: Optional[str] = Field(default="Financial Nomad", description="From name for emails")
    
    # Push notification settings
    fcm_server_key: Optional[str] = Field(default=None, description="FCM server key for Android push notifications")
    apns_key_file: Optional[str] = Field(default=None, description="APNS key file path for iOS push notifications")
    apns_key_id: Optional[str] = Field(default=None, description="APNS key ID")
    apns_team_id: Optional[str] = Field(default=None, description="APNS team ID")
    
    # Frontend settings
    frontend_url: str = Field(default="http://localhost:4200", description="Frontend application URL")
    
    # Redis/Caching settings
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    cache_default_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    cache_max_memory: int = Field(default=100, description="Max cache memory in MB")
    
    def get_cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
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