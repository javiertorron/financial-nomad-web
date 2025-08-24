"""
Distributed Caching Service with Redis.
Provides high-performance caching, session management, and real-time data
synchronization with advanced features like cache warming and invalidation strategies.
"""

import asyncio
import json
import pickle
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass, field
import structlog

from src.config import settings

logger = structlog.get_logger()

# Redis imports (in production, use aioredis)
try:
    import aioredis
    from aioredis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache fallback")


class CacheStrategy(Enum):
    """Cache invalidation strategies."""
    TTL = "ttl"                    # Time-based expiration
    LRU = "lru"                    # Least Recently Used
    LFU = "lfu"                    # Least Frequently Used
    WRITE_THROUGH = "write_through" # Write to cache and storage simultaneously
    WRITE_BEHIND = "write_behind"   # Write to cache immediately, storage later
    REFRESH_AHEAD = "refresh_ahead" # Refresh before expiration


class CacheNamespace(Enum):
    """Cache namespaces for data organization."""
    USER_SESSIONS = "sessions"
    FINANCIAL_DATA = "financial"
    REPORTS = "reports"
    ANALYTICS = "analytics"
    API_RESPONSES = "api"
    COMPUTATIONS = "computations"
    CONFIGURATIONS = "config"
    TEMPORARY = "temp"


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    namespace: CacheNamespace
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    size_bytes: int = 0
    version: int = 1


@dataclass
class CacheStats:
    """Cache statistics."""
    total_keys: int = 0
    memory_usage_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    expired_count: int = 0
    namespace_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.hit_count + self.miss_count
        return (self.hit_count / total_requests * 100) if total_requests > 0 else 0.0


class SerializationManager:
    """Handles serialization of cache data."""
    
    def __init__(self):
        self.serializers = {
            'json': self._json_serialize,
            'pickle': self._pickle_serialize,
            'string': self._string_serialize
        }
        
        self.deserializers = {
            'json': self._json_deserialize,
            'pickle': self._pickle_deserialize,
            'string': self._string_deserialize
        }
    
    def serialize(self, data: Any, method: str = 'json') -> bytes:
        """Serialize data using specified method."""
        if method not in self.serializers:
            raise ValueError(f"Unsupported serialization method: {method}")
        
        return self.serializers[method](data)
    
    def deserialize(self, data: bytes, method: str = 'json') -> Any:
        """Deserialize data using specified method."""
        if method not in self.deserializers:
            raise ValueError(f"Unsupported deserialization method: {method}")
        
        return self.deserializers[method](data)
    
    def _json_serialize(self, data: Any) -> bytes:
        """JSON serialization."""
        return json.dumps(data, default=str).encode('utf-8')
    
    def _json_deserialize(self, data: bytes) -> Any:
        """JSON deserialization."""
        return json.loads(data.decode('utf-8'))
    
    def _pickle_serialize(self, data: Any) -> bytes:
        """Pickle serialization."""
        return pickle.dumps(data)
    
    def _pickle_deserialize(self, data: bytes) -> Any:
        """Pickle deserialization."""
        return pickle.loads(data)
    
    def _string_serialize(self, data: Any) -> bytes:
        """String serialization."""
        return str(data).encode('utf-8')
    
    def _string_deserialize(self, data: bytes) -> Any:
        """String deserialization."""
        return data.decode('utf-8')


class CacheKeyBuilder:
    """Builds consistent cache keys."""
    
    def __init__(self, prefix: str = "fn"):
        self.prefix = prefix
    
    def build_key(self, namespace: CacheNamespace, *args, **kwargs) -> str:
        """Build cache key with namespace and parameters."""
        # Create a hash of the arguments for consistent key generation
        key_parts = [str(arg) for arg in args]
        
        # Add keyword arguments
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        # Create hash for long keys
        if len(key_parts) > 5 or sum(len(part) for part in key_parts) > 100:
            content = ":".join(key_parts)
            key_hash = hashlib.md5(content.encode()).hexdigest()
            return f"{self.prefix}:{namespace.value}:hash:{key_hash}"
        else:
            key_suffix = ":".join(key_parts) if key_parts else "default"
            return f"{self.prefix}:{namespace.value}:{key_suffix}"
    
    def build_user_key(self, user_id: str, data_type: str, *args) -> str:
        """Build user-specific cache key."""
        return self.build_key(CacheNamespace.FINANCIAL_DATA, "user", user_id, data_type, *args)
    
    def build_session_key(self, session_id: str) -> str:
        """Build session cache key."""
        return self.build_key(CacheNamespace.USER_SESSIONS, session_id)
    
    def build_report_key(self, user_id: str, report_type: str, **params) -> str:
        """Build report cache key."""
        return self.build_key(CacheNamespace.REPORTS, user_id, report_type, **params)


