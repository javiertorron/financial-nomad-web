"""
Enterprise Notification Service.
Handles push notifications, emails, SMS, and in-app notifications with templates,
scheduling, personalization, and delivery tracking.
"""

import asyncio
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import jinja2
import structlog

from src.config import settings

logger = structlog.get_logger()


class NotificationType(Enum):
    """Types of notifications."""
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class NotificationPriority(Enum):
    """Notification priorities."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"


class TemplateType(Enum):
    """Template types."""
    WELCOME = "welcome"
    TRANSACTION_ALERT = "transaction_alert"
    BUDGET_WARNING = "budget_warning"
    MONTHLY_REPORT = "monthly_report"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"
    PAYMENT_REMINDER = "payment_reminder"
    GOAL_ACHIEVED = "goal_achieved"
    ASANA_SYNC_ERROR = "asana_sync_error"
    SYSTEM_MAINTENANCE = "system_maintenance"


@dataclass
class NotificationTemplate:
    """Notification template configuration."""
    id: str
    type: TemplateType
    name: str
    subject_template: str
    body_template: str
    supported_channels: List[NotificationType]
    variables: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NotificationRecipient:
    """Notification recipient information."""
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    push_token: Optional[str] = None
    preferred_channel: NotificationType = NotificationType.EMAIL
    timezone: str = "UTC"
    language: str = "en"
    unsubscribed_channels: List[NotificationType] = field(default_factory=list)


@dataclass
class NotificationMessage:
    """Notification message structure."""
    id: str
    recipient: NotificationRecipient
    template_id: str
    channel: NotificationType
    priority: NotificationPriority
    subject: str
    body: str
    variables: Dict[str, Any] = field(default_factory=dict)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None


class NotificationTemplateManager:
    """Manages notification templates."""
    
    def __init__(self):
        self.templates: Dict[str, NotificationTemplate] = {}
        self.jinja_env = jinja2.Environment(
            loader=jinja2.DictLoader({}),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default notification templates."""
        templates = [
            NotificationTemplate(
                id="welcome_email",
                type=TemplateType.WELCOME,
                name="Welcome Email",
                subject_template="Welcome to Financial Nomad, {{user_name}}!",
                body_template="""
                <html>
                <body>
                    <h2>Welcome to Financial Nomad!</h2>
                    <p>Hi {{user_name}},</p>
                    <p>Thank you for joining Financial Nomad. We're excited to help you manage your finances more effectively.</p>
                    <p>Here's what you can do next:</p>
                    <ul>
                        <li>Connect your bank accounts</li>
                        <li>Set up your first budget</li>
                        <li>Explore our Asana integration</li>
                    </ul>
                    <p>If you have any questions, feel free to reach out to our support team.</p>
                    <p>Best regards,<br>The Financial Nomad Team</p>
                </body>
                </html>
                """,
                supported_channels=[NotificationType.EMAIL, NotificationType.IN_APP],
                variables=["user_name", "login_url"]
            ),
            NotificationTemplate(
                id="transaction_alert",
                type=TemplateType.TRANSACTION_ALERT,
                name="Transaction Alert",
                subject_template="New {{transaction_type}}: {{amount}} - {{description}}",
                body_template="""
                <html>
                <body>
                    <h3>Transaction Alert</h3>
                    <p>A new {{transaction_type}} has been recorded:</p>
                    <ul>
                        <li><strong>Amount:</strong> {{amount}}</li>
                        <li><strong>Description:</strong> {{description}}</li>
                        <li><strong>Category:</strong> {{category}}</li>
                        <li><strong>Date:</strong> {{transaction_date}}</li>
                        <li><strong>Account:</strong> {{account_name}}</li>
                    </ul>
                    <p>View your transactions in the app for more details.</p>
                </body>
                </html>
                """,
                supported_channels=[NotificationType.EMAIL, NotificationType.PUSH, NotificationType.IN_APP],
                variables=["transaction_type", "amount", "description", "category", "transaction_date", "account_name"]
            ),
            NotificationTemplate(
                id="budget_warning",
                type=TemplateType.BUDGET_WARNING,
                name="Budget Warning",
                subject_template="Budget Alert: {{budget_name}} - {{percentage}}% Used",
                body_template="""
                <html>
                <body>
                    <h3>Budget Warning</h3>
                    <p>Your budget "{{budget_name}}" is {{percentage}}% used.</p>
                    <ul>
                        <li><strong>Budget:</strong> {{budget_amount}}</li>
                        <li><strong>Spent:</strong> {{spent_amount}}</li>
                        <li><strong>Remaining:</strong> {{remaining_amount}}</li>
                        <li><strong>Days left:</strong> {{days_remaining}}</li>
                    </ul>
                    <p>Consider reviewing your spending to stay within budget.</p>
                </body>
                </html>
                """,
                supported_channels=[NotificationType.EMAIL, NotificationType.PUSH, NotificationType.IN_APP],
                variables=["budget_name", "percentage", "budget_amount", "spent_amount", "remaining_amount", "days_remaining"]
            ),
            NotificationTemplate(
                id="monthly_report",
                type=TemplateType.MONTHLY_REPORT,
                name="Monthly Financial Report",
                subject_template="Your {{month}} {{year}} Financial Report",
                body_template="""
                <html>
                <body>
                    <h2>Monthly Financial Report - {{month}} {{year}}</h2>
                    <p>Hi {{user_name}},</p>
                    <p>Here's your financial summary for {{month}} {{year}}:</p>
                    
                    <h3>Income & Expenses</h3>
                    <ul>
                        <li><strong>Total Income:</strong> {{total_income}}</li>
                        <li><strong>Total Expenses:</strong> {{total_expenses}}</li>
                        <li><strong>Net:</strong> {{net_amount}}</li>
                    </ul>
                    
                    <h3>Top Categories</h3>
                    <ul>
                    {% for category in top_categories %}
                        <li>{{category.name}}: {{category.amount}}</li>
                    {% endfor %}
                    </ul>
                    
                    <h3>Budget Performance</h3>
                    <ul>
                    {% for budget in budgets %}
                        <li>{{budget.name}}: {{budget.used_percentage}}% used</li>
                    {% endfor %}
                    </ul>
                    
                    <p>View detailed reports in your dashboard.</p>
                </body>
                </html>
                """,
                supported_channels=[NotificationType.EMAIL],
                variables=["user_name", "month", "year", "total_income", "total_expenses", "net_amount", "top_categories", "budgets"],
                attachments=["monthly_report.pdf"]
            ),
            NotificationTemplate(
                id="system_maintenance",
                type=TemplateType.SYSTEM_MAINTENANCE,
                name="System Maintenance Notice",
                subject_template="Scheduled Maintenance: {{maintenance_date}}",
                body_template="""
                <html>
                <body>
                    <h3>Scheduled System Maintenance</h3>
                    <p>We will be performing scheduled maintenance on our systems:</p>
                    <ul>
                        <li><strong>Date:</strong> {{maintenance_date}}</li>
                        <li><strong>Start Time:</strong> {{start_time}}</li>
                        <li><strong>Duration:</strong> {{duration}}</li>
                        <li><strong>Expected End:</strong> {{end_time}}</li>
                    </ul>
                    <p>During this time, you may experience:</p>
                    <ul>
                        <li>Brief service interruptions</li>
                        <li>Slower response times</li>
                        <li>Limited functionality in some features</li>
                    </ul>
                    <p>We apologize for any inconvenience and appreciate your understanding.</p>
                </body>
                </html>
                """,
                supported_channels=[NotificationType.EMAIL, NotificationType.IN_APP],
                variables=["maintenance_date", "start_time", "duration", "end_time"]
            )
        ]
        
        for template in templates:
            self.templates[template.id] = template
            # Add template to Jinja environment
            self.jinja_env.loader.mapping[template.id + "_subject"] = template.subject_template
            self.jinja_env.loader.mapping[template.id + "_body"] = template.body_template
    
    def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get template by ID."""
        return self.templates.get(template_id)
    
    def render_template(self, template_id: str, variables: Dict[str, Any]) -> Tuple[str, str]:
        """Render template with variables."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        try:
            subject_template = self.jinja_env.get_template(template_id + "_subject")
            body_template = self.jinja_env.get_template(template_id + "_body")
            
            subject = subject_template.render(**variables)
            body = body_template.render(**variables)
            
            return subject, body
            
        except Exception as e:
            logger.error("Template rendering failed", template_id=template_id, error=str(e))
            raise


