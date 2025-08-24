"""
Webhook Service for External Integrations.
Handles webhook management, event publishing, delivery, and external API integrations
with retry logic, security, and comprehensive logging.
"""

import asyncio
import json
import hmac
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
import httpx
import structlog
from urllib.parse import urlparse

from src.config import settings

logger = structlog.get_logger()


class WebhookEvent(Enum):
    """Types of webhook events."""
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_UPDATED = "transaction.updated"
    TRANSACTION_DELETED = "transaction.deleted"
    ACCOUNT_CREATED = "account.created"
    ACCOUNT_UPDATED = "account.updated"
    BUDGET_EXCEEDED = "budget.exceeded"
    BUDGET_WARNING = "budget.warning"
    GOAL_ACHIEVED = "goal.achieved"
    GOAL_PROGRESS = "goal.progress"
    MONTHLY_REPORT = "report.monthly"
    PAYMENT_REMINDER = "payment.reminder"
    ANOMALY_DETECTED = "anomaly.detected"
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"
    SYNC_COMPLETED = "sync.completed"
    SYNC_FAILED = "sync.failed"


class WebhookStatus(Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY = "retry"
    DISABLED = "disabled"


class WebhookFormat(Enum):
    """Webhook payload formats."""
    JSON = "json"
    FORM_DATA = "form_data"
    XML = "xml"


@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration."""
    id: str
    user_id: str
    name: str
    url: str
    events: List[WebhookEvent]
    secret: str
    is_active: bool = True
    format: WebhookFormat = WebhookFormat.JSON
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_interval_seconds: int = 60
    custom_headers: Dict[str, str] = field(default_factory=dict)
    filter_conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0


@dataclass
class WebhookDelivery:
    """Webhook delivery record."""
    id: str
    endpoint_id: str
    event_type: WebhookEvent
    payload: Dict[str, Any]
    status: WebhookStatus = WebhookStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    next_retry: Optional[datetime] = None
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    delivered_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


@dataclass
class WebhookPayload:
    """Webhook payload structure."""
    event: str
    timestamp: str
    data: Dict[str, Any]
    user_id: str
    webhook_id: str
    signature: Optional[str] = None
    version: str = "1.0"


class WebhookSigner:
    """Handles webhook signature generation and verification."""
    
    @staticmethod
    def generate_signature(payload: str, secret: str, algorithm: str = "sha256") -> str:
        """Generate HMAC signature for webhook payload."""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            getattr(hashlib, algorithm)
        ).hexdigest()
        return f"{algorithm}={signature}"
    
    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature."""
        try:
            # Extract algorithm and signature
            if '=' not in signature:
                return False
            
            algorithm, provided_sig = signature.split('=', 1)
            expected_sig = WebhookSigner.generate_signature(payload, secret, algorithm)
            
            # Use constant-time comparison
            return hmac.compare_digest(expected_sig, signature)
            
        except Exception as e:
            logger.error("Signature verification failed", error=str(e))
            return False


class WebhookFilter:
    """Filters webhook events based on conditions."""
    
    def __init__(self):
        pass
    
    def should_deliver(self, endpoint: WebhookEndpoint, event_data: Dict[str, Any]) -> bool:
        """Check if webhook should be delivered based on filter conditions."""
        if not endpoint.filter_conditions:
            return True
        
        try:
            # Apply filters
            for field_path, expected_value in endpoint.filter_conditions.items():
                actual_value = self._get_nested_value(event_data, field_path)
                
                if actual_value != expected_value:
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Filter evaluation failed", 
                        endpoint_id=endpoint.id, 
                        error=str(e))
            return True  # Default to delivery on filter errors
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from data using dot notation."""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value


class WebhookDeliveryEngine:
    """Handles webhook delivery with retry logic."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.signer = WebhookSigner()
        self.filter = WebhookFilter()
    
    async def deliver_webhook(self, endpoint: WebhookEndpoint, 
                            delivery: WebhookDelivery) -> bool:
        """Deliver webhook to endpoint."""
        if not endpoint.is_active:
            logger.info("Webhook endpoint is disabled", endpoint_id=endpoint.id)
            delivery.status = WebhookStatus.DISABLED
            return False
        
        # Check filters
        if not self.filter.should_deliver(endpoint, delivery.payload):
            logger.info("Webhook filtered out", endpoint_id=endpoint.id)
            return True  # Not an error, just filtered
        
        # Prepare payload
        webhook_payload = WebhookPayload(
            event=delivery.event_type.value,
            timestamp=delivery.created_at.isoformat() + "Z",
            data=delivery.payload,
            user_id=endpoint.user_id,
            webhook_id=endpoint.id,
            version="1.0"
        )
        
        # Convert to appropriate format
        if endpoint.format == WebhookFormat.JSON:
            payload_str = json.dumps(webhook_payload.__dict__, default=str)
            content_type = "application/json"
        elif endpoint.format == WebhookFormat.FORM_DATA:
            payload_str = self._to_form_data(webhook_payload.__dict__)
            content_type = "application/x-www-form-urlencoded"
        else:  # XML
            payload_str = self._to_xml(webhook_payload.__dict__)
            content_type = "application/xml"
        
        # Generate signature
        signature = self.signer.generate_signature(payload_str, endpoint.secret)
        
        # Prepare headers
        headers = {
            "Content-Type": content_type,
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": delivery.event_type.value,
            "X-Webhook-ID": delivery.id,
            "X-Webhook-Timestamp": webhook_payload.timestamp,
            "User-Agent": f"FinancialNomad-Webhooks/1.0"
        }
        
        # Add custom headers
        headers.update(endpoint.custom_headers)
        
        # Attempt delivery
        start_time = datetime.utcnow()
        delivery.attempts += 1
        
        try:
            response = await self.client.post(
                endpoint.url,
                content=payload_str,
                headers=headers,
                timeout=endpoint.timeout_seconds
            )
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            delivery.duration_ms = duration_ms
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:1000]  # Limit response body
            
            # Check if delivery was successful
            if 200 <= response.status_code < 300:
                delivery.status = WebhookStatus.DELIVERED
                delivery.delivered_at = datetime.utcnow()
                
                # Update endpoint stats
                endpoint.successful_deliveries += 1
                endpoint.total_deliveries += 1
                endpoint.last_used = datetime.utcnow()
                
                logger.info("Webhook delivered successfully",
                           endpoint_id=endpoint.id,
                           delivery_id=delivery.id,
                           status_code=response.status_code,
                           duration_ms=duration_ms)
                
                return True
            else:
                # HTTP error response
                delivery.status = WebhookStatus.FAILED
                delivery.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                
                endpoint.failed_deliveries += 1
                endpoint.total_deliveries += 1
                
                logger.warning("Webhook delivery failed with HTTP error",
                              endpoint_id=endpoint.id,
                              delivery_id=delivery.id,
                              status_code=response.status_code,
                              error=delivery.error_message)
                
                return False
                
        except httpx.TimeoutException:
            delivery.status = WebhookStatus.FAILED
            delivery.error_message = f"Request timeout after {endpoint.timeout_seconds} seconds"
            
            endpoint.failed_deliveries += 1
            endpoint.total_deliveries += 1
            
            logger.warning("Webhook delivery timed out",
                          endpoint_id=endpoint.id,
                          delivery_id=delivery.id,
                          timeout=endpoint.timeout_seconds)
            
            return False
            
        except Exception as e:
            delivery.status = WebhookStatus.FAILED
            delivery.error_message = str(e)
            
            endpoint.failed_deliveries += 1
            endpoint.total_deliveries += 1
            
            logger.error("Webhook delivery failed",
                        endpoint_id=endpoint.id,
                        delivery_id=delivery.id,
                        error=str(e))
            
            return False
    
    def _to_form_data(self, data: Dict[str, Any]) -> str:
        """Convert data to form-encoded string."""
        from urllib.parse import urlencode
        flattened = self._flatten_dict(data)
        return urlencode(flattened)
    
    def _to_xml(self, data: Dict[str, Any]) -> str:
        """Convert data to XML string."""
        def dict_to_xml(d, root_name="webhook"):
            xml = f"<{root_name}>"
            for key, value in d.items():
                if isinstance(value, dict):
                    xml += dict_to_xml(value, key)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            xml += dict_to_xml(item, key)
                        else:
                            xml += f"<{key}>{item}</{key}>"
                else:
                    xml += f"<{key}>{value}</{key}>"
            xml += f"</{root_name}>"
            return xml
        
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{dict_to_xml(data)}'
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, str(v)))
        return dict(items)
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class WebhookRetryManager:
    """Manages webhook retry logic."""
    
    def __init__(self):
        self.retry_queue: List[WebhookDelivery] = []
    
    def schedule_retry(self, delivery: WebhookDelivery, endpoint: WebhookEndpoint):
        """Schedule webhook for retry."""
        if delivery.attempts >= delivery.max_attempts:
            delivery.status = WebhookStatus.FAILED
            logger.info("Webhook max retries exceeded",
                       delivery_id=delivery.id,
                       attempts=delivery.attempts)
            return
        
        # Calculate next retry time with exponential backoff
        backoff_factor = 2 ** (delivery.attempts - 1)
        retry_delay = endpoint.retry_interval_seconds * backoff_factor
        delivery.next_retry = datetime.utcnow() + timedelta(seconds=retry_delay)
        delivery.status = WebhookStatus.RETRY
        
        self.retry_queue.append(delivery)
        
        logger.info("Webhook scheduled for retry",
                   delivery_id=delivery.id,
                   attempt=delivery.attempts,
                   next_retry=delivery.next_retry,
                   delay_seconds=retry_delay)
    
    def get_ready_retries(self) -> List[WebhookDelivery]:
        """Get deliveries ready for retry."""
        now = datetime.utcnow()
        ready = []
        remaining = []
        
        for delivery in self.retry_queue:
            if delivery.next_retry and delivery.next_retry <= now:
                ready.append(delivery)
            else:
                remaining.append(delivery)
        
        self.retry_queue = remaining
        return ready


