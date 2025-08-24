"""
Webhook Management endpoints.
Handles webhook registration, configuration, testing, and monitoring.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, status, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator, HttpUrl
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional
from src.services.webhook_service import (
    get_webhook_service,
    WebhookEvent,
    WebhookFormat,
    WebhookEndpoint
)

logger = structlog.get_logger()
router = APIRouter()


class CreateWebhookRequest(BaseModel):
    """Create webhook request."""
    name: str = Field(..., min_length=1, max_length=100, description="Webhook name")
    url: HttpUrl = Field(..., description="Webhook URL")
    events: List[str] = Field(..., min_items=1, description="List of events to subscribe to")
    format: str = Field(default="json", description="Payload format (json, form_data, xml)")
    timeout_seconds: int = Field(default=30, ge=5, le=120, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Custom HTTP headers")
    filter_conditions: Optional[Dict[str, Any]] = Field(None, description="Event filtering conditions")
    
    @validator('events')
    def validate_events(cls, v):
        valid_events = [event.value for event in WebhookEvent]
        for event in v:
            if event not in valid_events:
                raise ValueError(f'Invalid event: {event}. Valid events: {valid_events}')
        return v
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = [fmt.value for fmt in WebhookFormat]
        if v not in valid_formats:
            raise ValueError(f'Invalid format: {v}. Valid formats: {valid_formats}')
        return v


class UpdateWebhookRequest(BaseModel):
    """Update webhook request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Webhook name")
    url: Optional[HttpUrl] = Field(None, description="Webhook URL")
    events: Optional[List[str]] = Field(None, min_items=1, description="List of events to subscribe to")
    is_active: Optional[bool] = Field(None, description="Enable/disable webhook")
    timeout_seconds: Optional[int] = Field(None, ge=5, le=120, description="Request timeout in seconds")
    max_retries: Optional[int] = Field(None, ge=0, le=10, description="Maximum retry attempts")
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Custom HTTP headers")
    filter_conditions: Optional[Dict[str, Any]] = Field(None, description="Event filtering conditions")
    
    @validator('events')
    def validate_events(cls, v):
        if v is not None:
            valid_events = [event.value for event in WebhookEvent]
            for event in v:
                if event not in valid_events:
                    raise ValueError(f'Invalid event: {event}. Valid events: {valid_events}')
        return v


class WebhookResponse(BaseModel):
    """Webhook response model."""
    id: str = Field(..., description="Webhook ID")
    name: str = Field(..., description="Webhook name")
    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., description="Subscribed events")
    is_active: bool = Field(..., description="Whether webhook is active")
    format: str = Field(..., description="Payload format")
    timeout_seconds: int = Field(..., description="Request timeout")
    max_retries: int = Field(..., description="Maximum retries")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    last_used: Optional[str] = Field(None, description="Last delivery timestamp")
    total_deliveries: int = Field(..., description="Total delivery attempts")
    successful_deliveries: int = Field(..., description="Successful deliveries")
    failed_deliveries: int = Field(..., description="Failed deliveries")
    success_rate: float = Field(..., description="Success rate percentage")


class WebhookStatsResponse(BaseModel):
    """Webhook statistics response."""
    endpoint_id: str = Field(..., description="Webhook endpoint ID")
    total_deliveries: int = Field(..., description="Total delivery attempts")
    successful_deliveries: int = Field(..., description="Successful deliveries")
    failed_deliveries: int = Field(..., description="Failed deliveries")
    success_rate: float = Field(..., description="Success rate percentage")
    last_used: Optional[str] = Field(None, description="Last used timestamp")
    is_active: bool = Field(..., description="Whether webhook is active")


class WebhookTestResponse(BaseModel):
    """Webhook test response."""
    success: bool = Field(..., description="Whether test was successful")
    status_code: Optional[int] = Field(None, description="HTTP response status code")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class WebhookEventInfo(BaseModel):
    """Webhook event information."""
    event: str = Field(..., description="Event name")
    description: str = Field(..., description="Event description")
    example_payload: Dict[str, Any] = Field(..., description="Example payload structure")


