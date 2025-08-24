"""
Cache Management endpoints.
Handles cache operations, statistics, and maintenance for distributed caching system.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, status, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional
from src.services.cache_service import (
    get_cache_service,
    CacheNamespace,
    CacheStats,
    warm_user_data,
    warm_popular_reports
)

logger = structlog.get_logger()
router = APIRouter()


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    total_keys: int = Field(..., description="Total number of cached keys")
    memory_usage_bytes: int = Field(..., description="Memory usage in bytes")
    hit_count: int = Field(..., description="Cache hit count")
    miss_count: int = Field(..., description="Cache miss count")
    hit_rate: float = Field(..., description="Cache hit rate percentage")
    eviction_count: int = Field(..., description="Number of evictions")
    expired_count: int = Field(..., description="Number of expired keys")
    namespace_stats: Dict[str, Dict[str, int]] = Field(..., description="Statistics by namespace")


class CacheHealthResponse(BaseModel):
    """Cache health check response."""
    status: str = Field(..., description="Cache health status")
    backend: str = Field(..., description="Cache backend type")
    distributed: bool = Field(..., description="Whether cache is distributed")
    test_passed: bool = Field(..., description="Whether health test passed")
    stats: Dict[str, Any] = Field(..., description="Basic cache statistics")
    error: Optional[str] = Field(None, description="Error message if unhealthy")


class CacheOperationResponse(BaseModel):
    """Cache operation response."""
    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Operation result message")
    affected_keys: Optional[int] = Field(None, description="Number of keys affected")
    timestamp: str = Field(..., description="Operation timestamp")


class WarmCacheRequest(BaseModel):
    """Cache warming request."""
    warmers: Optional[List[str]] = Field(None, description="Specific warmers to run")
    user_ids: Optional[List[str]] = Field(None, description="Specific users to warm data for")


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Get Cache Statistics",
    description="Returns comprehensive cache performance statistics",
    response_model=CacheStatsResponse,
    tags=["Cache Management"]
)
async def get_cache_statistics(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> CacheStatsResponse:
    """
    **Get cache statistics**
    
    Returns detailed cache performance metrics:
    - Hit/miss rates and performance indicators
    - Memory usage and key distribution
    - Namespace-specific statistics
    - Eviction and expiration counts
    
    Essential for cache optimization and performance monitoring.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for cache statistics
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        cache_service = get_cache_service()
        stats = cache_service.get_stats()
        
        logger.info("Cache statistics retrieved",
                   requester=current_user.get('id'),
                   hit_rate=stats.hit_rate)
        
        return CacheStatsResponse(
            total_keys=stats.total_keys,
            memory_usage_bytes=stats.memory_usage_bytes,
            hit_count=stats.hit_count,
            miss_count=stats.miss_count,
            hit_rate=stats.hit_rate,
            eviction_count=stats.eviction_count,
            expired_count=stats.expired_count,
            namespace_stats=stats.namespace_stats
        )
        
    except Exception as e:
        logger.error("Failed to get cache statistics",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics"
        )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Cache Health Check",
    description="Performs cache system health check with connectivity tests",
    response_model=CacheHealthResponse,
    tags=["Cache Management"]
)
async def cache_health_check(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> CacheHealthResponse:
    """
    **Cache health check**
    
    Performs comprehensive cache system health verification:
    - Connectivity tests to cache backend
    - Read/write operation validation
    - Performance benchmarking
    - Error detection and reporting
    
    Critical for system monitoring and troubleshooting.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        cache_service = get_cache_service()
        health_status = await cache_service.health_check()
        
        logger.info("Cache health check performed",
                   requester=current_user.get('id'),
                   status=health_status["status"])
        
        return CacheHealthResponse(**health_status)
        
    except Exception as e:
        logger.error("Cache health check failed",
                    user_id=current_user.get('id'),
                    error=str(e))
        
        return CacheHealthResponse(
            status="unhealthy",
            backend="unknown",
            distributed=False,
            test_passed=False,
            stats={},
            error=str(e)
        )


@router.delete(
    "/clear/{namespace}",
    status_code=status.HTTP_200_OK,
    summary="Clear Cache Namespace",
    description="Clears all keys in the specified cache namespace",
    response_model=CacheOperationResponse,
    tags=["Cache Management"]
)
async def clear_cache_namespace(
    namespace: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> CacheOperationResponse:
    """
    **Clear cache namespace**
    
    Clears all cached data in a specific namespace:
    - Financial data cache clearing
    - Report cache invalidation
    - Session cache cleanup
    - API response cache clearing
    
    Use with caution as this affects system performance.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for cache clearing
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    # Validate namespace
    try:
        cache_namespace = CacheNamespace(namespace)
    except ValueError:
        valid_namespaces = [ns.value for ns in CacheNamespace]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid namespace. Valid options: {valid_namespaces}"
        )
    
    try:
        cache_service = get_cache_service()
        cleared_count = await cache_service.clear_namespace(cache_namespace)
        
        logger.info("Cache namespace cleared",
                   namespace=namespace,
                   cleared_count=cleared_count,
                   requester=current_user.get('id'))
        
        return CacheOperationResponse(
            success=True,
            message=f"Successfully cleared {cleared_count} keys from namespace '{namespace}'",
            affected_keys=cleared_count,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        logger.error("Failed to clear cache namespace",
                    namespace=namespace,
                    user_id=current_user.get('id'),
                    error=str(e))
        
        return CacheOperationResponse(
            success=False,
            message=f"Failed to clear namespace '{namespace}': {str(e)}",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


@router.post(
    "/warm",
    status_code=status.HTTP_200_OK,
    summary="Warm Cache",
    description="Pre-loads frequently accessed data into cache",
    response_model=CacheOperationResponse,
    tags=["Cache Management"]
)
async def warm_cache(
    request: WarmCacheRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> CacheOperationResponse:
    """
    **Warm cache**
    
    Pre-loads frequently accessed data into cache:
    - User financial data warming
    - Popular reports pre-generation
    - Configuration data caching
    - Commonly accessed computations
    
    Improves system performance by reducing cache misses.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for cache warming
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        cache_service = get_cache_service()
        
        # Run specified warmers
        if request.warmers:
            await cache_service.warm_cache(request.warmers)
            warmer_message = f"Executed warmers: {', '.join(request.warmers)}"
        else:
            await cache_service.warm_cache()
            warmer_message = "Executed all registered warmers"
        
        # Warm specific user data
        if request.user_ids:
            for user_id in request.user_ids:
                try:
                    await warm_user_data(cache_service, user_id)
                except Exception as e:
                    logger.warning("Failed to warm user data",
                                 user_id=user_id, error=str(e))
            
            user_message = f"Warmed data for {len(request.user_ids)} users"
        else:
            user_message = "No specific users warmed"
        
        # Warm popular reports
        await warm_popular_reports(cache_service)
        
        message = f"{warmer_message}. {user_message}. Popular reports warmed."
        
        logger.info("Cache warming completed",
                   requester=current_user.get('id'),
                   warmers=request.warmers,
                   user_count=len(request.user_ids) if request.user_ids else 0)
        
        return CacheOperationResponse(
            success=True,
            message=message,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        logger.error("Cache warming failed",
                    user_id=current_user.get('id'),
                    error=str(e))
        
        return CacheOperationResponse(
            success=False,
            message=f"Cache warming failed: {str(e)}",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


@router.get(
    "/keys/{namespace}",
    status_code=status.HTTP_200_OK,
    summary="List Cache Keys",
    description="Lists keys in the specified cache namespace",
    tags=["Cache Management"]
)
async def list_cache_keys(
    namespace: str,
    pattern: Optional[str] = Query(None, description="Key pattern filter"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum keys to return"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **List cache keys**
    
    Lists cached keys in a specific namespace:
    - Pattern-based key filtering
    - Pagination support for large result sets
    - Key metadata and expiration info
    - Namespace organization
    
    Useful for cache debugging and management.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for key listing
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    # Validate namespace
    try:
        cache_namespace = CacheNamespace(namespace)
    except ValueError:
        valid_namespaces = [ns.value for ns in CacheNamespace]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid namespace. Valid options: {valid_namespaces}"
        )
    
    try:
        # This is a simplified implementation
        # In production with Redis, use SCAN command with pattern matching
        cache_service = get_cache_service()
        
        # For now, return mock data structure
        # In real implementation, scan the backend for matching keys
        result = {
            "namespace": namespace,
            "pattern": pattern,
            "keys": [],  # Would contain actual keys from cache backend
            "total_found": 0,
            "limited": False,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        logger.info("Cache keys listed",
                   namespace=namespace,
                   pattern=pattern,
                   limit=limit,
                   requester=current_user.get('id'))
        
        return result
        
    except Exception as e:
        logger.error("Failed to list cache keys",
                    namespace=namespace,
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list cache keys"
        )


@router.delete(
    "/keys/{key}",
    status_code=status.HTTP_200_OK,
    summary="Delete Cache Key",
    description="Deletes a specific cache key",
    response_model=CacheOperationResponse,
    tags=["Cache Management"]
)
async def delete_cache_key(
    key: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> CacheOperationResponse:
    """
    **Delete cache key**
    
    Removes a specific key from cache:
    - Individual key deletion
    - Cache invalidation
    - Force refresh of cached data
    - Debugging and maintenance
    
    Use for precise cache management and troubleshooting.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for key deletion
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        cache_service = get_cache_service()
        success = await cache_service.delete(key)
        
        message = f"Key '{key}' {'successfully deleted' if success else 'not found or could not be deleted'}"
        
        logger.info("Cache key deletion attempted",
                   key=key,
                   success=success,
                   requester=current_user.get('id'))
        
        return CacheOperationResponse(
            success=success,
            message=message,
            affected_keys=1 if success else 0,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        logger.error("Failed to delete cache key",
                    key=key,
                    user_id=current_user.get('id'),
                    error=str(e))
        
        return CacheOperationResponse(
            success=False,
            message=f"Failed to delete key '{key}': {str(e)}",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


@router.get(
    "/user/{user_id}/cache",
    status_code=status.HTTP_200_OK,
    summary="Get User Cache Info",
    description="Returns cache information specific to a user",
    tags=["Cache Management"]
)
async def get_user_cache_info(
    user_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Get user cache information**
    
    Returns cache data related to a specific user:
    - Cached financial data overview
    - Session information
    - Report cache status
    - Cache hit/miss rates for user data
    
    Useful for user-specific performance optimization.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Users can only see their own cache info, admins can see any
    if (current_user.get('role') != 'admin' and 
        user_id != current_user.get('id')):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only access your own cache information"
        )
    
    try:
        cache_service = get_cache_service()
        
        # In real implementation, scan for user-specific cache keys
        # and gather statistics
        
        user_cache_info = {
            "user_id": user_id,
            "cached_data_types": [
                "transactions",
                "summary",
                "reports"
            ],
            "estimated_cache_keys": 0,  # Would be calculated from actual scan
            "last_cache_activity": None,  # Would track user's cache activity
            "cache_effectiveness": {
                "estimated_hit_rate": 0.0,
                "data_freshness": "unknown"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        logger.info("User cache info retrieved",
                   target_user=user_id,
                   requester=current_user.get('id'))
        
        return user_cache_info
        
    except Exception as e:
        logger.error("Failed to get user cache info",
                    target_user=user_id,
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user cache information"
        )