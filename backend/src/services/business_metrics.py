"""
Business metrics and KPI tracking service.
Provides insights into application usage, user engagement, and business performance.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import structlog
import asyncio
from collections import defaultdict, Counter
import time

from src.config import settings

logger = structlog.get_logger()


class MetricType(Enum):
    """Types of business metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class BusinessMetric:
    """Business metric data structure."""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class UserEngagementMetrics:
    """User engagement metrics."""
    total_active_users: int = 0
    new_users_today: int = 0
    returning_users: int = 0
    avg_session_duration: float = 0.0
    page_views_per_session: float = 0.0
    bounce_rate: float = 0.0
    user_retention_rate: float = 0.0


@dataclass
class FinancialMetrics:
    """Financial application specific metrics."""
    total_transactions: int = 0
    transactions_today: int = 0
    total_accounts: int = 0
    active_budgets: int = 0
    avg_transaction_amount: float = 0.0
    budget_compliance_rate: float = 0.0
    asana_sync_success_rate: float = 0.0


@dataclass
class SystemPerformanceKPIs:
    """System performance KPIs."""
    availability_percentage: float = 0.0
    avg_response_time_ms: float = 0.0
    error_rate_percentage: float = 0.0
    throughput_requests_per_minute: float = 0.0
    cache_hit_rate: float = 0.0
    database_query_time_ms: float = 0.0


@dataclass
class BusinessKPIs:
    """Complete business KPIs dashboard."""
    timestamp: datetime
    user_engagement: UserEngagementMetrics
    financial: FinancialMetrics
    system_performance: SystemPerformanceKPIs
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


