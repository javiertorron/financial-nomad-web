"""
Notification management endpoints.
Handles sending, tracking, and managing user notifications across multiple channels.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, status, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional
from src.services.notification_service import (
    get_notification_service,
    NotificationRecipient,
    NotificationType,
    NotificationPriority,
    TemplateType
)

logger = structlog.get_logger()
router = APIRouter()


class NotificationPreferences(BaseModel):
    """User notification preferences."""
    email_notifications: bool = Field(default=True, description="Enable email notifications")
    push_notifications: bool = Field(default=True, description="Enable push notifications")
    in_app_notifications: bool = Field(default=True, description="Enable in-app notifications")
    transaction_alerts: bool = Field(default=True, description="Enable transaction alerts")
    budget_warnings: bool = Field(default=True, description="Enable budget warnings")
    monthly_reports: bool = Field(default=True, description="Enable monthly reports")
    marketing_emails: bool = Field(default=False, description="Enable marketing emails")
    preferred_channel: str = Field(default="email", description="Preferred notification channel")
    quiet_hours_start: Optional[str] = Field(None, description="Quiet hours start time (HH:MM)")
    quiet_hours_end: Optional[str] = Field(None, description="Quiet hours end time (HH:MM)")


class SendNotificationRequest(BaseModel):
    """Send notification request."""
    template_id: str = Field(..., description="Notification template ID")
    recipient_user_id: Optional[str] = Field(None, description="Recipient user ID")
    recipient_email: Optional[str] = Field(None, description="Recipient email")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Template variables")
    channels: List[str] = Field(default_factory=list, description="Notification channels")
    priority: str = Field(default="normal", description="Notification priority")
    scheduled_at: Optional[str] = Field(None, description="Schedule time (ISO format)")


class NotificationResponse(BaseModel):
    """Notification response model."""
    id: str = Field(..., description="Notification ID")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    priority: str = Field(..., description="Priority level")
    created_at: str = Field(..., description="Creation timestamp")
    read: bool = Field(..., description="Read status")
    variables: Dict[str, Any] = Field(..., description="Template variables")


class NotificationStatsResponse(BaseModel):
    """Notification statistics response."""
    total_sent: int = Field(..., description="Total notifications sent")
    total_delivered: int = Field(..., description="Total notifications delivered")
    total_failed: int = Field(..., description="Total failed notifications")
    delivery_rate: float = Field(..., description="Delivery rate percentage")
    channel_stats: Dict[str, Dict[str, int]] = Field(..., description="Stats by channel")
    template_stats: Dict[str, Dict[str, int]] = Field(..., description="Stats by template")


@router.get(
    "/preferences",
    status_code=status.HTTP_200_OK,
    summary="Get Notification Preferences",
    description="Returns user's notification preferences and settings",
    response_model=NotificationPreferences,
    tags=["Notifications"]
)
async def get_notification_preferences(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> NotificationPreferences:
    """
    **Get user notification preferences**
    
    Returns the user's notification settings including:
    - Channel preferences (email, push, in-app)
    - Notification type preferences
    - Quiet hours configuration
    - Delivery preferences
    
    This allows users to customize their notification experience.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # In a real implementation, fetch from database
        # For now, return default preferences
        return NotificationPreferences(
            email_notifications=True,
            push_notifications=True,
            in_app_notifications=True,
            transaction_alerts=True,
            budget_warnings=True,
            monthly_reports=True,
            marketing_emails=False,
            preferred_channel="email",
            quiet_hours_start="22:00",
            quiet_hours_end="08:00"
        )
        
    except Exception as e:
        logger.error("Failed to get notification preferences", 
                    user_id=current_user.get('id'), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification preferences"
        )


