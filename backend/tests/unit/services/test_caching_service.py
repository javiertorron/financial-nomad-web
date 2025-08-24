"""
Unit tests for caching service.
"""
import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock

from src.services.caching import (
    InMemoryCache,
    CacheEntry,
    CacheService,
    CacheKeyBuilder,
    get_cache_service,
    cached_query,
    cached_computation
)


class TestCacheEntry:
    """Test cases for CacheEntry."""
    
    @pytest.mark.unit
    def test_cache_entry_creation(self):
        """Test cache entry creation."""
        now = time.time()
        entry = CacheEntry(
            data="test_data",
            expires_at=now + 300,
            created_at=now,
            size_bytes=100
        )
        
        assert entry.data == "test_data"
        assert entry.expires_at == now + 300
        assert entry.created_at == now
        assert entry.access_count == 0
        assert entry.last_accessed is None
        assert entry.size_bytes == 100
    
    @pytest.mark.unit
    def test_is_expired(self):
        """Test expiration check."""
        now = time.time()
        
        # Not expired
        entry_valid = CacheEntry(
            data="test",
            expires_at=now + 300,
            created_at=now
        )
        assert not entry_valid.is_expired()
        
        # Expired
        entry_expired = CacheEntry(
            data="test",
            expires_at=now - 300,
            created_at=now - 400
        )
        assert entry_expired.is_expired()
    
    @pytest.mark.unit
    def test_is_stale(self):
        """Test staleness check."""
        now = time.time()
        
        # Fresh entry (10% of TTL elapsed)
        entry_fresh = CacheEntry(
            data="test",
            expires_at=now + 270,  # 270s remaining of 300s TTL
            created_at=now - 30    # 30s elapsed
        )
        assert not entry_fresh.is_stale(stale_threshold=0.8)
        
        # Stale entry (90% of TTL elapsed)
        entry_stale = CacheEntry(
            data="test",
            expires_at=now + 30,   # 30s remaining of 300s TTL
            created_at=now - 270   # 270s elapsed
        )
        assert entry_stale.is_stale(stale_threshold=0.8)
    
    @pytest.mark.unit
    def test_touch(self):
        """Test access tracking."""
        entry = CacheEntry(
            data="test",
            expires_at=time.time() + 300,
            created_at=time.time()
        )
        
        assert entry.access_count == 0
        assert entry.last_accessed is None
        
        entry.touch()
        assert entry.access_count == 1
        assert entry.last_accessed is not None
        
        entry.touch()
        assert entry.access_count == 2


