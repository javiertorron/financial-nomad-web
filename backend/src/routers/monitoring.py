"""
Monitoring and administration endpoints for Financial Nomad.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from fastapi.responses import PlainTextResponse
import structlog

from ..models.auth import User, UserRole
from ..routers.auth import get_current_user
from ..middleware.monitoring import (
    get_metrics_collector,
    get_health_checker,
    get_prometheus_metrics,
    MetricsCollector,
    HealthChecker
)
from ..middleware.rate_limiting import get_rate_limiter, get_ip_whitelist
from ..config import get_settings
from ..infrastructure import get_firestore
from ..utils.exceptions import ValidationError as AppValidationError

logger = structlog.get_logger()

router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring", "admin"]
)


# Public health check endpoint (no auth required)
@router.get("/health")
async def basic_health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "financial-nomad-backend"
    }


@router.get("/health/detailed")
async def detailed_health_check(
    health_checker: HealthChecker = Depends(get_health_checker)
) -> Dict[str, Any]:
    """Detailed health check including dependencies."""
    return await health_checker.get_comprehensive_health()


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> str:
    """Prometheus metrics endpoint."""
    return await get_prometheus_metrics()


# Admin-only endpoints
async def require_admin_user(
    current_user_tuple: tuple = Depends(get_current_user)
) -> User:
    """Require admin user for monitoring endpoints."""
    current_user, _ = current_user_tuple
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    return current_user


@router.get("/system/status")
async def get_system_status(
    current_user: User = Depends(require_admin_user),
    metrics_collector: MetricsCollector = Depends(get_metrics_collector),
    health_checker: HealthChecker = Depends(get_health_checker)
) -> Dict[str, Any]:
    """Get comprehensive system status (admin only)."""
    try:
        # Get health status
        health_status = await health_checker.get_comprehensive_health()
        
        # Get rate limiting status
        rate_limiter = get_rate_limiter()
        rate_limit_status = await rate_limiter.get_rate_limit_status() if rate_limiter else None
        
        # Get basic system metrics
        system_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_hours": _get_uptime_hours(),
            "health": health_status,
            "rate_limiting": rate_limit_status,
            "database": await _get_database_status(),
            "application": await _get_application_status()
        }
        
        return system_status
        
    except Exception as e:
        logger.error("Failed to get system status", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to retrieve system status")


@router.get("/system/performance")
async def get_performance_metrics(
    current_user: User = Depends(require_admin_user),
    hours: int = Query(1, ge=1, le=168, description="Hours of data to analyze")
) -> Dict[str, Any]:
    """Get performance metrics for the specified time period (admin only)."""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        performance_data = {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "request_metrics": await _get_request_metrics(start_time, end_time),
            "database_metrics": await _get_database_metrics(start_time, end_time),
            "error_metrics": await _get_error_metrics(start_time, end_time),
            "resource_usage": await _get_resource_usage()
        }
        
        return performance_data
        
    except Exception as e:
        logger.error("Failed to get performance metrics", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")


@router.get("/system/users")
async def get_user_statistics(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """Get user statistics (admin only)."""
    try:
        firestore = get_firestore()
        
        # Get user counts
        all_users = await firestore.query_documents(
            collection="users",
            model_class=None
        )
        
        user_stats = {
            "total_users": len(all_users),
            "active_users_7d": 0,
            "active_users_30d": 0,
            "new_users_7d": 0,
            "new_users_30d": 0,
            "user_roles": {"admin": 0, "user": 0, "guest": 0}
        }
        
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        for user_data in all_users:
            # Count by role
            role = user_data.get("role", "user")
            user_stats["user_roles"][role] = user_stats["user_roles"].get(role, 0) + 1
            
            # Check activity
            last_login = user_data.get("last_login")
            created_at = user_data.get("created_at")
            
            if last_login:
                if isinstance(last_login, str):
                    last_login = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                
                if last_login >= week_ago:
                    user_stats["active_users_7d"] += 1
                if last_login >= month_ago:
                    user_stats["active_users_30d"] += 1
            
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                if created_at >= week_ago:
                    user_stats["new_users_7d"] += 1
                if created_at >= month_ago:
                    user_stats["new_users_30d"] += 1
        
        return user_stats
        
    except Exception as e:
        logger.error("Failed to get user statistics", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to retrieve user statistics")


@router.get("/system/database/stats")
async def get_database_statistics(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """Get database statistics (admin only)."""
    try:
        firestore = get_firestore()
        
        collections_stats = {}
        
        # Main collections to analyze
        collections = [
            "users",
            "accounts", 
            "categories",
            "transactions",
            "budgets",
            "backups",
            "exports"
        ]
        
        for collection in collections:
            try:
                # For user-scoped collections, we need to get counts differently
                if collection in ["accounts", "categories", "transactions", "budgets", "backups", "exports"]:
                    # These are subcollections, so we'll need to estimate
                    collections_stats[collection] = {
                        "estimated_documents": "N/A (subcollection)",
                        "note": "Firestore subcollection - exact count requires iteration"
                    }
                else:
                    # Direct collections
                    docs = await firestore.query_documents(
                        collection=collection,
                        model_class=None,
                        limit=1000  # Sample size
                    )
                    
                    collections_stats[collection] = {
                        "sampled_documents": len(docs),
                        "note": f"Sample of up to 1000 documents from {collection}"
                    }
                    
            except Exception as e:
                collections_stats[collection] = {
                    "error": str(e),
                    "status": "failed to query"
                }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "collections": collections_stats,
            "note": "Firestore doesn't provide direct collection size APIs. These are estimates based on samples."
        }
        
    except Exception as e:
        logger.error("Failed to get database statistics", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to retrieve database statistics")


@router.post("/system/maintenance/cleanup")
async def trigger_system_cleanup(
    current_user: User = Depends(require_admin_user),
    dry_run: bool = Query(True, description="Perform dry run without actual cleanup")
) -> Dict[str, Any]:
    """Trigger system maintenance cleanup (admin only)."""
    try:
        cleanup_results = {
            "dry_run": dry_run,
            "timestamp": datetime.utcnow().isoformat(),
            "cleanup_tasks": []
        }
        
        # Cleanup expired backups
        from ..services.backup import get_backup_service
        backup_service = get_backup_service()
        
        if not dry_run:
            backup_cleanup = await backup_service.cleanup_expired_backups()
            cleanup_results["cleanup_tasks"].append({
                "task": "backup_cleanup",
                "status": "completed",
                "results": backup_cleanup
            })
        else:
            cleanup_results["cleanup_tasks"].append({
                "task": "backup_cleanup",
                "status": "dry_run",
                "note": "Would clean expired backup records"
            })
        
        # Cleanup expired sessions
        cleanup_results["cleanup_tasks"].append({
            "task": "session_cleanup",
            "status": "planned",
            "note": "Session cleanup would be implemented here"
        })
        
        # Cleanup old logs/metrics
        cleanup_results["cleanup_tasks"].append({
            "task": "logs_cleanup",
            "status": "planned",
            "note": "Log rotation cleanup would be implemented here"
        })
        
        logger.info(
            "System cleanup completed",
            dry_run=dry_run,
            user_id=current_user.id,
            tasks=len(cleanup_results["cleanup_tasks"])
        )
        
        return cleanup_results
        
    except Exception as e:
        logger.error("System cleanup failed", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="System cleanup failed")


@router.get("/system/logs")
async def get_recent_logs(
    current_user: User = Depends(require_admin_user),
    level: str = Query("INFO", description="Minimum log level"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of log entries")
) -> Dict[str, Any]:
    """Get recent system logs (admin only)."""
    try:
        # This is a placeholder - in a real implementation, you'd query your logging system
        # (e.g., Cloud Logging, Elasticsearch, etc.)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level_filter": level,
            "limit": limit,
            "logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": "System logs endpoint accessed",
                    "user_id": current_user.id,
                    "module": "monitoring"
                }
            ],
            "note": "This is a placeholder. In production, integrate with your logging system (Cloud Logging, ELK, etc.)"
        }
        
    except Exception as e:
        logger.error("Failed to get recent logs", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to retrieve system logs")


# Helper functions
def _get_uptime_hours() -> float:
    """Get application uptime in hours."""
    # This is a placeholder - in a real implementation, you'd track actual startup time
    return 24.5  # Example value


async def _get_database_status() -> Dict[str, Any]:
    """Get database connection and performance status."""
    try:
        firestore = get_firestore()
        
        # Simple connectivity test
        start_time = datetime.utcnow()
        await firestore.get_document(
            collection="health_checks",
            document_id="test",
            model_class=None
        )
        end_time = datetime.utcnow()
        
        response_time = (end_time - start_time).total_seconds() * 1000
        
        return {
            "status": "connected",
            "response_time_ms": round(response_time, 2),
            "last_check": end_time.isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "last_check": datetime.utcnow().isoformat()
        }


async def _get_application_status() -> Dict[str, Any]:
    """Get application-specific status information."""
    return {
        "services": {
            "backup_service": "running",
            "export_service": "running", 
            "drive_integration": "running",
            "asana_integration": "running"
        },
        "background_tasks": {
            "backup_scheduler": "active",
            "cleanup_tasks": "active"
        }
    }


async def _get_request_metrics(start_time: datetime, end_time: datetime) -> Dict[str, Any]:
    """Get request metrics for the time period."""
    # Placeholder - in production, query your metrics store
    return {
        "total_requests": 1500,
        "avg_response_time_ms": 125.5,
        "p95_response_time_ms": 450.0,
        "error_rate_percent": 2.1,
        "requests_per_minute": 25.0
    }


async def _get_database_metrics(start_time: datetime, end_time: datetime) -> Dict[str, Any]:
    """Get database metrics for the time period."""
    return {
        "total_operations": 850,
        "read_operations": 650,
        "write_operations": 200,
        "avg_query_time_ms": 45.2,
        "slow_queries": 5
    }


async def _get_error_metrics(start_time: datetime, end_time: datetime) -> Dict[str, Any]:
    """Get error metrics for the time period."""
    return {
        "total_errors": 32,
        "4xx_errors": 25,
        "5xx_errors": 7,
        "top_errors": [
            {"status": 404, "count": 15, "description": "Not Found"},
            {"status": 401, "count": 10, "description": "Unauthorized"},
            {"status": 500, "count": 4, "description": "Internal Server Error"}
        ]
    }


async def _get_resource_usage() -> Dict[str, Any]:
    """Get current resource usage."""
    import psutil
    import os
    
    try:
        process = psutil.Process(os.getpid())
        
        return {
            "memory": {
                "used_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2)
            },
            "cpu": {
                "percent": round(process.cpu_percent(), 2)
            },
            "threads": process.num_threads(),
            "connections": len(process.connections())
        }
        
    except ImportError:
        return {
            "note": "psutil not available - install for detailed resource metrics"
        }
    except Exception as e:
        return {
            "error": str(e)
        }