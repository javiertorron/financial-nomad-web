"""
Automated Data Migration Service.
Handles database schema migrations, data transformations, and version management
with rollback capabilities and comprehensive validation.
"""

import asyncio
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import structlog

from src.config import settings

logger = structlog.get_logger()


class MigrationStatus(Enum):
    """Migration execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class MigrationDirection(Enum):
    """Migration direction."""
    UP = "up"
    DOWN = "down"


class MigrationType(Enum):
    """Types of migrations."""
    SCHEMA = "schema"              # Database schema changes
    DATA = "data"                  # Data transformations
    INDEX = "index"                # Index management
    CLEANUP = "cleanup"            # Data cleanup operations
    PERFORMANCE = "performance"    # Performance optimizations
    SECURITY = "security"          # Security-related changes
    FEATURE = "feature"            # Feature-specific migrations


@dataclass
class MigrationStep:
    """Individual migration step."""
    name: str
    description: str
    operation: Callable
    rollback_operation: Optional[Callable] = None
    validation: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    critical: bool = False  # If True, failure stops entire migration
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Migration:
    """Migration definition."""
    id: str
    version: str
    name: str
    description: str
    migration_type: MigrationType
    author: str
    created_at: datetime
    
    # Execution steps
    up_steps: List[MigrationStep] = field(default_factory=list)
    down_steps: List[MigrationStep] = field(default_factory=list)
    
    # Requirements and dependencies
    dependencies: List[str] = field(default_factory=list)
    required_version: Optional[str] = None
    target_version: str = "latest"
    
    # Validation and safety
    pre_conditions: List[Callable] = field(default_factory=list)
    post_conditions: List[Callable] = field(default_factory=list)
    dry_run_supported: bool = True
    requires_downtime: bool = False
    estimated_duration_minutes: int = 5
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    changelog: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationExecution:
    """Migration execution record."""
    id: str
    migration_id: str
    migration_version: str
    direction: MigrationDirection
    status: MigrationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    executed_by: Optional[str] = None
    
    # Results and logs
    steps_completed: int = 0
    total_steps: int = 0
    error_message: Optional[str] = None
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    rollback_available: bool = True
    
    # Validation results
    pre_validation_passed: bool = False
    post_validation_passed: bool = False
    
    # Metadata
    environment: str = "production"
    dry_run: bool = False
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)


class MigrationValidator:
    """Validates migration safety and requirements."""
    
    def __init__(self):
        pass
    
    async def validate_pre_conditions(self, migration: Migration) -> List[str]:
        """Validate pre-conditions before migration."""
        errors = []
        
        for condition in migration.pre_conditions:
            try:
                if asyncio.iscoroutinefunction(condition):
                    result = await condition()
                else:
                    result = condition()
                
                if not result:
                    errors.append(f"Pre-condition failed: {condition.__name__}")
                    
            except Exception as e:
                errors.append(f"Pre-condition error in {condition.__name__}: {str(e)}")
        
        return errors
    
    async def validate_post_conditions(self, migration: Migration) -> List[str]:
        """Validate post-conditions after migration."""
        errors = []
        
        for condition in migration.post_conditions:
            try:
                if asyncio.iscoroutinefunction(condition):
                    result = await condition()
                else:
                    result = condition()
                
                if not result:
                    errors.append(f"Post-condition failed: {condition.__name__}")
                    
            except Exception as e:
                errors.append(f"Post-condition error in {condition.__name__}: {str(e)}")
        
        return errors
    
    def validate_dependencies(self, migration: Migration, 
                            applied_migrations: List[str]) -> List[str]:
        """Validate migration dependencies."""
        errors = []
        
        for dependency in migration.dependencies:
            if dependency not in applied_migrations:
                errors.append(f"Missing dependency: {dependency}")
        
        return errors
    
    def validate_migration_structure(self, migration: Migration) -> List[str]:
        """Validate migration structure and configuration."""
        errors = []
        
        if not migration.id:
            errors.append("Migration ID is required")
        
        if not migration.version:
            errors.append("Migration version is required")
        
        if not migration.name:
            errors.append("Migration name is required")
        
        if not migration.up_steps:
            errors.append("Migration must have at least one up step")
        
        # Validate version format
        if migration.version and not self._is_valid_version(migration.version):
            errors.append("Invalid version format")
        
        return errors
    
    def _is_valid_version(self, version: str) -> bool:
        """Validate version format (semantic versioning)."""
        try:
            parts = version.split('.')
            if len(parts) != 3:
                return False
            
            for part in parts:
                int(part)  # Must be numeric
            
            return True
        except (ValueError, AttributeError):
            return False


class MigrationExecutor:
    """Executes migration steps with monitoring and recovery."""
    
    def __init__(self):
        self.validator = MigrationValidator()
    
    async def execute_migration(self, migration: Migration, 
                              direction: MigrationDirection = MigrationDirection.UP,
                              dry_run: bool = False,
                              executed_by: Optional[str] = None) -> MigrationExecution:
        """Execute migration with comprehensive monitoring."""
        
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        steps = migration.up_steps if direction == MigrationDirection.UP else migration.down_steps
        
        execution = MigrationExecution(
            id=execution_id,
            migration_id=migration.id,
            migration_version=migration.version,
            direction=direction,
            status=MigrationStatus.PENDING,
            started_at=datetime.utcnow(),
            total_steps=len(steps),
            executed_by=executed_by,
            dry_run=dry_run,
            environment=getattr(settings, 'environment', 'production')
        )
        
        logger.info("Migration execution started",
                   migration_id=migration.id,
                   execution_id=execution_id,
                   direction=direction.value,
                   dry_run=dry_run)
        
        try:
            # Validate pre-conditions
            execution.status = MigrationStatus.RUNNING
            
            if direction == MigrationDirection.UP:
                pre_errors = await self.validator.validate_pre_conditions(migration)
                if pre_errors:
                    execution.status = MigrationStatus.FAILED
                    execution.error_message = f"Pre-condition validation failed: {'; '.join(pre_errors)}"
                    return execution
                
                execution.pre_validation_passed = True
            
            # Execute steps
            for i, step in enumerate(steps):
                step_start = datetime.utcnow()
                
                try:
                    logger.info("Executing migration step",
                               migration_id=migration.id,
                               step_name=step.name,
                               step_index=i + 1,
                               dry_run=dry_run)
                    
                    if dry_run and hasattr(step.operation, 'dry_run'):
                        # Execute dry run if supported
                        await step.operation(dry_run=True)
                    elif not dry_run:
                        # Execute actual operation
                        if asyncio.iscoroutinefunction(step.operation):
                            await asyncio.wait_for(step.operation(), timeout=step.timeout_seconds)
                        else:
                            await asyncio.wait_for(
                                asyncio.to_thread(step.operation), 
                                timeout=step.timeout_seconds
                            )
                    
                    # Validate step if validation function provided
                    if step.validation and not dry_run:
                        if asyncio.iscoroutinefunction(step.validation):
                            validation_result = await step.validation()
                        else:
                            validation_result = step.validation()
                        
                        if not validation_result:
                            raise Exception(f"Step validation failed: {step.name}")
                    
                    execution.steps_completed += 1
                    step_duration = (datetime.utcnow() - step_start).total_seconds()
                    
                    execution.execution_log.append({
                        "step_name": step.name,
                        "step_index": i + 1,
                        "status": "completed",
                        "duration_seconds": step_duration,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                except asyncio.TimeoutError:
                    error_msg = f"Step '{step.name}' timed out after {step.timeout_seconds} seconds"
                    execution.execution_log.append({
                        "step_name": step.name,
                        "step_index": i + 1,
                        "status": "timeout",
                        "error": error_msg,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    if step.critical:
                        execution.status = MigrationStatus.FAILED
                        execution.error_message = error_msg
                        return execution
                    else:
                        logger.warning("Non-critical step timed out, continuing",
                                     step_name=step.name)
                        continue
                
                except Exception as e:
                    error_msg = f"Step '{step.name}' failed: {str(e)}"
                    execution.execution_log.append({
                        "step_name": step.name,
                        "step_index": i + 1,
                        "status": "failed",
                        "error": error_msg,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    if step.critical:
                        execution.status = MigrationStatus.FAILED
                        execution.error_message = error_msg
                        return execution
                    else:
                        logger.warning("Non-critical step failed, continuing",
                                     step_name=step.name, error=str(e))
                        continue
            
            # Validate post-conditions for UP migrations
            if direction == MigrationDirection.UP and not dry_run:
                post_errors = await self.validator.validate_post_conditions(migration)
                if post_errors:
                    execution.status = MigrationStatus.FAILED
                    execution.error_message = f"Post-condition validation failed: {'; '.join(post_errors)}"
                    return execution
                
                execution.post_validation_passed = True
            
            # Mark as completed
            execution.status = MigrationStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = int(
                (execution.completed_at - execution.started_at).total_seconds()
            )
            
            logger.info("Migration execution completed successfully",
                       migration_id=migration.id,
                       execution_id=execution_id,
                       duration_seconds=execution.duration_seconds)
            
        except Exception as e:
            execution.status = MigrationStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = int(
                (execution.completed_at - execution.started_at).total_seconds()
            )
            
            logger.error("Migration execution failed",
                        migration_id=migration.id,
                        execution_id=execution_id,
                        error=str(e))
        
        return execution
    
    async def rollback_migration(self, migration: Migration, 
                               executed_by: Optional[str] = None) -> MigrationExecution:
        """Rollback a migration using down steps."""
        if not migration.down_steps:
            raise ValueError("Migration does not support rollback (no down steps defined)")
        
        return await self.execute_migration(
            migration, 
            direction=MigrationDirection.DOWN,
            dry_run=False,
            executed_by=executed_by
        )


class MigrationRegistry:
    """Registry for managing migrations."""
    
    def __init__(self):
        self.migrations: Dict[str, Migration] = {}
        self.executions: Dict[str, MigrationExecution] = {}
        self.applied_migrations: List[str] = []
    
    def register_migration(self, migration: Migration):
        """Register a migration."""
        validator = MigrationValidator()
        errors = validator.validate_migration_structure(migration)
        
        if errors:
            raise ValueError(f"Invalid migration: {'; '.join(errors)}")
        
        self.migrations[migration.id] = migration
        logger.info("Migration registered", migration_id=migration.id, version=migration.version)
    
    def get_migration(self, migration_id: str) -> Optional[Migration]:
        """Get migration by ID."""
        return self.migrations.get(migration_id)
    
    def get_migrations_by_type(self, migration_type: MigrationType) -> List[Migration]:
        """Get migrations by type."""
        return [m for m in self.migrations.values() if m.migration_type == migration_type]
    
    def get_pending_migrations(self) -> List[Migration]:
        """Get migrations that haven't been applied."""
        return [
            migration for migration in self.migrations.values()
            if migration.id not in self.applied_migrations
        ]
    
    def get_migration_plan(self, target_version: Optional[str] = None) -> List[Migration]:
        """Get ordered list of migrations to execute."""
        pending = self.get_pending_migrations()
        
        if target_version:
            # Filter migrations up to target version
            pending = [
                m for m in pending 
                if self._compare_versions(m.version, target_version) <= 0
            ]
        
        # Sort by version
        pending.sort(key=lambda m: m.version)
        
        # Resolve dependencies
        return self._resolve_dependencies(pending)
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two semantic versions."""
        def version_tuple(v):
            return tuple(map(int, v.split('.')))
        
        v1_tuple = version_tuple(version1)
        v2_tuple = version_tuple(version2)
        
        if v1_tuple < v2_tuple:
            return -1
        elif v1_tuple > v2_tuple:
            return 1
        else:
            return 0
    
    def _resolve_dependencies(self, migrations: List[Migration]) -> List[Migration]:
        """Resolve migration dependencies and return ordered list."""
        resolved = []
        unresolved = migrations.copy()
        
        while unresolved:
            # Find migration with all dependencies satisfied
            for migration in unresolved[:]:
                dependencies_satisfied = all(
                    dep in [m.id for m in resolved] or dep in self.applied_migrations
                    for dep in migration.dependencies
                )
                
                if dependencies_satisfied:
                    resolved.append(migration)
                    unresolved.remove(migration)
                    break
            else:
                # Circular dependency or missing dependency
                remaining_ids = [m.id for m in unresolved]
                raise ValueError(f"Cannot resolve dependencies for migrations: {remaining_ids}")
        
        return resolved
    
    def mark_applied(self, migration_id: str):
        """Mark migration as applied."""
        if migration_id not in self.applied_migrations:
            self.applied_migrations.append(migration_id)
    
    def mark_rolled_back(self, migration_id: str):
        """Mark migration as rolled back."""
        if migration_id in self.applied_migrations:
            self.applied_migrations.remove(migration_id)


class MigrationService:
    """Main migration service."""
    
    def __init__(self):
        self.registry = MigrationRegistry()
        self.executor = MigrationExecutor()
        self.validator = MigrationValidator()
        
        logger.info("Migration service initialized")
    
    async def run_migrations(self, target_version: Optional[str] = None,
                           dry_run: bool = False,
                           executed_by: Optional[str] = None) -> List[MigrationExecution]:
        """Run all pending migrations up to target version."""
        
        migration_plan = self.registry.get_migration_plan(target_version)
        
        if not migration_plan:
            logger.info("No migrations to run")
            return []
        
        logger.info("Migration plan created",
                   migrations_count=len(migration_plan),
                   target_version=target_version,
                   dry_run=dry_run)
        
        executions = []
        
        for migration in migration_plan:
            try:
                # Validate dependencies
                dep_errors = self.validator.validate_dependencies(
                    migration, self.registry.applied_migrations
                )
                
                if dep_errors:
                    logger.error("Migration dependency validation failed",
                               migration_id=migration.id,
                               errors=dep_errors)
                    continue
                
                # Execute migration
                execution = await self.executor.execute_migration(
                    migration, 
                    MigrationDirection.UP, 
                    dry_run, 
                    executed_by
                )
                
                executions.append(execution)
                
                # Mark as applied if successful and not dry run
                if execution.status == MigrationStatus.COMPLETED and not dry_run:
                    self.registry.mark_applied(migration.id)
                    self.registry.executions[execution.id] = execution
                
                # Stop on critical failure
                elif execution.status == MigrationStatus.FAILED:
                    logger.error("Migration failed, stopping execution",
                               migration_id=migration.id,
                               error=execution.error_message)
                    break
                    
            except Exception as e:
                logger.error("Unexpected error during migration",
                           migration_id=migration.id,
                           error=str(e))
                break
        
        logger.info("Migration batch completed",
                   total_migrations=len(migration_plan),
                   executed_migrations=len(executions),
                   successful_migrations=len([e for e in executions if e.status == MigrationStatus.COMPLETED]))
        
        return executions
    
    async def rollback_migration(self, migration_id: str,
                               executed_by: Optional[str] = None) -> Optional[MigrationExecution]:
        """Rollback a specific migration."""
        
        migration = self.registry.get_migration(migration_id)
        if not migration:
            raise ValueError(f"Migration not found: {migration_id}")
        
        if migration_id not in self.registry.applied_migrations:
            raise ValueError(f"Migration not applied: {migration_id}")
        
        execution = await self.executor.rollback_migration(migration, executed_by)
        
        if execution.status == MigrationStatus.COMPLETED:
            self.registry.mark_rolled_back(migration_id)
            self.registry.executions[execution.id] = execution
        
        return execution
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get overall migration status."""
        total_migrations = len(self.registry.migrations)
        applied_migrations = len(self.registry.applied_migrations)
        pending_migrations = len(self.registry.get_pending_migrations())
        
        recent_executions = [
            e for e in self.registry.executions.values()
            if e.started_at > datetime.utcnow() - timedelta(days=7)
        ]
        
        return {
            "total_migrations": total_migrations,
            "applied_migrations": applied_migrations,
            "pending_migrations": pending_migrations,
            "recent_executions": len(recent_executions),
            "last_migration": max(
                self.registry.applied_migrations, 
                key=lambda mid: self.registry.migrations[mid].version,
                default=None
            ),
            "status": "up_to_date" if pending_migrations == 0 else "pending_migrations"
        }
    
    def create_migration_template(self, name: str, migration_type: MigrationType,
                                author: str, description: str = "") -> Migration:
        """Create migration template."""
        
        # Generate version based on current time
        now = datetime.utcnow()
        version = f"{now.year}.{now.month:02d}.{now.day:02d}"
        
        # Generate unique ID
        migration_id = f"{migration_type.value}_{name.lower().replace(' ', '_')}_{int(now.timestamp())}"
        
        migration = Migration(
            id=migration_id,
            version=version,
            name=name,
            description=description,
            migration_type=migration_type,
            author=author,
            created_at=now
        )
        
        return migration


