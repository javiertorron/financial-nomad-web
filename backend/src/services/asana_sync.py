"""
Asana synchronization service for managing task synchronization between Financial Nomad and Asana.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

import aiohttp
import structlog

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.asana import (
    AsanaIntegration,
    AsanaTaskMapping,
    AsanaIntegrationStatus,
    AsanaTaskStatus,
    AsanaWebhookEvent as AsanaWebhookEventModel,
    AsanaWebhookPayload,
    AsanaSyncRequest,
    AsanaSyncResponse,
    AsanaTaskMappingCreateRequest,
    AsanaTaskMappingResponse,
    AsanaTask,
    AsanaProject,
    AsanaWorkspace
)
from ..models.financial import Transaction, Budget, RecurringTransaction
from ..services.asana_integration import AsanaIntegrationService, get_asana_integration_service
from ..utils.exceptions import (
    NotFoundError, 
    ValidationError as AppValidationError, 
    BusinessLogicError,
    ExternalServiceError
)

logger = structlog.get_logger()


class AsanaSyncService:
    """Service for synchronizing tasks between Financial Nomad and Asana."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
        self.integration_service = get_asana_integration_service()
        self.asana_base_url = "https://app.asana.com/api/1.0"
    
    async def trigger_manual_sync(
        self, user_id: str, request: AsanaSyncRequest
    ) -> AsanaSyncResponse:
        """Trigger manual synchronization with Asana."""
        sync_id = "sync_" + str(uuid4())
        started_at = datetime.utcnow()
        
        try:
            # Get user's Asana integration
            integration = await self._get_active_integration(user_id)
            if not integration:
                raise NotFoundError(
                    message="Asana integration not found",
                    resource_type="asana_integration",
                    resource_id=user_id
                )
            
            # Decrypt access token
            access_token = self.integration_service._decrypt_token(integration.access_token)
            
            synced_tasks = 0
            created_tasks = 0
            updated_tasks = 0
            errors = []
            warnings = []
            
            # Sync based on request parameters
            if request.sync_entity_type and request.sync_entity_id:
                # Sync specific entity
                result = await self._sync_specific_entity(
                    user_id, integration, access_token, 
                    request.sync_entity_type, request.sync_entity_id
                )
                synced_tasks += result.get('synced', 0)
                created_tasks += result.get('created', 0)
                updated_tasks += result.get('updated', 0)
                errors.extend(result.get('errors', []))
                warnings.extend(result.get('warnings', []))
                
            elif request.force_full_sync:
                # Full synchronization
                result = await self._full_sync(user_id, integration, access_token)
                synced_tasks += result.get('synced', 0)
                created_tasks += result.get('created', 0)
                updated_tasks += result.get('updated', 0)
                errors.extend(result.get('errors', []))
                warnings.extend(result.get('warnings', []))
                
            else:
                # Incremental sync (default)
                result = await self._incremental_sync(user_id, integration, access_token)
                synced_tasks += result.get('synced', 0)
                created_tasks += result.get('created', 0)
                updated_tasks += result.get('updated', 0)
                errors.extend(result.get('errors', []))
                warnings.extend(result.get('warnings', []))
            
            # Update integration sync timestamp
            await self._update_sync_timestamp(user_id, integration.id)
            
            completed_at = datetime.utcnow()
            
            logger.info(
                "Manual sync completed",
                user_id=user_id,
                sync_id=sync_id,
                synced_tasks=synced_tasks,
                created_tasks=created_tasks,
                updated_tasks=updated_tasks,
                errors_count=len(errors)
            )
            
            return AsanaSyncResponse(
                sync_id=sync_id,
                status="completed" if not errors else "completed_with_errors",
                started_at=started_at,
                completed_at=completed_at,
                synced_tasks=synced_tasks,
                created_tasks=created_tasks,
                updated_tasks=updated_tasks,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error("Failed to complete manual sync", user_id=user_id, sync_id=sync_id, error=str(e))
            return AsanaSyncResponse(
                sync_id=sync_id,
                status="failed",
                started_at=started_at,
                completed_at=datetime.utcnow(),
                synced_tasks=0,
                created_tasks=0,
                updated_tasks=0,
                errors=[str(e)],
                warnings=[]
            )
    
    async def create_task_mapping(
        self, user_id: str, request: AsanaTaskMappingCreateRequest
    ) -> AsanaTaskMappingResponse:
        """Create a new Asana task mapping."""
        try:
            # Get user's Asana integration
            integration = await self._get_active_integration(user_id)
            if not integration:
                raise NotFoundError(
                    message="Asana integration not found",
                    resource_type="asana_integration",
                    resource_id=user_id
                )
            
            # Get entity information
            entity = await self._get_entity_by_type_and_id(user_id, request.entity_type, request.entity_id)
            if not entity:
                raise NotFoundError(
                    message=f"{request.entity_type} not found",
                    resource_type=request.entity_type,
                    resource_id=request.entity_id
                )
            
            # Decrypt access token
            access_token = self.integration_service._decrypt_token(integration.access_token)
            
            # Create task in Asana
            asana_task = await self._create_asana_task(
                access_token, integration, request, entity
            )
            
            # Create task mapping
            mapping_id = str(uuid4())
            task_mapping = AsanaTaskMapping(
                id=mapping_id,
                user_id=user_id,
                asana_task_id=asana_task['gid'],
                asana_task_name=asana_task['name'],
                asana_project_id=request.asana_project_id,
                entity_type=request.entity_type,
                entity_id=request.entity_id,
                entity_name=entity.get('name') or entity.get('description', 'Unknown'),
                task_status=AsanaTaskStatus.INCOMPLETE,
                due_date=request.due_date,
                assignee_id=request.assignee_id,
                sync_notes=f"Created from {request.entity_type}",
                last_synced=datetime.utcnow()
            )
            
            await self.firestore.create_document(
                collection=f"task_mappings/{user_id}/user_task_mappings",
                document_id=mapping_id,
                data=task_mapping
            )
            
            logger.info(
                "Task mapping created",
                user_id=user_id,
                mapping_id=mapping_id,
                asana_task_id=asana_task['gid'],
                entity_type=request.entity_type,
                entity_id=request.entity_id
            )
            
            return AsanaTaskMappingResponse(
                id=task_mapping.id,
                asana_task_id=task_mapping.asana_task_id,
                asana_task_name=task_mapping.asana_task_name,
                asana_project_name=None,  # TODO: Get project name
                entity_type=task_mapping.entity_type,
                entity_id=task_mapping.entity_id,
                entity_name=task_mapping.entity_name,
                task_status=task_mapping.task_status,
                due_date=task_mapping.due_date,
                completed_date=task_mapping.completed_date,
                last_synced=task_mapping.last_synced,
                created_at=task_mapping.created_at,
                updated_at=task_mapping.updated_at
            )
            
        except (NotFoundError, ExternalServiceError):
            raise
        except Exception as e:
            logger.error("Failed to create task mapping", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to create Asana task mapping",
                details=[str(e)]
            )
    
    async def list_task_mappings(
        self, user_id: str, entity_type: Optional[str] = None
    ) -> List[AsanaTaskMappingResponse]:
        """List user's task mappings."""
        try:
            where_clauses = []
            if entity_type:
                where_clauses.append(("entity_type", "==", entity_type))
            
            mappings = await self.firestore.query_documents(
                collection=f"task_mappings/{user_id}/user_task_mappings",
                model_class=AsanaTaskMapping,
                where_clauses=where_clauses,
                order_by="created_at"
            )
            
            responses = []
            for mapping in mappings:
                responses.append(AsanaTaskMappingResponse(
                    id=mapping.id,
                    asana_task_id=mapping.asana_task_id,
                    asana_task_name=mapping.asana_task_name,
                    asana_project_name=mapping.asana_project_name,
                    entity_type=mapping.entity_type,
                    entity_id=mapping.entity_id,
                    entity_name=mapping.entity_name,
                    task_status=mapping.task_status,
                    due_date=mapping.due_date,
                    completed_date=mapping.completed_date,
                    last_synced=mapping.last_synced,
                    created_at=mapping.created_at,
                    updated_at=mapping.updated_at
                ))
            
            return responses
            
        except Exception as e:
            logger.error("Failed to list task mappings", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to list task mappings",
                details=[str(e)]
            )
    
    async def process_webhook(self, payload: AsanaWebhookPayload) -> Dict[str, Any]:
        """Process Asana webhook events."""
        try:
            processed_events = 0
            errors = []
            
            for event_data in payload.events:
                try:
                    await self._process_webhook_event(event_data)
                    processed_events += 1
                except Exception as e:
                    logger.error("Failed to process webhook event", event=event_data, error=str(e))
                    errors.append(str(e))
            
            logger.info(
                "Webhook processed",
                total_events=len(payload.events),
                processed_events=processed_events,
                errors_count=len(errors)
            )
            
            return {
                "status": "processed",
                "total_events": len(payload.events),
                "processed_events": processed_events,
                "errors": errors
            }
            
        except Exception as e:
            logger.error("Failed to process webhook", error=str(e))
            return {
                "status": "failed",
                "error": str(e)
            }
    
    # Private helper methods
    
    async def _get_active_integration(self, user_id: str) -> Optional[AsanaIntegration]:
        """Get user's active Asana integration."""
        integrations = await self.firestore.query_documents(
            collection=f"integrations/{user_id}/asana",
            model_class=AsanaIntegration,
            where_clauses=[("status", "==", AsanaIntegrationStatus.ACTIVE)],
            limit=1
        )
        return integrations[0] if integrations else None
    
    async def _sync_specific_entity(
        self, user_id: str, integration: AsanaIntegration, access_token: str,
        entity_type: str, entity_id: str
    ) -> Dict[str, Any]:
        """Sync a specific entity."""
        result = {'synced': 0, 'created': 0, 'updated': 0, 'errors': [], 'warnings': []}
        
        try:
            # Check if mapping already exists
            existing_mappings = await self.firestore.query_documents(
                collection=f"task_mappings/{user_id}/user_task_mappings",
                model_class=AsanaTaskMapping,
                where_clauses=[
                    ("entity_type", "==", entity_type),
                    ("entity_id", "==", entity_id)
                ]
            )
            
            if existing_mappings:
                # Update existing mapping
                mapping = existing_mappings[0]
                await self._sync_task_mapping(access_token, mapping)
                result['updated'] = 1
                result['synced'] = 1
            else:
                # Create new mapping (if auto-sync is enabled)
                if self._should_auto_sync(integration, entity_type):
                    entity = await self._get_entity_by_type_and_id(user_id, entity_type, entity_id)
                    if entity:
                        await self._create_task_from_entity(user_id, integration, access_token, entity_type, entity)
                        result['created'] = 1
                        result['synced'] = 1
            
        except Exception as e:
            result['errors'].append(f"Failed to sync {entity_type} {entity_id}: {str(e)}")
        
        return result
    
    async def _full_sync(
        self, user_id: str, integration: AsanaIntegration, access_token: str
    ) -> Dict[str, Any]:
        """Perform full synchronization."""
        result = {'synced': 0, 'created': 0, 'updated': 0, 'errors': [], 'warnings': []}
        
        try:
            # Sync existing task mappings
            mappings = await self.firestore.query_documents(
                collection=f"task_mappings/{user_id}/user_task_mappings",
                model_class=AsanaTaskMapping
            )
            
            for mapping in mappings:
                try:
                    await self._sync_task_mapping(access_token, mapping)
                    result['updated'] += 1
                    result['synced'] += 1
                except Exception as e:
                    result['errors'].append(f"Failed to sync mapping {mapping.id}: {str(e)}")
            
            # Create tasks for entities without mappings
            if integration.sync_transactions:
                transactions_result = await self._sync_transactions(user_id, integration, access_token)
                result['created'] += transactions_result.get('created', 0)
                result['synced'] += transactions_result.get('synced', 0)
                result['errors'].extend(transactions_result.get('errors', []))
            
            if integration.sync_budgets:
                budgets_result = await self._sync_budgets(user_id, integration, access_token)
                result['created'] += budgets_result.get('created', 0)
                result['synced'] += budgets_result.get('synced', 0)
                result['errors'].extend(budgets_result.get('errors', []))
            
            if integration.sync_recurring:
                recurring_result = await self._sync_recurring_transactions(user_id, integration, access_token)
                result['created'] += recurring_result.get('created', 0)
                result['synced'] += recurring_result.get('synced', 0)
                result['errors'].extend(recurring_result.get('errors', []))
            
        except Exception as e:
            result['errors'].append(f"Full sync failed: {str(e)}")
        
        return result
    
    async def _incremental_sync(
        self, user_id: str, integration: AsanaIntegration, access_token: str
    ) -> Dict[str, Any]:
        """Perform incremental synchronization."""
        # For now, incremental sync is the same as full sync
        # In a real implementation, this would sync only changes since last sync
        return await self._full_sync(user_id, integration, access_token)
    
    async def _get_entity_by_type_and_id(
        self, user_id: str, entity_type: str, entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get entity by type and ID."""
        try:
            if entity_type == "transaction":
                entity = await self.firestore.get_document(
                    collection=f"transactions/{user_id}/user_transactions",
                    document_id=entity_id,
                    model_class=Transaction
                )
            elif entity_type == "budget":
                entity = await self.firestore.get_document(
                    collection=f"budgets/{user_id}/user_budgets",
                    document_id=entity_id,
                    model_class=Budget
                )
            elif entity_type == "recurring_transaction":
                entity = await self.firestore.get_document(
                    collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                    document_id=entity_id,
                    model_class=RecurringTransaction
                )
            else:
                return None
            
            return entity.dict() if entity else None
            
        except Exception:
            return None
    
    async def _create_asana_task(
        self, access_token: str, integration: AsanaIntegration,
        request: AsanaTaskMappingCreateRequest, entity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a task in Asana."""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Determine project based on entity type and configuration
        project_id = request.asana_project_id
        if not project_id:
            if request.entity_type == "transaction" and integration.transaction_project_id:
                project_id = integration.transaction_project_id
            elif request.entity_type == "budget" and integration.budget_project_id:
                project_id = integration.budget_project_id
            elif request.entity_type == "recurring_transaction" and integration.recurring_project_id:
                project_id = integration.recurring_project_id
        
        # Build task data
        task_name = request.task_name or self._generate_task_name(request.entity_type, entity)
        task_data = {
            'data': {
                'name': task_name,
                'notes': request.notes or self._generate_task_notes(request.entity_type, entity),
                'projects': [project_id] if project_id else [],
                'due_date': request.due_date.date().isoformat() if request.due_date else None,
                'assignee': request.assignee_id
            }
        }
        
        # Remove None values
        task_data['data'] = {k: v for k, v in task_data['data'].items() if v is not None}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.asana_base_url}/tasks",
                headers=headers,
                json=task_data
            ) as response:
                if response.status != 201:
                    error_text = await response.text()
                    raise ExternalServiceError(
                        message="Failed to create Asana task",
                        details=[f"HTTP {response.status}: {error_text}"]
                    )
                
                result = await response.json()
                return result['data']
    
    def _generate_task_name(self, entity_type: str, entity: Dict[str, Any]) -> str:
        """Generate task name from entity."""
        if entity_type == "transaction":
            return f"Review transaction: {entity.get('description', 'Unknown')}"
        elif entity_type == "budget":
            return f"Monitor budget: {entity.get('name', 'Unknown')}"
        elif entity_type == "recurring_transaction":
            return f"Setup recurring: {entity.get('name', 'Unknown')}"
        else:
            return f"Review {entity_type}: {entity.get('name', entity.get('description', 'Unknown'))}"
    
    def _generate_task_notes(self, entity_type: str, entity: Dict[str, Any]) -> str:
        """Generate task notes from entity."""
        notes = f"Financial Nomad {entity_type.replace('_', ' ').title()}\n\n"
        
        if entity_type == "transaction":
            notes += f"Amount: {entity.get('amount', 'N/A')}\n"
            notes += f"Date: {entity.get('transaction_date', 'N/A')}\n"
            notes += f"Description: {entity.get('description', 'N/A')}\n"
        elif entity_type == "budget":
            notes += f"Amount: {entity.get('amount', 'N/A')}\n"
            notes += f"Period: {entity.get('period_start', 'N/A')} to {entity.get('period_end', 'N/A')}\n"
        elif entity_type == "recurring_transaction":
            notes += f"Amount: {entity.get('amount', 'N/A')}\n"
            notes += f"Frequency: {entity.get('frequency', 'N/A')}\n"
        
        notes += f"\nEntity ID: {entity.get('id', 'N/A')}"
        return notes
    
    def _should_auto_sync(self, integration: AsanaIntegration, entity_type: str) -> bool:
        """Check if entity type should be auto-synced."""
        if not integration.auto_sync_enabled:
            return False
        
        if entity_type == "transaction":
            return integration.sync_transactions
        elif entity_type == "budget":
            return integration.sync_budgets
        elif entity_type == "recurring_transaction":
            return integration.sync_recurring
        
        return False
    
    async def _update_sync_timestamp(self, user_id: str, integration_id: str) -> None:
        """Update integration sync timestamp."""
        try:
            await self.firestore.update_document(
                collection=f"integrations/{user_id}/asana",
                document_id=integration_id,
                data={"last_full_sync": datetime.utcnow()}
            )
        except Exception as e:
            logger.warning("Failed to update sync timestamp", 
                         user_id=user_id, integration_id=integration_id, error=str(e))
    
    async def _sync_task_mapping(self, access_token: str, mapping: AsanaTaskMapping) -> None:
        """Sync a specific task mapping with Asana."""
        # TODO: Implement task synchronization logic
        # This would fetch the task from Asana, compare with local state, and update as needed
        pass
    
    async def _sync_transactions(
        self, user_id: str, integration: AsanaIntegration, access_token: str
    ) -> Dict[str, Any]:
        """Sync transactions that don't have mappings."""
        # TODO: Implement transaction syncing
        return {'created': 0, 'synced': 0, 'errors': []}
    
    async def _sync_budgets(
        self, user_id: str, integration: AsanaIntegration, access_token: str
    ) -> Dict[str, Any]:
        """Sync budgets that don't have mappings."""
        # TODO: Implement budget syncing
        return {'created': 0, 'synced': 0, 'errors': []}
    
    async def _sync_recurring_transactions(
        self, user_id: str, integration: AsanaIntegration, access_token: str
    ) -> Dict[str, Any]:
        """Sync recurring transactions that don't have mappings."""
        # TODO: Implement recurring transaction syncing
        return {'created': 0, 'synced': 0, 'errors': []}
    
    async def _create_task_from_entity(
        self, user_id: str, integration: AsanaIntegration, access_token: str,
        entity_type: str, entity: Dict[str, Any]
    ) -> None:
        """Create Asana task from entity."""
        # TODO: Implement automatic task creation
        pass
    
    async def _process_webhook_event(self, event_data: Dict[str, Any]) -> None:
        """Process individual webhook event."""
        # TODO: Implement webhook event processing
        pass


# Global service instance
_asana_sync_service: Optional[AsanaSyncService] = None


def get_asana_sync_service() -> AsanaSyncService:
    """Get the global Asana sync service instance."""
    global _asana_sync_service
    if _asana_sync_service is None:
        _asana_sync_service = AsanaSyncService()
    return _asana_sync_service