class EmailService:
    """Email notification service."""
    
    def __init__(self):
        self.smtp_server = settings.smtp_server or "smtp.gmail.com"
        self.smtp_port = settings.smtp_port or 587
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.from_email = settings.from_email or "noreply@financial-nomad.com"
        self.from_name = settings.from_name or "Financial Nomad"
    
    async def send_email(self, message: NotificationMessage) -> bool:
        """Send email notification."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = message.subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = message.recipient.email
            
            # Add body
            if message.body:
                body_part = MIMEText(message.body, 'html')
                msg.attach(body_part)
            
            # Add attachments
            for attachment in message.attachments:
                await self._add_attachment(msg, attachment)
            
            # Send via SMTP
            await self._send_smtp(msg)
            
            logger.info("Email sent successfully", 
                       recipient=message.recipient.email,
                       template_id=message.template_id)
            return True
            
        except Exception as e:
            logger.error("Email sending failed", 
                        recipient=message.recipient.email,
                        error=str(e))
            return False
    
    async def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email."""
        try:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['data'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment["filename"]}'
            )
            msg.attach(part)
        except Exception as e:
            logger.error("Failed to add attachment", filename=attachment.get('filename'), error=str(e))
    
    async def _send_smtp(self, msg: MIMEMultipart):
        """Send email via SMTP."""
        # In production, use async SMTP library like aiosmtplib
        # For now, using sync version wrapped in thread
        import threading
        
        def send_sync():
            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    if self.smtp_username and self.smtp_password:
                        server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            except Exception as e:
                logger.error("SMTP sending failed", error=str(e))
                raise
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, send_sync)


