"""
Resilience monitoring and management endpoints.
Provides insights into circuit breakers, fault tolerance, and system resilience.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, status, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional
from src.services.circuit_breaker import (
    get_circuit_breaker_manager, 
    CircuitState, 
    FallbackType,
    CircuitBreakerConfig
)
from src.services.fault_tolerance import get_fault_tolerance_service

logger = structlog.get_logger()
router = APIRouter()


class CircuitBreakerStatusResponse(BaseModel):
    """Circuit breaker status response."""
    name: str = Field(..., description="Circuit breaker name")
    state: str = Field(..., description="Current state")
    failure_count: int = Field(..., description="Current failure count")
    success_count: int = Field(..., description="Current success count")
    total_calls: int = Field(..., description="Total calls in evaluation window")
    success_rate: float = Field(..., description="Success rate percentage")
    average_response_time: float = Field(..., description="Average response time")
    slow_call_rate: float = Field(..., description="Slow call rate percentage")
    last_failure_time: Optional[str] = Field(None, description="Last failure timestamp")
    state_changed_time: str = Field(..., description="State change timestamp")


class FaultToleranceStatsResponse(BaseModel):
    """Fault tolerance statistics response."""
    service_name: str = Field(..., description="Service name")
    total_calls: int = Field(..., description="Total calls")
    successful_calls: int = Field(..., description="Successful calls")
    failed_calls: int = Field(..., description="Failed calls")
    retried_calls: int = Field(..., description="Calls that were retried")
    timeout_calls: int = Field(..., description="Calls that timed out")
    circuit_breaker_calls: int = Field(..., description="Circuit breaker triggered calls")
    bulkhead_rejections: int = Field(..., description="Bulkhead rejections")
    fallback_executions: int = Field(..., description="Fallback executions")
    avg_response_time: float = Field(..., description="Average response time")
    success_rate: float = Field(..., description="Success rate percentage")


class ResilienceOverviewResponse(BaseModel):
    """Overall resilience status response."""
    timestamp: str = Field(..., description="Status timestamp")
    overall_health: str = Field(..., description="Overall resilience health")
    circuit_breakers: List[CircuitBreakerStatusResponse] = Field(..., description="Circuit breaker statuses")
    fault_tolerance_stats: List[FaultToleranceStatsResponse] = Field(..., description="Fault tolerance statistics")
    recommendations: List[str] = Field(..., description="Resilience recommendations")


class CircuitBreakerActionRequest(BaseModel):
    """Circuit breaker action request."""
    action: str = Field(..., description="Action to perform (reset, open, close)")
    reason: str = Field(..., description="Reason for the action")


@router.get(
    "/circuit-breakers",
    status_code=status.HTTP_200_OK,
    summary="Get All Circuit Breakers Status",
    description="Returns status of all circuit breakers in the system",
    response_model=List[CircuitBreakerStatusResponse],
    tags=["Resilience"]
)
async def get_circuit_breakers_status(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[CircuitBreakerStatusResponse]:
    """
    **Get all circuit breakers status**
    
    Returns comprehensive status information for all circuit breakers:
    - Current state (CLOSED, OPEN, HALF_OPEN)
    - Success and failure rates
    - Response time metrics
    - State change history
    
    This endpoint helps monitor system resilience and identify
    problematic external dependencies.
    """
    try:
        manager = get_circuit_breaker_manager()
        stats = manager.get_all_stats()
        
        result = []
        for name, stat in stats.items():
            result.append(CircuitBreakerStatusResponse(
                name=name,
                state=stat.state.value,
                failure_count=stat.failure_count,
                success_count=stat.success_count,
                total_calls=stat.total_calls,
                success_rate=stat.success_rate,
                average_response_time=stat.average_response_time,
                slow_call_rate=stat.slow_call_rate,
                last_failure_time=stat.last_failure_time.isoformat() + "Z" if stat.last_failure_time else None,
                state_changed_time=stat.state_changed_time.isoformat() + "Z"
            ))
        
        return result
        
    except Exception as e:
        logger.error("Failed to get circuit breakers status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve circuit breakers status"
        )


@router.get(
    "/circuit-breakers/{breaker_name}",
    status_code=status.HTTP_200_OK,
    summary="Get Circuit Breaker Status",
    description="Returns detailed status of a specific circuit breaker",
    response_model=CircuitBreakerStatusResponse,
    tags=["Resilience"]
)
async def get_circuit_breaker_status(
    breaker_name: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> CircuitBreakerStatusResponse:
    """
    **Get specific circuit breaker status**
    
    Returns detailed information about a specific circuit breaker:
    - Current operational state
    - Performance metrics
    - Failure patterns
    - Configuration details
    """
    try:
        manager = get_circuit_breaker_manager()
        
        if breaker_name not in manager.circuit_breakers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Circuit breaker '{breaker_name}' not found"
            )
        
        breaker = manager.circuit_breakers[breaker_name]
        stat = breaker.get_stats()
        
        return CircuitBreakerStatusResponse(
            name=breaker_name,
            state=stat.state.value,
            failure_count=stat.failure_count,
            success_count=stat.success_count,
            total_calls=stat.total_calls,
            success_rate=stat.success_rate,
            average_response_time=stat.average_response_time,
            slow_call_rate=stat.slow_call_rate,
            last_failure_time=stat.last_failure_time.isoformat() + "Z" if stat.last_failure_time else None,
            state_changed_time=stat.state_changed_time.isoformat() + "Z"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get circuit breaker status", breaker_name=breaker_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve circuit breaker '{breaker_name}' status"
        )


@router.post(
    "/circuit-breakers/{breaker_name}/action",
    status_code=status.HTTP_200_OK,
    summary="Perform Circuit Breaker Action",
    description="Perform administrative actions on a circuit breaker",
    tags=["Resilience"]
)
async def perform_circuit_breaker_action(
    breaker_name: str,
    action_request: CircuitBreakerActionRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Perform circuit breaker action**
    
    Administrative actions for circuit breakers:
    - reset: Reset circuit breaker to CLOSED state
    - open: Force circuit breaker to OPEN state
    - close: Force circuit breaker to CLOSED state
    
    These actions should be used carefully and are typically
    needed for maintenance or emergency situations.
    
    Requires administrative privileges.
    """
    try:
        # Check admin privileges
        if not current_user or current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required for circuit breaker actions"
            )
        
        manager = get_circuit_breaker_manager()
        
        if breaker_name not in manager.circuit_breakers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Circuit breaker '{breaker_name}' not found"
            )
        
        breaker = manager.circuit_breakers[breaker_name]
        
        if action_request.action == "reset":
            breaker.reset()
            message = f"Circuit breaker '{breaker_name}' reset to CLOSED state"
            
        elif action_request.action == "open":
            breaker._transition_to_open()
            message = f"Circuit breaker '{breaker_name}' forced to OPEN state"
            
        elif action_request.action == "close":
            breaker._transition_to_closed()
            message = f"Circuit breaker '{breaker_name}' forced to CLOSED state"
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action. Valid actions: reset, open, close"
            )
        
        # Log the action
        logger.warning("Circuit breaker action performed",
                      breaker_name=breaker_name,
                      action=action_request.action,
                      reason=action_request.reason,
                      performed_by=current_user.get('email', 'unknown'))
        
        return {
            "status": "success",
            "message": message,
            "action": action_request.action,
            "reason": action_request.reason,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to perform circuit breaker action", 
                    breaker_name=breaker_name, action=action_request.action, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform circuit breaker action"
        )


