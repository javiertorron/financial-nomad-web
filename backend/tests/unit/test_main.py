"""
Tests for main FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.mark.unit
class TestMainApp:
    """Test main FastAPI application."""
    
    def test_create_app(self, test_settings):
        """Test app creation."""
        with pytest.mock.patch('src.config.settings', test_settings):
            app = create_app()
            
            assert app.title == test_settings.app_name
            assert app.version == test_settings.version
            assert app.debug == test_settings.debug
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "health_check" in data
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
    
    def test_detailed_health_check_endpoint(self, client):
        """Test detailed health check endpoint."""
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data
    
    def test_readiness_check_endpoint(self, client):
        """Test readiness check endpoint."""
        response = client.get("/api/v1/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
    
    def test_liveness_check_endpoint(self, client):
        """Test liveness check endpoint."""
        response = client.get("/api/v1/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/v1/health")
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    def test_security_headers(self, client):
        """Test security headers are present."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert response.headers.get("x-xss-protection") == "1; mode=block"
    
    def test_request_id_header(self, client):
        """Test request ID header is added."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert "x-request-id" in response.headers
    
    def test_process_time_header(self, client):
        """Test process time header is added."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        assert "x-process-time" in response.headers
        
        # Should be a valid float
        process_time = float(response.headers["x-process-time"])
        assert process_time >= 0
    
    def test_placeholder_auth_endpoints(self, client):
        """Test placeholder auth endpoints."""
        # Login endpoint
        response = client.post("/api/v1/auth/login")
        assert response.status_code == 200
        
        # Profile endpoint
        response = client.get("/api/v1/auth/profile")
        assert response.status_code == 200
        
        # Logout endpoint
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 204
    
    def test_404_endpoint(self, client):
        """Test 404 for non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404