@router.get(
    "/events",
    status_code=status.HTTP_200_OK,
    summary="List Available Webhook Events",
    description="Returns all available webhook events with descriptions and examples",
    response_model=List[WebhookEventInfo],
    tags=["Webhooks"]
)
async def list_webhook_events() -> List[WebhookEventInfo]:
    """
    **List available webhook events**
    
    Returns all webhook events that can be subscribed to:
    - Event types and descriptions
    - Example payload structures
    - Integration use cases
    
    Useful for understanding what events are available for webhooks.
    """
    events = [
        WebhookEventInfo(
            event=WebhookEvent.TRANSACTION_CREATED.value,
            description="Triggered when a new transaction is created",
            example_payload={
                "id": "txn_123",
                "amount": -25.50,
                "description": "Coffee Shop",
                "category": "Food & Dining",
                "date": "2024-01-15T10:30:00Z",
                "account_id": "acc_456"
            }
        ),
        WebhookEventInfo(
            event=WebhookEvent.BUDGET_EXCEEDED.value,
            description="Triggered when a budget limit is exceeded",
            example_payload={
                "budget_id": "bdg_789",
                "budget_name": "Monthly Dining",
                "limit": 500.00,
                "current_spending": 525.50,
                "percentage": 105.1,
                "period": "2024-01"
            }
        ),
        WebhookEventInfo(
            event=WebhookEvent.GOAL_ACHIEVED.value,
            description="Triggered when a financial goal is achieved",
            example_payload={
                "goal_id": "goal_101",
                "goal_name": "Emergency Fund",
                "target_amount": 10000.00,
                "achieved_amount": 10000.00,
                "achievement_date": "2024-01-15T15:45:00Z"
            }
        ),
        WebhookEventInfo(
            event=WebhookEvent.ANOMALY_DETECTED.value,
            description="Triggered when unusual spending is detected",
            example_payload={
                "transaction_id": "txn_unusual_123",
                "amount": -1500.00,
                "anomaly_score": 95,
                "description": "Large unusual expense",
                "category": "Shopping",
                "date": "2024-01-15T14:20:00Z"
            }
        ),
        WebhookEventInfo(
            event=WebhookEvent.MONTHLY_REPORT.value,
            description="Triggered when monthly financial report is generated",
            example_payload={
                "report_id": "rpt_monthly_202401",
                "period": "2024-01",
                "total_income": 5000.00,
                "total_expenses": 3500.00,
                "net_savings": 1500.00,
                "report_url": "https://api.financial-nomad.com/reports/rpt_monthly_202401"
            }
        )
    ]
    
    return events