@router.get(
    "/fault-tolerance",
    status_code=status.HTTP_200_OK,
    summary="Get Fault Tolerance Statistics",
    description="Returns fault tolerance statistics for all services",
    response_model=List[FaultToleranceStatsResponse],
    tags=["Resilience"]
)
async def get_fault_tolerance_stats(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[FaultToleranceStatsResponse]:
    """
    **Get fault tolerance statistics**
    
    Returns comprehensive fault tolerance metrics:
    - Retry statistics and patterns
    - Timeout occurrences
    - Bulkhead performance
    - Fallback execution rates
    - Overall success rates
    
    These metrics help understand how well the system
    is handling failures and recovering from issues.
    """
    try:
        service = get_fault_tolerance_service()
        all_stats = service.get_all_stats()
        
        result = []
        for service_name, stats in all_stats.items():
            result.append(FaultToleranceStatsResponse(
                service_name=service_name,
                total_calls=stats.total_calls,
                successful_calls=stats.successful_calls,
                failed_calls=stats.failed_calls,
                retried_calls=stats.retried_calls,
                timeout_calls=stats.timeout_calls,
                circuit_breaker_calls=stats.circuit_breaker_calls,
                bulkhead_rejections=stats.bulkhead_rejections,
                fallback_executions=stats.fallback_executions,
                avg_response_time=stats.avg_response_time,
                success_rate=stats.success_rate
            ))
        
        return result
        
    except Exception as e:
        logger.error("Failed to get fault tolerance stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve fault tolerance statistics"
        )


@router.get(
    "/fault-tolerance/{service_name}",
    status_code=status.HTTP_200_OK,
    summary="Get Service Fault Tolerance Statistics",
    description="Returns fault tolerance statistics for a specific service",
    response_model=FaultToleranceStatsResponse,
    tags=["Resilience"]
)
async def get_service_fault_tolerance_stats(
    service_name: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> FaultToleranceStatsResponse:
    """
    **Get service-specific fault tolerance statistics**
    
    Returns detailed fault tolerance metrics for a specific service:
    - Call patterns and success rates
    - Retry behavior and effectiveness
    - Resource isolation metrics
    - Failure recovery patterns
    """
    try:
        service = get_fault_tolerance_service()
        stats = service.get_service_stats(service_name)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No fault tolerance stats found for service '{service_name}'"
            )
        
        return FaultToleranceStatsResponse(
            service_name=service_name,
            total_calls=stats.total_calls,
            successful_calls=stats.successful_calls,
            failed_calls=stats.failed_calls,
            retried_calls=stats.retried_calls,
            timeout_calls=stats.timeout_calls,
            circuit_breaker_calls=stats.circuit_breaker_calls,
            bulkhead_rejections=stats.bulkhead_rejections,
            fallback_executions=stats.fallback_executions,
            avg_response_time=stats.avg_response_time,
            success_rate=stats.success_rate
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get service fault tolerance stats", 
                    service_name=service_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve fault tolerance stats for '{service_name}'"
        )


@router.get(
    "/overview",
    status_code=status.HTTP_200_OK,
    summary="Get Resilience Overview",
    description="Returns comprehensive resilience overview with recommendations",
    response_model=ResilienceOverviewResponse,
    tags=["Resilience"]
)
async def get_resilience_overview(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> ResilienceOverviewResponse:
    """
    **Get comprehensive resilience overview**
    
    Provides a high-level view of system resilience including:
    - Overall health assessment
    - Circuit breaker states and trends
    - Fault tolerance effectiveness
    - Actionable recommendations
    
    This is the primary endpoint for monitoring system resilience
    and identifying potential issues before they impact users.
    """
    try:
        # Get circuit breaker stats
        cb_manager = get_circuit_breaker_manager()
        cb_stats = cb_manager.get_all_stats()
        
        circuit_breakers = []
        open_breakers = 0
        
        for name, stat in cb_stats.items():
            if stat.state == CircuitState.OPEN:
                open_breakers += 1
            
            circuit_breakers.append(CircuitBreakerStatusResponse(
                name=name,
                state=stat.state.value,
                failure_count=stat.failure_count,
                success_count=stat.success_count,
                total_calls=stat.total_calls,
                success_rate=stat.success_rate,
                average_response_time=stat.average_response_time,
                slow_call_rate=stat.slow_call_rate,
                last_failure_time=stat.last_failure_time.isoformat() + "Z" if stat.last_failure_time else None,
                state_changed_time=stat.state_changed_time.isoformat() + "Z"
            ))
        
        # Get fault tolerance stats
        ft_service = get_fault_tolerance_service()
        ft_stats = ft_service.get_all_stats()
        
        fault_tolerance_stats = []
        total_success_rate = 0
        
        for service_name, stats in ft_stats.items():
            fault_tolerance_stats.append(FaultToleranceStatsResponse(
                service_name=service_name,
                total_calls=stats.total_calls,
                successful_calls=stats.successful_calls,
                failed_calls=stats.failed_calls,
                retried_calls=stats.retried_calls,
                timeout_calls=stats.timeout_calls,
                circuit_breaker_calls=stats.circuit_breaker_calls,
                bulkhead_rejections=stats.bulkhead_rejections,
                fallback_executions=stats.fallback_executions,
                avg_response_time=stats.avg_response_time,
                success_rate=stats.success_rate
            ))
            total_success_rate += stats.success_rate
        
        # Calculate overall health
        avg_success_rate = total_success_rate / len(ft_stats) if ft_stats else 100.0
        
        if open_breakers > 0:
            overall_health = "degraded"
        elif avg_success_rate < 95:
            overall_health = "warning"
        else:
            overall_health = "healthy"
        
        # Generate recommendations
        recommendations = []
        
        if open_breakers > 0:
            recommendations.append(f"{open_breakers} circuit breaker(s) are open - investigate external dependencies")
        
        if avg_success_rate < 90:
            recommendations.append("Low success rate detected - review error patterns and retry configurations")
        
        high_timeout_services = [s for s in ft_stats.values() if s.timeout_calls / max(s.total_calls, 1) > 0.1]
        if high_timeout_services:
            recommendations.append("High timeout rates detected - consider adjusting timeout configurations")
        
        high_bulkhead_rejection_services = [s for s in ft_stats.values() if s.bulkhead_rejections > 10]
        if high_bulkhead_rejection_services:
            recommendations.append("High bulkhead rejections - consider increasing concurrency limits")
        
        if not recommendations:
            recommendations = [
                "System resilience is operating normally",
                "Continue monitoring for trends and patterns",
                "Consider load testing to validate fault tolerance"
            ]
        
        return ResilienceOverviewResponse(
            timestamp=datetime.utcnow().isoformat() + "Z",
            overall_health=overall_health,
            circuit_breakers=circuit_breakers,
            fault_tolerance_stats=fault_tolerance_stats,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error("Failed to get resilience overview", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resilience overview"
        )


@router.post(
    "/reset",
    status_code=status.HTTP_200_OK,
    summary="Reset Resilience Statistics",
    description="Reset all resilience statistics and circuit breakers",
    tags=["Resilience"]
)
async def reset_resilience_stats(
    reset_type: str = Query(default="stats", description="Type of reset (stats, circuit_breakers, all)"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Reset resilience statistics**
    
    Administrative function to reset resilience components:
    - stats: Reset fault tolerance statistics
    - circuit_breakers: Reset all circuit breakers to CLOSED
    - all: Reset both statistics and circuit breakers
    
    This is typically used after maintenance or for testing purposes.
    Requires administrative privileges.
    """
    try:
        # Check admin privileges
        if not current_user or current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required for resilience reset"
            )
        
        reset_actions = []
        
        if reset_type in ["stats", "all"]:
            ft_service = get_fault_tolerance_service()
            ft_service.reset_stats()
            reset_actions.append("fault tolerance statistics")
        
        if reset_type in ["circuit_breakers", "all"]:
            cb_manager = get_circuit_breaker_manager()
            cb_manager.reset_all()
            reset_actions.append("circuit breakers")
        
        if not reset_actions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset type. Valid types: stats, circuit_breakers, all"
            )
        
        logger.warning("Resilience reset performed",
                      reset_type=reset_type,
                      actions=reset_actions,
                      performed_by=current_user.get('email', 'unknown'))
        
        return {
            "status": "success",
            "message": f"Reset completed for: {', '.join(reset_actions)}",
            "reset_type": reset_type,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to reset resilience stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset resilience statistics"
        )