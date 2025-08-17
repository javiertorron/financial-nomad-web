"""
Tests for configuration module.
"""

import pytest
from pydantic import ValidationError

from src.config import Settings


@pytest.mark.unit
class TestSettings:
    """Test Settings configuration."""
    
    def test_settings_with_minimal_config(self):
        """Test settings with minimal required config."""
        settings = Settings(
            secret_key="test-secret",
            google_client_id="test-client-id",
            firestore_project_id="test-project"
        )
        
        assert settings.secret_key == "test-secret"
        assert settings.google_client_id == "test-client-id"
        assert settings.firestore_project_id == "test-project"
        assert settings.environment == "production"  # default
        assert settings.debug is False  # default
    
    def test_settings_with_development_config(self):
        """Test settings for development environment."""
        settings = Settings(
            secret_key="dev-secret",
            google_client_id="dev-client-id",
            firestore_project_id="dev-project",
            environment="development",
            debug=True
        )
        
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.debug is True
        assert settings.docs_url == "/docs"
        assert settings.redoc_url == "/redoc"
        assert settings.openapi_url == "/openapi.json"
    
    def test_settings_with_production_config(self):
        """Test settings for production environment."""
        settings = Settings(
            secret_key="prod-secret",
            google_client_id="prod-client-id",
            firestore_project_id="prod-project",
            environment="production",
            debug=False
        )
        
        assert settings.is_production is True
        assert settings.is_development is False
        assert settings.debug is False
        assert settings.docs_url is None
        assert settings.redoc_url is None
        assert settings.openapi_url is None
    
    def test_cors_origins_parsing_from_string_list(self):
        """Test CORS origins parsing from string representation of list."""
        settings = Settings(
            secret_key="test-secret",
            google_client_id="test-client-id",
            firestore_project_id="test-project",
            cors_origins="['http://localhost:3000', 'http://localhost:4200']"
        )
        
        assert settings.cors_origins == ['http://localhost:3000', 'http://localhost:4200']
    
    def test_cors_origins_parsing_from_comma_separated(self):
        """Test CORS origins parsing from comma-separated string."""
        settings = Settings(
            secret_key="test-secret",
            google_client_id="test-client-id",
            firestore_project_id="test-project",
            cors_origins="http://localhost:3000, http://localhost:4200"
        )
        
        assert settings.cors_origins == ['http://localhost:3000', 'http://localhost:4200']
    
    def test_cors_origins_parsing_from_list(self):
        """Test CORS origins parsing from actual list."""
        origins = ['http://localhost:3000', 'http://localhost:4200']
        settings = Settings(
            secret_key="test-secret",
            google_client_id="test-client-id",
            firestore_project_id="test-project",
            cors_origins=origins
        )
        
        assert settings.cors_origins == origins
    
    def test_invalid_log_level_raises_error(self):
        """Test that invalid log level raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                secret_key="test-secret",
                google_client_id="test-client-id",
                firestore_project_id="test-project",
                log_level="INVALID"
            )
        
        assert "Invalid log level" in str(exc_info.value)
    
    def test_valid_log_levels(self):
        """Test all valid log levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            settings = Settings(
                secret_key="test-secret",
                google_client_id="test-client-id",
                firestore_project_id="test-project",
                log_level=level.lower()  # Test case insensitive
            )
            assert settings.log_level == level
    
    def test_invalid_environment_raises_error(self):
        """Test that invalid environment raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                secret_key="test-secret",
                google_client_id="test-client-id",
                firestore_project_id="test-project",
                environment="invalid"
            )
        
        assert "Invalid environment" in str(exc_info.value)
    
    def test_valid_environments(self):
        """Test all valid environments."""
        valid_envs = ["development", "testing", "staging", "production"]
        
        for env in valid_envs:
            settings = Settings(
                secret_key="test-secret",
                google_client_id="test-client-id",
                firestore_project_id="test-project",
                environment=env.upper()  # Test case insensitive
            )
            assert settings.environment == env
    
    def test_session_expire_hours_validation(self):
        """Test session expire hours validation."""
        # Valid values
        for hours in [1, 24, 168]:
            settings = Settings(
                secret_key="test-secret",
                google_client_id="test-client-id",
                firestore_project_id="test-project",
                session_expire_hours=hours
            )
            assert settings.session_expire_hours == hours
        
        # Invalid values
        with pytest.raises(ValidationError):
            Settings(
                secret_key="test-secret",
                google_client_id="test-client-id",
                firestore_project_id="test-project",
                session_expire_hours=0  # Too low
            )
        
        with pytest.raises(ValidationError):
            Settings(
                secret_key="test-secret",
                google_client_id="test-client-id",
                firestore_project_id="test-project",
                session_expire_hours=200  # Too high
            )
    
    def test_port_validation(self):
        """Test port number validation."""
        # Valid port
        settings = Settings(
            secret_key="test-secret",
            google_client_id="test-client-id",
            firestore_project_id="test-project",
            port=8080
        )
        assert settings.port == 8080
        
        # Invalid ports
        with pytest.raises(ValidationError):
            Settings(
                secret_key="test-secret",
                google_client_id="test-client-id",
                firestore_project_id="test-project",
                port=0  # Too low
            )
        
        with pytest.raises(ValidationError):
            Settings(
                secret_key="test-secret",
                google_client_id="test-client-id",
                firestore_project_id="test-project",
                port=99999  # Too high
            )
    
    def test_missing_required_fields_raises_error(self):
        """Test that missing required fields raise validation errors."""
        # Missing secret_key
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                google_client_id="test-client-id",
                firestore_project_id="test-project"
            )
        assert "secret_key" in str(exc_info.value)
        
        # Missing google_client_id
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                secret_key="test-secret",
                firestore_project_id="test-project"
            )
        assert "google_client_id" in str(exc_info.value)
        
        # Missing firestore_project_id
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                secret_key="test-secret",
                google_client_id="test-client-id"
            )
        assert "firestore_project_id" in str(exc_info.value)