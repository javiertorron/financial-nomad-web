"""
Backup and export models for Financial Nomad API.
"""
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, Field, validator

from .base import UserOwnedModel


class BackupType(str, Enum):
    """Types of backups."""
    MANUAL = "manual"
    SCHEDULED_DAILY = "scheduled_daily"
    SCHEDULED_WEEKLY = "scheduled_weekly"
    SCHEDULED_MONTHLY = "scheduled_monthly"


class BackupStatus(str, Enum):
    """Backup status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class BackupDestination(str, Enum):
    """Backup destinations."""
    GOOGLE_DRIVE = "google_drive"
    LOCAL_STORAGE = "local_storage"
    CLOUD_STORAGE = "cloud_storage"


class ExportFormat(str, Enum):
    """Export formats."""
    JSON = "json"
    CSV = "csv" 
    YAML = "yaml"
    PDF = "pdf"


class ExportType(str, Enum):
    """Types of exports."""
    FULL_BACKUP = "full_backup"
    TRANSACTIONS_ONLY = "transactions_only"
    BUDGETS_ONLY = "budgets_only"
    LLM_SNAPSHOT = "llm_snapshot"
    FINANCIAL_SUMMARY = "financial_summary"


# Core backup models

class BackupConfiguration(UserOwnedModel):
    """User's backup configuration."""
    auto_backup_enabled: bool = Field(default=True, description="Enable automatic backups")
    backup_frequency: BackupType = Field(default=BackupType.SCHEDULED_WEEKLY, description="Backup frequency")
    destinations: List[BackupDestination] = Field(default=[BackupDestination.GOOGLE_DRIVE], description="Backup destinations")
    retention_days: int = Field(default=90, ge=1, le=365, description="Backup retention in days")
    include_attachments: bool = Field(default=True, description="Include transaction attachments")
    encryption_enabled: bool = Field(default=True, description="Enable backup encryption")
    notification_email: Optional[str] = Field(default=None, description="Email for backup notifications")
    google_drive_folder_id: Optional[str] = Field(default=None, description="Google Drive folder for backups")
    
    @validator('retention_days')
    def validate_retention_days(cls, v):
        """Validate retention days based on backup frequency."""
        if v < 7:
            raise ValueError("Minimum retention is 7 days")
        return v


class BackupMetadata(BaseModel):
    """Metadata about backup content."""
    users_count: int = Field(default=0, description="Number of users included")
    accounts_count: int = Field(default=0, description="Number of accounts")
    transactions_count: int = Field(default=0, description="Number of transactions")
    categories_count: int = Field(default=0, description="Number of categories")
    budgets_count: int = Field(default=0, description="Number of budgets")
    date_range_start: Optional[date] = Field(default=None, description="Earliest transaction date")
    date_range_end: Optional[date] = Field(default=None, description="Latest transaction date")
    file_size_bytes: Optional[int] = Field(default=None, description="Backup file size in bytes")
    compression_ratio: Optional[float] = Field(default=None, description="Compression ratio if compressed")


class BackupRecord(UserOwnedModel):
    """Record of a backup operation."""
    backup_type: BackupType = Field(..., description="Type of backup")
    status: BackupStatus = Field(default=BackupStatus.PENDING, description="Backup status")
    destinations: List[BackupDestination] = Field(..., description="Backup destinations")
    file_paths: Dict[str, str] = Field(default_factory=dict, description="File paths per destination")
    metadata: Optional[BackupMetadata] = Field(default=None, description="Backup metadata")
    started_at: Optional[datetime] = Field(default=None, description="Backup start time")
    completed_at: Optional[datetime] = Field(default=None, description="Backup completion time")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    expires_at: Optional[datetime] = Field(default=None, description="Backup expiration time")
    checksum: Optional[str] = Field(default=None, description="Backup file checksum")
    encryption_key_id: Optional[str] = Field(default=None, description="Encryption key ID if encrypted")
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate backup duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class ExportRequest(BaseModel):
    """Request for data export."""
    export_type: ExportType = Field(..., description="Type of export")
    format: ExportFormat = Field(default=ExportFormat.JSON, description="Export format")
    date_range_start: Optional[date] = Field(default=None, description="Start date for filtered export")
    date_range_end: Optional[date] = Field(default=None, description="End date for filtered export")
    include_categories: Optional[List[str]] = Field(default=None, description="Category IDs to include")
    include_accounts: Optional[List[str]] = Field(default=None, description="Account IDs to include")
    anonymize_data: bool = Field(default=False, description="Anonymize personal data")
    include_attachments: bool = Field(default=False, description="Include transaction attachments")
    compress_output: bool = Field(default=True, description="Compress export file")
    
    @validator('date_range_end')
    def validate_date_range(cls, v, values):
        """Validate date range."""
        start = values.get('date_range_start')
        if start and v and v < start:
            raise ValueError("End date must be after start date")
        return v