@router.post(
    "/endpoints",
    status_code=status.HTTP_201_CREATED,
    summary="Create Webhook Endpoint",
    description="Creates a new webhook endpoint for receiving events",
    response_model=WebhookResponse,
    tags=["Webhooks"]
)
async def create_webhook_endpoint(
    request: CreateWebhookRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> WebhookResponse:
    """
    **Create webhook endpoint**
    
    Creates a new webhook endpoint to receive financial events:
    - Configure URL and event subscriptions
    - Set custom headers and filtering
    - Automatic retry logic and error handling
    - Secure HMAC signature verification
    
    Returns webhook configuration and secret for signature verification.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_webhook_service()
        
        # Convert event strings to enum
        events = [WebhookEvent(event) for event in request.events]
        
        # Create endpoint
        endpoint = await service.create_endpoint(
            user_id=current_user.get('id'),
            name=request.name,
            url=str(request.url),
            events=events,
            custom_headers=request.custom_headers,
            filter_conditions=request.filter_conditions
        )
        
        # Update optional fields
        endpoint.timeout_seconds = request.timeout_seconds
        endpoint.max_retries = request.max_retries
        endpoint.format = WebhookFormat(request.format)
        
        logger.info("Webhook endpoint created",
                   user_id=current_user.get('id'),
                   endpoint_id=endpoint.id,
                   name=request.name,
                   url=str(request.url))
        
        return WebhookResponse(
            id=endpoint.id,
            name=endpoint.name,
            url=endpoint.url,
            events=[e.value for e in endpoint.events],
            is_active=endpoint.is_active,
            format=endpoint.format.value,
            timeout_seconds=endpoint.timeout_seconds,
            max_retries=endpoint.max_retries,
            created_at=endpoint.created_at.isoformat() + "Z",
            updated_at=endpoint.updated_at.isoformat() + "Z",
            last_used=endpoint.last_used.isoformat() + "Z" if endpoint.last_used else None,
            total_deliveries=endpoint.total_deliveries,
            successful_deliveries=endpoint.successful_deliveries,
            failed_deliveries=endpoint.failed_deliveries,
            success_rate=(endpoint.successful_deliveries / max(endpoint.total_deliveries, 1)) * 100
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to create webhook endpoint",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create webhook endpoint"
        )


@router.get(
    "/endpoints",
    status_code=status.HTTP_200_OK,
    summary="List Webhook Endpoints",
    description="Returns all webhook endpoints for the authenticated user",
    response_model=List[WebhookResponse],
    tags=["Webhooks"]
)
async def list_webhook_endpoints(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[WebhookResponse]:
    """
    **List webhook endpoints**
    
    Returns all webhook endpoints configured by the user:
    - Endpoint configurations and status
    - Delivery statistics and success rates
    - Event subscriptions and filters
    - Last activity timestamps
    
    Useful for managing and monitoring webhook integrations.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_webhook_service()
        user_id = current_user.get('id')
        
        # Get user's endpoints
        endpoints = [
            endpoint for endpoint in service.registry.endpoints.values()
            if endpoint.user_id == user_id
        ]
        
        result = []
        for endpoint in endpoints:
            success_rate = (endpoint.successful_deliveries / max(endpoint.total_deliveries, 1)) * 100
            
            result.append(WebhookResponse(
                id=endpoint.id,
                name=endpoint.name,
                url=endpoint.url,
                events=[e.value for e in endpoint.events],
                is_active=endpoint.is_active,
                format=endpoint.format.value,
                timeout_seconds=endpoint.timeout_seconds,
                max_retries=endpoint.max_retries,
                created_at=endpoint.created_at.isoformat() + "Z",
                updated_at=endpoint.updated_at.isoformat() + "Z",
                last_used=endpoint.last_used.isoformat() + "Z" if endpoint.last_used else None,
                total_deliveries=endpoint.total_deliveries,
                successful_deliveries=endpoint.successful_deliveries,
                failed_deliveries=endpoint.failed_deliveries,
                success_rate=success_rate
            ))
        
        logger.info("Webhook endpoints listed",
                   user_id=user_id,
                   count=len(result))
        
        return result
        
    except Exception as e:
        logger.error("Failed to list webhook endpoints",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list webhook endpoints"
        )


@router.get(
    "/endpoints/{endpoint_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Webhook Endpoint",
    description="Returns details of a specific webhook endpoint",
    response_model=WebhookResponse,
    tags=["Webhooks"]
)
async def get_webhook_endpoint(
    endpoint_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> WebhookResponse:
    """
    **Get webhook endpoint details**
    
    Returns detailed information about a specific webhook endpoint:
    - Complete configuration settings
    - Delivery statistics and performance
    - Recent activity and status
    - Error rates and success metrics
    
    Useful for monitoring and debugging webhook integrations.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_webhook_service()
        endpoint = service.registry.get_endpoint(endpoint_id)
        
        if not endpoint or endpoint.user_id != current_user.get('id'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )
        
        success_rate = (endpoint.successful_deliveries / max(endpoint.total_deliveries, 1)) * 100
        
        return WebhookResponse(
            id=endpoint.id,
            name=endpoint.name,
            url=endpoint.url,
            events=[e.value for e in endpoint.events],
            is_active=endpoint.is_active,
            format=endpoint.format.value,
            timeout_seconds=endpoint.timeout_seconds,
            max_retries=endpoint.max_retries,
            created_at=endpoint.created_at.isoformat() + "Z",
            updated_at=endpoint.updated_at.isoformat() + "Z",
            last_used=endpoint.last_used.isoformat() + "Z" if endpoint.last_used else None,
            total_deliveries=endpoint.total_deliveries,
            successful_deliveries=endpoint.successful_deliveries,
            failed_deliveries=endpoint.failed_deliveries,
            success_rate=success_rate
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get webhook endpoint",
                    endpoint_id=endpoint_id,
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhook endpoint"
        )


@router.put(
    "/endpoints/{endpoint_id}",
    status_code=status.HTTP_200_OK,
    summary="Update Webhook Endpoint",
    description="Updates an existing webhook endpoint configuration",
    response_model=WebhookResponse,
    tags=["Webhooks"]
)
async def update_webhook_endpoint(
    endpoint_id: str,
    request: UpdateWebhookRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> WebhookResponse:
    """
    **Update webhook endpoint**
    
    Updates webhook endpoint configuration:
    - Modify URL and event subscriptions
    - Enable/disable endpoints
    - Update filters and custom headers
    - Adjust retry and timeout settings
    
    Changes take effect immediately for new events.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_webhook_service()
        endpoint = service.registry.get_endpoint(endpoint_id)
        
        if not endpoint or endpoint.user_id != current_user.get('id'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )
        
        # Prepare updates
        updates = {}
        if request.name is not None:
            updates['name'] = request.name
        if request.url is not None:
            updates['url'] = str(request.url)
        if request.events is not None:
            updates['events'] = [WebhookEvent(event) for event in request.events]
        if request.is_active is not None:
            updates['is_active'] = request.is_active
        if request.timeout_seconds is not None:
            updates['timeout_seconds'] = request.timeout_seconds
        if request.max_retries is not None:
            updates['max_retries'] = request.max_retries
        if request.custom_headers is not None:
            updates['custom_headers'] = request.custom_headers
        if request.filter_conditions is not None:
            updates['filter_conditions'] = request.filter_conditions
        
        # Update endpoint
        updated_endpoint = await service.update_endpoint(endpoint_id, **updates)
        if not updated_endpoint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )
        
        success_rate = (updated_endpoint.successful_deliveries / max(updated_endpoint.total_deliveries, 1)) * 100
        
        logger.info("Webhook endpoint updated",
                   endpoint_id=endpoint_id,
                   user_id=current_user.get('id'),
                   updates=list(updates.keys()))
        
        return WebhookResponse(
            id=updated_endpoint.id,
            name=updated_endpoint.name,
            url=updated_endpoint.url,
            events=[e.value for e in updated_endpoint.events],
            is_active=updated_endpoint.is_active,
            format=updated_endpoint.format.value,
            timeout_seconds=updated_endpoint.timeout_seconds,
            max_retries=updated_endpoint.max_retries,
            created_at=updated_endpoint.created_at.isoformat() + "Z",
            updated_at=updated_endpoint.updated_at.isoformat() + "Z",
            last_used=updated_endpoint.last_used.isoformat() + "Z" if updated_endpoint.last_used else None,
            total_deliveries=updated_endpoint.total_deliveries,
            successful_deliveries=updated_endpoint.successful_deliveries,
            failed_deliveries=updated_endpoint.failed_deliveries,
            success_rate=success_rate
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to update webhook endpoint",
                    endpoint_id=endpoint_id,
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update webhook endpoint"
        )


@router.delete(
    "/endpoints/{endpoint_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Webhook Endpoint",
    description="Deletes a webhook endpoint",
    tags=["Webhooks"]
)
async def delete_webhook_endpoint(
    endpoint_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Delete webhook endpoint**
    
    Permanently deletes a webhook endpoint:
    - Stops all future event deliveries
    - Removes endpoint configuration
    - Cancels pending retries
    
    This action cannot be undone.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_webhook_service()
        endpoint = service.registry.get_endpoint(endpoint_id)
        
        if not endpoint or endpoint.user_id != current_user.get('id'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )
        
        # Delete endpoint
        success = await service.delete_endpoint(endpoint_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )
        
        logger.info("Webhook endpoint deleted",
                   endpoint_id=endpoint_id,
                   user_id=current_user.get('id'))
        
        return {
            "message": "Webhook endpoint deleted successfully",
            "endpoint_id": endpoint_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete webhook endpoint",
                    endpoint_id=endpoint_id,
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete webhook endpoint"
        )


@router.post(
    "/endpoints/{endpoint_id}/test",
    status_code=status.HTTP_200_OK,
    summary="Test Webhook Endpoint",
    description="Sends a test webhook to verify endpoint configuration",
    response_model=WebhookTestResponse,
    tags=["Webhooks"]
)
async def test_webhook_endpoint(
    endpoint_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> WebhookTestResponse:
    """
    **Test webhook endpoint**
    
    Sends a test webhook to verify configuration:
    - Tests URL accessibility and response
    - Validates signature verification
    - Measures response time and status
    - Provides debugging information
    
    Useful for troubleshooting webhook setup issues.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_webhook_service()
        endpoint = service.registry.get_endpoint(endpoint_id)
        
        if not endpoint or endpoint.user_id != current_user.get('id'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )
        
        # Test endpoint
        result = await service.test_endpoint(endpoint_id)
        
        logger.info("Webhook endpoint tested",
                   endpoint_id=endpoint_id,
                   user_id=current_user.get('id'),
                   success=result['success'])
        
        return WebhookTestResponse(
            success=result['success'],
            status_code=result.get('status_code'),
            response_time_ms=result.get('response_time_ms'),
            error_message=result.get('error_message')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to test webhook endpoint",
                    endpoint_id=endpoint_id,
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test webhook endpoint"
        )


@router.get(
    "/endpoints/{endpoint_id}/stats",
    status_code=status.HTTP_200_OK,
    summary="Get Webhook Statistics",
    description="Returns delivery statistics for a webhook endpoint",
    response_model=WebhookStatsResponse,
    tags=["Webhooks"]
)
async def get_webhook_stats(
    endpoint_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> WebhookStatsResponse:
    """
    **Get webhook statistics**
    
    Returns detailed delivery statistics:
    - Success and failure rates
    - Total delivery attempts
    - Performance metrics
    - Activity timeline
    
    Useful for monitoring webhook health and performance.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_webhook_service()
        endpoint = service.registry.get_endpoint(endpoint_id)
        
        if not endpoint or endpoint.user_id != current_user.get('id'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )
        
        # Get statistics
        stats = service.get_endpoint_stats(endpoint_id)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook endpoint not found"
            )
        
        return WebhookStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get webhook stats",
                    endpoint_id=endpoint_id,
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhook statistics"
        )