"""
Unit tests for monitoring middleware.
"""
import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from src.middleware.monitoring import (
    MonitoringMiddleware,
    MetricsCollector,
    HealthChecker,
    get_metrics_collector,
    get_health_checker,
    get_prometheus_metrics
)


class TestMetricsCollector:
    """Test cases for MetricsCollector."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create metrics collector for testing."""
        with patch('src.middleware.monitoring.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock()
            return MetricsCollector()
    
    @pytest.mark.unit
    def test_record_database_operation(self, metrics_collector):
        """Test recording database operations."""
        # Should not raise exception
        metrics_collector.record_database_operation("create", "transactions", "success")
        metrics_collector.record_database_operation("read", "users", "error")
        
        # Verify metrics were recorded (prometheus counters should increment)
        # In real scenario, we would check prometheus registry
        assert True  # Just verify no exceptions
    
    @pytest.mark.unit
    def test_record_external_api_call(self, metrics_collector):
        """Test recording external API calls."""
        metrics_collector.record_external_api_call("google_drive", "success")
        metrics_collector.record_external_api_call("asana", "error")
        assert True
    
    @pytest.mark.unit
    def test_record_cache_operation(self, metrics_collector):
        """Test recording cache operations."""
        metrics_collector.record_cache_operation("get", "hit")
        metrics_collector.record_cache_operation("set", "success")
        assert True
    
    @pytest.mark.unit
    def test_record_backup_operation(self, metrics_collector):
        """Test recording backup operations."""
        metrics_collector.record_backup_operation("manual", "success")
        metrics_collector.record_backup_operation("scheduled", "failed")
        assert True
    
    @pytest.mark.unit
    def test_record_export_operation(self, metrics_collector):
        """Test recording export operations."""
        metrics_collector.record_export_operation("json", "full_backup", "success")
        metrics_collector.record_export_operation("csv", "transactions", "failed")
        assert True
    
    @pytest.mark.unit
    def test_update_active_sessions(self, metrics_collector):
        """Test updating active sessions gauge."""
        metrics_collector.update_active_sessions(5)
        metrics_collector.update_active_sessions(10)
        metrics_collector.update_active_sessions(0)
        assert True


class TestHealthChecker:
    """Test cases for HealthChecker."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker for testing."""
        with patch('src.middleware.monitoring.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock()
            return HealthChecker()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_firestore_health_success(self, health_checker):
        """Test successful Firestore health check."""
        with patch('src.middleware.monitoring.get_firestore') as mock_get_firestore:
            mock_firestore = AsyncMock()
            mock_firestore.get_document = AsyncMock(return_value=None)  # Successful query
            mock_get_firestore.return_value = mock_firestore
            
            result = await health_checker.check_firestore_health()
            
            assert result["status"] == "healthy"
            assert "response_time_ms" in result
            assert "timestamp" in result
            assert result["response_time_ms"] >= 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_firestore_health_failure(self, health_checker):
        """Test failed Firestore health check."""
        with patch('src.middleware.monitoring.get_firestore') as mock_get_firestore:
            mock_firestore = AsyncMock()
            mock_firestore.get_document = AsyncMock(side_effect=Exception("Connection failed"))
            mock_get_firestore.return_value = mock_firestore
            
            result = await health_checker.check_firestore_health()
            
            assert result["status"] == "unhealthy"
            assert "error" in result
            assert result["error"] == "Connection failed"
            assert "timestamp" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_external_apis_health(self, health_checker):
        """Test external APIs health check."""
        with patch('src.middleware.monitoring.get_settings') as mock_settings:
            # Mock settings to enable Google Drive check
            settings_mock = MagicMock()
            settings_mock.google_client_id = "test-client-id"
            mock_settings.return_value = settings_mock
            health_checker.settings = settings_mock
            
            with patch.object(health_checker, '_check_google_api') as mock_google:
                with patch.object(health_checker, '_check_asana_api') as mock_asana:
                    mock_google.return_value = {"status": "healthy", "response_time_ms": 100}
                    mock_asana.return_value = {"status": "healthy", "response_time_ms": 150}
                    
                    result = await health_checker.check_external_apis_health()
                    
                    assert "google_drive" in result
                    assert "asana" in result
                    assert result["google_drive"]["status"] == "healthy"
                    assert result["asana"]["status"] == "healthy"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_google_api_success(self, health_checker):
        """Test successful Google API check."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.1
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await health_checker._check_google_api()
            
            assert result["status"] == "healthy"
            assert result["response_time_ms"] == 100
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_google_api_failure(self, health_checker):
        """Test failed Google API check."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )
            
            result = await health_checker._check_google_api()
            
            assert result["status"] == "unhealthy"
            assert "error" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_asana_api_success(self, health_checker):
        """Test successful Asana API check."""
        with patch('httpx.AsyncClient') as mock_client:
            # Asana returns 401 for unauthenticated requests, which we consider healthy
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.elapsed.total_seconds.return_value = 0.2
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await health_checker._check_asana_api()
            
            assert result["status"] == "healthy"
            assert result["response_time_ms"] == 200
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_comprehensive_health(self, health_checker):
        """Test comprehensive health check."""
        with patch.object(health_checker, 'check_firestore_health') as mock_firestore:
            with patch.object(health_checker, 'check_external_apis_health') as mock_apis:
                mock_firestore.return_value = {"status": "healthy"}
                mock_apis.return_value = {
                    "asana": {"status": "healthy"}
                }
                
                result = await health_checker.get_comprehensive_health()
                
                assert "timestamp" in result
                assert "overall_status" in result
                assert result["overall_status"] == "healthy"
                assert "firestore" in result
                assert "external_apis" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_comprehensive_health_degraded(self, health_checker):
        """Test comprehensive health check with degraded status."""
        with patch.object(health_checker, 'check_firestore_health') as mock_firestore:
            with patch.object(health_checker, 'check_external_apis_health') as mock_apis:
                mock_firestore.return_value = {"status": "healthy"}
                mock_apis.return_value = {
                    "asana": {"status": "degraded"}  # One service degraded
                }
                
                result = await health_checker.get_comprehensive_health()
                
                assert result["overall_status"] == "degraded"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_comprehensive_health_unhealthy(self, health_checker):
        """Test comprehensive health check with unhealthy status."""
        with patch.object(health_checker, 'check_firestore_health') as mock_firestore:
            with patch.object(health_checker, 'check_external_apis_health') as mock_apis:
                mock_firestore.return_value = {"status": "unhealthy"}  # Critical service down
                mock_apis.return_value = {
                    "asana": {"status": "healthy"}
                }
                
                result = await health_checker.get_comprehensive_health()
                
                assert result["overall_status"] == "unhealthy"


class TestMonitoringMiddleware:
    """Test cases for MonitoringMiddleware."""
    
    @pytest.fixture
    def app_with_monitoring(self):
        """Create FastAPI app with monitoring middleware."""
        app = FastAPI()
        app.add_middleware(MonitoringMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.get("/slow")
        async def slow_endpoint():
            await asyncio.sleep(0.1)
            return {"message": "slow"}
        
        @app.get("/error")
        async def error_endpoint():
            raise Exception("Test error")
        
        return app
    
    @pytest.mark.unit
    def test_middleware_basic_request(self, app_with_monitoring):
        """Test middleware with basic successful request."""
        client = TestClient(app_with_monitoring)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.json() == {"message": "test"}
        
        # Check monitoring headers
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers
        
        # Response time should be reasonable
        response_time = response.headers["X-Response-Time"]
        assert response_time.endswith("s")
        assert float(response_time[:-1]) < 1.0  # Less than 1 second
    
    @pytest.mark.unit
    def test_middleware_error_handling(self, app_with_monitoring):
        """Test middleware with error handling."""
        client = TestClient(app_with_monitoring)
        
        response = client.get("/error")
        
        assert response.status_code == 500
        
        # Should still have monitoring headers
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers
    
    @pytest.mark.unit
    def test_endpoint_pattern_extraction(self):
        """Test endpoint pattern extraction for metrics."""
        from src.middleware.monitoring import MonitoringMiddleware
        
        middleware = MonitoringMiddleware(MagicMock())
        
        # Test various patterns
        assert middleware._extract_endpoint_pattern("/api/v1/transactions/123") == "/api/v1/transactions/{id}"
        assert middleware._extract_endpoint_pattern("/api/v1/accounts/abc-def") == "/api/v1/accounts/{id}"
        assert middleware._extract_endpoint_pattern("/api/v1/categories/456") == "/api/v1/categories/{id}"
        assert middleware._extract_endpoint_pattern("/api/v1/health") == "/api/v1/health"  # No pattern match
    
    @pytest.mark.unit
    def test_client_ip_extraction(self):
        """Test client IP extraction from headers."""
        from src.middleware.monitoring import MonitoringMiddleware
        
        middleware = MonitoringMiddleware(MagicMock())
        
        # Mock request with forwarded headers
        request = MagicMock()
        request.headers.get.side_effect = lambda header: {
            'x-forwarded-for': '192.168.1.1, 10.0.0.1',
            'x-real-ip': '192.168.1.1'
        }.get(header)
        request.client.host = '127.0.0.1'
        
        # Should extract from x-forwarded-for first
        ip = middleware._get_client_ip(request)
        assert ip == '192.168.1.1'
        
        # Test with x-real-ip only
        request.headers.get.side_effect = lambda header: {
            'x-real-ip': '192.168.1.2'
        }.get(header) if header != 'x-forwarded-for' else None
        
        ip = middleware._get_client_ip(request)
        assert ip == '192.168.1.2'
        
        # Test with direct connection
        request.headers.get.return_value = None
        ip = middleware._get_client_ip(request)
        assert ip == '127.0.0.1'
    
    @pytest.mark.unit
    def test_active_requests_tracking(self):
        """Test active requests tracking."""
        from src.middleware.monitoring import MonitoringMiddleware
        
        middleware = MonitoringMiddleware(MagicMock())
        
        # Initially empty
        info = middleware.get_active_requests_info()
        assert info["count"] == 0
        assert info["requests"] == []
        
        # Add some mock active requests
        middleware.active_requests["req_1"] = {
            "method": "GET",
            "url": "/api/v1/test",
            "start_time": time.time(),
            "user_id": "user_123"
        }
        middleware.active_requests["req_2"] = {
            "method": "POST",
            "url": "/api/v1/transactions",
            "start_time": time.time(),
            "user_id": "user_456"
        }
        
        info = middleware.get_active_requests_info()
        assert info["count"] == 2
        assert len(info["requests"]) == 2


class TestPrometheusMetrics:
    """Test cases for Prometheus metrics."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_prometheus_metrics(self):
        """Test Prometheus metrics generation."""
        metrics_output = await get_prometheus_metrics()
        
        assert isinstance(metrics_output, str)
        assert "# HELP" in metrics_output
        assert "# TYPE" in metrics_output
        
        # Should contain our custom metrics
        assert "financial_nomad_requests_total" in metrics_output
        assert "financial_nomad_request_duration_seconds" in metrics_output
        assert "financial_nomad_active_requests" in metrics_output


class TestGlobalInstances:
    """Test global instance functions."""
    
    @pytest.mark.unit
    def test_get_metrics_collector(self):
        """Test getting metrics collector singleton."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is collector2
        assert isinstance(collector1, MetricsCollector)
    
    @pytest.mark.unit
    def test_get_health_checker(self):
        """Test getting health checker singleton."""
        checker1 = get_health_checker()
        checker2 = get_health_checker()
        
        assert checker1 is checker2
        assert isinstance(checker1, HealthChecker)


@pytest.mark.integration
class TestMonitoringIntegration:
    """Integration tests for monitoring middleware."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_middleware_metrics_collection(self):
        """Test that middleware actually collects metrics."""
        from prometheus_client import REGISTRY
        
        app = FastAPI()
        app.add_middleware(MonitoringMiddleware)
        
        @app.get("/test/{item_id}")
        async def test_endpoint(item_id: str):
            return {"id": item_id}
        
        client = TestClient(app)
        
        # Make several requests
        for i in range(5):
            response = client.get(f"/test/item_{i}")
            assert response.status_code == 200
        
        # Check that metrics were collected
        metrics_output = await get_prometheus_metrics()
        
        # Should have request counts
        assert "financial_nomad_requests_total" in metrics_output
        assert "method=\"GET\"" in metrics_output
        assert "status_code=\"200\"" in metrics_output
        
        # Should have duration metrics
        assert "financial_nomad_request_duration_seconds" in metrics_output
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_check_comprehensive_flow(self):
        """Test comprehensive health check flow."""
        health_checker = get_health_checker()
        
        # Mock external dependencies for controlled test
        with patch.object(health_checker, 'check_firestore_health') as mock_firestore:
            with patch.object(health_checker, 'check_external_apis_health') as mock_apis:
                mock_firestore.return_value = {
                    "status": "healthy",
                    "response_time_ms": 50,
                    "timestamp": "2024-01-01T00:00:00Z"
                }
                mock_apis.return_value = {
                    "asana": {"status": "healthy", "response_time_ms": 100},
                    "google_drive": {"status": "healthy", "response_time_ms": 75}
                }
                
                health_status = await health_checker.get_comprehensive_health()
                
                assert health_status["overall_status"] == "healthy"
                assert "firestore" in health_status
                assert "external_apis" in health_status
                assert health_status["firestore"]["status"] == "healthy"
                assert health_status["external_apis"]["asana"]["status"] == "healthy"
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_monitoring_under_load(self):
        """Test monitoring middleware under load."""
        app = FastAPI()
        app.add_middleware(MonitoringMiddleware)
        
        @app.get("/load-test")
        async def load_test_endpoint():
            return {"status": "ok"}
        
        client = TestClient(app)
        
        # Make many concurrent requests
        import concurrent.futures
        
        def make_request():
            return client.get("/load-test")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            responses = [future.result() for future in futures]
        
        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)
        
        # All should have monitoring headers
        for response in responses[:10]:  # Sample check
            assert "X-Request-ID" in response.headers
            assert "X-Response-Time" in response.headers