class WebhookRegistry:
    """Registry for webhook endpoints and event handlers."""
    
    def __init__(self):
        self.endpoints: Dict[str, WebhookEndpoint] = {}
        self.event_handlers: Dict[WebhookEvent, List[Callable]] = {}
        self.deliveries: Dict[str, WebhookDelivery] = {}
    
    def register_endpoint(self, endpoint: WebhookEndpoint):
        """Register webhook endpoint."""
        self.endpoints[endpoint.id] = endpoint
        logger.info("Webhook endpoint registered",
                   endpoint_id=endpoint.id,
                   url=endpoint.url,
                   events=[e.value for e in endpoint.events])
    
    def unregister_endpoint(self, endpoint_id: str):
        """Unregister webhook endpoint."""
        if endpoint_id in self.endpoints:
            del self.endpoints[endpoint_id]
            logger.info("Webhook endpoint unregistered", endpoint_id=endpoint_id)
    
    def get_endpoints_for_event(self, event: WebhookEvent, user_id: str) -> List[WebhookEndpoint]:
        """Get endpoints subscribed to specific event for user."""
        return [
            endpoint for endpoint in self.endpoints.values()
            if endpoint.user_id == user_id 
            and event in endpoint.events 
            and endpoint.is_active
        ]
    
    def get_endpoint(self, endpoint_id: str) -> Optional[WebhookEndpoint]:
        """Get endpoint by ID."""
        return self.endpoints.get(endpoint_id)
    
    def register_event_handler(self, event: WebhookEvent, handler: Callable):
        """Register event handler."""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
    
    def get_event_handlers(self, event: WebhookEvent) -> List[Callable]:
        """Get event handlers for event type."""
        return self.event_handlers.get(event, [])


