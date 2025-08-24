"""
Business Intelligence and KPI endpoints.
Provides insights into application usage, user engagement, and business performance.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, status, Depends, Query, HTTPException
from pydantic import BaseModel, Field
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional
from src.services.business_metrics import (
    get_business_metrics_collector, 
    BusinessKPIs, 
    UserEngagementMetrics,
    FinancialMetrics, 
    SystemPerformanceKPIs,
    MetricType,
    get_business_dashboard_data
)

logger = structlog.get_logger()
router = APIRouter()


class BusinessDashboard(BaseModel):
    """Business intelligence dashboard response."""
    timestamp: str = Field(..., description="Dashboard timestamp", example="2024-01-15T10:30:00Z")
    period: str = Field(..., description="Data period", example="last_24_hours")
    user_engagement: UserEngagementMetrics = Field(..., description="User engagement metrics")
    financial: FinancialMetrics = Field(..., description="Financial metrics")
    system_performance: SystemPerformanceKPIs = Field(..., description="System performance KPIs")
    custom_metrics: Dict[str, Any] = Field(..., description="Custom application metrics")


class MetricDataPoint(BaseModel):
    """Individual metric data point."""
    timestamp: str = Field(..., description="Data point timestamp")
    value: float = Field(..., description="Metric value")
    labels: Dict[str, str] = Field(default_factory=dict, description="Metric labels")


class MetricHistory(BaseModel):
    """Historical metric data."""
    metric_name: str = Field(..., description="Metric name")
    description: str = Field(..., description="Metric description")
    type: str = Field(..., description="Metric type")
    data_points: List[MetricDataPoint] = Field(..., description="Historical data points")
    summary: Dict[str, float] = Field(..., description="Summary statistics")


class FeatureUsageReport(BaseModel):
    """Feature usage analytics."""
    period: str = Field(..., description="Report period")
    total_feature_interactions: int = Field(..., description="Total feature interactions")
    top_features: List[Dict[str, Any]] = Field(..., description="Most used features")
    feature_adoption_rate: float = Field(..., description="Feature adoption rate percentage")
    user_engagement_by_feature: Dict[str, int] = Field(..., description="Engagement per feature")


class APIUsageReport(BaseModel):
    """API usage analytics."""
    period: str = Field(..., description="Report period")
    total_requests: int = Field(..., description="Total API requests")
    top_endpoints: List[Dict[str, Any]] = Field(..., description="Most used endpoints")
    error_distribution: Dict[str, int] = Field(..., description="Error distribution by status code")
    avg_response_time: float = Field(..., description="Average response time in milliseconds")
    peak_usage_hours: List[int] = Field(..., description="Peak usage hours")


class UserBehaviorInsights(BaseModel):
    """User behavior analytics."""
    period: str = Field(..., description="Analysis period")
    total_active_users: int = Field(..., description="Total active users")
    new_vs_returning: Dict[str, int] = Field(..., description="New vs returning users")
    user_journey_patterns: List[Dict[str, Any]] = Field(..., description="Common user journey patterns")
    session_analytics: Dict[str, float] = Field(..., description="Session analytics")
    retention_metrics: Dict[str, float] = Field(..., description="User retention metrics")


@router.get(
    "/dashboard",
    status_code=status.HTTP_200_OK,
    summary="Get Business Intelligence Dashboard",
    description="Returns comprehensive business intelligence dashboard with key metrics and KPIs",
    response_model=BusinessDashboard,
    tags=["Business Intelligence"]
)
async def get_business_dashboard(
    period: str = Query(default="24h", description="Data period (1h, 6h, 24h, 7d, 30d)"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> BusinessDashboard:
    """
    **Get business intelligence dashboard**
    
    Provides a comprehensive view of business metrics including:
    - User engagement and behavior analytics
    - Financial application metrics
    - System performance indicators
    - Custom business KPIs
    
    This dashboard helps stakeholders understand:
    - How users are engaging with the application
    - Business performance trends
    - System health and performance
    - Feature adoption and usage patterns
    """
    try:
        # Get business KPIs
        kpis = await get_business_dashboard_data()
        
        return BusinessDashboard(
            timestamp=kpis.timestamp.isoformat() + "Z",
            period=f"last_{period}",
            user_engagement=kpis.user_engagement,
            financial=kpis.financial,
            system_performance=kpis.system_performance,
            custom_metrics=kpis.custom_metrics
        )
        
    except Exception as e:
        logger.error("Failed to get business dashboard", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve business dashboard data"
        )


@router.get(
    "/metrics/{metric_name}/history",
    status_code=status.HTTP_200_OK,
    summary="Get Metric History",
    description="Returns historical data for a specific business metric",
    response_model=MetricHistory,
    tags=["Business Intelligence"]
)
async def get_metric_history(
    metric_name: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history to retrieve"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> MetricHistory:
    """
    **Get historical data for a specific metric**
    
    Returns time-series data for business metrics including:
    - Transaction volumes and amounts
    - User engagement metrics
    - API usage patterns
    - System performance indicators
    
    Useful for:
    - Trend analysis
    - Performance monitoring
    - Business forecasting
    - Anomaly detection
    """
    try:
        collector = get_business_metrics_collector()
        history = collector.get_metric_history(metric_name, hours)
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for metric: {metric_name}"
            )
        
        # Convert to data points
        data_points = []
        values = []
        
        for metric in history:
            data_points.append(MetricDataPoint(
                timestamp=metric.timestamp.isoformat() + "Z",
                value=metric.value,
                labels=metric.labels
            ))
            values.append(metric.value)
        
        # Calculate summary statistics
        summary = {}
        if values:
            summary = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values),
                "sum": sum(values)
            }
        
        return MetricHistory(
            metric_name=metric_name,
            description=history[0].description if history else "",
            type=history[0].type.value if history else "unknown",
            data_points=data_points,
            summary=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get metric history", metric_name=metric_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history for metric: {metric_name}"
        )


@router.get(
    "/features/usage",
    status_code=status.HTTP_200_OK,
    summary="Get Feature Usage Report",
    description="Returns detailed feature usage analytics and adoption metrics",
    response_model=FeatureUsageReport,
    tags=["Business Intelligence"]
)
async def get_feature_usage_report(
    period: str = Query(default="24h", description="Analysis period"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> FeatureUsageReport:
    """
    **Get feature usage analytics**
    
    Provides insights into how users interact with different features:
    - Most popular features
    - Feature adoption rates
    - User engagement per feature
    - Usage trends over time
    
    This data helps with:
    - Product development decisions
    - Feature prioritization
    - User experience optimization
    - Resource allocation
    """
    try:
        collector = get_business_metrics_collector()
        
        # Get feature usage data
        feature_usage = dict(collector.feature_usage)
        total_interactions = sum(feature_usage.values())
        
        # Calculate top features
        top_features = [
            {"feature": feature, "usage_count": count, "percentage": (count/total_interactions)*100}
            for feature, count in collector.feature_usage.most_common(10)
        ]
        
        # Calculate adoption rate (placeholder - would need user base data)
        unique_users_with_features = len(collector.daily_stats['active_sessions'])
        feature_adoption_rate = 85.5  # Placeholder calculation
        
        return FeatureUsageReport(
            period=f"last_{period}",
            total_feature_interactions=total_interactions,
            top_features=top_features,
            feature_adoption_rate=feature_adoption_rate,
            user_engagement_by_feature=feature_usage
        )
        
    except Exception as e:
        logger.error("Failed to get feature usage report", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feature usage report"
        )


@router.get(
    "/api/usage",
    status_code=status.HTTP_200_OK,
    summary="Get API Usage Report",
    description="Returns detailed API usage analytics and performance metrics",
    response_model=APIUsageReport,
    tags=["Business Intelligence"]
)
async def get_api_usage_report(
    period: str = Query(default="24h", description="Analysis period"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> APIUsageReport:
    """
    **Get API usage analytics**
    
    Provides comprehensive API usage insights:
    - Most used endpoints
    - Request volume trends
    - Error patterns and distribution
    - Performance characteristics
    - Peak usage patterns
    
    Useful for:
    - API optimization
    - Infrastructure planning
    - Rate limiting configuration
    - Performance tuning
    """
    try:
        collector = get_business_metrics_collector()
        
        # Get API usage data
        total_requests = sum(collector.api_endpoint_usage.values())
        
        # Top endpoints
        top_endpoints = [
            {
                "endpoint": endpoint.split(":", 1)[1] if ":" in endpoint else endpoint,
                "method": endpoint.split(":", 1)[0] if ":" in endpoint else "GET",
                "request_count": count,
                "percentage": (count/total_requests)*100 if total_requests > 0 else 0
            }
            for endpoint, count in collector.api_endpoint_usage.most_common(10)
        ]
        
        # Error distribution
        error_distribution = dict(collector.error_counts)
        
        # Average response time
        avg_response_time = (
            sum(collector.response_times_buffer) / len(collector.response_times_buffer) * 1000
            if collector.response_times_buffer else 0
        )
        
        # Peak usage hours (simplified calculation)
        peak_hours = [9, 10, 11, 14, 15, 16]  # Placeholder - would analyze actual data
        
        return APIUsageReport(
            period=f"last_{period}",
            total_requests=total_requests,
            top_endpoints=top_endpoints,
            error_distribution=error_distribution,
            avg_response_time=avg_response_time,
            peak_usage_hours=peak_hours
        )
        
    except Exception as e:
        logger.error("Failed to get API usage report", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API usage report"
        )


@router.get(
    "/users/behavior",
    status_code=status.HTTP_200_OK,
    summary="Get User Behavior Insights",
    description="Returns detailed user behavior analytics and engagement patterns",
    response_model=UserBehaviorInsights,
    tags=["Business Intelligence"]
)
async def get_user_behavior_insights(
    period: str = Query(default="24h", description="Analysis period"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> UserBehaviorInsights:
    """
    **Get user behavior analytics**
    
    Provides deep insights into user behavior patterns:
    - User journey analysis
    - Session characteristics
    - Engagement patterns
    - Retention metrics
    - Usage preferences
    
    This data supports:
    - User experience optimization
    - Product development
    - Marketing strategies
    - Customer success initiatives
    """
    try:
        collector = get_business_metrics_collector()
        engagement_metrics = await collector.get_user_engagement_metrics()
        
        # User segmentation
        new_vs_returning = {
            "new_users": engagement_metrics.new_users_today,
            "returning_users": engagement_metrics.returning_users,
            "total_active": engagement_metrics.total_active_users
        }
        
        # User journey patterns (simplified)
        journey_patterns = [
            {"pattern": "Login -> Dashboard -> Transactions -> Budget", "frequency": 45},
            {"pattern": "Login -> Dashboard -> Reports", "frequency": 30},
            {"pattern": "Login -> Settings -> Asana Sync", "frequency": 15},
            {"pattern": "Login -> Dashboard -> Export", "frequency": 10}
        ]
        
        # Session analytics
        session_analytics = {
            "avg_session_duration": engagement_metrics.avg_session_duration,
            "avg_page_views": engagement_metrics.page_views_per_session,
            "bounce_rate": engagement_metrics.bounce_rate,
            "active_sessions": len(collector.user_sessions)
        }
        
        # Retention metrics
        retention_metrics = {
            "day_1_retention": 78.5,  # Placeholder
            "day_7_retention": 65.2,  # Placeholder
            "day_30_retention": 45.8,  # Placeholder
            "overall_retention": engagement_metrics.user_retention_rate
        }
        
        return UserBehaviorInsights(
            period=f"last_{period}",
            total_active_users=engagement_metrics.total_active_users,
            new_vs_returning=new_vs_returning,
            user_journey_patterns=journey_patterns,
            session_analytics=session_analytics,
            retention_metrics=retention_metrics
        )
        
    except Exception as e:
        logger.error("Failed to get user behavior insights", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user behavior insights"
        )


@router.post(
    "/track/event",
    status_code=status.HTTP_201_CREATED,
    summary="Track Custom Business Event",
    description="Track a custom business event for analytics",
    tags=["Business Intelligence"]
)
async def track_business_event(
    event_data: Dict[str, Any],
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, str]:
    """
    **Track custom business event**
    
    Allows tracking of custom business events for analytics:
    - User actions and interactions
    - Business process completions
    - Feature usage events
    - Custom KPI data points
    
    Event data should include:
    - event_type: Type of event
    - value: Numeric value (if applicable)
    - metadata: Additional context
    """
    try:
        collector = get_business_metrics_collector()
        
        event_type = event_data.get('event_type', 'custom_event')
        value = event_data.get('value', 1.0)
        user_id = current_user.get('id') if current_user else None
        metadata = event_data.get('metadata', {})
        
        # Track the event based on type
        if event_type.startswith('financial_'):
            collector.track_financial_event(event_type, value, user_id, metadata)
        else:
            collector.track_feature_usage(event_type, user_id, metadata)
        
        logger.info("Business event tracked", 
                   event_type=event_type, user_id=user_id, value=value)
        
        return {
            "status": "success", 
            "message": f"Event '{event_type}' tracked successfully"
        }
        
    except Exception as e:
        logger.error("Failed to track business event", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track business event"
        )


@router.get(
    "/export/data",
    status_code=status.HTTP_200_OK,
    summary="Export Business Intelligence Data",
    description="Export business intelligence data in various formats",
    tags=["Business Intelligence"]
)
async def export_bi_data(
    format: str = Query(default="json", description="Export format (json, csv)"),
    period: str = Query(default="24h", description="Data period"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Export business intelligence data**
    
    Exports comprehensive BI data for external analysis:
    - Raw metrics data
    - Aggregated KPIs
    - User behavior data
    - System performance metrics
    
    Supports multiple export formats for integration with:
    - Business intelligence tools
    - Data warehouses
    - Analytics platforms
    - Reporting systems
    """
    try:
        # Get all BI data
        dashboard_data = await get_business_dashboard_data()
        collector = get_business_metrics_collector()
        
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat() + "Z",
            "period": period,
            "format": format,
            "data": {
                "business_kpis": {
                    "user_engagement": dashboard_data.user_engagement.__dict__,
                    "financial": dashboard_data.financial.__dict__,
                    "system_performance": dashboard_data.system_performance.__dict__,
                    "custom_metrics": dashboard_data.custom_metrics
                },
                "raw_metrics": {
                    name: [
                        {
                            "timestamp": m.timestamp.isoformat() + "Z",
                            "value": m.value,
                            "labels": m.labels
                        }
                        for m in metrics
                    ]
                    for name, metrics in collector.metrics_storage.items()
                }
            }
        }
        
        # TODO: Convert to CSV format if requested
        if format == "csv":
            # Would implement CSV conversion here
            pass
        
        logger.info("BI data exported", format=format, period=period, 
                   user_id=current_user.get('id') if current_user else None)
        
        return export_data
        
    except Exception as e:
        logger.error("Failed to export BI data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export business intelligence data"
        )