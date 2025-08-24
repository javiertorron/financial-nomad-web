"""
Backup and export endpoints for Financial Nomad API.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from fastapi.responses import StreamingResponse
import structlog

from ..models.backup import (
    BackupConfigurationResponse,
    BackupConfigurationUpdateRequest,
    BackupTriggerRequest,
    BackupRecordResponse,
    ExportRequest,
    ExportRecordResponse,
    DriveIntegrationResponse,
    DriveAuthRequest,
    DriveConfigUpdateRequest
)
from ..models.auth import User
from ..services.backup import BackupService, get_backup_service
from ..services.export import ExportService, get_export_service
from ..services.drive_integration import DriveIntegrationService, get_drive_integration_service
from ..services.scheduler import BackupSchedulerEndpoint, get_backup_scheduler_endpoint
from ..routers.auth import get_current_user
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError, BusinessLogicError

logger = structlog.get_logger()

router = APIRouter(
    prefix="/backup",
    tags=["backup-export"]
)


# Backup Configuration Endpoints

@router.get("/config", response_model=Optional[BackupConfigurationResponse])
async def get_backup_configuration(
    current_user_tuple: tuple = Depends(get_current_user),
    backup_service: BackupService = Depends(get_backup_service)
) -> Optional[BackupConfigurationResponse]:
    """Get user's backup configuration."""
    try:
        current_user, _ = current_user_tuple
        config = await backup_service.get_backup_configuration(current_user.id)
        return config
        
    except Exception as e:
        logger.error("Failed to get backup configuration", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve backup configuration")


@router.put("/config", response_model=BackupConfigurationResponse)
async def update_backup_configuration(
    request: BackupConfigurationUpdateRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    backup_service: BackupService = Depends(get_backup_service)
) -> BackupConfigurationResponse:
    """Update user's backup configuration."""
    try:
        current_user, _ = current_user_tuple
        
        # Convert request to dict, excluding None values
        config_data = {}
        for field, value in request.dict().items():
            if value is not None:
                config_data[field] = value
        
        config = await backup_service.create_or_update_backup_configuration(current_user.id, config_data)
        return config
        
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Failed to update backup configuration", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update backup configuration")


# Backup Operations Endpoints

@router.post("/trigger", response_model=BackupRecordResponse)
async def trigger_backup(
    request: BackupTriggerRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    backup_service: BackupService = Depends(get_backup_service)
) -> BackupRecordResponse:
    """Trigger a manual backup."""
    try:
        current_user, _ = current_user_tuple
        backup_record = await backup_service.trigger_backup(current_user.id, request)
        return backup_record
        
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Failed to trigger backup", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to trigger backup")


