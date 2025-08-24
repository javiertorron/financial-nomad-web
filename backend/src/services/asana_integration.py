"""
Asana integration service for managing OAuth, synchronization, and task mapping.
"""
import asyncio
import base64
import hashlib
import hmac
import json
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

import aiohttp
import structlog
from cryptography.fernet import Fernet

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.asana import (
    AsanaIntegration,
    AsanaTaskMapping,
    AsanaIntegrationStatus,
    AsanaTaskStatus,
    AsanaWebhookEvent,
    AsanaWebhookPayload,
    AsanaIntegrationResponse,
    AsanaIntegrationConfigRequest,
    AsanaTaskMappingResponse,
    AsanaTaskMappingCreateRequest,
    AsanaSyncRequest,
    AsanaSyncResponse,
    AsanaWorkspace,
    AsanaProject,
    AsanaTask,
    AsanaUser
)
from ..models.financial import Transaction, Budget, RecurringTransaction
from ..utils.exceptions import (
    NotFoundError, 
    ValidationError as AppValidationError, 
    BusinessLogicError,
    ExternalServiceError
)

logger = structlog.get_logger()


class AsanaIntegrationService:
    """Service for Asana integration operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
        
        # Asana API configuration
        self.asana_base_url = "https://app.asana.com/api/1.0"
        self.oauth_base_url = "https://app.asana.com/-/oauth"
        
        # Get Asana credentials from settings
        self.client_id = getattr(self.settings, 'asana_client_id', None)
        self.client_secret = getattr(self.settings, 'asana_client_secret', None)
        self.redirect_uri = getattr(self.settings, 'asana_redirect_uri', 'http://localhost:8080/api/v1/asana/oauth/callback')
        
        # Encryption key for tokens (should be from settings)
        encryption_key = getattr(self.settings, 'asana_encryption_key', None)
        if encryption_key:
            self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        else:
            # Generate a key for development (should be stored securely in production)
            self.fernet = Fernet(Fernet.generate_key())
            logger.warning("Using generated encryption key for Asana tokens - configure asana_encryption_key in production")
    
    async def get_oauth_authorization_url(self, user_id: str, state: Optional[str] = None) -> str:
        """Generate OAuth authorization URL for Asana."""
        if not self.client_id:
            raise AppValidationError(
                message="Asana integration not configured",
                details=["Missing client_id configuration"]
            )
        
        # Generate state if not provided
        if not state:
            state = str(uuid4())
        
        # Store state for validation
        await self._store_oauth_state(user_id, state)
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'state': state,
            'scope': 'default'
        }
        
        query_string = urllib.parse.urlencode(params)
        authorization_url = f"{self.oauth_base_url}/authorize?{query_string}"
        
        logger.info(
            "OAuth authorization URL generated",
            user_id=user_id,
            state=state
        )
        
        return authorization_url
    
    async def handle_oauth_callback(self, user_id: str, code: str, state: Optional[str] = None) -> AsanaIntegrationResponse:
        """Handle OAuth callback and create integration."""
        try:
            # Validate state if provided
            if state:
                await self._validate_oauth_state(user_id, state)
            
            # Exchange code for tokens
            tokens = await self._exchange_code_for_tokens(code)
            
            # Get user information from Asana
            user_info = await self._get_asana_user_info(tokens['access_token'])
            
            # Encrypt tokens
            encrypted_access_token = self._encrypt_token(tokens['access_token'])
            encrypted_refresh_token = None
            if tokens.get('refresh_token'):
                encrypted_refresh_token = self._encrypt_token(tokens['refresh_token'])
            
            # Calculate token expiration
            expires_at = None
            if tokens.get('expires_in'):
                expires_at = datetime.utcnow() + timedelta(seconds=tokens['expires_in'])
            
            # Check if integration already exists
            existing_integrations = await self.firestore.query_documents(
                collection=f"integrations/{user_id}/asana",
                model_class=AsanaIntegration,
                where_clauses=[("asana_user_id", "==", user_info.gid)]
            )
            
            integration_data = {
                "user_id": user_id,
                "access_token": encrypted_access_token,
                "refresh_token": encrypted_refresh_token,
                "token_expires_at": expires_at,
                "asana_user_id": user_info.gid,
                "asana_user_email": user_info.email,
                "asana_user_name": user_info.name,
                "status": AsanaIntegrationStatus.ACTIVE,
                "auto_sync_enabled": True,
                "sync_transactions": True,
                "sync_budgets": True,
                "sync_recurring": False
            }
            
            # Set default workspace if user has workspaces
            if user_info.workspaces:
                default_workspace = user_info.workspaces[0]
                integration_data.update({
                    "default_workspace_id": default_workspace.gid,
                    "default_workspace_name": default_workspace.name
                })
            
            if existing_integrations:
                # Update existing integration
                integration_id = existing_integrations[0].id
                integration_data["updated_at"] = datetime.utcnow()
                
                await self.firestore.update_document(
                    collection=f"integrations/{user_id}/asana",
                    document_id=integration_id,
                    data=integration_data
                )
                
                integration = existing_integrations[0]
                for key, value in integration_data.items():
                    setattr(integration, key, value)
                
            else:
                # Create new integration
                integration_id = str(uuid4())
                integration = AsanaIntegration(
                    id=integration_id,
                    **integration_data
                )
                
                await self.firestore.create_document(
                    collection=f"integrations/{user_id}/asana",
                    document_id=integration_id,
                    data=integration
                )
            
            logger.info(
                "Asana integration created/updated successfully",
                user_id=user_id,
                integration_id=integration_id,
                asana_user_id=user_info.gid
            )
            
            return AsanaIntegrationResponse(
                id=integration.id,
                user_id=integration.user_id,
                status=integration.status,
                asana_user_email=integration.asana_user_email,
                asana_user_name=integration.asana_user_name,
                default_workspace_name=integration.default_workspace_name,
                auto_sync_enabled=integration.auto_sync_enabled,
                sync_transactions=integration.sync_transactions,
                sync_budgets=integration.sync_budgets,
                sync_recurring=integration.sync_recurring,
                last_full_sync=integration.last_full_sync,
                created_at=integration.created_at,
                updated_at=integration.updated_at
            )
            
        except Exception as e:
            logger.error("Failed to handle OAuth callback", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to complete Asana integration",
                details=[str(e)]
            )
    
    async def get_integration(self, user_id: str) -> Optional[AsanaIntegrationResponse]:
        """Get user's Asana integration."""
        try:
            integrations = await self.firestore.query_documents(
                collection=f"integrations/{user_id}/asana",
                model_class=AsanaIntegration,
                where_clauses=[("status", "==", AsanaIntegrationStatus.ACTIVE)],
                limit=1
            )
            
            if not integrations:
                return None
            
            integration = integrations[0]
            return AsanaIntegrationResponse(
                id=integration.id,
                user_id=integration.user_id,
                status=integration.status,
                asana_user_email=integration.asana_user_email,
                asana_user_name=integration.asana_user_name,
                default_workspace_name=integration.default_workspace_name,
                auto_sync_enabled=integration.auto_sync_enabled,
                sync_transactions=integration.sync_transactions,
                sync_budgets=integration.sync_budgets,
                sync_recurring=integration.sync_recurring,
                last_full_sync=integration.last_full_sync,
                created_at=integration.created_at,
                updated_at=integration.updated_at
            )
            
        except Exception as e:
            logger.error("Failed to get Asana integration", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve Asana integration",
                details=[str(e)]
            )
    
    async def update_integration_config(
        self, user_id: str, request: AsanaIntegrationConfigRequest
    ) -> AsanaIntegrationResponse:
        """Update Asana integration configuration."""
        try:
            # Get existing integration
            integrations = await self.firestore.query_documents(
                collection=f"integrations/{user_id}/asana",
                model_class=AsanaIntegration,
                where_clauses=[("status", "==", AsanaIntegrationStatus.ACTIVE)],
                limit=1
            )
            
            if not integrations:
                raise NotFoundError(
                    message="Asana integration not found",
                    resource_type="asana_integration",
                    resource_id=user_id
                )
            
            integration = integrations[0]
            
            # Update configuration
            update_data = {"updated_at": datetime.utcnow()}
            
            if request.auto_sync_enabled is not None:
                update_data["auto_sync_enabled"] = request.auto_sync_enabled
            if request.sync_transactions is not None:
                update_data["sync_transactions"] = request.sync_transactions
            if request.sync_budgets is not None:
                update_data["sync_budgets"] = request.sync_budgets
            if request.sync_recurring is not None:
                update_data["sync_recurring"] = request.sync_recurring
            if request.default_workspace_id is not None:
                update_data["default_workspace_id"] = request.default_workspace_id
            if request.transaction_project_id is not None:
                update_data["transaction_project_id"] = request.transaction_project_id
            if request.budget_project_id is not None:
                update_data["budget_project_id"] = request.budget_project_id
            if request.recurring_project_id is not None:
                update_data["recurring_project_id"] = request.recurring_project_id
            
            # Apply updates
            for field, value in update_data.items():
                setattr(integration, field, value)
            
            await self.firestore.update_document(
                collection=f"integrations/{user_id}/asana",
                document_id=integration.id,
                data=integration.dict()
            )
            
            logger.info(
                "Asana integration configuration updated",
                user_id=user_id,
                integration_id=integration.id,
                updated_fields=list(update_data.keys())
            )
            
            return AsanaIntegrationResponse(
                id=integration.id,
                user_id=integration.user_id,
                status=integration.status,
                asana_user_email=integration.asana_user_email,
                asana_user_name=integration.asana_user_name,
                default_workspace_name=integration.default_workspace_name,
                auto_sync_enabled=integration.auto_sync_enabled,
                sync_transactions=integration.sync_transactions,
                sync_budgets=integration.sync_budgets,
                sync_recurring=integration.sync_recurring,
                last_full_sync=integration.last_full_sync,
                created_at=integration.created_at,
                updated_at=integration.updated_at
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to update Asana integration config", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to update Asana integration configuration",
                details=[str(e)]
            )
    
    async def delete_integration(self, user_id: str) -> None:
        """Delete/deactivate Asana integration."""
        try:
            integrations = await self.firestore.query_documents(
                collection=f"integrations/{user_id}/asana",
                model_class=AsanaIntegration,
                where_clauses=[("status", "==", AsanaIntegrationStatus.ACTIVE)],
                limit=1
            )
            
            if not integrations:
                raise NotFoundError(
                    message="Asana integration not found",
                    resource_type="asana_integration",
                    resource_id=user_id
                )
            
            integration = integrations[0]
            
            # Deactivate integration
            integration.status = AsanaIntegrationStatus.INACTIVE
            integration.updated_at = datetime.utcnow()
            
            await self.firestore.update_document(
                collection=f"integrations/{user_id}/asana",
                document_id=integration.id,
                data=integration.dict()
            )
            
            # TODO: Revoke webhook if exists
            # TODO: Optionally delete task mappings
            
            logger.info(
                "Asana integration deactivated",
                user_id=user_id,
                integration_id=integration.id
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete Asana integration", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to delete Asana integration",
                details=[str(e)]
            )
    
    # Private helper methods
    
    async def _store_oauth_state(self, user_id: str, state: str) -> None:
        """Store OAuth state for validation."""
        state_data = {
            "user_id": user_id,
            "state": state,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=10)
        }
        
        await self.firestore.create_document(
            collection="oauth_states",
            document_id=state,
            data=state_data
        )
    
    async def _validate_oauth_state(self, user_id: str, state: str) -> None:
        """Validate OAuth state parameter."""
        try:
            state_doc = await self.firestore.get_document(
                collection="oauth_states",
                document_id=state,
                model_class=dict
            )
            
            if not state_doc:
                raise AppValidationError(
                    message="Invalid OAuth state",
                    details=["State parameter not found"]
                )
            
            # Check if state belongs to user and hasn't expired
            if (state_doc["user_id"] != user_id or 
                state_doc["expires_at"] < datetime.utcnow()):
                raise AppValidationError(
                    message="Invalid OAuth state",
                    details=["State parameter expired or invalid"]
                )
            
            # Clean up state after validation
            await self.firestore.delete_document(
                collection="oauth_states",
                document_id=state
            )
            
        except AppValidationError:
            raise
        except Exception as e:
            logger.error("Failed to validate OAuth state", state=state, error=str(e))
            raise AppValidationError(
                message="OAuth validation failed",
                details=[str(e)]
            )
    
    async def _exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth code for access tokens."""
        if not self.client_id or not self.client_secret:
            raise AppValidationError(
                message="Asana OAuth not configured",
                details=["Missing client credentials"]
            )
        
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'code': code
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.oauth_base_url}/token",
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("Failed to exchange OAuth code", status=response.status, error=error_text)
                    raise ExternalServiceError(
                        message="Failed to exchange OAuth code",
                        details=[f"HTTP {response.status}: {error_text}"]
                    )
                
                tokens = await response.json()
                return tokens
    
    async def _get_asana_user_info(self, access_token: str) -> AsanaUser:
        """Get user information from Asana API."""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            # Get user info
            async with session.get(
                f"{self.asana_base_url}/users/me",
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ExternalServiceError(
                        message="Failed to get Asana user info",
                        details=[f"HTTP {response.status}: {error_text}"]
                    )
                
                user_data = await response.json()
                user_info = user_data['data']
                
                # Get workspaces
                workspaces = []
                for workspace_ref in user_info.get('workspaces', []):
                    async with session.get(
                        f"{self.asana_base_url}/workspaces/{workspace_ref['gid']}",
                        headers=headers
                    ) as ws_response:
                        if ws_response.status == 200:
                            ws_data = await ws_response.json()
                            workspaces.append(AsanaWorkspace(
                                gid=ws_data['data']['gid'],
                                name=ws_data['data']['name'],
                                is_organization=ws_data['data'].get('is_organization', False)
                            ))
                
                return AsanaUser(
                    gid=user_info['gid'],
                    name=user_info['name'],
                    email=user_info['email'],
                    photo=user_info.get('photo'),
                    workspaces=workspaces
                )
    
    def _encrypt_token(self, token: str) -> str:
        """Encrypt access/refresh token."""
        return self.fernet.encrypt(token.encode()).decode()
    
    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt access/refresh token."""
        return self.fernet.decrypt(encrypted_token.encode()).decode()


# Global service instance
_asana_integration_service: Optional[AsanaIntegrationService] = None


def get_asana_integration_service() -> AsanaIntegrationService:
    """Get the global Asana integration service instance."""
    global _asana_integration_service
    if _asana_integration_service is None:
        _asana_integration_service = AsanaIntegrationService()
    return _asana_integration_service