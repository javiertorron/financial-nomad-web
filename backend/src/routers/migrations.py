"""
Database Migration endpoints.
Handles automated database migrations, version management, and rollback operations.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, status, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional
from src.services.migration_service import (
    get_migration_service,
    MigrationStatus,
    MigrationType,
    MigrationDirection,
    create_example_migrations
)

logger = structlog.get_logger()
router = APIRouter()


class MigrationStatusResponse(BaseModel):
    """Migration status response."""
    total_migrations: int = Field(..., description="Total migrations available")
    applied_migrations: int = Field(..., description="Number of applied migrations")
    pending_migrations: int = Field(..., description="Number of pending migrations")
    recent_executions: int = Field(..., description="Recent executions in last 7 days")
    last_migration: Optional[str] = Field(None, description="Last applied migration ID")
    status: str = Field(..., description="Overall migration status")


class MigrationResponse(BaseModel):
    """Migration definition response."""
    id: str = Field(..., description="Migration ID")
    version: str = Field(..., description="Migration version")
    name: str = Field(..., description="Migration name")
    description: str = Field(..., description="Migration description")
    migration_type: str = Field(..., description="Migration type")
    author: str = Field(..., description="Migration author")
    created_at: str = Field(..., description="Creation timestamp")
    dependencies: List[str] = Field(..., description="Migration dependencies")
    requires_downtime: bool = Field(..., description="Whether migration requires downtime")
    estimated_duration_minutes: int = Field(..., description="Estimated duration in minutes")
    dry_run_supported: bool = Field(..., description="Whether dry run is supported")


class MigrationExecutionResponse(BaseModel):
    """Migration execution response."""
    id: str = Field(..., description="Execution ID")
    migration_id: str = Field(..., description="Migration ID")
    migration_version: str = Field(..., description="Migration version")
    direction: str = Field(..., description="Migration direction")
    status: str = Field(..., description="Execution status")
    started_at: str = Field(..., description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds")
    steps_completed: int = Field(..., description="Number of steps completed")
    total_steps: int = Field(..., description="Total number of steps")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    dry_run: bool = Field(..., description="Whether this was a dry run")


class RunMigrationsRequest(BaseModel):
    """Run migrations request."""
    target_version: Optional[str] = Field(None, description="Target version to migrate to")
    dry_run: bool = Field(default=False, description="Whether to perform dry run")
    force: bool = Field(default=False, description="Force migration even with warnings")


class CreateMigrationRequest(BaseModel):
    """Create migration request."""
    name: str = Field(..., min_length=1, max_length=100, description="Migration name")
    description: str = Field(..., min_length=1, description="Migration description")
    migration_type: str = Field(..., description="Migration type")
    author: str = Field(..., description="Migration author")
    
    @validator('migration_type')
    def validate_migration_type(cls, v):
        valid_types = [t.value for t in MigrationType]
        if v not in valid_types:
            raise ValueError(f'Invalid migration type. Valid options: {valid_types}')
        return v


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Get Migration Status",
    description="Returns current migration system status and statistics",
    response_model=MigrationStatusResponse,
    tags=["Migrations"]
)
async def get_migration_status(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> MigrationStatusResponse:
    """
    **Get migration status**
    
    Returns comprehensive migration system status:
    - Total, applied, and pending migration counts
    - Recent execution activity
    - Overall system migration state
    - Last applied migration information
    
    Essential for understanding database schema state.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for migration status
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        migration_service = get_migration_service()
        status_info = migration_service.get_migration_status()
        
        logger.info("Migration status retrieved",
                   requester=current_user.get('id'))
        
        return MigrationStatusResponse(**status_info)
        
    except Exception as e:
        logger.error("Failed to get migration status",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve migration status"
        )


