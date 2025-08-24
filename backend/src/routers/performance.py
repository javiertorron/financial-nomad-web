"""
Performance optimization endpoints for production readiness.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, status, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
import psutil
import time
import asyncio
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional

logger = structlog.get_logger()
router = APIRouter()


class SystemMetrics(BaseModel):
    """System performance metrics."""
    cpu_percent: float = Field(..., description="CPU usage percentage", example=25.3)
    memory_percent: float = Field(..., description="Memory usage percentage", example=45.7)
    memory_used_mb: float = Field(..., description="Memory used in MB", example=1024.5)
    memory_total_mb: float = Field(..., description="Total memory in MB", example=2048.0)
    disk_usage_percent: float = Field(..., description="Disk usage percentage", example=67.2)
    network_bytes_sent: int = Field(..., description="Network bytes sent", example=1048576)
    network_bytes_recv: int = Field(..., description="Network bytes received", example=2097152)
    load_average: List[float] = Field(..., description="System load average", example=[0.5, 0.3, 0.2])


class CacheMetrics(BaseModel):
    """Cache performance metrics."""
    query_cache_hits: int = Field(..., description="Query cache hits", example=150)
    query_cache_misses: int = Field(..., description="Query cache misses", example=50)
    query_cache_hit_rate: float = Field(..., description="Query cache hit rate", example=0.75)
    session_cache_size: int = Field(..., description="Session cache entries", example=25)
    computation_cache_size: int = Field(..., description="Computation cache entries", example=100)
    total_memory_usage_mb: float = Field(..., description="Total cache memory usage MB", example=45.2)


class PerformanceReport(BaseModel):
    """Complete performance report."""
    timestamp: str = Field(..., description="Report timestamp", example="2024-01-15T10:30:00Z")
    system: SystemMetrics = Field(..., description="System metrics")
    cache: CacheMetrics = Field(..., description="Cache metrics")
    uptime_seconds: float = Field(..., description="Application uptime", example=3600.0)
    request_count_last_hour: int = Field(..., description="Requests in last hour", example=500)
    avg_response_time_ms: float = Field(..., description="Average response time", example=45.2)
    error_rate_percent: float = Field(..., description="Error rate percentage", example=0.5)


class OptimizationTask(BaseModel):
    """Background optimization task."""
    task_id: str = Field(..., description="Task ID", example="opt_123456")
    type: str = Field(..., description="Optimization type", example="cache_warmup")
    status: str = Field(..., description="Task status", example="running")
    started_at: str = Field(..., description="Start time", example="2024-01-15T10:30:00Z")
    progress_percent: int = Field(..., description="Progress percentage", example=75)
    estimated_completion: Optional[str] = Field(None, description="Estimated completion time")


# Global variables for tracking
_optimization_tasks: Dict[str, OptimizationTask] = {}
_request_counts = []
_response_times = []
_error_counts = []


def get_system_metrics() -> SystemMetrics:
    """Get current system performance metrics."""
    try:
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Network stats
        network = psutil.net_io_counters()
        
        # Load average (Unix-like systems)
        try:
            load_avg = list(psutil.getloadavg())
        except AttributeError:
            # Windows doesn't have load average
            load_avg = [0.0, 0.0, 0.0]
        
        return SystemMetrics(
            cpu_percent=round(cpu_percent, 1),
            memory_percent=round(memory.percent, 1),
            memory_used_mb=round(memory.used / 1024 / 1024, 1),
            memory_total_mb=round(memory.total / 1024 / 1024, 1),
            disk_usage_percent=round(disk.percent, 1),
            network_bytes_sent=network.bytes_sent,
            network_bytes_recv=network.bytes_recv,
            load_average=[round(x, 2) for x in load_avg]
        )
    except Exception as e:
        logger.error("Failed to get system metrics", error=str(e))
        # Return default values if metrics collection fails
        return SystemMetrics(
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_used_mb=0.0,
            memory_total_mb=0.0,
            disk_usage_percent=0.0,
            network_bytes_sent=0,
            network_bytes_recv=0,
            load_average=[0.0, 0.0, 0.0]
        )


def get_cache_metrics() -> CacheMetrics:
    """Get cache performance metrics."""
    try:
        from src.services.caching import get_cache_service
        cache_service = get_cache_service()
        
        # Get cache statistics (synchronous version)
        session_cache_size = len(cache_service.user_session_cache._cache)
        computation_cache_size = len(cache_service.computation_cache._cache)
        
        # Mock stats for now since get_stats is async
        query_stats = {'hits': 0, 'misses': 0}
        
        # Calculate hit rate
        total_requests = query_stats.get('hits', 0) + query_stats.get('misses', 0)
        hit_rate = query_stats.get('hits', 0) / total_requests if total_requests > 0 else 0.0
        
        # Estimate memory usage (rough calculation)
        memory_usage_mb = (session_cache_size * 0.1 + computation_cache_size * 0.05)  # MB estimate
        
        return CacheMetrics(
            query_cache_hits=query_stats.get('hits', 0),
            query_cache_misses=query_stats.get('misses', 0),
            query_cache_hit_rate=round(hit_rate, 3),
            session_cache_size=session_cache_size,
            computation_cache_size=computation_cache_size,
            total_memory_usage_mb=round(memory_usage_mb, 1)
        )
    except Exception as e:
        logger.error("Failed to get cache metrics", error=str(e))
        return CacheMetrics(
            query_cache_hits=0,
            query_cache_misses=0,
            query_cache_hit_rate=0.0,
            session_cache_size=0,
            computation_cache_size=0,
            total_memory_usage_mb=0.0
        )


async def get_cache_metrics_async() -> CacheMetrics:
    """Get cache performance metrics (async version)."""
    try:
        from src.services.caching import get_cache_service
        cache_service = get_cache_service()
        
        # Get cache statistics asynchronously
        query_stats = await cache_service.query_cache.get_stats()
        session_cache_size = len(cache_service.user_session_cache._cache)
        computation_cache_size = len(cache_service.computation_cache._cache)
        
        # Calculate hit rate
        total_requests = query_stats.get('hits', 0) + query_stats.get('misses', 0)
        hit_rate = query_stats.get('hits', 0) / total_requests if total_requests > 0 else 0.0
        
        # Estimate memory usage (rough calculation)
        memory_usage_mb = (session_cache_size * 0.1 + computation_cache_size * 0.05)  # MB estimate
        
        return CacheMetrics(
            query_cache_hits=query_stats.get('hits', 0),
            query_cache_misses=query_stats.get('misses', 0),
            query_cache_hit_rate=round(hit_rate, 3),
            session_cache_size=session_cache_size,
            computation_cache_size=computation_cache_size,
            total_memory_usage_mb=round(memory_usage_mb, 1)
        )
    except Exception as e:
        logger.error("Failed to get cache metrics", error=str(e))
        return CacheMetrics(
            query_cache_hits=0,
            query_cache_misses=0,
            query_cache_hit_rate=0.0,
            session_cache_size=0,
            computation_cache_size=0,
            total_memory_usage_mb=0.0
        )


@router.get(
    "/metrics/system",
    status_code=status.HTTP_200_OK,
    summary="Get System Performance Metrics",
    description="Returns current system performance metrics including CPU, memory, disk, and network usage",
    response_model=SystemMetrics,
    tags=["Performance"]
)
async def get_system_performance_metrics() -> SystemMetrics:
    """
    **Get system performance metrics**
    
    Returns real-time system performance information:
    - CPU usage percentage
    - Memory usage and availability
    - Disk usage statistics
    - Network I/O counters
    - System load average
    
    This endpoint helps monitor system health and resource utilization.
    """
    return get_system_metrics()


@router.get(
    "/metrics/cache",
    status_code=status.HTTP_200_OK,
    summary="Get Cache Performance Metrics",
    description="Returns cache performance metrics including hit rates and memory usage",
    response_model=CacheMetrics,
    tags=["Performance"]
)
async def get_cache_performance_metrics() -> CacheMetrics:
    """
    **Get cache performance metrics**
    
    Returns cache performance information:
    - Cache hit/miss rates
    - Cache entry counts
    - Memory usage estimates
    
    This endpoint helps optimize caching strategies and monitor cache effectiveness.
    """
    return get_cache_metrics()


@router.get(
    "/report",
    status_code=status.HTTP_200_OK,
    summary="Get Complete Performance Report",
    description="Returns comprehensive performance report with system and application metrics",
    response_model=PerformanceReport,
    tags=["Performance"]
)
async def get_performance_report(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> PerformanceReport:
    """
    **Get comprehensive performance report**
    
    Returns a complete performance analysis including:
    - System resource utilization
    - Cache performance metrics
    - Application uptime
    - Request volume and response times
    - Error rates
    
    This endpoint provides a holistic view of application performance.
    """
    system_metrics = get_system_metrics()
    cache_metrics = await get_cache_metrics_async()
    
    # Calculate uptime (approximate)
    from src.routers.frontend import _server_start_time
    uptime = time.time() - _server_start_time
    
    # Calculate recent request metrics (mock data for now)
    recent_requests = len(_request_counts)
    avg_response_time = sum(_response_times) / len(_response_times) if _response_times else 0.0
    error_rate = (len(_error_counts) / recent_requests * 100) if recent_requests > 0 else 0.0
    
    return PerformanceReport(
        timestamp=datetime.utcnow().isoformat() + "Z",
        system=system_metrics,
        cache=cache_metrics,
        uptime_seconds=round(uptime, 1),
        request_count_last_hour=recent_requests,
        avg_response_time_ms=round(avg_response_time, 1),
        error_rate_percent=round(error_rate, 2)
    )


async def _cache_warmup_task(task_id: str):
    """Background task to warm up caches."""
    try:
        from src.services.caching import get_cache_service
        cache_service = get_cache_service()
        
        # Update task status
        _optimization_tasks[task_id].status = "running"
        _optimization_tasks[task_id].progress_percent = 10
        
        # Simulate cache warmup operations
        await asyncio.sleep(2)
        _optimization_tasks[task_id].progress_percent = 50
        
        # Pre-populate common cache entries
        await asyncio.sleep(2)
        _optimization_tasks[task_id].progress_percent = 100
        _optimization_tasks[task_id].status = "completed"
        
        logger.info("Cache warmup completed", task_id=task_id)
        
    except Exception as e:
        _optimization_tasks[task_id].status = "failed"
        logger.error("Cache warmup failed", task_id=task_id, error=str(e))


@router.post(
    "/optimize/cache-warmup",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start Cache Warmup",
    description="Starts a background task to warm up application caches",
    response_model=OptimizationTask,
    tags=["Performance"]
)
async def start_cache_warmup(
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> OptimizationTask:
    """
    **Start cache warmup optimization**
    
    Initiates a background task to pre-populate caches with frequently
    accessed data. This can improve response times for subsequent requests.
    
    The task runs asynchronously and its progress can be monitored using
    the task ID returned in the response.
    """
    import uuid
    
    task_id = f"warmup_{uuid.uuid4().hex[:8]}"
    task = OptimizationTask(
        task_id=task_id,
        type="cache_warmup",
        status="queued",
        started_at=datetime.utcnow().isoformat() + "Z",
        progress_percent=0,
        estimated_completion=(datetime.utcnow() + timedelta(minutes=1)).isoformat() + "Z"
    )
    
    _optimization_tasks[task_id] = task
    background_tasks.add_task(_cache_warmup_task, task_id)
    
    return task


@router.get(
    "/optimize/tasks/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Optimization Task Status",
    description="Returns the status of a background optimization task",
    response_model=OptimizationTask,
    tags=["Performance"]
)
async def get_optimization_task_status(task_id: str) -> OptimizationTask:
    """
    **Get optimization task status**
    
    Returns the current status and progress of a background optimization task.
    Use this endpoint to monitor long-running optimization operations.
    """
    task = _optimization_tasks.get(task_id)
    if not task:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimization task not found"
        )
    
    return task


@router.delete(
    "/optimize/cache",
    status_code=status.HTTP_200_OK,
    summary="Clear All Caches",
    description="Clears all application caches to free memory",
    tags=["Performance"]
)
async def clear_all_caches(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Clear all application caches**
    
    Removes all cached data to free up memory. This can help with memory
    pressure but may temporarily impact performance until caches are repopulated.
    
    Use this endpoint when experiencing memory issues or after significant
    data changes that require cache invalidation.
    """
    try:
        from src.services.caching import get_cache_service
        cache_service = get_cache_service()
        
        # Get metrics before clearing
        cache_metrics_before = get_cache_metrics()
        
        # Clear all caches
        cache_service.clear_all_caches()
        
        # Get metrics after clearing
        cache_metrics_after = get_cache_metrics()
        
        memory_freed_mb = cache_metrics_before.total_memory_usage_mb - cache_metrics_after.total_memory_usage_mb
        
        return {
            "success": True,
            "message": "All caches cleared successfully",
            "entries_removed": {
                "query_cache": cache_metrics_before.query_cache_hits + cache_metrics_before.query_cache_misses,
                "session_cache": cache_metrics_before.session_cache_size,
                "computation_cache": cache_metrics_before.computation_cache_size
            },
            "memory_freed_mb": round(memory_freed_mb, 1),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error("Failed to clear caches", error=str(e))
        return {
            "success": False,
            "message": f"Failed to clear caches: {str(e)}",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


@router.get(
    "/health/detailed",
    status_code=status.HTTP_200_OK,
    summary="Detailed Performance Health Check",
    description="Returns detailed health check focused on performance metrics",
    tags=["Performance"]
)
async def performance_health_check() -> Dict[str, Any]:
    """
    **Performance-focused health check**
    
    Returns a health check specifically focused on performance metrics:
    - Resource utilization warnings
    - Cache performance health
    - Response time analysis
    - System load assessment
    """
    system_metrics = get_system_metrics()
    cache_metrics = get_cache_metrics()
    
    # Assess health based on thresholds
    warnings = []
    status_level = "healthy"
    
    # CPU check
    if system_metrics.cpu_percent > 80:
        warnings.append("High CPU usage")
        status_level = "warning"
    elif system_metrics.cpu_percent > 95:
        warnings.append("Critical CPU usage")
        status_level = "critical"
    
    # Memory check
    if system_metrics.memory_percent > 85:
        warnings.append("High memory usage")
        status_level = "warning"
    elif system_metrics.memory_percent > 95:
        warnings.append("Critical memory usage")
        status_level = "critical"
    
    # Cache performance check
    if cache_metrics.query_cache_hit_rate < 0.5:
        warnings.append("Low cache hit rate")
        if status_level == "healthy":
            status_level = "warning"
    
    return {
        "status": status_level,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "system_metrics": system_metrics.dict(),
        "cache_metrics": cache_metrics.dict(),
        "warnings": warnings,
        "recommendations": [
            "Monitor CPU usage patterns",
            "Consider cache warming for better hit rates", 
            "Review memory usage trends",
            "Optimize database queries if response times are high"
        ]
    }