class PushNotificationService:
    """Push notification service."""
    
    def __init__(self):
        self.fcm_server_key = getattr(settings, 'fcm_server_key', None)
        self.apns_key_file = getattr(settings, 'apns_key_file', None)
        self.apns_key_id = getattr(settings, 'apns_key_id', None)
        self.apns_team_id = getattr(settings, 'apns_team_id', None)
    
    async def send_push_notification(self, message: NotificationMessage) -> bool:
        """Send push notification."""
        try:
            if not message.recipient.push_token:
                logger.warning("No push token for recipient", user_id=message.recipient.user_id)
                return False
            
            # Determine platform (simplified)
            if message.recipient.push_token.startswith('ExponentPushToken'):
                # Expo push notification
                return await self._send_expo_push(message)
            elif len(message.recipient.push_token) > 100:
                # FCM token (Android)
                return await self._send_fcm_push(message)
            else:
                # APNS token (iOS)
                return await self._send_apns_push(message)
                
        except Exception as e:
            logger.error("Push notification failed", 
                        user_id=message.recipient.user_id,
                        error=str(e))
            return False
    
    async def _send_fcm_push(self, message: NotificationMessage) -> bool:
        """Send FCM push notification."""
        # Implementation would use aiofcm or similar library
        logger.info("FCM push notification sent", user_id=message.recipient.user_id)
        return True
    
    async def _send_apns_push(self, message: NotificationMessage) -> bool:
        """Send APNS push notification."""
        # Implementation would use aioapns or similar library
        logger.info("APNS push notification sent", user_id=message.recipient.user_id)
        return True
    
    async def _send_expo_push(self, message: NotificationMessage) -> bool:
        """Send Expo push notification."""
        # Implementation would use Expo Push API
        logger.info("Expo push notification sent", user_id=message.recipient.user_id)
        return True