class WebhookService:
    """Main webhook service orchestrator."""
    
    def __init__(self):
        self.registry = WebhookRegistry()
        self.delivery_engine = WebhookDeliveryEngine()
        self.retry_manager = WebhookRetryManager()
        self.is_processing = False
        
        logger.info("Webhook service initialized")
    
    async def create_endpoint(self, user_id: str, name: str, url: str, 
                            events: List[WebhookEvent], 
                            custom_headers: Dict[str, str] = None,
                            filter_conditions: Dict[str, Any] = None) -> WebhookEndpoint:
        """Create new webhook endpoint."""
        
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")
        
        if parsed_url.scheme not in ['http', 'https']:
            raise ValueError("URL must use HTTP or HTTPS protocol")
        
        # Generate endpoint
        endpoint = WebhookEndpoint(
            id=f"wh_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            name=name,
            url=url,
            events=events,
            secret=self._generate_secret(),
            custom_headers=custom_headers or {},
            filter_conditions=filter_conditions or {}
        )
        
        self.registry.register_endpoint(endpoint)
        
        logger.info("Webhook endpoint created",
                   user_id=user_id,
                   endpoint_id=endpoint.id,
                   url=url,
                   events=[e.value for e in events])
        
        return endpoint
    
    async def update_endpoint(self, endpoint_id: str, **updates) -> Optional[WebhookEndpoint]:
        """Update webhook endpoint."""
        endpoint = self.registry.get_endpoint(endpoint_id)
        if not endpoint:
            return None
        
        # Update allowed fields
        allowed_fields = ['name', 'url', 'events', 'is_active', 'custom_headers', 
                         'filter_conditions', 'timeout_seconds', 'max_retries']
        
        for field, value in updates.items():
            if field in allowed_fields and hasattr(endpoint, field):
                setattr(endpoint, field, value)
        
        endpoint.updated_at = datetime.utcnow()
        
        logger.info("Webhook endpoint updated",
                   endpoint_id=endpoint_id,
                   updates=list(updates.keys()))
        
        return endpoint
    
    async def delete_endpoint(self, endpoint_id: str) -> bool:
        """Delete webhook endpoint."""
        endpoint = self.registry.get_endpoint(endpoint_id)
        if not endpoint:
            return False
        
        self.registry.unregister_endpoint(endpoint_id)
        
        logger.info("Webhook endpoint deleted", endpoint_id=endpoint_id)
        return True
    
    async def publish_event(self, event: WebhookEvent, user_id: str, 
                          data: Dict[str, Any]) -> List[str]:
        """Publish event to all subscribed webhooks."""
        
        endpoints = self.registry.get_endpoints_for_event(event, user_id)
        delivery_ids = []
        
        for endpoint in endpoints:
            # Create delivery record
            delivery = WebhookDelivery(
                id=f"del_{uuid.uuid4().hex[:12]}",
                endpoint_id=endpoint.id,
                event_type=event,
                payload=data,
                max_attempts=endpoint.max_retries
            )
            
            self.registry.deliveries[delivery.id] = delivery
            delivery_ids.append(delivery.id)
            
            # Attempt immediate delivery
            success = await self.delivery_engine.deliver_webhook(endpoint, delivery)
            
            # Schedule retry if failed
            if not success and delivery.attempts < delivery.max_attempts:
                self.retry_manager.schedule_retry(delivery, endpoint)
        
        logger.info("Event published to webhooks",
                   event=event.value,
                   user_id=user_id,
                   endpoints_count=len(endpoints),
                   deliveries=len(delivery_ids))
        
        return delivery_ids
    
    async def process_retries(self):
        """Process webhook retries."""
        if self.is_processing:
            return
        
        self.is_processing = True
        
        try:
            ready_retries = self.retry_manager.get_ready_retries()
            
            for delivery in ready_retries:
                endpoint = self.registry.get_endpoint(delivery.endpoint_id)
                if not endpoint:
                    continue
                
                success = await self.delivery_engine.deliver_webhook(endpoint, delivery)
                
                # Schedule another retry if failed
                if not success and delivery.attempts < delivery.max_attempts:
                    self.retry_manager.schedule_retry(delivery, endpoint)
            
            if ready_retries:
                logger.info("Processed webhook retries", count=len(ready_retries))
                
        except Exception as e:
            logger.error("Error processing webhook retries", error=str(e))
        finally:
            self.is_processing = False
    
    def get_endpoint_stats(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get endpoint delivery statistics."""
        endpoint = self.registry.get_endpoint(endpoint_id)
        if not endpoint:
            return None
        
        success_rate = (endpoint.successful_deliveries / max(endpoint.total_deliveries, 1)) * 100
        
        return {
            "endpoint_id": endpoint_id,
            "total_deliveries": endpoint.total_deliveries,
            "successful_deliveries": endpoint.successful_deliveries,
            "failed_deliveries": endpoint.failed_deliveries,
            "success_rate": success_rate,
            "last_used": endpoint.last_used.isoformat() if endpoint.last_used else None,
            "is_active": endpoint.is_active
        }
    
    def _generate_secret(self) -> str:
        """Generate webhook secret."""
        return f"whs_{uuid.uuid4().hex}"
    
    async def test_endpoint(self, endpoint_id: str) -> Dict[str, Any]:
        """Test webhook endpoint with a ping event."""
        endpoint = self.registry.get_endpoint(endpoint_id)
        if not endpoint:
            raise ValueError("Endpoint not found")
        
        # Create test delivery
        test_data = {
            "message": "This is a test webhook from Financial Nomad",
            "timestamp": datetime.utcnow().isoformat(),
            "test": True
        }
        
        delivery = WebhookDelivery(
            id=f"test_{uuid.uuid4().hex[:12]}",
            endpoint_id=endpoint.id,
            event_type=WebhookEvent.USER_UPDATED,  # Use generic event for testing
            payload=test_data,
            max_attempts=1
        )
        
        # Attempt delivery
        success = await self.delivery_engine.deliver_webhook(endpoint, delivery)
        
        return {
            "success": success,
            "status_code": delivery.response_status,
            "response_time_ms": delivery.duration_ms,
            "error_message": delivery.error_message
        }
    
    async def shutdown(self):
        """Shutdown webhook service."""
        await self.delivery_engine.close()
        logger.info("Webhook service shut down")


# Global webhook service
_webhook_service = None


def get_webhook_service() -> WebhookService:
    """Get global webhook service."""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service


# Event publishing helpers
async def publish_transaction_created(user_id: str, transaction: Dict[str, Any]):
    """Publish transaction created event."""
    service = get_webhook_service()
    await service.publish_event(WebhookEvent.TRANSACTION_CREATED, user_id, transaction)


async def publish_budget_exceeded(user_id: str, budget: Dict[str, Any]):
    """Publish budget exceeded event."""
    service = get_webhook_service()
    await service.publish_event(WebhookEvent.BUDGET_EXCEEDED, user_id, budget)


async def publish_goal_achieved(user_id: str, goal: Dict[str, Any]):
    """Publish goal achieved event."""
    service = get_webhook_service()
    await service.publish_event(WebhookEvent.GOAL_ACHIEVED, user_id, goal)


async def publish_anomaly_detected(user_id: str, anomaly: Dict[str, Any]):
    """Publish spending anomaly detected event."""
    service = get_webhook_service()
    await service.publish_event(WebhookEvent.ANOMALY_DETECTED, user_id, anomaly)