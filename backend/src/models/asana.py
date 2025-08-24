"""
Asana integration models and DTOs.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from .base import UserOwnedModel


class AsanaTaskStatus(str, Enum):
    """Status of Asana tasks."""
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"


class AsanaProjectStatus(str, Enum):
    """Status of Asana projects."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class AsanaIntegrationStatus(str, Enum):
    """Status of Asana integration for a user."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    ERROR = "error"


class AsanaWebhookEvent(str, Enum):
    """Types of Asana webhook events."""
    ADDED = "added"
    REMOVED = "removed" 
    CHANGED = "changed"
    UNDELETED = "undeleted"
    DELETED = "deleted"


class AsanaTaskMapping(UserOwnedModel):
    """Mapping between Financial Nomad entities and Asana tasks."""
    
    # Asana task information
    asana_task_id: str = Field(..., description="Asana task GID")
    asana_task_name: str = Field(..., description="Asana task name")
    asana_project_id: Optional[str] = Field(None, description="Asana project GID")
    asana_project_name: Optional[str] = Field(None, description="Asana project name")
    
    # Financial Nomad entity mapping
    entity_type: str = Field(..., description="Type of entity (transaction, budget, recurring_transaction)")
    entity_id: str = Field(..., description="ID of the mapped entity")
    entity_name: str = Field(..., description="Name/description of the mapped entity")
    
    # Task status and metadata
    task_status: AsanaTaskStatus = Field(default=AsanaTaskStatus.INCOMPLETE)
    due_date: Optional[datetime] = Field(None, description="Task due date")
    completed_date: Optional[datetime] = Field(None, description="Task completion date")
    assignee_id: Optional[str] = Field(None, description="Asana user GID of assignee")
    
    # Integration metadata
    sync_notes: Optional[str] = Field(None, max_length=1000, description="Integration sync notes")
    last_synced: Optional[datetime] = Field(None, description="Last synchronization timestamp")
    
    # Task custom fields (for financial data)
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Asana custom fields")


class AsanaIntegration(UserOwnedModel):
    """User's Asana integration configuration."""
    
    # OAuth tokens
    access_token: str = Field(..., description="Encrypted Asana access token")
    refresh_token: Optional[str] = Field(None, description="Encrypted Asana refresh token")
    token_expires_at: Optional[datetime] = Field(None, description="Access token expiration")
    
    # User information
    asana_user_id: str = Field(..., description="Asana user GID")
    asana_user_email: str = Field(..., description="Asana user email")
    asana_user_name: str = Field(..., description="Asana user name")
    
    # Integration configuration
    status: AsanaIntegrationStatus = Field(default=AsanaIntegrationStatus.ACTIVE)
    default_workspace_id: Optional[str] = Field(None, description="Default Asana workspace GID")
    default_workspace_name: Optional[str] = Field(None, description="Default Asana workspace name")
    
    # Sync configuration
    auto_sync_enabled: bool = Field(default=True, description="Enable automatic synchronization")
    sync_transactions: bool = Field(default=True, description="Sync transaction-related tasks")
    sync_budgets: bool = Field(default=True, description="Sync budget-related tasks")
    sync_recurring: bool = Field(default=False, description="Sync recurring transaction tasks")
    
    # Project mappings
    transaction_project_id: Optional[str] = Field(None, description="Asana project for transaction tasks")
    budget_project_id: Optional[str] = Field(None, description="Asana project for budget tasks")
    recurring_project_id: Optional[str] = Field(None, description="Asana project for recurring tasks")
    
    # Webhook configuration
    webhook_id: Optional[str] = Field(None, description="Asana webhook GID")
    webhook_secret: Optional[str] = Field(None, description="Webhook verification secret")
    
    # Sync metadata
    last_full_sync: Optional[datetime] = Field(None, description="Last full synchronization")
    last_webhook_sync: Optional[datetime] = Field(None, description="Last webhook synchronization")
    sync_error_count: int = Field(default=0, description="Count of consecutive sync errors")
    last_sync_error: Optional[str] = Field(None, max_length=500, description="Last sync error message")