class InAppNotificationService:
    """In-app notification service."""
    
    def __init__(self):
        self.notifications_storage: Dict[str, List[Dict[str, Any]]] = {}
    
    async def send_in_app_notification(self, message: NotificationMessage) -> bool:
        """Send in-app notification."""
        try:
            user_id = message.recipient.user_id
            
            if user_id not in self.notifications_storage:
                self.notifications_storage[user_id] = []
            
            notification_data = {
                "id": message.id,
                "title": message.subject,
                "body": message.body,
                "priority": message.priority.value,
                "created_at": message.created_at.isoformat(),
                "read": False,
                "variables": message.variables
            }
            
            self.notifications_storage[user_id].append(notification_data)
            
            # Keep only last 100 notifications per user
            if len(self.notifications_storage[user_id]) > 100:
                self.notifications_storage[user_id] = self.notifications_storage[user_id][-100:]
            
            logger.info("In-app notification stored", user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("In-app notification failed", 
                        user_id=message.recipient.user_id,
                        error=str(e))
            return False
    
    def get_user_notifications(self, user_id: str, limit: int = 50, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get user's in-app notifications."""
        notifications = self.notifications_storage.get(user_id, [])
        
        if unread_only:
            notifications = [n for n in notifications if not n.get('read', False)]
        
        return notifications[-limit:] if limit else notifications
    
    def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        """Mark notification as read."""
        notifications = self.notifications_storage.get(user_id, [])
        
        for notification in notifications:
            if notification['id'] == notification_id:
                notification['read'] = True
                return True
        
        return False


class NotificationService:
    """Main notification service orchestrator."""
    
    def __init__(self):
        self.template_manager = NotificationTemplateManager()
        self.email_service = EmailService()
        self.push_service = PushNotificationService()
        self.in_app_service = InAppNotificationService()
        
        # Message queue for async processing
        self.message_queue: List[NotificationMessage] = []
        self.processing_queue = False
        
        # Delivery tracking
        self.delivery_stats: Dict[str, Dict[str, int]] = {}
        
        logger.info("Notification service initialized")
    
    async def send_notification(self, 
                              recipient: NotificationRecipient,
                              template_id: str,
                              variables: Dict[str, Any],
                              priority: NotificationPriority = NotificationPriority.NORMAL,
                              channels: Optional[List[NotificationType]] = None,
                              scheduled_at: Optional[datetime] = None) -> List[str]:
        """Send notification via specified channels."""
        
        template = self.template_manager.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Determine channels to use
        if channels is None:
            channels = [recipient.preferred_channel]
        
        # Filter out unsubscribed channels
        channels = [ch for ch in channels if ch not in recipient.unsubscribed_channels]
        
        # Filter channels supported by template
        channels = [ch for ch in channels if ch in template.supported_channels]
        
        message_ids = []
        
        for channel in channels:
            try:
                # Render template
                subject, body = self.template_manager.render_template(template_id, variables)
                
                # Create message
                message = NotificationMessage(
                    id=f"{template_id}_{recipient.user_id}_{channel.value}_{int(datetime.utcnow().timestamp())}",
                    recipient=recipient,
                    template_id=template_id,
                    channel=channel,
                    priority=priority,
                    subject=subject,
                    body=body,
                    variables=variables,
                    scheduled_at=scheduled_at
                )
                
                message_ids.append(message.id)
                
                if scheduled_at and scheduled_at > datetime.utcnow():
                    # Schedule for later
                    self.message_queue.append(message)
                else:
                    # Send immediately
                    await self._dispatch_message(message)
                    
            except Exception as e:
                logger.error("Failed to create notification message",
                           template_id=template_id,
                           channel=channel.value,
                           error=str(e))
        
        return message_ids
    
    async def _dispatch_message(self, message: NotificationMessage):
        """Dispatch message to appropriate service."""
        try:
            success = False
            
            if message.channel == NotificationType.EMAIL:
                success = await self.email_service.send_email(message)
            elif message.channel == NotificationType.PUSH:
                success = await self.push_service.send_push_notification(message)
            elif message.channel == NotificationType.IN_APP:
                success = await self.in_app_service.send_in_app_notification(message)
            
            # Update message status
            if success:
                message.status = NotificationStatus.SENT
                message.sent_at = datetime.utcnow()
                self._record_delivery_stat(message.template_id, message.channel, "sent")
            else:
                message.status = NotificationStatus.FAILED
                self._record_delivery_stat(message.template_id, message.channel, "failed")
                
                # Retry if applicable
                if message.retry_count < message.max_retries:
                    message.retry_count += 1
                    # Schedule retry (exponential backoff)
                    retry_delay = 2 ** message.retry_count * 60  # minutes
                    message.scheduled_at = datetime.utcnow() + timedelta(minutes=retry_delay)
                    self.message_queue.append(message)
            
        except Exception as e:
            logger.error("Message dispatch failed", message_id=message.id, error=str(e))
            message.status = NotificationStatus.FAILED
            message.error_message = str(e)
    
    def _record_delivery_stat(self, template_id: str, channel: NotificationType, status: str):
        """Record delivery statistics."""
        if template_id not in self.delivery_stats:
            self.delivery_stats[template_id] = {}
        
        stat_key = f"{channel.value}_{status}"
        if stat_key not in self.delivery_stats[template_id]:
            self.delivery_stats[template_id][stat_key] = 0
        
        self.delivery_stats[template_id][stat_key] += 1
    
    async def process_scheduled_messages(self):
        """Process scheduled messages."""
        if self.processing_queue:
            return
        
        self.processing_queue = True
        
        try:
            now = datetime.utcnow()
            messages_to_process = []
            remaining_messages = []
            
            for message in self.message_queue:
                if message.scheduled_at and message.scheduled_at <= now:
                    messages_to_process.append(message)
                elif message.expires_at and message.expires_at <= now:
                    # Message expired, don't process
                    logger.info("Message expired", message_id=message.id)
                else:
                    remaining_messages.append(message)
            
            self.message_queue = remaining_messages
            
            # Process messages
            for message in messages_to_process:
                await self._dispatch_message(message)
                
        except Exception as e:
            logger.error("Error processing scheduled messages", error=str(e))
        finally:
            self.processing_queue = False
    
    def get_delivery_stats(self) -> Dict[str, Dict[str, int]]:
        """Get delivery statistics."""
        return self.delivery_stats.copy()
    
    def get_user_notifications(self, user_id: str, limit: int = 50, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get user's in-app notifications."""
        return self.in_app_service.get_user_notifications(user_id, limit, unread_only)
    
    def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        """Mark notification as read."""
        return self.in_app_service.mark_notification_read(user_id, notification_id)


# Global notification service
_notification_service = None


def get_notification_service() -> NotificationService:
    """Get global notification service."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


# Convenience functions
async def send_welcome_email(user_id: str, email: str, user_name: str):
    """Send welcome email to new user."""
    service = get_notification_service()
    recipient = NotificationRecipient(
        user_id=user_id,
        email=email,
        preferred_channel=NotificationType.EMAIL
    )
    
    await service.send_notification(
        recipient=recipient,
        template_id="welcome_email",
        variables={"user_name": user_name, "login_url": settings.frontend_url},
        priority=NotificationPriority.HIGH
    )


async def send_transaction_alert(user_id: str, email: str, transaction_data: Dict[str, Any]):
    """Send transaction alert."""
    service = get_notification_service()
    recipient = NotificationRecipient(
        user_id=user_id,
        email=email,
        preferred_channel=NotificationType.EMAIL
    )
    
    await service.send_notification(
        recipient=recipient,
        template_id="transaction_alert",
        variables=transaction_data,
        priority=NotificationPriority.NORMAL,
        channels=[NotificationType.EMAIL, NotificationType.PUSH]
    )


async def send_budget_warning(user_id: str, email: str, budget_data: Dict[str, Any]):
    """Send budget warning notification."""
    service = get_notification_service()
    recipient = NotificationRecipient(
        user_id=user_id,
        email=email,
        preferred_channel=NotificationType.PUSH
    )
    
    await service.send_notification(
        recipient=recipient,
        template_id="budget_warning",
        variables=budget_data,
        priority=NotificationPriority.HIGH,
        channels=[NotificationType.EMAIL, NotificationType.PUSH, NotificationType.IN_APP]
    )