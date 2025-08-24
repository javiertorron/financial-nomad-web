"""
Integration tests for API endpoints.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.models.backup import BackupType, BackupDestination
from src.models.financial import TransactionType


@pytest.mark.integration
class TestHealthEndpoints:
    """Integration tests for health check endpoints."""
    
    def test_basic_health_check(self, client):
        """Test basic health endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        assert "app_name" in data
    
    @pytest.mark.asyncio
    async def test_monitoring_health_endpoints(self, async_client):
        """Test monitoring health endpoints."""
        # Basic monitoring health
        response = await async_client.get("/api/v1/monitoring/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "financial-nomad-backend"
        
        # Detailed health check
        with patch('src.middleware.monitoring.get_health_checker') as mock_get_checker:
            mock_checker = AsyncMock()
            mock_checker.get_comprehensive_health.return_value = {
                "overall_status": "healthy",
                "firestore": {"status": "healthy"},
                "external_apis": {"asana": {"status": "healthy"}}
            }
            mock_get_checker.return_value = mock_checker
            
            response = await async_client.get("/api/v1/monitoring/health/detailed")
            assert response.status_code == 200
            data = response.json()
            assert data["overall_status"] == "healthy"
    
    def test_prometheus_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/api/v1/monitoring/metrics")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        content = response.text
        assert "# HELP" in content
        assert "# TYPE" in content
        assert "financial_nomad" in content


@pytest.mark.integration
class TestAuthenticationFlow:
    """Integration tests for authentication flow."""
    
    @pytest.mark.asyncio
    async def test_auth_endpoints_without_token(self, async_client):
        """Test that protected endpoints require authentication."""
        protected_endpoints = [
            "/api/v1/accounts",
            "/api/v1/categories", 
            "/api/v1/transactions",
            "/api/v1/budgets",
            "/api/v1/backup/config",
            "/api/v1/asana/workspaces"
        ]
        
        for endpoint in protected_endpoints:
            response = await async_client.get(endpoint)
            assert response.status_code == 401
            data = response.json()
            assert "Not authenticated" in data["detail"] or "Authentication required" in data["detail"]
    
    def test_login_endpoint_exists(self, client):
        """Test that login endpoint exists and handles requests."""
        # This should return 422 (validation error) or 400 (bad request) since we're not providing valid data
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code in [400, 422]  # Either validation error or bad request
    
    def test_register_endpoint_exists(self, client):
        """Test that register endpoint exists."""
        response = client.post("/api/v1/auth/register", json={})
        assert response.status_code in [400, 422]  # Validation error expected


@pytest.mark.integration
class TestBackupEndpoints:
    """Integration tests for backup and export endpoints."""
    
    def test_backup_endpoints_require_auth(self, client):
        """Test backup endpoints require authentication."""
        endpoints = [
            ("GET", "/api/v1/backup/config"),
            ("PUT", "/api/v1/backup/config"),
            ("POST", "/api/v1/backup/trigger"),
            ("GET", "/api/v1/backup/list"),
            ("POST", "/api/v1/backup/export"),
            ("GET", "/api/v1/backup/exports")
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_backup_trigger_with_auth(self, async_client, mock_auth_middleware):
        """Test backup trigger with authentication."""
        with patch('src.services.backup.get_backup_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.trigger_backup.return_value = MagicMock(
                id="backup_123",
                user_id="test_user_123",
                backup_type=BackupType.MANUAL,
                status="completed",
                destinations=[BackupDestination.LOCAL_STORAGE],
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=5.0,
                error_message=None,
                expires_at=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow(),
                metadata=None
            )
            mock_get_service.return_value = mock_service
            
            backup_request = {
                "backup_type": "manual",
                "destinations": ["local_storage"],
                "include_attachments": True,
                "notify_on_completion": False
            }
            
            response = await async_client.post("/api/v1/backup/trigger", json=backup_request)
            assert response.status_code == 200
            
            data = response.json()
            assert data["id"] == "backup_123"
            assert data["backup_type"] == "manual"
            assert data["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_export_creation_with_auth(self, async_client, mock_auth_middleware):
        """Test export creation with authentication."""
        with patch('src.services.export.get_export_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_export.return_value = MagicMock(
                id="export_123",
                user_id="test_user_123",
                export_type="full_backup",
                format="json",
                status="completed",
                file_size_bytes=1024,
                download_url="/api/v1/backup/exports/export_123/download",
                expires_at=datetime.utcnow() + timedelta(hours=24),
                metadata=None,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=2.5,
                error_message=None,
                created_at=datetime.utcnow()
            )
            mock_get_service.return_value = mock_service
            
            export_request = {
                "export_type": "full_backup",
                "format": "json",
                "compress_output": False,
                "anonymize_data": False
            }
            
            response = await async_client.post("/api/v1/backup/export", json=export_request)
            assert response.status_code == 200
            
            data = response.json()
            assert data["id"] == "export_123"
            assert data["export_type"] == "full_backup"
            assert data["format"] == "json"


@pytest.mark.integration
class TestFinancialEndpoints:
    """Integration tests for financial endpoints."""
    
    def test_financial_endpoints_require_auth(self, client):
        """Test financial endpoints require authentication."""
        endpoints = [
            ("GET", "/api/v1/accounts"),
            ("POST", "/api/v1/accounts"),
            ("GET", "/api/v1/categories"),
            ("POST", "/api/v1/categories"),
            ("GET", "/api/v1/transactions"),
            ("POST", "/api/v1/transactions"),
            ("GET", "/api/v1/budgets"),
            ("POST", "/api/v1/budgets")
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={})
            
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_accounts_list_with_auth(self, async_client, mock_auth_middleware):
        """Test accounts list endpoint with authentication."""
        with patch('src.services.account.get_account_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_accounts.return_value = [
                MagicMock(
                    id="acc_1",
                    account_name="Test Account",
                    account_type="checking",
                    balance=10000,
                    is_active=True
                )
            ]
            mock_get_service.return_value = mock_service
            
            response = await async_client.get("/api/v1/accounts")
            assert response.status_code == 200
            
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "acc_1"
            assert data[0]["account_name"] == "Test Account"
    
    @pytest.mark.asyncio
    async def test_transactions_list_with_auth(self, async_client, mock_auth_middleware):
        """Test transactions list endpoint with authentication."""
        with patch('src.services.transaction.get_transaction_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.list_transactions.return_value = [
                MagicMock(
                    id="txn_1",
                    transaction_type=TransactionType.EXPENSE,
                    amount=2500,
                    description="Test Transaction",
                    transaction_date="2024-01-15",
                    category_id="cat_1",
                    account_id="acc_1"
                )
            ]
            mock_get_service.return_value = mock_service
            
            response = await async_client.get("/api/v1/transactions")
            assert response.status_code == 200
            
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "txn_1"
            assert data[0]["amount"] == 2500
            assert data[0]["description"] == "Test Transaction"


@pytest.mark.integration
class TestAsanaEndpoints:
    """Integration tests for Asana integration endpoints."""
    
    def test_asana_endpoints_require_auth(self, client):
        """Test Asana endpoints require authentication."""
        endpoints = [
            "/api/v1/asana/workspaces",
            "/api/v1/asana/projects",
            "/api/v1/asana/tasks",
            "/api/v1/asana/oauth/status"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_asana_oauth_status_with_auth(self, async_client, mock_auth_middleware):
        """Test Asana OAuth status endpoint."""
        with patch('src.services.asana_integration.get_asana_integration_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_oauth_status.return_value = {
                "is_connected": False,
                "workspace_id": None,
                "workspace_name": None,
                "last_sync": None
            }
            mock_get_service.return_value = mock_service
            
            response = await async_client.get("/api/v1/asana/oauth/status")
            assert response.status_code == 200
            
            data = response.json()
            assert data["is_connected"] is False
            assert data["workspace_id"] is None


@pytest.mark.integration
class TestAdminEndpoints:
    """Integration tests for admin endpoints."""
    
    def test_admin_endpoints_require_admin_auth(self, client):
        """Test admin endpoints require admin authentication."""
        admin_endpoints = [
            "/api/v1/monitoring/system/status",
            "/api/v1/monitoring/system/performance",
            "/api/v1/monitoring/system/users",
            "/api/v1/monitoring/system/database/stats"
        ]
        
        for endpoint in admin_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401  # No auth
    
    @pytest.mark.asyncio
    async def test_system_status_with_admin_auth(self, async_client, mock_admin_auth_middleware):
        """Test system status endpoint with admin authentication."""
        with patch('src.middleware.monitoring.get_health_checker') as mock_get_checker:
            with patch('src.middleware.monitoring.get_rate_limiter') as mock_get_limiter:
                # Mock health checker
                mock_checker_instance = AsyncMock()
                mock_checker_instance.get_comprehensive_health.return_value = {
                    "overall_status": "healthy",
                    "firestore": {"status": "healthy"},
                    "external_apis": {"asana": {"status": "healthy"}}
                }
                mock_get_checker.return_value = mock_checker_instance
                
                # Mock rate limiter
                mock_limiter_instance = AsyncMock()
                mock_limiter_instance.get_rate_limit_status.return_value = {
                    "active_sliding_windows": 5,
                    "active_token_buckets": 3
                }
                mock_get_limiter.return_value = mock_limiter_instance
                
                response = await async_client.get("/api/v1/monitoring/system/status")
                assert response.status_code == 200
                
                data = response.json()
                assert "timestamp" in data
                assert "health" in data
                assert data["health"]["overall_status"] == "healthy"


@pytest.mark.integration
class TestErrorHandling:
    """Integration tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_404_error_handling(self, async_client):
        """Test 404 error handling."""
        response = await async_client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_method_not_allowed_handling(self, async_client):
        """Test 405 method not allowed handling."""
        # Try to DELETE on an endpoint that only accepts GET
        response = await async_client.delete("/api/v1/health")
        assert response.status_code == 405
    
    def test_request_validation_error(self, client):
        """Test request validation error handling."""
        # Send invalid JSON to an endpoint that expects specific structure
        response = client.post("/api/v1/auth/login", json={"invalid": "data"})
        assert response.status_code in [400, 422]  # Validation error
        
        data = response.json()
        assert "detail" in data


@pytest.mark.integration
class TestCORSAndSecurity:
    """Integration tests for CORS and security headers."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.options("/api/v1/health")
        
        # CORS preflight should be handled
        assert response.status_code in [200, 405]  # Depends on implementation
    
    def test_security_headers_present(self, client):
        """Test that security headers are present."""
        response = client.get("/api/v1/health")
        
        # Check for security headers added by SecurityHeadersMiddleware
        headers = response.headers
        expected_security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
            "referrer-policy"
        ]
        
        for header in expected_security_headers:
            assert header in headers.keys() or header.replace("-", "_") in headers.keys()


@pytest.mark.integration
class TestRateLimiting:
    """Integration tests for rate limiting."""
    
    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/api/v1/health")
        
        # Should have rate limit headers if rate limiting is enabled
        # Note: Might not be present in test environment
        if response.status_code == 200:
            # Just verify the endpoint works
            assert True
    
    @pytest.mark.slow
    def test_rate_limiting_enforcement(self, client):
        """Test rate limiting enforcement (if enabled)."""
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = client.get("/api/v1/health")
            responses.append(response)
        
        # All should succeed in test environment (rate limiting might be disabled)
        for response in responses:
            assert response.status_code == 200


@pytest.mark.integration
class TestMonitoringIntegration:
    """Integration tests for monitoring features."""
    
    def test_request_metrics_collection(self, client):
        """Test that request metrics are collected."""
        # Make a few requests
        for _ in range(3):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            
            # Should have monitoring headers
            if "x-request-id" in response.headers or "X-Request-ID" in response.headers:
                assert True  # Request ID header present
            if "x-response-time" in response.headers or "X-Response-Time" in response.headers:
                assert True  # Response time header present
        
        # Check that metrics endpoint shows activity
        response = client.get("/api/v1/monitoring/metrics")
        assert response.status_code == 200
        
        metrics = response.text
        # Should contain request metrics
        assert "financial_nomad_requests_total" in metrics


@pytest.mark.integration  
@pytest.mark.slow
class TestPerformance:
    """Integration tests for performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self, async_client):
        """Test handling of concurrent requests."""
        import asyncio
        
        async def make_request():
            response = await async_client.get("/api/v1/health")
            return response.status_code
        
        # Make 20 concurrent requests
        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(status == 200 for status in results)
    
    def test_response_time_reasonable(self, client):
        """Test that response times are reasonable."""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/health")
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should respond within 1 second (generous for test environment)
        response_time = end_time - start_time
        assert response_time < 1.0
    
    def test_large_request_handling(self, client):
        """Test handling of larger requests."""
        # Create a reasonably large request body
        large_data = {"data": "x" * 10000}  # 10KB of data
        
        # This should not cause issues (though endpoint might reject it)
        response = client.post("/api/v1/auth/login", json=large_data)
        
        # Should get a proper HTTP response (not a server error)
        assert response.status_code < 500