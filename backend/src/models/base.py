"""
Base models for all Pydantic models in the application.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TimestampedModel(BaseModel):
    """Base model with automatic timestamps."""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class IdentifiedModel(TimestampedModel):
    """Base model with UUID identification and timestamps."""
    
    id: UUID = Field(default_factory=uuid4)


class SoftDeleteModel(IdentifiedModel):
    """Base model with soft delete capability."""
    
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)
    
    def soft_delete(self) -> None:
        """Mark the model as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.update_timestamp()
    
    def restore(self) -> None:
        """Restore a soft-deleted model."""
        self.is_deleted = False
        self.deleted_at = None
        self.update_timestamp()


class UserOwnedModel(SoftDeleteModel):
    """Base model for entities owned by a user."""
    
    user_id: str = Field(..., description="Google user ID who owns this entity")