# Global migration service
_migration_service = None


def get_migration_service() -> MigrationService:
    """Get global migration service."""
    global _migration_service
    if _migration_service is None:
        _migration_service = MigrationService()
    return _migration_service


# Example migrations
def create_example_migrations() -> List[Migration]:
    """Create example migrations for demonstration."""
    
    # Schema migration example
    async def add_user_preferences_field():
        """Add preferences field to users table."""
        logger.info("Adding user preferences field")
        # In real implementation: ALTER TABLE users ADD COLUMN preferences JSONB
    
    def rollback_user_preferences_field():
        """Remove preferences field from users table."""
        logger.info("Removing user preferences field")
        # In real implementation: ALTER TABLE users DROP COLUMN preferences
    
    schema_migration = Migration(
        id="schema_add_user_preferences_001",
        version="1.2.0",
        name="Add User Preferences Field",
        description="Add JSONB preferences field to users table",
        migration_type=MigrationType.SCHEMA,
        author="system",
        created_at=datetime.utcnow(),
        up_steps=[
            MigrationStep(
                name="add_preferences_field",
                description="Add preferences JSONB field",
                operation=add_user_preferences_field,
                rollback_operation=rollback_user_preferences_field,
                critical=True
            )
        ],
        down_steps=[
            MigrationStep(
                name="remove_preferences_field",
                description="Remove preferences field",
                operation=rollback_user_preferences_field,
                critical=True
            )
        ]
    )
    
    # Data migration example
    async def migrate_legacy_categories():
        """Migrate legacy category format to new structure."""
        logger.info("Migrating legacy categories")
        # In real implementation: complex data transformation
    
    data_migration = Migration(
        id="data_migrate_categories_001",
        version="1.2.1",
        name="Migrate Legacy Categories",
        description="Convert legacy category format to new hierarchical structure",
        migration_type=MigrationType.DATA,
        author="system",
        created_at=datetime.utcnow(),
        dependencies=["schema_add_user_preferences_001"],
        up_steps=[
            MigrationStep(
                name="migrate_categories",
                description="Transform legacy category data",
                operation=migrate_legacy_categories,
                critical=True,
                timeout_seconds=600
            )
        ],
        estimated_duration_minutes=10
    )
    
    return [schema_migration, data_migration]