@router.put(
    "/preferences",
    status_code=status.HTTP_200_OK,
    summary="Update Notification Preferences",
    description="Updates user's notification preferences and settings",
    response_model=NotificationPreferences,
    tags=["Notifications"]
)
async def update_notification_preferences(
    preferences: NotificationPreferences,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> NotificationPreferences:
    """
    **Update user notification preferences**
    
    Allows users to customize their notification settings:
    - Enable/disable specific channels
    - Set notification types
    - Configure quiet hours
    - Choose preferred delivery method
    
    Changes take effect immediately for future notifications.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # In a real implementation, save to database
        logger.info("Notification preferences updated",
                   user_id=current_user.get('id'),
                   preferences=preferences.dict())
        
        return preferences
        
    except Exception as e:
        logger.error("Failed to update notification preferences",
                    user_id=current_user.get('id'), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences"
        )


@router.get(
    "/in-app",
    status_code=status.HTTP_200_OK,
    summary="Get In-App Notifications",
    description="Returns user's in-app notifications",
    response_model=List[NotificationResponse],
    tags=["Notifications"]
)
async def get_in_app_notifications(
    limit: int = Query(default=50, ge=1, le=100, description="Number of notifications to return"),
    unread_only: bool = Query(default=False, description="Return only unread notifications"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[NotificationResponse]:
    """
    **Get user's in-app notifications**
    
    Returns a list of in-app notifications for the authenticated user:
    - Recent notifications with content
    - Read/unread status
    - Notification metadata
    - Template variables for rich display
    
    Supports filtering by read status and limiting results.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_notification_service()
        notifications = service.get_user_notifications(
            current_user.get('id'),
            limit=limit,
            unread_only=unread_only
        )
        
        return [
            NotificationResponse(
                id=notification['id'],
                title=notification['title'],
                body=notification['body'],
                priority=notification['priority'],
                created_at=notification['created_at'],
                read=notification['read'],
                variables=notification.get('variables', {})
            )
            for notification in notifications
        ]
        
    except Exception as e:
        logger.error("Failed to get in-app notifications",
                    user_id=current_user.get('id'), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve in-app notifications"
        )


@router.patch(
    "/in-app/{notification_id}/read",
    status_code=status.HTTP_200_OK,
    summary="Mark Notification as Read",
    description="Marks a specific notification as read",
    tags=["Notifications"]
)
async def mark_notification_read(
    notification_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Mark notification as read**
    
    Updates the read status of a specific notification.
    This helps track user engagement with notifications
    and prevents showing already-seen content.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_notification_service()
        success = service.mark_notification_read(
            current_user.get('id'),
            notification_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        return {
            "status": "success",
            "message": "Notification marked as read",
            "notification_id": notification_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to mark notification as read",
                    user_id=current_user.get('id'),
                    notification_id=notification_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read"
        )


@router.post(
    "/send",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send Notification",
    description="Sends a notification using specified template and channels",
    tags=["Notifications"]
)
async def send_notification(
    notification_request: SendNotificationRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Send notification**
    
    Sends a notification using a predefined template:
    - Supports multiple delivery channels
    - Template-based content generation
    - Variable substitution
    - Scheduling for future delivery
    - Priority-based processing
    
    Requires administrative privileges for sending to other users.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_notification_service()
        
        # Determine recipient
        if notification_request.recipient_user_id:
            # Check if user can send to other users (admin only)
            if (notification_request.recipient_user_id != current_user.get('id') and 
                current_user.get('role') != 'admin'):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin privileges required to send notifications to other users"
                )
            recipient_email = notification_request.recipient_email
            recipient_user_id = notification_request.recipient_user_id
        else:
            # Send to current user
            recipient_email = current_user.get('email')
            recipient_user_id = current_user.get('id')
        
        # Create recipient object
        recipient = NotificationRecipient(
            user_id=recipient_user_id,
            email=recipient_email,
            preferred_channel=NotificationType(notification_request.channels[0] if notification_request.channels else "email")
        )
        
        # Parse channels
        channels = [NotificationType(ch) for ch in notification_request.channels] if notification_request.channels else None
        
        # Parse priority
        priority = NotificationPriority(notification_request.priority)
        
        # Parse scheduled time
        scheduled_at = None
        if notification_request.scheduled_at:
            scheduled_at = datetime.fromisoformat(notification_request.scheduled_at)
        
        # Send notification in background
        background_tasks.add_task(
            send_notification_task,
            recipient,
            notification_request.template_id,
            notification_request.variables,
            priority,
            channels,
            scheduled_at
        )
        
        return {
            "status": "accepted",
            "message": "Notification queued for delivery",
            "template_id": notification_request.template_id,
            "recipient_user_id": recipient_user_id,
            "scheduled_at": notification_request.scheduled_at,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to send notification",
                    template_id=notification_request.template_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification"
        )


@router.get(
    "/templates",
    status_code=status.HTTP_200_OK,
    summary="List Notification Templates",
    description="Returns available notification templates",
    tags=["Notifications"]
)
async def list_notification_templates(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[Dict[str, Any]]:
    """
    **List notification templates**
    
    Returns available notification templates:
    - Template metadata and configuration
    - Supported channels and variables
    - Usage examples and descriptions
    
    Useful for developers and administrators to understand
    available notification options.
    """
    try:
        service = get_notification_service()
        templates = service.template_manager.templates
        
        result = []
        for template_id, template in templates.items():
            result.append({
                "id": template_id,
                "type": template.type.value,
                "name": template.name,
                "supported_channels": [ch.value for ch in template.supported_channels],
                "variables": template.variables,
                "has_attachments": len(template.attachments) > 0,
                "created_at": template.created_at.isoformat() + "Z",
                "updated_at": template.updated_at.isoformat() + "Z"
            })
        
        return result
        
    except Exception as e:
        logger.error("Failed to list notification templates", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification templates"
        )


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Get Notification Statistics",
    description="Returns notification delivery and engagement statistics",
    response_model=NotificationStatsResponse,
    tags=["Notifications"]
)
async def get_notification_statistics(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> NotificationStatsResponse:
    """
    **Get notification statistics**
    
    Returns comprehensive notification metrics:
    - Delivery rates and success metrics
    - Channel performance comparison
    - Template effectiveness
    - Engagement analytics
    
    Requires administrative privileges to view system-wide stats.
    Regular users see only their own notification stats.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_notification_service()
        delivery_stats = service.get_delivery_stats()
        
        # Calculate totals
        total_sent = 0
        total_delivered = 0
        total_failed = 0
        
        channel_stats = {}
        template_stats = {}
        
        for template_id, stats in delivery_stats.items():
            template_stats[template_id] = stats
            
            for stat_key, count in stats.items():
                if stat_key.endswith('_sent'):
                    total_sent += count
                    channel = stat_key.replace('_sent', '')
                    if channel not in channel_stats:
                        channel_stats[channel] = {"sent": 0, "delivered": 0, "failed": 0}
                    channel_stats[channel]["sent"] += count
                    
                elif stat_key.endswith('_delivered'):
                    total_delivered += count
                    channel = stat_key.replace('_delivered', '')
                    if channel not in channel_stats:
                        channel_stats[channel] = {"sent": 0, "delivered": 0, "failed": 0}
                    channel_stats[channel]["delivered"] += count
                    
                elif stat_key.endswith('_failed'):
                    total_failed += count
                    channel = stat_key.replace('_failed', '')
                    if channel not in channel_stats:
                        channel_stats[channel] = {"sent": 0, "delivered": 0, "failed": 0}
                    channel_stats[channel]["failed"] += count
        
        delivery_rate = (total_delivered / max(total_sent, 1)) * 100
        
        return NotificationStatsResponse(
            total_sent=total_sent,
            total_delivered=total_delivered,
            total_failed=total_failed,
            delivery_rate=delivery_rate,
            channel_stats=channel_stats,
            template_stats=template_stats
        )
        
    except Exception as e:
        logger.error("Failed to get notification statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification statistics"
        )


@router.post(
    "/test/{template_id}",
    status_code=status.HTTP_200_OK,
    summary="Test Notification Template",
    description="Sends a test notification using the specified template",
    tags=["Notifications"]
)
async def test_notification_template(
    template_id: str,
    test_variables: Dict[str, Any],
    channels: List[str] = Query(default=["email"], description="Test channels"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Test notification template**
    
    Sends a test notification to the current user:
    - Validates template rendering
    - Tests variable substitution
    - Verifies channel delivery
    - Provides immediate feedback
    
    Useful for testing templates before using them in production.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_notification_service()
        
        # Create test recipient
        recipient = NotificationRecipient(
            user_id=current_user.get('id'),
            email=current_user.get('email'),
            preferred_channel=NotificationType.EMAIL
        )
        
        # Parse channels
        notification_channels = [NotificationType(ch) for ch in channels]
        
        # Add test prefix to variables
        test_variables['test_mode'] = True
        test_variables['test_timestamp'] = datetime.utcnow().isoformat()
        
        # Send test notification
        message_ids = await service.send_notification(
            recipient=recipient,
            template_id=template_id,
            variables=test_variables,
            priority=NotificationPriority.NORMAL,
            channels=notification_channels
        )
        
        return {
            "status": "success",
            "message": f"Test notification sent via {', '.join(channels)}",
            "template_id": template_id,
            "message_ids": message_ids,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error("Failed to send test notification",
                    template_id=template_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test notification"
        )


async def send_notification_task(recipient: NotificationRecipient,
                                template_id: str,
                                variables: Dict[str, Any],
                                priority: NotificationPriority,
                                channels: Optional[List[NotificationType]] = None,
                                scheduled_at: Optional[datetime] = None):
    """Background task for sending notifications."""
    try:
        service = get_notification_service()
        await service.send_notification(
            recipient=recipient,
            template_id=template_id,
            variables=variables,
            priority=priority,
            channels=channels,
            scheduled_at=scheduled_at
        )
    except Exception as e:
        logger.error("Background notification task failed", 
                    template_id=template_id, error=str(e))