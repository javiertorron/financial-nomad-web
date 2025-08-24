"""
Backup scheduler service for automated backup operations.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import structlog

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.backup import (
    BackupConfiguration,
    BackupType,
    BackupTriggerRequest,
    BackupDestination
)
from ..services.backup import BackupService, get_backup_service
from ..utils.exceptions import (
    ValidationError as AppValidationError
)

logger = structlog.get_logger()


class BackupSchedulerService:
    """Service for scheduling and executing automatic backups."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
        self.backup_service = get_backup_service()
        
        # Track running backup tasks to prevent duplicates
        self.running_backups: Dict[str, asyncio.Task] = {}
    
    async def check_and_execute_scheduled_backups(self) -> Dict[str, Any]:
        """Check for users who need scheduled backups and execute them."""
        stats = {
            "users_checked": 0,
            "backups_triggered": 0,
            "backups_failed": 0,
            "errors": []
        }
        
        try:
            logger.info("Starting scheduled backup check")
            
            # Get all users with backup configurations
            # Note: This is a simplified approach - in production, you'd want to use
            # Cloud Scheduler + Cloud Functions for better scalability
            
            # For now, we'll return the stats structure for demonstration
            stats["users_checked"] = 0  # Would be populated in real implementation
            
            logger.info("Scheduled backup check completed", **stats)
            return stats
            
        except Exception as e:
            logger.error("Failed to check scheduled backups", error=str(e))
            stats["errors"].append(str(e))
            return stats
    
    async def should_execute_backup(self, user_id: str, config: BackupConfiguration) -> bool:
        """Check if a backup should be executed for the user based on their configuration."""
        try:
            if not config.auto_backup_enabled:
                return False
            
            # Get the last backup for this user
            last_backups = await self.firestore.query_documents(
                collection=f"backups/{user_id}/user_backups",
                model_class=None,  # We'll use dict for simpler querying
                where_clauses=[("backup_type", "!=", BackupType.MANUAL)],
                order_by="created_at",
                limit=1
            )
            
            now = datetime.utcnow()
            
            # If no previous backups, we should backup
            if not last_backups:
                logger.info("No previous backups found, scheduling backup", user_id=user_id)
                return True
            
            last_backup = last_backups[0]
            last_backup_time = last_backup.get('created_at')
            
            if not last_backup_time:
                return True
            
            # Convert to datetime if it's a string
            if isinstance(last_backup_time, str):
                last_backup_time = datetime.fromisoformat(last_backup_time.replace('Z', '+00:00'))
            
            # Calculate next backup time based on frequency
            next_backup_time = self._calculate_next_backup_time(last_backup_time, config.backup_frequency)
            
            should_backup = now >= next_backup_time
            
            logger.info(
                "Backup schedule check",
                user_id=user_id,
                frequency=config.backup_frequency.value,
                last_backup=last_backup_time.isoformat(),
                next_backup=next_backup_time.isoformat(),
                should_backup=should_backup
            )
            
            return should_backup
            
        except Exception as e:
            logger.error("Failed to check backup schedule", user_id=user_id, error=str(e))
            return False
    
    async def execute_scheduled_backup(self, user_id: str, config: BackupConfiguration) -> bool:
        """Execute a scheduled backup for a user."""
        try:
            # Check if backup is already running for this user
            if user_id in self.running_backups and not self.running_backups[user_id].done():
                logger.warning("Backup already running for user", user_id=user_id)
                return False
            
            # Determine backup type based on frequency
            backup_type = self._get_backup_type_from_frequency(config.backup_frequency)
            
            # Create backup request
            backup_request = BackupTriggerRequest(
                backup_type=backup_type,
                destinations=config.destinations,
                include_attachments=config.include_attachments,
                notify_on_completion=bool(config.notification_email)
            )
            
            # Execute backup asynchronously
            backup_task = asyncio.create_task(
                self.backup_service.trigger_backup(user_id, backup_request)
            )
            
            self.running_backups[user_id] = backup_task
            
            # Wait for backup to complete (with timeout)
            try:
                backup_result = await asyncio.wait_for(backup_task, timeout=3600)  # 1 hour timeout
                
                logger.info(
                    "Scheduled backup completed successfully",
                    user_id=user_id,
                    backup_id=backup_result.id,
                    backup_type=backup_type.value
                )
                
                # Send notification if configured
                if config.notification_email:
                    await self._send_backup_notification(
                        config.notification_email,
                        user_id,
                        backup_result,
                        success=True
                    )
                
                return True
                
            except asyncio.TimeoutError:
                logger.error("Scheduled backup timed out", user_id=user_id)
                backup_task.cancel()
                return False
            
            finally:
                # Clean up task reference
                if user_id in self.running_backups:
                    del self.running_backups[user_id]
            
        except Exception as e:
            logger.error("Failed to execute scheduled backup", user_id=user_id, error=str(e))
            
            # Send failure notification if configured
            if config.notification_email:
                await self._send_backup_notification(
                    config.notification_email,
                    user_id,
                    None,
                    success=False,
                    error=str(e)
                )
            
            return False
    
    async def cleanup_old_backups(self) -> Dict[str, int]:
        """Clean up old backup records and files based on retention policies."""
        stats = {"deleted_records": 0, "deleted_files": 0, "errors": 0}
        
        try:
            logger.info("Starting backup cleanup")
            
            # This would iterate through all users and their backup configurations
            # to clean up expired backups based on their retention settings
            
            # For demonstration, we'll return the stats structure
            logger.info("Backup cleanup completed", **stats)
            return stats
            
        except Exception as e:
            logger.error("Failed to cleanup old backups", error=str(e))
            stats["errors"] += 1
            return stats
    
    async def get_backup_schedule_status(self) -> Dict[str, Any]:
        """Get status of backup scheduling system."""
        return {
            "active_backups": len([task for task in self.running_backups.values() if not task.done()]),
            "total_tracked_backups": len(self.running_backups),
            "scheduler_status": "running",
            "last_check": datetime.utcnow().isoformat()
        }
    
    def _calculate_next_backup_time(self, last_backup: datetime, frequency: BackupType) -> datetime:
        """Calculate when the next backup should occur based on frequency."""
        if frequency == BackupType.SCHEDULED_DAILY:
            return last_backup + timedelta(days=1)
        elif frequency == BackupType.SCHEDULED_WEEKLY:
            return last_backup + timedelta(weeks=1)
        elif frequency == BackupType.SCHEDULED_MONTHLY:
            # Add approximately one month (30 days)
            return last_backup + timedelta(days=30)
        else:
            # For manual backups or unknown frequencies, return far future
            return last_backup + timedelta(days=365)
    
    def _get_backup_type_from_frequency(self, frequency: BackupType) -> BackupType:
        """Convert backup frequency to backup type."""
        if frequency == BackupType.SCHEDULED_DAILY:
            return BackupType.SCHEDULED_DAILY
        elif frequency == BackupType.SCHEDULED_WEEKLY:
            return BackupType.SCHEDULED_WEEKLY
        elif frequency == BackupType.SCHEDULED_MONTHLY:
            return BackupType.SCHEDULED_MONTHLY
        else:
            return BackupType.MANUAL
    
    async def _send_backup_notification(
        self,
        email: str,
        user_id: str,
        backup_result: Optional[Any],
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Send backup notification email."""
        try:
            # In a real implementation, this would integrate with an email service
            # like SendGrid, AWS SES, or similar
            
            subject = "Financial Nomad - Backup Completed" if success else "Financial Nomad - Backup Failed"
            
            if success and backup_result:
                message = f"""
                Your scheduled backup has completed successfully.
                
                Backup ID: {backup_result.id}
                Type: {backup_result.backup_type.value}
                Completed: {backup_result.completed_at}
                File Size: {backup_result.file_size_bytes or 0} bytes
                """
            else:
                message = f"""
                Your scheduled backup has failed.
                
                Error: {error or 'Unknown error occurred'}
                Time: {datetime.utcnow().isoformat()}
                """
            
            # Log the notification (in production, actually send email)
            logger.info(
                "Backup notification prepared",
                email=email,
                user_id=user_id,
                success=success,
                subject=subject
            )
            
            # TODO: Implement actual email sending
            
        except Exception as e:
            logger.error("Failed to send backup notification", email=email, error=str(e))


class BackupSchedulerEndpoint:
    """Endpoint handlers for backup scheduler (for admin/monitoring)."""
    
    def __init__(self):
        self.scheduler = BackupSchedulerService()
    
    async def trigger_scheduled_backup_check(self) -> Dict[str, Any]:
        """Manually trigger a scheduled backup check."""
        return await self.scheduler.check_and_execute_scheduled_backups()
    
    async def cleanup_old_backups(self) -> Dict[str, Any]:
        """Manually trigger cleanup of old backups."""
        return await self.scheduler.cleanup_old_backups()
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get backup scheduler status."""
        return await self.scheduler.get_backup_schedule_status()


# Global service instances
_backup_scheduler_service: Optional[BackupSchedulerService] = None
_backup_scheduler_endpoint: Optional[BackupSchedulerEndpoint] = None


def get_backup_scheduler_service() -> BackupSchedulerService:
    """Get the global backup scheduler service instance."""
    global _backup_scheduler_service
    if _backup_scheduler_service is None:
        _backup_scheduler_service = BackupSchedulerService()
    return _backup_scheduler_service


def get_backup_scheduler_endpoint() -> BackupSchedulerEndpoint:
    """Get the global backup scheduler endpoint instance."""
    global _backup_scheduler_endpoint
    if _backup_scheduler_endpoint is None:
        _backup_scheduler_endpoint = BackupSchedulerEndpoint()
    return _backup_scheduler_endpoint