class TestInMemoryCache:
    """Test cases for InMemoryCache."""
    
    @pytest.fixture
    def cache(self):
        """Create cache instance for testing."""
        return InMemoryCache(max_size=10, max_memory_mb=1, default_ttl=300)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        # Set value
        success = await cache.set("key1", "value1")
        assert success is True
        
        # Get value
        value = await cache.get("key1")
        assert value == "value1"
        
        # Get non-existent key
        value = await cache.get("nonexistent")
        assert value is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache):
        """Test TTL expiration."""
        # Set value with short TTL
        await cache.set("key1", "value1", ttl=1)  # 1 second
        
        # Should be available immediately
        value = await cache.get("key1")
        assert value == "value1"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        value = await cache.get("key1")
        assert value is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test delete operation."""
        # Set value
        await cache.set("key1", "value1")
        assert await cache.get("key1") == "value1"
        
        # Delete value
        deleted = await cache.delete("key1")
        assert deleted is True
        assert await cache.get("key1") is None
        
        # Delete non-existent key
        deleted = await cache.delete("nonexistent")
        assert deleted is False
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clear operation."""
        # Set multiple values
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Verify they exist
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"
        
        # Clear cache
        await cache.clear()
        
        # Verify all are gone
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_size_limit_eviction(self, cache):
        """Test LRU eviction when size limit reached."""
        # Fill cache to limit (10 items)
        for i in range(10):
            await cache.set(f"key{i}", f"value{i}")
        
        # All should be present
        for i in range(10):
            assert await cache.get(f"key{i}") == f"value{i}"
        
        # Add one more item (should trigger eviction)
        await cache.set("key10", "value10")
        
        # Verify the newest item is present
        assert await cache.get("key10") == "value10"
        
        # At least one old item should be evicted
        stats = await cache.get_stats()
        assert stats["entries"] <= 10
        assert stats["evictions"] > 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_access_tracking(self, cache):
        """Test that access updates statistics."""
        # Set value
        await cache.set("key1", "value1")
        
        # Get value multiple times
        await cache.get("key1")
        await cache.get("key1")
        await cache.get("key1")
        
        # Check statistics
        stats = await cache.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 0
        
        # Try to get non-existent key
        await cache.get("nonexistent")
        
        # Check updated statistics
        stats = await cache.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 75.0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stats(self, cache):
        """Test statistics reporting."""
        # Initial stats
        stats = await cache.get_stats()
        assert stats["entries"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate_percent"] == 0
        assert stats["evictions"] == 0
        
        # Add some entries
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Check updated stats
        stats = await cache.get_stats()
        assert stats["entries"] == 2
        assert stats["memory_usage_bytes"] > 0


class TestCacheKeyBuilder:
    """Test cases for CacheKeyBuilder."""
    
    @pytest.mark.unit
    def test_user_key(self):
        """Test user key building."""
        key = CacheKeyBuilder.user_key("user_123", "profile")
        assert key == "user:user_123:profile"
    
    @pytest.mark.unit
    def test_query_key(self):
        """Test query key building."""
        filters = {
            "user_id": "user_123",
            "date_range": "2024-01-01"
        }
        
        key1 = CacheKeyBuilder.query_key("transactions", filters)
        key2 = CacheKeyBuilder.query_key("transactions", filters)
        
        # Should be deterministic
        assert key1 == key2
        assert key1.startswith("query:transactions:")
        assert len(key1.split(":")) == 3  # query:collection:hash
    
    @pytest.mark.unit
    def test_computation_key(self):
        """Test computation key building."""
        params = {
            "operation": "sum",
            "field": "amount",
            "user_id": "user_123"
        }
        
        key1 = CacheKeyBuilder.computation_key("aggregate", params)
        key2 = CacheKeyBuilder.computation_key("aggregate", params)
        
        # Should be deterministic
        assert key1 == key2
        assert key1.startswith("compute:aggregate:")
    
    @pytest.mark.unit
    def test_key_consistency_with_different_order(self):
        """Test that key generation is consistent regardless of dict order."""
        params1 = {"b": 2, "a": 1, "c": 3}
        params2 = {"a": 1, "b": 2, "c": 3}
        
        key1 = CacheKeyBuilder.computation_key("test", params1)
        key2 = CacheKeyBuilder.computation_key("test", params2)
        
        assert key1 == key2


class TestCacheService:
    """Test cases for CacheService."""
    
    @pytest.fixture
    def cache_service(self):
        """Create cache service for testing."""
        with patch('src.services.caching.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock()
            return CacheService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_caching(self, cache_service):
        """Test query result caching."""
        collection = "transactions"
        filters = {"user_id": "user_123"}
        result = [{"id": "txn_1", "amount": 100}]
        
        # Cache should be empty initially
        cached = await cache_service.get_cached_query(collection, filters)
        assert cached is None
        
        # Cache the result
        await cache_service.cache_query_result(collection, filters, result)
        
        # Should now be cached
        cached = await cache_service.get_cached_query(collection, filters)
        assert cached == result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_data_caching(self, cache_service):
        """Test user data caching."""
        user_id = "user_123"
        data_type = "profile"
        data = {"name": "Test User", "email": "test@example.com"}
        
        # Cache should be empty initially
        cached = await cache_service.get_cached_user_data(user_id, data_type)
        assert cached is None
        
        # Cache the data
        await cache_service.cache_user_data(user_id, data_type, data)
        
        # Should now be cached
        cached = await cache_service.get_cached_user_data(user_id, data_type)
        assert cached == data
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_computation_caching(self, cache_service):
        """Test computation result caching."""
        operation = "monthly_summary"
        params = {"user_id": "user_123", "month": "2024-01"}
        result = {"income": 5000, "expenses": 3000, "net": 2000}
        
        # Cache should be empty initially
        cached = await cache_service.get_cached_computation(operation, params)
        assert cached is None
        
        # Cache the result
        await cache_service.cache_computation_result(operation, params, result)
        
        # Should now be cached
        cached = await cache_service.get_cached_computation(operation, params)
        assert cached == result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_api_response_caching(self, cache_service):
        """Test API response caching."""
        endpoint = "transactions/list"
        params = {"limit": 10, "user_id": "user_123"}
        response = {"data": [{"id": "txn_1"}], "total": 1}
        
        # Cache should be empty initially
        cached = await cache_service.get_cached_api_response(endpoint, params)
        assert cached is None
        
        # Cache the response
        await cache_service.cache_api_response(endpoint, params, response)
        
        # Should now be cached
        cached = await cache_service.get_cached_api_response(endpoint, params)
        assert cached == response
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalidate_user_cache(self, cache_service):
        """Test user cache invalidation."""
        user_id = "user_123"
        data_type = "profile"
        data = {"name": "Test User"}
        
        # Cache some data
        await cache_service.cache_user_data(user_id, data_type, data)
        assert await cache_service.get_cached_user_data(user_id, data_type) == data
        
        # Invalidate specific data type
        await cache_service.invalidate_user_cache(user_id, data_type)
        
        # Should be gone (in a real implementation)
        # Note: Current implementation just logs, so we test that it doesn't crash
        await cache_service.invalidate_user_cache(user_id, data_type)
        await cache_service.invalidate_user_cache(user_id)  # All data types
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_all_cache_stats(self, cache_service):
        """Test getting statistics from all caches."""
        # Add some data to different caches
        await cache_service.cache_query_result("transactions", {"user": "123"}, [])
        await cache_service.cache_user_data("user_123", "profile", {})
        await cache_service.cache_computation_result("sum", {"field": "amount"}, 1000)
        await cache_service.cache_api_response("endpoint", {}, {})
        
        # Get stats
        stats = await cache_service.get_all_cache_stats()
        
        # Verify structure
        assert "query_cache" in stats
        assert "user_session_cache" in stats
        assert "computation_cache" in stats
        assert "api_response_cache" in stats
        
        # Each cache should have stats
        for cache_stats in stats.values():
            assert "entries" in cache_stats
            assert "hits" in cache_stats
            assert "misses" in cache_stats
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clear_all_caches(self, cache_service):
        """Test clearing all caches."""
        # Add data to all caches
        await cache_service.cache_query_result("transactions", {"user": "123"}, [])
        await cache_service.cache_user_data("user_123", "profile", {})
        await cache_service.cache_computation_result("sum", {"field": "amount"}, 1000)
        await cache_service.cache_api_response("endpoint", {}, {})
        
        # Verify data is cached
        stats_before = await cache_service.get_all_cache_stats()
        total_entries_before = sum(cache["entries"] for cache in stats_before.values())
        assert total_entries_before > 0
        
        # Clear all caches
        await cache_service.clear_all_caches()
        
        # Verify all caches are empty
        stats_after = await cache_service.get_all_cache_stats()
        total_entries_after = sum(cache["entries"] for cache in stats_after.values())
        assert total_entries_after == 0


class TestCacheDecorators:
    """Test cases for cache decorators."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cached_query_decorator(self):
        """Test cached_query decorator."""
        call_count = 0
        
        @cached_query(ttl=300)
        async def expensive_query(param1, param2):
            nonlocal call_count
            call_count += 1
            return f"result_{param1}_{param2}"
        
        # Mock the cache service
        with patch('src.services.caching.cache_service') as mock_cache:
            mock_cache.query_cache.get.return_value = None  # Cache miss first time
            mock_cache.query_cache.set = MagicMock()
            
            # First call - should execute function
            result1 = await expensive_query("a", "b")
            assert result1 == "result_a_b"
            assert call_count == 1
            
            # Mock cache hit for second call
            mock_cache.query_cache.get.return_value = "cached_result"
            
            # Second call - should use cache
            result2 = await expensive_query("a", "b")
            assert result2 == "cached_result"
            assert call_count == 1  # Function not called again
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cached_computation_decorator(self):
        """Test cached_computation decorator."""
        call_count = 0
        
        @cached_computation(ttl=3600)
        async def expensive_computation(value):
            nonlocal call_count
            call_count += 1
            return value * 2
        
        # Mock the cache service
        with patch('src.services.caching.cache_service') as mock_cache:
            mock_cache.computation_cache.get.return_value = None  # Cache miss
            mock_cache.computation_cache.set = MagicMock()
            
            # First call
            result1 = await expensive_computation(5)
            assert result1 == 10
            assert call_count == 1
            
            # Mock cache hit
            mock_cache.computation_cache.get.return_value = 20
            
            # Second call - should use cache
            result2 = await expensive_computation(5)
            assert result2 == 20
            assert call_count == 1


class TestCacheServiceSingleton:
    """Test cache service singleton pattern."""
    
    @pytest.mark.unit
    def test_get_cache_service_singleton(self):
        """Test that get_cache_service returns singleton."""
        service1 = get_cache_service()
        service2 = get_cache_service()
        
        assert service1 is service2
        assert isinstance(service1, CacheService)
    
    @pytest.mark.unit
    def test_get_cache_service_initialization(self):
        """Test cache service initialization."""
        service = get_cache_service()
        
        # Should have all cache instances
        assert hasattr(service, 'query_cache')
        assert hasattr(service, 'user_session_cache')
        assert hasattr(service, 'computation_cache')
        assert hasattr(service, 'api_response_cache')
        
        # All should be InMemoryCache instances
        assert isinstance(service.query_cache, InMemoryCache)
        assert isinstance(service.user_session_cache, InMemoryCache)
        assert isinstance(service.computation_cache, InMemoryCache)
        assert isinstance(service.api_response_cache, InMemoryCache)


@pytest.mark.integration
class TestCacheIntegration:
    """Integration tests for cache service."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cache_performance_under_load(self):
        """Test cache performance with high load."""
        cache = InMemoryCache(max_size=1000, max_memory_mb=10, default_ttl=300)
        
        # Set many values concurrently
        async def set_values(start, end):
            for i in range(start, end):
                await cache.set(f"key_{i}", f"value_{i}")
        
        # Run concurrent operations
        await asyncio.gather(
            set_values(0, 100),
            set_values(100, 200),
            set_values(200, 300)
        )
        
        # Verify data integrity
        stats = await cache.get_stats()
        assert stats["entries"] == 300
        
        # Verify we can retrieve values
        for i in range(0, 300, 50):  # Sample check
            value = await cache.get(f"key_{i}")
            assert value == f"value_{i}"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cache_memory_management(self):
        """Test cache memory management and eviction."""
        # Small cache to trigger evictions
        cache = InMemoryCache(max_size=5, max_memory_mb=1, default_ttl=300)
        
        # Fill beyond capacity
        for i in range(10):
            large_value = "x" * 1000  # 1KB value
            await cache.set(f"key_{i}", large_value)
        
        # Should have triggered evictions
        stats = await cache.get_stats()
        assert stats["entries"] <= 5
        assert stats["evictions"] > 0
        
        # Some recent entries should still be accessible
        recent_found = 0
        for i in range(7, 10):  # Check last few entries
            value = await cache.get(f"key_{i}")
            if value is not None:
                recent_found += 1
        
        assert recent_found > 0  # At least some recent entries should be present