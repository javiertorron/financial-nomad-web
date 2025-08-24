"""
Asana integration endpoints for Financial Nomad API.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from fastapi.responses import RedirectResponse
import structlog

from ..models.asana import (
    AsanaOAuthCallbackRequest,
    AsanaIntegrationResponse,
    AsanaIntegrationConfigRequest,
    AsanaTaskMappingResponse,
    AsanaTaskMappingCreateRequest,
    AsanaSyncRequest,
    AsanaSyncResponse,
    AsanaWebhookPayload
)
from ..models.auth import User
from ..services.asana_integration import AsanaIntegrationService, get_asana_integration_service
from ..services.asana_sync import AsanaSyncService, get_asana_sync_service
from ..routers.auth import get_current_user
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError, BusinessLogicError

logger = structlog.get_logger()

router = APIRouter(
    prefix="/asana",
    tags=["asana-integration"]
)


@router.get("/oauth/authorize")
async def initiate_oauth(
    current_user_tuple: tuple = Depends(get_current_user),
    asana_service: AsanaIntegrationService = Depends(get_asana_integration_service),
    state: Optional[str] = Query(None, description="OAuth state parameter")
):
    """Initiate OAuth flow with Asana."""
    try:
        current_user, _ = current_user_tuple
        authorization_url = await asana_service.get_oauth_authorization_url(current_user.id, state)
        
        # Redirect to Asana authorization page
        return RedirectResponse(url=authorization_url, status_code=302)
        
    except Exception as e:
        logger.error("Failed to initiate OAuth", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to initiate Asana OAuth")


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(..., description="OAuth authorization code"),
    state: Optional[str] = Query(None, description="OAuth state parameter"),
    error: Optional[str] = Query(None, description="OAuth error"),
    asana_service: AsanaIntegrationService = Depends(get_asana_integration_service)
):
    """Handle OAuth callback from Asana."""
    try:
        if error:
            logger.warning("OAuth callback received error", error=error, state=state)
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        # Extract user_id from state or handle differently
        # For now, we'll need the user to be authenticated separately
        # In a real implementation, you might encode user_id in state
        
        # This is a simplified approach - you might want to handle this differently
        # based on your frontend architecture
        
        return {
            "message": "OAuth callback received successfully",
            "code": code,
            "state": state,
            "instructions": "Please call POST /asana/oauth/complete with this code from your authenticated session"
        }
        
    except Exception as e:
        logger.error("Failed to handle OAuth callback", code=code[:10], state=state, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to handle OAuth callback")


@router.post("/oauth/complete", response_model=AsanaIntegrationResponse)
async def complete_oauth(
    request: AsanaOAuthCallbackRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    asana_service: AsanaIntegrationService = Depends(get_asana_integration_service)
) -> AsanaIntegrationResponse:
    """Complete OAuth flow and create integration."""
    try:
        current_user, _ = current_user_tuple
        integration = await asana_service.handle_oauth_callback(
            current_user.id, 
            request.code, 
            request.state
        )
        return integration
        
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Failed to complete OAuth", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to complete Asana integration")


@router.get("/integration", response_model=Optional[AsanaIntegrationResponse])
async def get_integration(
    current_user_tuple: tuple = Depends(get_current_user),
    asana_service: AsanaIntegrationService = Depends(get_asana_integration_service)
) -> Optional[AsanaIntegrationResponse]:
    """Get current Asana integration status."""
    try:
        current_user, _ = current_user_tuple
        integration = await asana_service.get_integration(current_user.id)
        return integration
        
    except Exception as e:
        logger.error("Failed to get Asana integration", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve Asana integration")


@router.put("/integration", response_model=AsanaIntegrationResponse)
async def update_integration_config(
    request: AsanaIntegrationConfigRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    asana_service: AsanaIntegrationService = Depends(get_asana_integration_service)
) -> AsanaIntegrationResponse:
    """Update Asana integration configuration."""
    try:
        current_user, _ = current_user_tuple
        integration = await asana_service.update_integration_config(current_user.id, request)
        return integration
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Failed to update Asana integration config", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update Asana integration")


@router.delete("/integration")
async def delete_integration(
    current_user_tuple: tuple = Depends(get_current_user),
    asana_service: AsanaIntegrationService = Depends(get_asana_integration_service)
):
    """Delete/deactivate Asana integration."""
    try:
        current_user, _ = current_user_tuple
        await asana_service.delete_integration(current_user.id)
        return {"message": "Asana integration deleted successfully"}
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        logger.error("Failed to delete Asana integration", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete Asana integration")


@router.post("/sync", response_model=AsanaSyncResponse)
async def manual_sync(
    request: AsanaSyncRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    sync_service: AsanaSyncService = Depends(get_asana_sync_service)
) -> AsanaSyncResponse:
    """Trigger manual synchronization with Asana."""
    try:
        current_user, _ = current_user_tuple
        sync_response = await sync_service.trigger_manual_sync(current_user.id, request)
        return sync_response
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Failed to trigger manual sync", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to trigger Asana sync")


@router.post("/webhook")
async def webhook_handler(
    request: Request,
    payload: AsanaWebhookPayload,
    sync_service: AsanaSyncService = Depends(get_asana_sync_service),
    x_hook_secret: Optional[str] = None
):
    """Handle Asana webhook events."""
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # TODO: Implement webhook signature verification
        
        # Process webhook events
        result = await sync_service.process_webhook(payload)
        
        logger.info("Webhook processed", 
                   events_count=len(payload.events),
                   processed_events=result.get('processed_events', 0))
        
        return result
        
    except Exception as e:
        logger.error("Failed to process webhook", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.get("/workspaces")
async def list_workspaces(
    current_user_tuple: tuple = Depends(get_current_user),
    asana_service: AsanaIntegrationService = Depends(get_asana_integration_service)
):
    """List available Asana workspaces."""
    try:
        current_user, _ = current_user_tuple
        
        # TODO: Implement workspace listing
        # For now, return empty list
        return {"workspaces": []}
        
    except Exception as e:
        logger.error("Failed to list workspaces", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list Asana workspaces")


@router.get("/projects")
async def list_projects(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    current_user_tuple: tuple = Depends(get_current_user),
    asana_service: AsanaIntegrationService = Depends(get_asana_integration_service)
):
    """List available Asana projects."""
    try:
        current_user, _ = current_user_tuple
        
        # TODO: Implement project listing
        # For now, return empty list
        return {"projects": []}
        
    except Exception as e:
        logger.error("Failed to list projects", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list Asana projects")


@router.get("/task-mappings")
async def list_task_mappings(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    current_user_tuple: tuple = Depends(get_current_user),
    sync_service: AsanaSyncService = Depends(get_asana_sync_service)
):
    """List Asana task mappings."""
    try:
        current_user, _ = current_user_tuple
        task_mappings = await sync_service.list_task_mappings(current_user.id, entity_type)
        return {"task_mappings": task_mappings}
        
    except Exception as e:
        logger.error("Failed to list task mappings", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list task mappings")


@router.post("/task-mappings", response_model=AsanaTaskMappingResponse)
async def create_task_mapping(
    request: AsanaTaskMappingCreateRequest,
    current_user_tuple: tuple = Depends(get_current_user),
    sync_service: AsanaSyncService = Depends(get_asana_sync_service)
) -> AsanaTaskMappingResponse:
    """Create a new Asana task mapping."""
    try:
        current_user, _ = current_user_tuple
        task_mapping = await sync_service.create_task_mapping(current_user.id, request)
        return task_mapping
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AppValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Failed to create task mapping", user_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create task mapping")