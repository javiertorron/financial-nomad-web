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
            jwt_secret_key="test-secret",
            firestore_project_id="test-project"
        )
        
        assert settings.jwt_secret_key == "test-secret"
        assert settings.firestore_project_id == "test-project"
        # debug and environment may be overridden by test environment
    
    def test_settings_with_development_config(self):
        """Test settings for development environment."""
        settings = Settings(
            jwt_secret_key="dev-secret",
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
            jwt_secret_key="prod-secret",
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
            jwt_secret_key="test-secret",
            firestore_project_id="test-project",
            cors_origins="http://localhost:3000,http://localhost:4200"
        )
        
        origins = settings.get_cors_origins_list()
        assert origins == ['http://localhost:3000', 'http://localhost:4200']
    
    def test_cors_origins_parsing_from_comma_separated(self):
        """Test CORS origins parsing from comma-separated string."""
        settings = Settings(
            jwt_secret_key="test-secret",
            firestore_project_id="test-project",
            cors_origins="http://localhost:3000, http://localhost:4200"
        )
        
        origins = settings.get_cors_origins_list()
        assert origins == ['http://localhost:3000', 'http://localhost:4200']
    
    def test_cors_origins_parsing_empty(self):
        """Test CORS origins parsing when empty."""
        settings = Settings(
            jwt_secret_key="test-secret",
            firestore_project_id="test-project",
            cors_origins=""
        )
        
        origins = settings.get_cors_origins_list()
        assert origins == []
    
    def test_invalid_log_level_raises_error(self):
        """Test that invalid log level raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                jwt_secret_key="test-secret",
                firestore_project_id="test-project",
                log_level="INVALID"
            )
        
        assert "Invalid log level" in str(exc_info.value)
    
    def test_valid_log_levels(self):
        """Test all valid log levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            settings = Settings(
                jwt_secret_key="test-secret",
                firestore_project_id="test-project",
                log_level=level.lower()  # Test case insensitive
            )
            assert settings.log_level == level
    
    def test_invalid_environment_raises_error(self):
        """Test that invalid environment raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                jwt_secret_key="test-secret",
                firestore_project_id="test-project",
                environment="invalid"
            )
        
        assert "Invalid environment" in str(exc_info.value)
    
    def test_valid_environments(self):
        """Test all valid environments."""
        valid_envs = ["development", "testing", "staging", "production"]
        
        for env in valid_envs:
            settings = Settings(
                jwt_secret_key="test-secret",
                firestore_project_id="test-project",
                environment=env.upper()  # Test case insensitive
            )
            assert settings.environment == env
    
    def test_session_expire_hours_validation(self):
        """Test session expire hours validation."""
        # Valid values
        for hours in [1, 24, 168]:
            settings = Settings(
                jwt_secret_key="test-secret",
                firestore_project_id="test-project",
                session_expire_hours=hours
            )
            assert settings.session_expire_hours == hours
        
        # Invalid values
        with pytest.raises(ValidationError):
            Settings(
                jwt_secret_key="test-secret",
                firestore_project_id="test-project",
                session_expire_hours=0  # Too low
            )
        
        with pytest.raises(ValidationError):
            Settings(
                jwt_secret_key="test-secret",
                firestore_project_id="test-project",
                session_expire_hours=200  # Too high
            )
    
    def test_port_validation(self):
        """Test port number validation."""
        # Valid port
        settings = Settings(
            jwt_secret_key="test-secret",
            firestore_project_id="test-project",
            port=8080
        )
        assert settings.port == 8080
        
        # Invalid ports
        with pytest.raises(ValidationError):
            Settings(
                jwt_secret_key="test-secret",
                firestore_project_id="test-project",
                port=0  # Too low
            )
        
        with pytest.raises(ValidationError):
            Settings(
                jwt_secret_key="test-secret",
                firestore_project_id="test-project",
                port=99999  # Too high
            )
    
    def test_default_values_applied(self):
        """Test that default values are properly applied."""
        settings = Settings(
            jwt_secret_key="test-secret",
            firestore_project_id="test-project"
        )
        
        # Check that defaults are applied
        assert settings.app_name == "financial-nomad-api"
        assert settings.version == "1.0.0"
        assert settings.api_prefix == "/api/v1"
        assert settings.session_expire_hours == 24
        assert settings.rate_limit_per_minute == 100