@router.get("/list", response_model=List[BackupRecordResponse])
async def list_backups(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of backups to return"),
    current_user_tuple: tuple = Depends(get_current_user),
    backup_service: BackupService = Depends(get_backup_service)
) -> List[BackupRecordResponse]:
    """List user's backup records."""
    try:
        current_user, _ = current_user_tuple
        backups = await backup_service.list_backups(current_user.id, limit)
        return backups
        
    except Exception as e:
        logger.error("Failed to list backups", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list backups")


@router.delete("/{backup_id}")
async def delete_backup(
    backup_id: str,
    current_user_tuple: tuple = Depends(get_current_user),
    backup_service: BackupService = Depends(get_backup_service)
):
    """Delete a backup record and associated files."""
    try:
        current_user, _ = current_user_tuple
        await backup_service.delete_backup(current_user.id, backup_id)
        return {"message": "Backup deleted successfully"}
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error("Failed to delete backup", user_id=current_user.id, backup_id=backup_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete backup")


# Export Operations Endpoints

@router.post("/export", response_model=ExportRecordResponse)
async def create_export(
    request: ExportRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    export_service: ExportService = Depends(get_export_service)
) -> ExportRecordResponse:
    """Create a new data export."""
    try:
        current_user, _ = current_user_tuple
        export_record = await export_service.create_export(current_user.id, request)
        return export_record
        
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Failed to create export", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create export")


@router.get("/exports", response_model=List[ExportRecordResponse])
async def list_exports(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of exports to return"),
    current_user_tuple: tuple = Depends(get_current_user),
    export_service: ExportService = Depends(get_export_service)
) -> List[ExportRecordResponse]:
    """List user's export records."""
    try:
        current_user, _ = current_user_tuple
        exports = await export_service.list_exports(current_user.id, limit)
        return exports
        
    except Exception as e:
        logger.error("Failed to list exports", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list exports")


@router.get("/exports/{export_id}", response_model=ExportRecordResponse)
async def get_export(
    export_id: str,
    current_user_tuple: tuple = Depends(get_current_user),
    export_service: ExportService = Depends(get_export_service)
) -> ExportRecordResponse:
    """Get export record by ID."""
    try:
        current_user, _ = current_user_tuple
        export_record = await export_service.get_export(current_user.id, export_id)
        
        if not export_record:
            raise NotFoundError(
                message="Export not found",
                resource_type="export",
                resource_id=export_id
            )
        
        return export_record
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error("Failed to get export", user_id=current_user.id, export_id=export_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve export")


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: str,
    current_user_tuple: tuple = Depends(get_current_user),
    export_service: ExportService = Depends(get_export_service)
):
    """Download export file."""
    try:
        current_user, _ = current_user_tuple
        filename, file_content = await export_service.get_export_file(current_user.id, export_id)
        
        # Determine media type based on file extension
        media_type = "application/octet-stream"
        if filename.endswith('.json'):
            media_type = "application/json"
        elif filename.endswith('.csv'):
            media_type = "text/csv"
        elif filename.endswith('.yaml') or filename.endswith('.yml'):
            media_type = "text/yaml"
        elif filename.endswith('.pdf'):
            media_type = "application/pdf"
        elif filename.endswith('.gz'):
            media_type = "application/gzip"
        
        # Create streaming response
        def generate():
            yield file_content
        
        return StreamingResponse(
            generate(),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Failed to download export", user_id=current_user.id, export_id=export_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to download export file")


@router.delete("/exports/{export_id}")
async def delete_export(
    export_id: str,
    current_user_tuple: tuple = Depends(get_current_user),
    export_service: ExportService = Depends(get_export_service)
):
    """Delete export record and file."""
    try:
        current_user, _ = current_user_tuple
        await export_service.delete_export(current_user.id, export_id)
        return {"message": "Export deleted successfully"}
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error("Failed to delete export", user_id=current_user.id, export_id=export_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete export")


# Google Drive Integration Endpoints

@router.get("/drive/oauth/authorize")
async def initiate_drive_oauth(
    current_user_tuple: tuple = Depends(get_current_user),
    drive_service: DriveIntegrationService = Depends(get_drive_integration_service),
    state: Optional[str] = Query(None, description="OAuth state parameter")
):
    """Initiate OAuth flow with Google Drive."""
    try:
        current_user, _ = current_user_tuple
        authorization_url = await drive_service.get_oauth_authorization_url(current_user.id, state)
        
        # Return redirect URL for frontend to handle
        return {"authorization_url": authorization_url}
        
    except Exception as e:
        logger.error("Failed to initiate Drive OAuth", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to initiate Google Drive OAuth")


@router.post("/drive/oauth/complete", response_model=DriveIntegrationResponse)
async def complete_drive_oauth(
    request: DriveAuthRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    drive_service: DriveIntegrationService = Depends(get_drive_integration_service)
) -> DriveIntegrationResponse:
    """Complete OAuth flow and create Drive integration."""
    try:
        current_user, _ = current_user_tuple
        integration = await drive_service.handle_oauth_callback(current_user.id, request)
        return integration
        
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Failed to complete Drive OAuth", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to complete Google Drive integration")


@router.get("/drive/integration", response_model=Optional[DriveIntegrationResponse])
async def get_drive_integration(
    current_user_tuple: tuple = Depends(get_current_user),
    drive_service: DriveIntegrationService = Depends(get_drive_integration_service)
) -> Optional[DriveIntegrationResponse]:
    """Get current Google Drive integration status."""
    try:
        current_user, _ = current_user_tuple
        integration = await drive_service.get_integration(current_user.id)
        return integration
        
    except Exception as e:
        logger.error("Failed to get Drive integration", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve Google Drive integration")


@router.put("/drive/integration", response_model=DriveIntegrationResponse)
async def update_drive_integration_config(
    request: DriveConfigUpdateRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    drive_service: DriveIntegrationService = Depends(get_drive_integration_service)
) -> DriveIntegrationResponse:
    """Update Google Drive integration configuration."""
    try:
        current_user, _ = current_user_tuple
        integration = await drive_service.update_integration_config(current_user.id, request)
        return integration
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Failed to update Drive integration config", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update Google Drive integration")


@router.delete("/drive/integration")
async def delete_drive_integration(
    current_user_tuple: tuple = Depends(get_current_user),
    drive_service: DriveIntegrationService = Depends(get_drive_integration_service)
):
    """Delete/disable Google Drive integration."""
    try:
        current_user, _ = current_user_tuple
        await drive_service.delete_integration(current_user.id)
        return {"message": "Google Drive integration deleted successfully"}
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error("Failed to delete Drive integration", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete Google Drive integration")


@router.get("/drive/files")
async def list_drive_backup_files(
    current_user_tuple: tuple = Depends(get_current_user),
    drive_service: DriveIntegrationService = Depends(get_drive_integration_service)
):
    """List backup files in Google Drive."""
    try:
        current_user, _ = current_user_tuple
        files = await drive_service.list_backup_files(current_user.id)
        return {"files": files}
        
    except Exception as e:
        logger.error("Failed to list Drive backup files", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list Google Drive backup files")


# Admin/Maintenance Endpoints

@router.post("/cleanup")
async def cleanup_expired_backups(
    current_user_tuple: tuple = Depends(get_current_user),
    backup_service: BackupService = Depends(get_backup_service)
):
    """Clean up expired backup records and files (admin only)."""
    try:
        current_user, _ = current_user_tuple
        
        # Check if user is admin (this should be implemented in your auth system)
        # For now, we'll allow any authenticated user to trigger cleanup
        
        stats = await backup_service.cleanup_expired_backups()
        return {
            "message": "Cleanup completed",
            "statistics": stats
        }
        
    except Exception as e:
        logger.error("Failed to cleanup expired backups", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to cleanup expired backups")


# Scheduler Endpoints (Admin)

@router.post("/scheduler/trigger-check")
async def trigger_scheduled_backup_check(
    current_user_tuple: tuple = Depends(get_current_user),
    scheduler: BackupSchedulerEndpoint = Depends(get_backup_scheduler_endpoint)
):
    """Manually trigger scheduled backup check (admin only)."""
    try:
        current_user, _ = current_user_tuple
        
        # TODO: Add admin check
        
        stats = await scheduler.trigger_scheduled_backup_check()
        return {
            "message": "Scheduled backup check completed",
            "statistics": stats
        }
        
    except Exception as e:
        logger.error("Failed to trigger scheduled backup check", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to trigger scheduled backup check")


@router.get("/scheduler/status")
async def get_scheduler_status(
    current_user_tuple: tuple = Depends(get_current_user),
    scheduler: BackupSchedulerEndpoint = Depends(get_backup_scheduler_endpoint)
):
    """Get backup scheduler status (admin only)."""
    try:
        current_user, _ = current_user_tuple
        
        # TODO: Add admin check
        
        status = await scheduler.get_scheduler_status()
        return status
        
    except Exception as e:
        logger.error("Failed to get scheduler status", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get scheduler status")


@router.post("/scheduler/cleanup")
async def trigger_backup_cleanup(
    current_user_tuple: tuple = Depends(get_current_user),
    scheduler: BackupSchedulerEndpoint = Depends(get_backup_scheduler_endpoint)
):
    """Manually trigger backup cleanup (admin only)."""
    try:
        current_user, _ = current_user_tuple
        
        # TODO: Add admin check
        
        stats = await scheduler.cleanup_old_backups()
        return {
            "message": "Backup cleanup completed",
            "statistics": stats
        }
        
    except Exception as e:
        logger.error("Failed to trigger backup cleanup", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to trigger backup cleanup")