class InMemoryCache:
    """Fallback in-memory cache when Redis is not available."""
    
    def __init__(self, max_size: int = 10000):
        self.data: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.stats = CacheStats()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self.data:
            entry = self.data[key]
            
            # Check expiration
            if entry.expires_at and datetime.utcnow() > entry.expires_at:
                await self.delete(key)
                self.stats.expired_count += 1
                self.stats.miss_count += 1
                return None
            
            # Update access statistics
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()
            self.stats.hit_count += 1
            
            return entry.value
        
        self.stats.miss_count += 1
        return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None,
                 namespace: CacheNamespace = CacheNamespace.TEMPORARY,
                 tags: List[str] = None) -> bool:
        """Set value in cache."""
        # Check size limits
        if len(self.data) >= self.max_size:
            await self._evict_lru()
        
        expires_at = None
        if expire:
            expires_at = datetime.utcnow() + timedelta(seconds=expire)
        
        # Calculate size
        try:
            size_bytes = len(pickle.dumps(value))
        except:
            size_bytes = len(str(value).encode())
        
        entry = CacheEntry(
            key=key,
            value=value,
            namespace=namespace,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            tags=tags or [],
            size_bytes=size_bytes
        )
        
        self.data[key] = entry
        self.stats.total_keys += 1
        self.stats.memory_usage_bytes += size_bytes
        
        # Update namespace stats
        ns_name = namespace.value
        if ns_name not in self.stats.namespace_stats:
            self.stats.namespace_stats[ns_name] = {"keys": 0, "size": 0}
        self.stats.namespace_stats[ns_name]["keys"] += 1
        self.stats.namespace_stats[ns_name]["size"] += size_bytes
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self.data:
            entry = self.data[key]
            del self.data[key]
            
            self.stats.total_keys -= 1
            self.stats.memory_usage_bytes -= entry.size_bytes
            
            # Update namespace stats
            ns_name = entry.namespace.value
            if ns_name in self.stats.namespace_stats:
                self.stats.namespace_stats[ns_name]["keys"] -= 1
                self.stats.namespace_stats[ns_name]["size"] -= entry.size_bytes
            
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self.data
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key."""
        if key in self.data:
            self.data[key].expires_at = datetime.utcnow() + timedelta(seconds=seconds)
            return True
        return False
    
    async def clear(self, namespace: Optional[CacheNamespace] = None) -> int:
        """Clear cache or specific namespace."""
        if namespace:
            keys_to_delete = [k for k, v in self.data.items() if v.namespace == namespace]
            count = 0
            for key in keys_to_delete:
                await self.delete(key)
                count += 1
            return count
        else:
            count = len(self.data)
            self.data.clear()
            self.stats = CacheStats()
            return count
    
    async def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.data:
            return
        
        # Find LRU entry
        lru_key = min(
            self.data.keys(),
            key=lambda k: self.data[k].last_accessed or self.data[k].created_at
        )
        
        await self.delete(lru_key)
        self.stats.eviction_count += 1


class RedisCache:
    """Redis-based distributed cache."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis: Optional[Redis] = None
        self.serializer = SerializationManager()
        self.stats = CacheStats()
    
    async def connect(self):
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis not available")
        
        try:
            self.redis = aioredis.from_url(self.redis_url)
            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis", url=self.redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if not self.redis:
            return None
        
        try:
            data = await self.redis.get(key)
            if data:
                self.stats.hit_count += 1
                return self.serializer.deserialize(data, 'json')
            else:
                self.stats.miss_count += 1
                return None
        except Exception as e:
            logger.error("Redis get failed", key=key, error=str(e))
            self.stats.miss_count += 1
            return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None,
                 namespace: CacheNamespace = CacheNamespace.TEMPORARY,
                 tags: List[str] = None) -> bool:
        """Set value in Redis."""
        if not self.redis:
            return False
        
        try:
            serialized_data = self.serializer.serialize(value, 'json')
            
            if expire:
                await self.redis.setex(key, expire, serialized_data)
            else:
                await self.redis.set(key, serialized_data)
            
            self.stats.total_keys += 1
            return True
        except Exception as e:
            logger.error("Redis set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.redis:
            return False
        
        try:
            result = await self.redis.delete(key)
            if result:
                self.stats.total_keys -= 1
            return bool(result)
        except Exception as e:
            logger.error("Redis delete failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.redis:
            return False
        
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error("Redis exists failed", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key in Redis."""
        if not self.redis:
            return False
        
        try:
            return bool(await self.redis.expire(key, seconds))
        except Exception as e:
            logger.error("Redis expire failed", key=key, error=str(e))
            return False
    
    async def clear(self, namespace: Optional[CacheNamespace] = None) -> int:
        """Clear cache or specific namespace."""
        if not self.redis:
            return 0
        
        try:
            if namespace:
                pattern = f"fn:{namespace.value}:*"
                keys = await self.redis.keys(pattern)
                if keys:
                    return await self.redis.delete(*keys)
                return 0
            else:
                return await self.redis.flushdb()
        except Exception as e:
            logger.error("Redis clear failed", error=str(e))
            return 0


class CacheService:
    """Main cache service with intelligent caching strategies."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.key_builder = CacheKeyBuilder()
        self.cache_warmers: Dict[str, Callable] = {}
        
        # Initialize cache backend
        if REDIS_AVAILABLE and redis_url:
            self.backend = RedisCache(redis_url)
            self.distributed = True
        else:
            self.backend = InMemoryCache()
            self.distributed = False
        
        logger.info("Cache service initialized", 
                   backend=type(self.backend).__name__,
                   distributed=self.distributed)
    
    async def connect(self):
        """Connect to cache backend."""
        if hasattr(self.backend, 'connect'):
            await self.backend.connect()
    
    async def disconnect(self):
        """Disconnect from cache backend."""
        if hasattr(self.backend, 'disconnect'):
            await self.backend.disconnect()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return await self.backend.get(key)
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None,
                 namespace: CacheNamespace = CacheNamespace.TEMPORARY,
                 tags: List[str] = None) -> bool:
        """Set value in cache."""
        return await self.backend.set(key, value, expire, namespace, tags)
    
    async def get_or_set(self, key: str, factory: Callable, expire: Optional[int] = None,
                        namespace: CacheNamespace = CacheNamespace.TEMPORARY) -> Any:
        """Get value or set using factory function."""
        value = await self.get(key)
        if value is not None:
            return value
        
        # Generate value using factory
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        await self.set(key, value, expire, namespace)
        return value
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        return await self.backend.delete(key)
    
    async def clear_namespace(self, namespace: CacheNamespace) -> int:
        """Clear all keys in namespace."""
        return await self.backend.clear(namespace)
    
    async def invalidate_tags(self, tags: List[str]) -> int:
        """Invalidate all keys with specified tags."""
        # This is a simplified implementation
        # In production, use Redis sets to track tagged keys
        logger.info("Tag invalidation requested", tags=tags)
        return 0
    
    # Financial data caching methods
    async def cache_user_transactions(self, user_id: str, transactions: List[Dict[str, Any]],
                                    filters: Optional[Dict] = None, expire: int = 300) -> str:
        """Cache user transactions with filters."""
        key = self.key_builder.build_user_key(user_id, "transactions", 
                                            **(filters or {}))
        await self.set(key, transactions, expire, CacheNamespace.FINANCIAL_DATA, 
                      tags=[f"user:{user_id}", "transactions"])
        return key
    
    async def get_user_transactions(self, user_id: str, 
                                  filters: Optional[Dict] = None) -> Optional[List[Dict[str, Any]]]:
        """Get cached user transactions."""
        key = self.key_builder.build_user_key(user_id, "transactions", 
                                            **(filters or {}))
        return await self.get(key)
    
    async def cache_user_summary(self, user_id: str, summary: Dict[str, Any],
                               period: str, expire: int = 1800) -> str:
        """Cache financial summary for user."""
        key = self.key_builder.build_user_key(user_id, "summary", period)
        await self.set(key, summary, expire, CacheNamespace.FINANCIAL_DATA,
                      tags=[f"user:{user_id}", "summary"])
        return key
    
    async def get_user_summary(self, user_id: str, period: str) -> Optional[Dict[str, Any]]:
        """Get cached financial summary."""
        key = self.key_builder.build_user_key(user_id, "summary", period)
        return await self.get(key)
    
    async def cache_report(self, user_id: str, report_type: str, 
                         report_data: Dict[str, Any], **params) -> str:
        """Cache generated report."""
        key = self.key_builder.build_report_key(user_id, report_type, **params)
        expire = 3600  # 1 hour for reports
        await self.set(key, report_data, expire, CacheNamespace.REPORTS,
                      tags=[f"user:{user_id}", "reports", report_type])
        return key
    
    async def get_report(self, user_id: str, report_type: str, 
                        **params) -> Optional[Dict[str, Any]]:
        """Get cached report."""
        key = self.key_builder.build_report_key(user_id, report_type, **params)
        return await self.get(key)
    
    # Session management
    async def create_session(self, user_id: str, session_data: Dict[str, Any],
                           expire: int = 86400) -> str:
        """Create user session."""
        session_id = str(uuid.uuid4())
        key = self.key_builder.build_session_key(session_id)
        
        session_info = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "data": session_data
        }
        
        await self.set(key, session_info, expire, CacheNamespace.USER_SESSIONS,
                      tags=[f"user:{user_id}", "sessions"])
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        key = self.key_builder.build_session_key(session_id)
        return await self.get(key)
    
    async def update_session(self, session_id: str, data: Dict[str, Any],
                           extend_expire: Optional[int] = None) -> bool:
        """Update session data."""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session["data"].update(data)
        session["updated_at"] = datetime.utcnow().isoformat()
        
        key = self.key_builder.build_session_key(session_id)
        
        if extend_expire:
            await self.backend.expire(key, extend_expire)
        
        await self.set(key, session, namespace=CacheNamespace.USER_SESSIONS)
        return True
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        key = self.key_builder.build_session_key(session_id)
        return await self.delete(key)
    
    # Cache warming
    def register_warmer(self, name: str, warmer_func: Callable):
        """Register cache warmer function."""
        self.cache_warmers[name] = warmer_func
    
    async def warm_cache(self, warmer_names: Optional[List[str]] = None):
        """Execute cache warmers."""
        warmers_to_run = warmer_names or list(self.cache_warmers.keys())
        
        for warmer_name in warmers_to_run:
            if warmer_name in self.cache_warmers:
                try:
                    warmer_func = self.cache_warmers[warmer_name]
                    if asyncio.iscoroutinefunction(warmer_func):
                        await warmer_func(self)
                    else:
                        warmer_func(self)
                    
                    logger.info("Cache warmer executed", warmer=warmer_name)
                except Exception as e:
                    logger.error("Cache warmer failed", warmer=warmer_name, error=str(e))
    
    # Cache statistics
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.backend.stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform cache health check."""
        try:
            # Test basic operations
            test_key = f"health_check_{uuid.uuid4().hex[:8]}"
            test_value = {"timestamp": datetime.utcnow().isoformat()}
            
            # Set and get test
            await self.set(test_key, test_value, expire=60)
            retrieved = await self.get(test_key)
            await self.delete(test_key)
            
            health_status = {
                "status": "healthy" if retrieved == test_value else "degraded",
                "backend": type(self.backend).__name__,
                "distributed": self.distributed,
                "test_passed": retrieved == test_value,
                "stats": {
                    "total_keys": self.backend.stats.total_keys,
                    "hit_rate": self.backend.stats.hit_rate,
                    "memory_usage": self.backend.stats.memory_usage_bytes
                }
            }
            
            return health_status
            
        except Exception as e:
            logger.error("Cache health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "backend": type(self.backend).__name__,
                "distributed": self.distributed
            }


# Global cache service
_cache_service = None


def get_cache_service() -> CacheService:
    """Get global cache service."""
    global _cache_service
    if _cache_service is None:
        redis_url = getattr(settings, 'redis_url', None)
        _cache_service = CacheService(redis_url)
    return _cache_service


# Cache decorators
def cached(expire: int = 300, namespace: CacheNamespace = CacheNamespace.API_RESPONSES,
          key_prefix: str = ""):
    """Decorator for caching function results."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            cache = get_cache_service()
            
            # Build cache key
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            
            cache_key = ":".join(filter(None, key_parts))
            
            # Try to get from cache
            result = await cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Store in cache
            await cache.set(cache_key, result, expire, namespace)
            return result
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, use asyncio.run in a thread
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Cache warmers
async def warm_user_data(cache: CacheService, user_id: str):
    """Warm cache with user's financial data."""
    logger.info("Warming cache for user", user_id=user_id)
    
    # In real implementation, fetch and cache user's most accessed data
    # This is a placeholder
    summary_data = {"total_balance": 10000, "recent_transactions": 25}
    await cache.cache_user_summary(user_id, summary_data, "current_month")


async def warm_popular_reports(cache: CacheService):
    """Warm cache with popular reports."""
    logger.info("Warming popular reports cache")
    
    # In real implementation, generate popular reports
    # This is a placeholder
    pass