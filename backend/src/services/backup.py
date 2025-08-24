"""
Backup service for automated and manual backups of Financial Nomad data.
"""
import asyncio
import gzip
import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

import aiofiles
import structlog
from cryptography.fernet import Fernet

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.backup import (
    BackupConfiguration,
    BackupRecord,
    ExportRecord,
    BackupMetadata,
    BackupType,
    BackupStatus,
    BackupDestination,
    ExportType,
    ExportFormat,
    BackupTriggerRequest,
    ExportRequest,
    BackupConfigurationResponse,
    BackupRecordResponse,
    ExportRecordResponse
)
from ..models.financial import Transaction, Budget, RecurringTransaction
from ..models.auth import User
from ..models.financial import Account, Category
from ..utils.exceptions import (
    NotFoundError,
    ValidationError as AppValidationError,
    BusinessLogicError,
    ExternalServiceError
)

logger = structlog.get_logger()


class BackupService:
    """Service for handling backup operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
        
        # Encryption setup
        encryption_key = getattr(self.settings, 'backup_encryption_key', None)
        if encryption_key:
            self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        else:
            self.fernet = Fernet(Fernet.generate_key())
            logger.warning("Using generated encryption key for backups - configure backup_encryption_key in production")
    
    async def get_backup_configuration(self, user_id: str) -> Optional[BackupConfigurationResponse]:
        """Get user's backup configuration."""
        try:
            configs = await self.firestore.query_documents(
                collection=f"backup_configs/{user_id}/user_configs",
                model_class=BackupConfiguration,
                limit=1
            )
            
            if not configs:
                return None
            
            config = configs[0]
            return BackupConfigurationResponse(
                id=config.id,
                user_id=config.user_id,
                auto_backup_enabled=config.auto_backup_enabled,
                backup_frequency=config.backup_frequency,
                destinations=config.destinations,
                retention_days=config.retention_days,
                include_attachments=config.include_attachments,
                encryption_enabled=config.encryption_enabled,
                notification_email=config.notification_email,
                google_drive_folder_id=config.google_drive_folder_id,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            
        except Exception as e:
            logger.error("Failed to get backup configuration", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve backup configuration",
                details=[str(e)]
            )
    
    async def create_or_update_backup_configuration(
        self, user_id: str, config_data: Dict[str, Any]
    ) -> BackupConfigurationResponse:
        """Create or update user's backup configuration."""
        try:
            # Check if configuration exists
            existing_config = await self.get_backup_configuration(user_id)
            
            if existing_config:
                # Update existing configuration
                config_id = existing_config.id
                config_data.update({
                    "updated_at": datetime.utcnow()
                })
                
                await self.firestore.update_document(
                    collection=f"backup_configs/{user_id}/user_configs",
                    document_id=config_id,
                    data=config_data
                )
                
                # Get updated configuration
                updated_config = await self.get_backup_configuration(user_id)
                return updated_config
                
            else:
                # Create new configuration
                config_id = str(uuid4())
                config = BackupConfiguration(
                    id=config_id,
                    user_id=user_id,
                    **config_data
                )
                
                await self.firestore.create_document(
                    collection=f"backup_configs/{user_id}/user_configs",
                    document_id=config_id,
                    data=config
                )
                
                logger.info("Backup configuration created", user_id=user_id, config_id=config_id)
                
                return BackupConfigurationResponse(
                    id=config.id,
                    user_id=config.user_id,
                    auto_backup_enabled=config.auto_backup_enabled,
                    backup_frequency=config.backup_frequency,
                    destinations=config.destinations,
                    retention_days=config.retention_days,
                    include_attachments=config.include_attachments,
                    encryption_enabled=config.encryption_enabled,
                    notification_email=config.notification_email,
                    google_drive_folder_id=config.google_drive_folder_id,
                    created_at=config.created_at,
                    updated_at=config.updated_at
                )
                
        except Exception as e:
            logger.error("Failed to create/update backup configuration", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to save backup configuration",
                details=[str(e)]
            )
    
    async def trigger_backup(self, user_id: str, request: BackupTriggerRequest) -> BackupRecordResponse:
        """Trigger a manual backup."""
        backup_id = str(uuid4())
        started_at = datetime.utcnow()
        
        try:
            # Get backup configuration
            config = await self.get_backup_configuration(user_id)
            if not config:
                # Create default configuration
                config = await self.create_or_update_backup_configuration(user_id, {})
            
            # Determine destinations
            destinations = request.destinations or config.destinations
            
            # Create backup record
            backup_record = BackupRecord(
                id=backup_id,
                user_id=user_id,
                backup_type=request.backup_type,
                destinations=destinations,
                started_at=started_at,
                expires_at=started_at + timedelta(days=config.retention_days)
            )
            
            await self.firestore.create_document(
                collection=f"backups/{user_id}/user_backups",
                document_id=backup_id,
                data=backup_record
            )
            
            # Perform backup
            backup_data = await self._collect_user_data(user_id, request.include_attachments)
            metadata = await self._generate_backup_metadata(backup_data)
            
            # Process each destination
            file_paths = {}
            errors = []
            
            for destination in destinations:
                try:
                    file_path = await self._store_backup(
                        user_id, backup_id, backup_data, destination, config.encryption_enabled
                    )
                    file_paths[destination.value] = file_path
                except Exception as e:
                    logger.error(f"Failed to store backup to {destination}", 
                               user_id=user_id, backup_id=backup_id, error=str(e))
                    errors.append(f"{destination}: {str(e)}")
            
            # Update backup record
            completed_at = datetime.utcnow()
            status = BackupStatus.COMPLETED if not errors else BackupStatus.FAILED
            
            checksum = None
            if file_paths and not errors:
                # Generate checksum from first successful backup
                first_path = list(file_paths.values())[0]
                checksum = await self._generate_file_checksum(first_path)
            
            update_data = {
                "status": status,
                "file_paths": file_paths,
                "metadata": metadata.dict(),
                "completed_at": completed_at,
                "checksum": checksum,
                "error_message": "; ".join(errors) if errors else None
            }
            
            await self.firestore.update_document(
                collection=f"backups/{user_id}/user_backups",
                document_id=backup_id,
                data=update_data
            )
            
            logger.info(
                "Backup completed",
                user_id=user_id,
                backup_id=backup_id,
                status=status.value,
                destinations=len(file_paths),
                errors=len(errors),
                duration_seconds=(completed_at - started_at).total_seconds()
            )
            
            return BackupRecordResponse(
                id=backup_id,
                user_id=user_id,
                backup_type=request.backup_type,
                status=status,
                destinations=destinations,
                metadata=metadata,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                error_message="; ".join(errors) if errors else None,
                expires_at=backup_record.expires_at,
                created_at=backup_record.created_at
            )
            
        except Exception as e:
            logger.error("Failed to complete backup", user_id=user_id, backup_id=backup_id, error=str(e))
            
            # Update backup record with failure
            await self.firestore.update_document(
                collection=f"backups/{user_id}/user_backups",
                document_id=backup_id,
                data={
                    "status": BackupStatus.FAILED,
                    "completed_at": datetime.utcnow(),
                    "error_message": str(e)
                }
            )
            
            raise AppValidationError(
                message="Failed to complete backup",
                details=[str(e)]
            )
    
    async def list_backups(self, user_id: str, limit: int = 50) -> List[BackupRecordResponse]:
        """List user's backup records."""
        try:
            backup_records = await self.firestore.query_documents(
                collection=f"backups/{user_id}/user_backups",
                model_class=BackupRecord,
                order_by="created_at",
                limit=limit
            )
            
            responses = []
            for record in backup_records:
                responses.append(BackupRecordResponse(
                    id=record.id,
                    user_id=record.user_id,
                    backup_type=record.backup_type,
                    status=record.status,
                    destinations=record.destinations,
                    metadata=record.metadata,
                    started_at=record.started_at,
                    completed_at=record.completed_at,
                    duration_seconds=record.duration_seconds,
                    error_message=record.error_message,
                    expires_at=record.expires_at,
                    created_at=record.created_at
                ))
            
            return responses
            
        except Exception as e:
            logger.error("Failed to list backups", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to list backups",
                details=[str(e)]
            )
    
    async def delete_backup(self, user_id: str, backup_id: str) -> None:
        """Delete a backup record and associated files."""
        try:
            # Get backup record
            backup_record = await self.firestore.get_document(
                collection=f"backups/{user_id}/user_backups",
                document_id=backup_id,
                model_class=BackupRecord
            )
            
            if not backup_record:
                raise NotFoundError(
                    message="Backup not found",
                    resource_type="backup",
                    resource_id=backup_id
                )
            
            # Delete files from storage
            for destination, file_path in backup_record.file_paths.items():
                try:
                    await self._delete_backup_file(file_path, BackupDestination(destination))
                except Exception as e:
                    logger.warning("Failed to delete backup file", 
                                 file_path=file_path, error=str(e))
            
            # Delete backup record
            await self.firestore.delete_document(
                collection=f"backups/{user_id}/user_backups",
                document_id=backup_id
            )
            
            logger.info("Backup deleted", user_id=user_id, backup_id=backup_id)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete backup", user_id=user_id, backup_id=backup_id, error=str(e))
            raise AppValidationError(
                message="Failed to delete backup",
                details=[str(e)]
            )
    
    async def cleanup_expired_backups(self) -> Dict[str, int]:
        """Clean up expired backup records and files."""
        try:
            cleanup_stats = {"records_deleted": 0, "files_deleted": 0, "errors": 0}
            
            # Find expired backups across all users
            # Note: This is a simplified approach - in production, you might want
            # to use a more efficient query or background job
            
            now = datetime.utcnow()
            
            # Query all backup records (this is inefficient for large datasets)
            # In production, consider using Cloud Scheduler + Cloud Functions
            
            logger.info("Starting backup cleanup job", timestamp=now)
            
            # For demo purposes, return statistics
            return cleanup_stats
            
        except Exception as e:
            logger.error("Failed to cleanup expired backups", error=str(e))
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _collect_user_data(self, user_id: str, include_attachments: bool = True) -> Dict[str, Any]:
        """Collect all user data for backup."""
        data = {
            "user_id": user_id,
            "backup_timestamp": datetime.utcnow().isoformat(),
            "data": {}
        }
        
        try:
            # Collect user profile
            user = await self.firestore.get_document(
                collection="users",
                document_id=user_id,
                model_class=User
            )
            if user:
                data["data"]["user"] = user.dict()
            
            # Collect bank accounts
            accounts = await self.firestore.query_documents(
                collection=f"accounts/{user_id}/bank_accounts",
                model_class=Account
            )
            data["data"]["bank_accounts"] = [account.dict() for account in accounts]
            
            # Collect categories  
            categories = await self.firestore.query_documents(
                collection=f"categories/{user_id}/user_categories",
                model_class=Category
            )
            data["data"]["categories"] = [category.dict() for category in categories]
            
            # Collect transactions
            transactions = await self.firestore.query_documents(
                collection=f"transactions/{user_id}/user_transactions",
                model_class=Transaction
            )
            data["data"]["transactions"] = [transaction.dict() for transaction in transactions]
            
            # Collect budgets
            budgets = await self.firestore.query_documents(
                collection=f"budgets/{user_id}/user_budgets",
                model_class=Budget
            )
            data["data"]["budgets"] = [budget.dict() for budget in budgets]
            
            # Collect recurring transactions
            recurring = await self.firestore.query_documents(
                collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                model_class=RecurringTransaction
            )
            data["data"]["recurring_transactions"] = [rec.dict() for rec in recurring]
            
            logger.info(
                "User data collected for backup",
                user_id=user_id,
                accounts=len(accounts),
                categories=len(categories),
                transactions=len(transactions),
                budgets=len(budgets),
                recurring=len(recurring)
            )
            
            return data
            
        except Exception as e:
            logger.error("Failed to collect user data", user_id=user_id, error=str(e))
            raise
    
    async def _generate_backup_metadata(self, backup_data: Dict[str, Any]) -> BackupMetadata:
        """Generate metadata for backup."""
        data = backup_data.get("data", {})
        
        transactions = data.get("transactions", [])
        date_range_start = None
        date_range_end = None
        
        if transactions:
            dates = [t.get("transaction_date") for t in transactions if t.get("transaction_date")]
            if dates:
                date_range_start = min(dates)
                date_range_end = max(dates)
        
        return BackupMetadata(
            users_count=1,
            accounts_count=len(data.get("bank_accounts", [])),
            transactions_count=len(transactions),
            categories_count=len(data.get("categories", [])),
            budgets_count=len(data.get("budgets", [])),
            date_range_start=date_range_start,
            date_range_end=date_range_end
        )
    
    async def _store_backup(
        self, user_id: str, backup_id: str, data: Dict[str, Any], 
        destination: BackupDestination, encrypt: bool
    ) -> str:
        """Store backup to specified destination."""
        filename = f"backup_{user_id}_{backup_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Serialize data
        json_data = json.dumps(data, default=str, indent=2)
        
        # Encrypt if requested
        if encrypt:
            json_data = self.fernet.encrypt(json_data.encode()).decode()
            filename += ".enc"
        
        # Compress
        compressed_data = gzip.compress(json_data.encode())
        filename += ".gz"
        
        if destination == BackupDestination.LOCAL_STORAGE:
            return await self._store_to_local(filename, compressed_data)
        elif destination == BackupDestination.GOOGLE_DRIVE:
            return await self._store_to_drive(user_id, filename, compressed_data)
        elif destination == BackupDestination.CLOUD_STORAGE:
            return await self._store_to_cloud_storage(user_id, filename, compressed_data)
        else:
            raise ValueError(f"Unsupported backup destination: {destination}")
    
    async def _store_to_local(self, filename: str, data: bytes) -> str:
        """Store backup to local filesystem."""
        # Create backup directory
        backup_dir = os.path.join(tempfile.gettempdir(), "financial_nomad_backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        file_path = os.path.join(backup_dir, filename)
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(data)
        
        logger.info("Backup stored locally", file_path=file_path, size=len(data))
        return file_path
    
    async def _store_to_drive(self, user_id: str, filename: str, data: bytes) -> str:
        """Store backup to Google Drive."""
        # This would integrate with Google Drive API
        # For now, return a placeholder path
        drive_path = f"drive://financial-nomad-backups/{filename}"
        
        # TODO: Implement actual Google Drive upload
        logger.info("Backup would be stored to Drive", path=drive_path, size=len(data))
        
        return drive_path
    
    async def _store_to_cloud_storage(self, user_id: str, filename: str, data: bytes) -> str:
        """Store backup to Google Cloud Storage."""
        # This would integrate with Cloud Storage API
        # For now, return a placeholder path
        gcs_path = f"gs://financial-nomad-backups/{user_id}/{filename}"
        
        # TODO: Implement actual GCS upload
        logger.info("Backup would be stored to GCS", path=gcs_path, size=len(data))
        
        return gcs_path
    
    async def _generate_file_checksum(self, file_path: str) -> str:
        """Generate SHA-256 checksum of backup file."""
        if file_path.startswith(('drive://', 'gs://')):
            # For remote files, return placeholder checksum
            return "remote_file_checksum"
        
        hash_sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            async for chunk in f:
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    async def _delete_backup_file(self, file_path: str, destination: BackupDestination) -> None:
        """Delete backup file from storage."""
        if destination == BackupDestination.LOCAL_STORAGE:
            if os.path.exists(file_path):
                os.remove(file_path)
        elif destination == BackupDestination.GOOGLE_DRIVE:
            # TODO: Implement Google Drive file deletion
            pass
        elif destination == BackupDestination.CLOUD_STORAGE:
            # TODO: Implement GCS file deletion
            pass


# Global service instance
_backup_service: Optional[BackupService] = None


def get_backup_service() -> BackupService:
    """Get the global backup service instance."""
    global _backup_service
    if _backup_service is None:
        _backup_service = BackupService()
    return _backup_service