class ExportRecord(UserOwnedModel):
    """Record of an export operation."""
    export_type: ExportType = Field(..., description="Type of export")
    format: ExportFormat = Field(..., description="Export format")
    status: BackupStatus = Field(default=BackupStatus.PENDING, description="Export status")
    request_params: ExportRequest = Field(..., description="Original export request")
    file_path: Optional[str] = Field(default=None, description="Generated file path")
    file_size_bytes: Optional[int] = Field(default=None, description="File size in bytes")
    download_url: Optional[str] = Field(default=None, description="Temporary download URL")
    expires_at: Optional[datetime] = Field(default=None, description="Download URL expiration")
    checksum: Optional[str] = Field(default=None, description="File checksum")
    metadata: Optional[BackupMetadata] = Field(default=None, description="Export metadata")
    started_at: Optional[datetime] = Field(default=None, description="Export start time")
    completed_at: Optional[datetime] = Field(default=None, description="Export completion time")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate export duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.started_at - self.completed_at).total_seconds()
        return None


class DriveIntegration(UserOwnedModel):
    """Google Drive integration configuration."""
    refresh_token: str = Field(..., description="Encrypted Google Drive refresh token")
    drive_email: str = Field(..., description="Google Drive account email")
    folder_id: Optional[str] = Field(default=None, description="Backup folder ID in Drive")
    folder_name: str = Field(default="Financial Nomad Backups", description="Backup folder name")
    quota_used_bytes: Optional[int] = Field(default=None, description="Drive quota used")
    quota_total_bytes: Optional[int] = Field(default=None, description="Drive total quota")
    last_sync_at: Optional[datetime] = Field(default=None, description="Last successful sync time")
    sync_enabled: bool = Field(default=True, description="Enable Drive sync")
    
    @validator('folder_name')
    def validate_folder_name(cls, v):
        """Validate folder name."""
        if not v or len(v.strip()) == 0:
            return "Financial Nomad Backups"
        return v.strip()


# Response models

class BackupConfigurationResponse(BaseModel):
    """Response model for backup configuration."""
    id: str
    user_id: str
    auto_backup_enabled: bool
    backup_frequency: BackupType
    destinations: List[BackupDestination]
    retention_days: int
    include_attachments: bool
    encryption_enabled: bool
    notification_email: Optional[str]
    google_drive_folder_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class BackupRecordResponse(BaseModel):
    """Response model for backup record."""
    id: str
    user_id: str
    backup_type: BackupType
    status: BackupStatus
    destinations: List[BackupDestination]
    metadata: Optional[BackupMetadata]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    error_message: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime


class ExportRecordResponse(BaseModel):
    """Response model for export record."""
    id: str
    user_id: str
    export_type: ExportType
    format: ExportFormat
    status: BackupStatus
    file_size_bytes: Optional[int]
    download_url: Optional[str]
    expires_at: Optional[datetime]
    metadata: Optional[BackupMetadata]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    error_message: Optional[str]
    created_at: datetime


class DriveIntegrationResponse(BaseModel):
    """Response model for Drive integration."""
    id: str
    user_id: str
    drive_email: str
    folder_name: str
    folder_id: Optional[str]
    quota_used_bytes: Optional[int]
    quota_total_bytes: Optional[int]
    last_sync_at: Optional[datetime]
    sync_enabled: bool
    created_at: datetime
    updated_at: datetime


# Request models for updates

class BackupConfigurationUpdateRequest(BaseModel):
    """Request to update backup configuration."""
    auto_backup_enabled: Optional[bool] = None
    backup_frequency: Optional[BackupType] = None
    destinations: Optional[List[BackupDestination]] = None
    retention_days: Optional[int] = Field(default=None, ge=1, le=365)
    include_attachments: Optional[bool] = None
    encryption_enabled: Optional[bool] = None
    notification_email: Optional[str] = None


class BackupTriggerRequest(BaseModel):
    """Request to trigger manual backup."""
    backup_type: BackupType = Field(default=BackupType.MANUAL, description="Type of backup")
    destinations: Optional[List[BackupDestination]] = Field(default=None, description="Override default destinations")
    include_attachments: bool = Field(default=True, description="Include attachments")
    notify_on_completion: bool = Field(default=False, description="Send notification when complete")


class DriveAuthRequest(BaseModel):
    """Request to authenticate with Google Drive."""
    authorization_code: str = Field(..., description="Google OAuth authorization code")
    redirect_uri: str = Field(..., description="OAuth redirect URI")


class DriveConfigUpdateRequest(BaseModel):
    """Request to update Drive configuration."""
    folder_name: Optional[str] = None
    sync_enabled: Optional[bool] = None