"""
Google Drive integration service for backup storage and file management.
"""
import asyncio
import io
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

import aiohttp
import structlog
from cryptography.fernet import Fernet

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.backup import (
    DriveIntegration,
    DriveIntegrationResponse,
    DriveAuthRequest,
    DriveConfigUpdateRequest,
    BackupDestination
)
from ..utils.exceptions import (
    NotFoundError,
    ValidationError as AppValidationError,
    BusinessLogicError,
    ExternalServiceError
)

logger = structlog.get_logger()


class DriveIntegrationService:
    """Service for Google Drive integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
        
        # Google Drive API configuration
        self.drive_api_base_url = "https://www.googleapis.com/drive/v3"
        self.oauth_base_url = "https://accounts.google.com/o/oauth2/v2"
        self.token_url = "https://oauth2.googleapis.com/token"
        
        # OAuth credentials
        self.client_id = getattr(self.settings, 'google_client_id', None)
        self.client_secret = getattr(self.settings, 'google_client_secret', None)
        self.redirect_uri = getattr(self.settings, 'google_redirect_uri', 'http://localhost:8080/api/v1/backup/drive/callback')
        
        # Encryption for tokens
        encryption_key = getattr(self.settings, 'drive_encryption_key', None)
        if encryption_key:
            self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        else:
            self.fernet = Fernet(Fernet.generate_key())
            logger.warning("Using generated encryption key for Drive tokens - configure drive_encryption_key in production")
    
    async def get_oauth_authorization_url(self, user_id: str, state: Optional[str] = None) -> str:
        """Generate OAuth authorization URL for Google Drive."""
        if not self.client_id:
            raise AppValidationError(
                message="Google Drive integration not configured",
                details=["Missing client_id configuration"]
            )
        
        if not state:
            state = str(uuid4())
        
        # Store state for validation
        await self._store_oauth_state(user_id, state)
        
        scopes = [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.metadata.readonly",
            "https://www.googleapis.com/auth/userinfo.email"
        ]
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(scopes),
            'state': state,
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        authorization_url = f"{self.oauth_base_url}/auth?{query_string}"
        
        logger.info(
            "Drive OAuth authorization URL generated",
            user_id=user_id,
            state=state
        )
        
        return authorization_url
    
    async def handle_oauth_callback(self, user_id: str, request: DriveAuthRequest) -> DriveIntegrationResponse:
        """Handle OAuth callback and create Drive integration."""
        try:
            # Exchange code for tokens
            tokens = await self._exchange_code_for_tokens(request.authorization_code, request.redirect_uri)
            
            # Get user information
            user_info = await self._get_drive_user_info(tokens['access_token'])
            
            # Encrypt tokens
            encrypted_refresh_token = self._encrypt_token(tokens['refresh_token'])
            
            # Create or update Drive integration
            existing_integrations = await self.firestore.query_documents(
                collection=f"drive_integrations/{user_id}/user_integrations",
                model_class=DriveIntegration,
                where_clauses=[("drive_email", "==", user_info['email'])],
                limit=1
            )
            
            if existing_integrations:
                # Update existing integration
                integration = existing_integrations[0]
                integration.refresh_token = encrypted_refresh_token
                integration.last_sync_at = datetime.utcnow()
                integration.updated_at = datetime.utcnow()
                
                await self.firestore.update_document(
                    collection=f"drive_integrations/{user_id}/user_integrations",
                    document_id=integration.id,
                    data=integration.dict()
                )
            else:
                # Create new integration
                integration_id = str(uuid4())
                integration = DriveIntegration(
                    id=integration_id,
                    user_id=user_id,
                    refresh_token=encrypted_refresh_token,
                    drive_email=user_info['email'],
                    last_sync_at=datetime.utcnow()
                )
                
                await self.firestore.create_document(
                    collection=f"drive_integrations/{user_id}/user_integrations",
                    document_id=integration_id,
                    data=integration
                )
            
            # Create backup folder if it doesn't exist
            if not integration.folder_id:
                folder_id = await self._create_backup_folder(tokens['access_token'], integration.folder_name)
                integration.folder_id = folder_id
                
                await self.firestore.update_document(
                    collection=f"drive_integrations/{user_id}/user_integrations",
                    document_id=integration.id,
                    data={"folder_id": folder_id}
                )
            
            # Get quota information
            quota_info = await self._get_drive_quota(tokens['access_token'])
            if quota_info:
                await self.firestore.update_document(
                    collection=f"drive_integrations/{user_id}/user_integrations",
                    document_id=integration.id,
                    data={
                        "quota_used_bytes": quota_info.get('used'),
                        "quota_total_bytes": quota_info.get('limit')
                    }
                )
            
            logger.info(
                "Drive integration created/updated successfully",
                user_id=user_id,
                integration_id=integration.id,
                drive_email=user_info['email']
            )
            
            return DriveIntegrationResponse(
                id=integration.id,
                user_id=integration.user_id,
                drive_email=integration.drive_email,
                folder_name=integration.folder_name,
                folder_id=integration.folder_id,
                quota_used_bytes=integration.quota_used_bytes,
                quota_total_bytes=integration.quota_total_bytes,
                last_sync_at=integration.last_sync_at,
                sync_enabled=integration.sync_enabled,
                created_at=integration.created_at,
                updated_at=integration.updated_at
            )
            
        except Exception as e:
            logger.error("Failed to handle Drive OAuth callback", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to complete Drive integration",
                details=[str(e)]
            )
    
    async def get_integration(self, user_id: str) -> Optional[DriveIntegrationResponse]:
        """Get user's Drive integration."""
        try:
            integrations = await self.firestore.query_documents(
                collection=f"drive_integrations/{user_id}/user_integrations",
                model_class=DriveIntegration,
                where_clauses=[("sync_enabled", "==", True)],
                limit=1
            )
            
            if not integrations:
                return None
            
            integration = integrations[0]
            return DriveIntegrationResponse(
                id=integration.id,
                user_id=integration.user_id,
                drive_email=integration.drive_email,
                folder_name=integration.folder_name,
                folder_id=integration.folder_id,
                quota_used_bytes=integration.quota_used_bytes,
                quota_total_bytes=integration.quota_total_bytes,
                last_sync_at=integration.last_sync_at,
                sync_enabled=integration.sync_enabled,
                created_at=integration.created_at,
                updated_at=integration.updated_at
            )
            
        except Exception as e:
            logger.error("Failed to get Drive integration", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve Drive integration",
                details=[str(e)]
            )
    
    async def update_integration_config(
        self, user_id: str, request: DriveConfigUpdateRequest
    ) -> DriveIntegrationResponse:
        """Update Drive integration configuration."""
        try:
            integration = await self.get_integration(user_id)
            if not integration:
                raise NotFoundError(
                    message="Drive integration not found",
                    resource_type="drive_integration",
                    resource_id=user_id
                )
            
            # Prepare update data
            update_data = {"updated_at": datetime.utcnow()}
            
            if request.folder_name is not None:
                update_data["folder_name"] = request.folder_name
            if request.sync_enabled is not None:
                update_data["sync_enabled"] = request.sync_enabled
            
            # Apply updates
            await self.firestore.update_document(
                collection=f"drive_integrations/{user_id}/user_integrations",
                document_id=integration.id,
                data=update_data
            )
            
            # Get updated integration
            updated_integration = await self.get_integration(user_id)
            
            logger.info(
                "Drive integration configuration updated",
                user_id=user_id,
                integration_id=integration.id,
                updated_fields=list(update_data.keys())
            )
            
            return updated_integration
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to update Drive integration config", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to update Drive integration configuration",
                details=[str(e)]
            )
    
    async def delete_integration(self, user_id: str) -> None:
        """Delete/disable Drive integration."""
        try:
            integration = await self.get_integration(user_id)
            if not integration:
                raise NotFoundError(
                    message="Drive integration not found",
                    resource_type="drive_integration",
                    resource_id=user_id
                )
            
            # Disable integration
            await self.firestore.update_document(
                collection=f"drive_integrations/{user_id}/user_integrations",
                document_id=integration.id,
                data={
                    "sync_enabled": False,
                    "updated_at": datetime.utcnow()
                }
            )
            
            logger.info(
                "Drive integration disabled",
                user_id=user_id,
                integration_id=integration.id
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete Drive integration", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to delete Drive integration",
                details=[str(e)]
            )
    
    async def upload_backup_to_drive(self, user_id: str, file_name: str, file_data: bytes) -> str:
        """Upload backup file to Google Drive."""
        try:
            # Get user's Drive integration
            integration = await self.get_integration(user_id)
            if not integration or not integration.sync_enabled:
                raise BusinessLogicError(
                    message="Drive integration not available",
                    details=["Drive sync is disabled or not configured"]
                )
            
            # Get fresh access token
            access_token = await self._get_fresh_access_token(user_id, integration.id)
            
            # Upload file
            file_id = await self._upload_file_to_drive(
                access_token, file_name, file_data, integration.folder_id
            )
            
            # Update last sync timestamp
            await self.firestore.update_document(
                collection=f"drive_integrations/{user_id}/user_integrations",
                document_id=integration.id,
                data={"last_sync_at": datetime.utcnow()}
            )
            
            logger.info(
                "Backup uploaded to Drive",
                user_id=user_id,
                file_name=file_name,
                file_id=file_id,
                size_bytes=len(file_data)
            )
            
            return f"drive://files/{file_id}"
            
        except Exception as e:
            logger.error("Failed to upload backup to Drive", user_id=user_id, file_name=file_name, error=str(e))
            raise ExternalServiceError(
                message="Failed to upload backup to Google Drive",
                details=[str(e)]
            )
    
    async def list_backup_files(self, user_id: str) -> List[Dict[str, Any]]:
        """List backup files in Google Drive."""
        try:
            integration = await self.get_integration(user_id)
            if not integration or not integration.sync_enabled:
                return []
            
            # Get fresh access token
            access_token = await self._get_fresh_access_token(user_id, integration.id)
            
            # List files in backup folder
            files = await self._list_files_in_folder(access_token, integration.folder_id)
            
            logger.info(
                "Listed backup files from Drive",
                user_id=user_id,
                files_count=len(files)
            )
            
            return files
            
        except Exception as e:
            logger.error("Failed to list backup files from Drive", user_id=user_id, error=str(e))
            raise ExternalServiceError(
                message="Failed to list backup files from Google Drive",
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
            collection="oauth_states_drive",
            document_id=state,
            data=state_data
        )
    
    async def _exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange OAuth code for access tokens."""
        if not self.client_id or not self.client_secret:
            raise AppValidationError(
                message="Google Drive OAuth not configured",
                details=["Missing client credentials"]
            )
        
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': redirect_uri,
            'code': code
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.token_url,
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
    
    async def _get_drive_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google Drive API."""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ExternalServiceError(
                        message="Failed to get user info",
                        details=[f"HTTP {response.status}: {error_text}"]
                    )
                
                user_info = await response.json()
                return user_info
    
    async def _create_backup_folder(self, access_token: str, folder_name: str) -> str:
        """Create backup folder in Google Drive."""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.drive_api_base_url}/files",
                headers=headers,
                json=folder_metadata
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ExternalServiceError(
                        message="Failed to create backup folder",
                        details=[f"HTTP {response.status}: {error_text}"]
                    )
                
                result = await response.json()
                return result['id']
    
    async def _get_drive_quota(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get Drive quota information."""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.drive_api_base_url}/about?fields=storageQuota",
                headers=headers
            ) as response:
                if response.status != 200:
                    logger.warning("Failed to get Drive quota info", status=response.status)
                    return None
                
                result = await response.json()
                quota = result.get('storageQuota', {})
                return {
                    'limit': int(quota.get('limit', 0)),
                    'used': int(quota.get('usage', 0))
                }
    
    async def _get_fresh_access_token(self, user_id: str, integration_id: str) -> str:
        """Get fresh access token using refresh token."""
        # Get integration
        integration = await self.firestore.get_document(
            collection=f"drive_integrations/{user_id}/user_integrations",
            document_id=integration_id,
            model_class=DriveIntegration
        )
        
        if not integration:
            raise NotFoundError(
                message="Drive integration not found",
                resource_type="drive_integration",
                resource_id=integration_id
            )
        
        # Decrypt refresh token
        refresh_token = self._decrypt_token(integration.refresh_token)
        
        # Get new access token
        token_data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.token_url,
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ExternalServiceError(
                        message="Failed to refresh access token",
                        details=[f"HTTP {response.status}: {error_text}"]
                    )
                
                tokens = await response.json()
                return tokens['access_token']
    
    async def _upload_file_to_drive(self, access_token: str, file_name: str, file_data: bytes, folder_id: str) -> str:
        """Upload file to Google Drive."""
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        # File metadata
        metadata = {
            'name': file_name,
            'parents': [folder_id] if folder_id else None
        }
        
        # Prepare multipart upload
        boundary = '-------314159265358979323846'
        body_parts = []
        
        # Metadata part
        body_parts.append(f'--{boundary}')
        body_parts.append('Content-Type: application/json; charset=UTF-8')
        body_parts.append('')
        body_parts.append(json.dumps(metadata))
        
        # File data part
        body_parts.append(f'--{boundary}')
        body_parts.append('Content-Type: application/octet-stream')
        body_parts.append('')
        
        # Join text parts
        body_prefix = '\r\n'.join(body_parts) + '\r\n'
        body_suffix = f'\r\n--{boundary}--'
        
        # Combine all parts
        full_body = body_prefix.encode('utf-8') + file_data + body_suffix.encode('utf-8')
        
        headers['Content-Type'] = f'multipart/related; boundary={boundary}'
        headers['Content-Length'] = str(len(full_body))
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.drive_api_base_url}/files?uploadType=multipart",
                headers=headers,
                data=full_body
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ExternalServiceError(
                        message="Failed to upload file to Drive",
                        details=[f"HTTP {response.status}: {error_text}"]
                    )
                
                result = await response.json()
                return result['id']
    
    async def _list_files_in_folder(self, access_token: str, folder_id: str) -> List[Dict[str, Any]]:
        """List files in Google Drive folder."""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        query = f"'{folder_id}' in parents and trashed=false"
        params = {
            'q': query,
            'fields': 'files(id,name,size,createdTime,modifiedTime)',
            'orderBy': 'modifiedTime desc'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.drive_api_base_url}/files",
                headers=headers,
                params=params
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ExternalServiceError(
                        message="Failed to list files from Drive",
                        details=[f"HTTP {response.status}: {error_text}"]
                    )
                
                result = await response.json()
                return result.get('files', [])
    
    def _encrypt_token(self, token: str) -> str:
        """Encrypt access/refresh token."""
        return self.fernet.encrypt(token.encode()).decode()
    
    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt access/refresh token."""
        return self.fernet.decrypt(encrypted_token.encode()).decode()


# Global service instance
_drive_integration_service: Optional[DriveIntegrationService] = None


def get_drive_integration_service() -> DriveIntegrationService:
    """Get the global Drive integration service instance."""
    global _drive_integration_service
    if _drive_integration_service is None:
        _drive_integration_service = DriveIntegrationService()
    return _drive_integration_service