class AsanaWebhookPayload(BaseModel):
    """Asana webhook payload structure."""
    
    events: List[Dict[str, Any]] = Field(..., description="List of webhook events")


class AsanaWebhookEvent(BaseModel):
    """Individual Asana webhook event."""
    
    user: Dict[str, Any] = Field(..., description="User who triggered the event")
    created_at: datetime = Field(..., description="Event creation timestamp")
    type: str = Field(..., description="Event type")
    action: str = Field(..., description="Event action")
    resource: Dict[str, Any] = Field(..., description="Resource that changed")
    parent: Optional[Dict[str, Any]] = Field(None, description="Parent resource if applicable")


# DTOs for API requests and responses

class AsanaOAuthCallbackRequest(BaseModel):
    """Request for Asana OAuth callback."""
    code: str = Field(..., description="OAuth authorization code")
    state: Optional[str] = Field(None, description="OAuth state parameter")


class AsanaIntegrationResponse(BaseModel):
    """Response for Asana integration status."""
    id: str
    user_id: str
    status: AsanaIntegrationStatus
    asana_user_email: str
    asana_user_name: str
    default_workspace_name: Optional[str]
    auto_sync_enabled: bool
    sync_transactions: bool
    sync_budgets: bool
    sync_recurring: bool
    last_full_sync: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AsanaIntegrationConfigRequest(BaseModel):
    """Request to update Asana integration configuration."""
    auto_sync_enabled: Optional[bool] = None
    sync_transactions: Optional[bool] = None
    sync_budgets: Optional[bool] = None
    sync_recurring: Optional[bool] = None
    default_workspace_id: Optional[str] = None
    transaction_project_id: Optional[str] = None
    budget_project_id: Optional[str] = None
    recurring_project_id: Optional[str] = None


class AsanaTaskMappingResponse(BaseModel):
    """Response for Asana task mapping."""
    id: str
    asana_task_id: str
    asana_task_name: str
    asana_project_name: Optional[str]
    entity_type: str
    entity_id: str
    entity_name: str
    task_status: AsanaTaskStatus
    due_date: Optional[datetime]
    completed_date: Optional[datetime]
    last_synced: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AsanaTaskMappingCreateRequest(BaseModel):
    """Request to create Asana task mapping."""
    entity_type: str = Field(..., description="Type of entity to map")
    entity_id: str = Field(..., description="ID of entity to map")
    asana_project_id: Optional[str] = Field(None, description="Target Asana project")
    task_name: Optional[str] = Field(None, description="Custom task name")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    assignee_id: Optional[str] = Field(None, description="Task assignee")
    notes: Optional[str] = Field(None, description="Task notes")


class AsanaSyncRequest(BaseModel):
    """Request for manual Asana synchronization."""
    force_full_sync: bool = Field(default=False, description="Force full synchronization")
    sync_entity_type: Optional[str] = Field(None, description="Sync only specific entity type")
    sync_entity_id: Optional[str] = Field(None, description="Sync only specific entity")


class AsanaSyncResponse(BaseModel):
    """Response for Asana synchronization."""
    sync_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    synced_tasks: int
    created_tasks: int
    updated_tasks: int
    errors: List[str]
    warnings: List[str]


class AsanaWorkspace(BaseModel):
    """Asana workspace information."""
    gid: str
    name: str
    is_organization: bool


class AsanaProject(BaseModel):
    """Asana project information."""
    gid: str
    name: str
    archived: bool
    color: Optional[str]
    notes: Optional[str]
    owner: Optional[Dict[str, Any]]


class AsanaTask(BaseModel):
    """Asana task information."""
    gid: str
    name: str
    notes: Optional[str]
    assignee: Optional[Dict[str, Any]]
    completed: bool
    completed_at: Optional[datetime]
    due_date: Optional[datetime]
    projects: List[Dict[str, Any]]
    tags: List[Dict[str, Any]]
    custom_fields: List[Dict[str, Any]]


class AsanaUser(BaseModel):
    """Asana user information."""
    gid: str
    name: str
    email: str
    photo: Optional[Dict[str, str]]
    workspaces: List[AsanaWorkspace]