@router.get(
    "/list",
    status_code=status.HTTP_200_OK,
    summary="List Migrations",
    description="Returns list of available migrations with details",
    response_model=List[MigrationResponse],
    tags=["Migrations"]
)
async def list_migrations(
    migration_type: Optional[str] = Query(None, description="Filter by migration type"),
    status_filter: str = Query(default="all", description="Filter by status (pending, applied, all)"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[MigrationResponse]:
    """
    **List migrations**
    
    Returns detailed list of database migrations:
    - Complete migration definitions and metadata
    - Dependency information and requirements
    - Execution status and history
    - Filtering by type and application status
    
    Useful for migration planning and review.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for migration listing
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        migration_service = get_migration_service()
        
        # Initialize with example migrations if none exist
        if not migration_service.registry.migrations:
            example_migrations = create_example_migrations()
            for migration in example_migrations:
                migration_service.registry.register_migration(migration)
        
        migrations = list(migration_service.registry.migrations.values())
        
        # Apply filters
        if migration_type:
            try:
                filter_type = MigrationType(migration_type)
                migrations = [m for m in migrations if m.migration_type == filter_type]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid migration type: {migration_type}"
                )
        
        if status_filter == "pending":
            migrations = [m for m in migrations if m.id not in migration_service.registry.applied_migrations]
        elif status_filter == "applied":
            migrations = [m for m in migrations if m.id in migration_service.registry.applied_migrations]
        
        # Convert to response format
        result = []
        for migration in migrations:
            result.append(MigrationResponse(
                id=migration.id,
                version=migration.version,
                name=migration.name,
                description=migration.description,
                migration_type=migration.migration_type.value,
                author=migration.author,
                created_at=migration.created_at.isoformat() + "Z",
                dependencies=migration.dependencies,
                requires_downtime=migration.requires_downtime,
                estimated_duration_minutes=migration.estimated_duration_minutes,
                dry_run_supported=migration.dry_run_supported
            ))
        
        # Sort by version
        result.sort(key=lambda m: m.version)
        
        logger.info("Migrations listed",
                   requester=current_user.get('id'),
                   total_count=len(result),
                   filter_type=migration_type,
                   status_filter=status_filter)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list migrations",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list migrations"
        )


@router.get(
    "/{migration_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Migration Details",
    description="Returns detailed information about a specific migration",
    response_model=MigrationResponse,
    tags=["Migrations"]
)
async def get_migration_details(
    migration_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> MigrationResponse:
    """
    **Get migration details**
    
    Returns comprehensive information about a specific migration:
    - Complete migration configuration
    - Step-by-step execution plan
    - Dependencies and requirements
    - Execution history and status
    
    Essential for migration review and planning.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for migration details
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        migration_service = get_migration_service()
        migration = migration_service.registry.get_migration(migration_id)
        
        if not migration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Migration not found"
            )
        
        logger.info("Migration details retrieved",
                   migration_id=migration_id,
                   requester=current_user.get('id'))
        
        return MigrationResponse(
            id=migration.id,
            version=migration.version,
            name=migration.name,
            description=migration.description,
            migration_type=migration.migration_type.value,
            author=migration.author,
            created_at=migration.created_at.isoformat() + "Z",
            dependencies=migration.dependencies,
            requires_downtime=migration.requires_downtime,
            estimated_duration_minutes=migration.estimated_duration_minutes,
            dry_run_supported=migration.dry_run_supported
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get migration details",
                    migration_id=migration_id,
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve migration details"
        )


@router.post(
    "/run",
    status_code=status.HTTP_200_OK,
    summary="Run Migrations",
    description="Executes pending migrations with optional target version",
    response_model=List[MigrationExecutionResponse],
    tags=["Migrations"]
)
async def run_migrations(
    request: RunMigrationsRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[MigrationExecutionResponse]:
    """
    **Run migrations**
    
    Executes database migrations with comprehensive monitoring:
    - Automatic dependency resolution
    - Step-by-step execution tracking
    - Rollback capabilities on failure
    - Dry run support for testing
    - Target version control
    
    Critical operation requiring careful planning and monitoring.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for migration execution
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        migration_service = get_migration_service()
        
        # Initialize with example migrations if none exist
        if not migration_service.registry.migrations:
            example_migrations = create_example_migrations()
            for migration in example_migrations:
                migration_service.registry.register_migration(migration)
        
        # Run migrations
        executions = await migration_service.run_migrations(
            target_version=request.target_version,
            dry_run=request.dry_run,
            executed_by=current_user.get('id')
        )
        
        # Convert to response format
        result = []
        for execution in executions:
            result.append(MigrationExecutionResponse(
                id=execution.id,
                migration_id=execution.migration_id,
                migration_version=execution.migration_version,
                direction=execution.direction.value,
                status=execution.status.value,
                started_at=execution.started_at.isoformat() + "Z",
                completed_at=execution.completed_at.isoformat() + "Z" if execution.completed_at else None,
                duration_seconds=execution.duration_seconds,
                steps_completed=execution.steps_completed,
                total_steps=execution.total_steps,
                error_message=execution.error_message,
                dry_run=execution.dry_run
            ))
        
        logger.info("Migrations executed",
                   requester=current_user.get('id'),
                   target_version=request.target_version,
                   dry_run=request.dry_run,
                   executions_count=len(executions))
        
        return result
        
    except Exception as e:
        logger.error("Failed to run migrations",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run migrations: {str(e)}"
        )


@router.post(
    "/{migration_id}/rollback",
    status_code=status.HTTP_200_OK,
    summary="Rollback Migration",
    description="Rolls back a specific applied migration",
    response_model=MigrationExecutionResponse,
    tags=["Migrations"]
)
async def rollback_migration(
    migration_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> MigrationExecutionResponse:
    """
    **Rollback migration**
    
    Reverses a previously applied migration:
    - Executes rollback steps in reverse order
    - Validates rollback safety and dependencies
    - Comprehensive logging and monitoring
    - Data integrity verification
    
    Use with extreme caution as rollbacks can cause data loss.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for migration rollback
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        migration_service = get_migration_service()
        
        # Execute rollback
        execution = await migration_service.rollback_migration(
            migration_id,
            executed_by=current_user.get('id')
        )
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Migration not found or not applied"
            )
        
        logger.info("Migration rollback executed",
                   migration_id=migration_id,
                   requester=current_user.get('id'),
                   status=execution.status.value)
        
        return MigrationExecutionResponse(
            id=execution.id,
            migration_id=execution.migration_id,
            migration_version=execution.migration_version,
            direction=execution.direction.value,
            status=execution.status.value,
            started_at=execution.started_at.isoformat() + "Z",
            completed_at=execution.completed_at.isoformat() + "Z" if execution.completed_at else None,
            duration_seconds=execution.duration_seconds,
            steps_completed=execution.steps_completed,
            total_steps=execution.total_steps,
            error_message=execution.error_message,
            dry_run=execution.dry_run
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to rollback migration",
                    migration_id=migration_id,
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rollback migration: {str(e)}"
        )


@router.get(
    "/executions",
    status_code=status.HTTP_200_OK,
    summary="List Migration Executions",
    description="Returns history of migration executions",
    response_model=List[MigrationExecutionResponse],
    tags=["Migrations"]
)
async def list_migration_executions(
    limit: int = Query(default=50, ge=1, le=500, description="Maximum executions to return"),
    status_filter: Optional[str] = Query(None, description="Filter by execution status"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[MigrationExecutionResponse]:
    """
    **List migration executions**
    
    Returns history of migration execution attempts:
    - Chronological execution history
    - Success/failure status and details
    - Performance metrics and timing
    - Error messages and troubleshooting info
    
    Essential for migration monitoring and troubleshooting.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for execution history
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        migration_service = get_migration_service()
        executions = list(migration_service.registry.executions.values())
        
        # Apply status filter
        if status_filter:
            try:
                filter_status = MigrationStatus(status_filter)
                executions = [e for e in executions if e.status == filter_status]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}"
                )
        
        # Sort by start time (newest first)
        executions.sort(key=lambda e: e.started_at, reverse=True)
        
        # Apply limit
        executions = executions[:limit]
        
        # Convert to response format
        result = []
        for execution in executions:
            result.append(MigrationExecutionResponse(
                id=execution.id,
                migration_id=execution.migration_id,
                migration_version=execution.migration_version,
                direction=execution.direction.value,
                status=execution.status.value,
                started_at=execution.started_at.isoformat() + "Z",
                completed_at=execution.completed_at.isoformat() + "Z" if execution.completed_at else None,
                duration_seconds=execution.duration_seconds,
                steps_completed=execution.steps_completed,
                total_steps=execution.total_steps,
                error_message=execution.error_message,
                dry_run=execution.dry_run
            ))
        
        logger.info("Migration executions listed",
                   requester=current_user.get('id'),
                   count=len(result),
                   status_filter=status_filter)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list migration executions",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list migration executions"
        )


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    summary="Create Migration Template",
    description="Creates a new migration template for development",
    response_model=MigrationResponse,
    tags=["Migrations"]
)
async def create_migration(
    request: CreateMigrationRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> MigrationResponse:
    """
    **Create migration template**
    
    Creates a new migration template for development:
    - Generates unique migration ID and version
    - Sets up basic migration structure
    - Includes metadata and configuration
    - Ready for step implementation
    
    Useful for developers creating new database changes.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for migration creation
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        migration_service = get_migration_service()
        
        # Create migration template
        migration = migration_service.create_migration_template(
            name=request.name,
            migration_type=MigrationType(request.migration_type),
            author=request.author,
            description=request.description
        )
        
        # Register the template
        migration_service.registry.register_migration(migration)
        
        logger.info("Migration template created",
                   migration_id=migration.id,
                   name=request.name,
                   author=request.author,
                   created_by=current_user.get('id'))
        
        return MigrationResponse(
            id=migration.id,
            version=migration.version,
            name=migration.name,
            description=migration.description,
            migration_type=migration.migration_type.value,
            author=migration.author,
            created_at=migration.created_at.isoformat() + "Z",
            dependencies=migration.dependencies,
            requires_downtime=migration.requires_downtime,
            estimated_duration_minutes=migration.estimated_duration_minutes,
            dry_run_supported=migration.dry_run_supported
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to create migration",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create migration: {str(e)}"
        )