class BusinessMetricsCollector:
    """Collects and tracks business metrics and KPIs."""
    
    def __init__(self):
        self.metrics_storage: Dict[str, List[BusinessMetric]] = defaultdict(list)
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        self.request_times: List[float] = []
        self.error_counts: Counter = Counter()
        self.feature_usage: Counter = Counter()
        self.api_endpoint_usage: Counter = Counter()
        
        # Performance tracking
        self.response_times_buffer = []
        self.request_count_buffer = []
        self.error_rate_buffer = []
        
        # Business event tracking
        self.daily_stats = {
            'transactions': 0,
            'new_users': 0,
            'active_sessions': set(),
            'budget_interactions': 0,
            'asana_syncs': 0,
            'asana_sync_errors': 0
        }
        
        logger.info("Business metrics collector initialized")

    def record_metric(self, name: str, metric_type: MetricType, value: float, 
                     labels: Optional[Dict[str, str]] = None, description: str = ""):
        """Record a business metric."""
        metric = BusinessMetric(
            name=name,
            type=metric_type,
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels or {},
            description=description
        )
        
        self.metrics_storage[name].append(metric)
        
        # Keep only recent metrics (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.metrics_storage[name] = [
            m for m in self.metrics_storage[name] 
            if m.timestamp > cutoff_time
        ]
        
        logger.debug("Business metric recorded", 
                    name=name, type=metric_type.value, value=value, labels=labels)

    def track_user_session(self, user_id: str, session_data: Dict[str, Any]):
        """Track user session for engagement metrics."""
        session_id = session_data.get('session_id', f"session_{int(time.time())}")
        
        self.user_sessions[session_id] = {
            'user_id': user_id,
            'start_time': datetime.utcnow(),
            'last_activity': datetime.utcnow(),
            'page_views': session_data.get('page_views', 0),
            'actions_performed': session_data.get('actions', []),
            'is_new_user': session_data.get('is_new_user', False)
        }
        
        # Track daily active users
        self.daily_stats['active_sessions'].add(user_id)
        
        if session_data.get('is_new_user'):
            self.daily_stats['new_users'] += 1
            self.record_metric('new_users_daily', MetricType.COUNTER, 1)

    def track_api_usage(self, endpoint: str, method: str, status_code: int, 
                       response_time: float, user_id: Optional[str] = None):
        """Track API endpoint usage for business insights."""
        endpoint_key = f"{method}:{endpoint}"
        self.api_endpoint_usage[endpoint_key] += 1
        
        # Track response times
        self.response_times_buffer.append(response_time)
        if len(self.response_times_buffer) > 1000:  # Keep last 1000 requests
            self.response_times_buffer.pop(0)
        
        # Track errors
        if status_code >= 400:
            self.error_counts[status_code] += 1
            self.record_metric('api_errors', MetricType.COUNTER, 1, 
                             {'status_code': str(status_code), 'endpoint': endpoint})
        
        # Record metrics
        self.record_metric('api_requests', MetricType.COUNTER, 1, 
                         {'endpoint': endpoint, 'method': method})
        self.record_metric('response_time', MetricType.HISTOGRAM, response_time,
                         {'endpoint': endpoint})

    def track_financial_event(self, event_type: str, amount: Optional[float] = None, 
                            user_id: Optional[str] = None, metadata: Optional[Dict] = None):
        """Track financial application specific events."""
        if event_type == 'transaction_created':
            self.daily_stats['transactions'] += 1
            if amount:
                self.record_metric('transaction_amount', MetricType.HISTOGRAM, amount)
            self.record_metric('transactions_daily', MetricType.COUNTER, 1)
            
        elif event_type == 'budget_interaction':
            self.daily_stats['budget_interactions'] += 1
            self.record_metric('budget_interactions', MetricType.COUNTER, 1)
            
        elif event_type == 'asana_sync':
            self.daily_stats['asana_syncs'] += 1
            self.record_metric('asana_syncs', MetricType.COUNTER, 1)
            
        elif event_type == 'asana_sync_error':
            self.daily_stats['asana_sync_errors'] += 1
            self.record_metric('asana_sync_errors', MetricType.COUNTER, 1)

    def track_feature_usage(self, feature_name: str, user_id: Optional[str] = None, 
                          context: Optional[Dict] = None):
        """Track feature usage for product insights."""
        self.feature_usage[feature_name] += 1
        self.record_metric('feature_usage', MetricType.COUNTER, 1, 
                         {'feature': feature_name}, f"Usage of {feature_name} feature")

    async def get_user_engagement_metrics(self) -> UserEngagementMetrics:
        """Calculate user engagement metrics."""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Active sessions in last 24 hours
        active_sessions = [
            s for s in self.user_sessions.values() 
            if s['last_activity'] > now - timedelta(hours=24)
        ]
        
        # New users today
        new_users_today = len([
            s for s in active_sessions 
            if s.get('is_new_user') and s['start_time'] > today_start
        ])
        
        # Calculate session durations
        session_durations = []
        page_views_total = 0
        
        for session in active_sessions:
            duration = (session['last_activity'] - session['start_time']).total_seconds()
            session_durations.append(duration)
            page_views_total += session.get('page_views', 0)
        
        avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0
        avg_page_views = page_views_total / len(active_sessions) if active_sessions else 0
        
        # Calculate bounce rate (sessions with only 1 page view)
        bounce_sessions = len([s for s in active_sessions if s.get('page_views', 0) <= 1])
        bounce_rate = (bounce_sessions / len(active_sessions)) * 100 if active_sessions else 0
        
        return UserEngagementMetrics(
            total_active_users=len(self.daily_stats['active_sessions']),
            new_users_today=new_users_today,
            returning_users=len(active_sessions) - new_users_today,
            avg_session_duration=avg_session_duration,
            page_views_per_session=avg_page_views,
            bounce_rate=bounce_rate,
            user_retention_rate=85.0  # Placeholder - would need historical data
        )

    async def get_financial_metrics(self) -> FinancialMetrics:
        """Calculate financial application metrics."""
        # Get transaction amounts from recorded metrics
        transaction_amounts = [
            m.value for m in self.metrics_storage.get('transaction_amount', [])
            if m.timestamp > datetime.utcnow() - timedelta(hours=24)
        ]
        
        avg_transaction_amount = sum(transaction_amounts) / len(transaction_amounts) if transaction_amounts else 0
        
        # Calculate Asana sync success rate
        total_syncs = self.daily_stats['asana_syncs']
        sync_errors = self.daily_stats['asana_sync_errors']
        asana_sync_success_rate = ((total_syncs - sync_errors) / total_syncs) * 100 if total_syncs > 0 else 0
        
        return FinancialMetrics(
            total_transactions=self.daily_stats['transactions'],
            transactions_today=self.daily_stats['transactions'],
            total_accounts=50,  # Would come from database query
            active_budgets=25,  # Would come from database query
            avg_transaction_amount=avg_transaction_amount,
            budget_compliance_rate=78.5,  # Would calculate from actual budget data
            asana_sync_success_rate=asana_sync_success_rate
        )

    async def get_system_performance_kpis(self) -> SystemPerformanceKPIs:
        """Calculate system performance KPIs."""
        # Calculate average response time
        avg_response_time = sum(self.response_times_buffer) / len(self.response_times_buffer) if self.response_times_buffer else 0
        
        # Calculate error rate
        total_requests = sum(self.api_endpoint_usage.values())
        total_errors = sum(self.error_counts.values())
        error_rate = (total_errors / total_requests) * 100 if total_requests > 0 else 0
        
        # Calculate throughput (requests per minute)
        # This is approximate based on recent activity
        recent_requests = len([
            m for m in self.metrics_storage.get('api_requests', [])
            if m.timestamp > datetime.utcnow() - timedelta(minutes=1)
        ])
        
        return SystemPerformanceKPIs(
            availability_percentage=99.8,  # Would calculate from uptime monitoring
            avg_response_time_ms=avg_response_time * 1000,
            error_rate_percentage=error_rate,
            throughput_requests_per_minute=recent_requests,
            cache_hit_rate=75.0,  # Would get from cache service
            database_query_time_ms=45.2  # Would get from database monitoring
        )

    async def get_business_kpis(self) -> BusinessKPIs:
        """Get complete business KPIs dashboard."""
        user_engagement = await self.get_user_engagement_metrics()
        financial = await self.get_financial_metrics()
        system_performance = await self.get_system_performance_kpis()
        
        # Custom metrics
        custom_metrics = {
            'top_features': dict(self.feature_usage.most_common(5)),
            'top_endpoints': dict(self.api_endpoint_usage.most_common(5)),
            'error_distribution': dict(self.error_counts),
            'metrics_collected': len(self.metrics_storage),
            'active_sessions': len(self.user_sessions)
        }
        
        return BusinessKPIs(
            timestamp=datetime.utcnow(),
            user_engagement=user_engagement,
            financial=financial,
            system_performance=system_performance,
            custom_metrics=custom_metrics
        )

    def get_metric_history(self, metric_name: str, hours: int = 24) -> List[BusinessMetric]:
        """Get historical data for a specific metric."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            m for m in self.metrics_storage.get(metric_name, [])
            if m.timestamp > cutoff_time
        ]

    def reset_daily_stats(self):
        """Reset daily statistics (should be called daily)."""
        self.daily_stats = {
            'transactions': 0,
            'new_users': 0,
            'active_sessions': set(),
            'budget_interactions': 0,
            'asana_syncs': 0,
            'asana_sync_errors': 0
        }
        logger.info("Daily statistics reset")


# Global instance
_business_metrics_collector = None


def get_business_metrics_collector() -> BusinessMetricsCollector:
    """Get global business metrics collector instance."""
    global _business_metrics_collector
    if _business_metrics_collector is None:
        _business_metrics_collector = BusinessMetricsCollector()
    return _business_metrics_collector


# Convenience functions for common tracking
def track_user_activity(user_id: str, action: str, context: Optional[Dict] = None):
    """Track user activity."""
    collector = get_business_metrics_collector()
    collector.track_feature_usage(action, user_id, context)


def track_financial_transaction(amount: float, user_id: str, transaction_type: str):
    """Track financial transaction."""
    collector = get_business_metrics_collector()
    collector.track_financial_event('transaction_created', amount, user_id, 
                                   {'type': transaction_type})


def track_budget_interaction(user_id: str, budget_id: str, action: str):
    """Track budget interaction."""
    collector = get_business_metrics_collector()
    collector.track_financial_event('budget_interaction', user_id=user_id, 
                                   metadata={'budget_id': budget_id, 'action': action})


def track_asana_sync(user_id: str, success: bool, tasks_synced: int = 0):
    """Track Asana sync operation."""
    collector = get_business_metrics_collector()
    if success:
        collector.track_financial_event('asana_sync', user_id=user_id, 
                                       metadata={'tasks_synced': tasks_synced})
    else:
        collector.track_financial_event('asana_sync_error', user_id=user_id)


async def get_business_dashboard_data() -> BusinessKPIs:
    """Get business dashboard data."""
    collector = get_business_metrics_collector()
    return await collector.get_business_kpis()