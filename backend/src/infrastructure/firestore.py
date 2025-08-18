"""
Firestore client implementation with connection pooling and error handling.
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Tuple
from uuid import UUID

import structlog
from google.api_core import exceptions as gcp_exceptions
from google.cloud import firestore
from google.cloud.firestore import Client as FirestoreClient
from google.cloud.firestore import DocumentReference, DocumentSnapshot, Query
from pydantic import BaseModel

from ..config import get_settings
from ..utils.exceptions import DatabaseError, NotFoundError, ValidationError

T = TypeVar("T", bound=BaseModel)

logger = structlog.get_logger()


class FirestoreService:
    """
    Firestore service with connection management and model serialization.
    """
    
    def __init__(self):
        """Initialize Firestore client with configuration."""
        self._client: Optional[FirestoreClient] = None
        self._settings = get_settings()
        
    @property
    def client(self) -> FirestoreClient:
        """Get or create Firestore client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> FirestoreClient:
        """Create and configure Firestore client."""
        try:
            if self._settings.use_firestore_emulator:
                # Configure for emulator
                os.environ["FIRESTORE_EMULATOR_HOST"] = self._settings.firestore_emulator_host
                client = firestore.Client(project=self._settings.firestore_project_id)
                logger.info(
                    "Connected to Firestore emulator",
                    host=self._settings.firestore_emulator_host,
                    project=self._settings.firestore_project_id
                )
            else:
                # Production configuration
                if self._settings.google_credentials_path:
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._settings.google_credentials_path
                
                client = firestore.Client(project=self._settings.firestore_project_id)
                logger.info(
                    "Connected to Firestore",
                    project=self._settings.firestore_project_id
                )
            
            return client
            
        except Exception as e:
            logger.error("Failed to create Firestore client", error=str(e))
            raise DatabaseError(
                message="Failed to connect to database",
                code="FIRESTORE_CONNECTION_ERROR",
                details=[str(e)]
            )
    
    def _serialize_model(self, model: BaseModel) -> Dict[str, Any]:
        """Serialize Pydantic model to Firestore document."""
        data = model.dict()
        
        # Convert UUID to string
        for key, value in data.items():
            if isinstance(value, UUID):
                data[key] = str(value)
            elif isinstance(value, datetime):
                data[key] = value
            elif isinstance(value, list):
                # Handle lists with UUIDs
                data[key] = [str(item) if isinstance(item, UUID) else item for item in value]
        
        return data
    
    def _deserialize_document(self, doc_data: Dict[str, Any], model_class: Type[T]) -> T:
        """Deserialize Firestore document to Pydantic model."""
        try:
            # Handle UUID fields that come as strings
            if "id" in doc_data and isinstance(doc_data["id"], str):
                try:
                    UUID(doc_data["id"])  # Validate UUID format
                except ValueError:
                    pass  # Keep as string if not valid UUID
            
            return model_class(**doc_data)
        except Exception as e:
            logger.error(
                "Failed to deserialize document",
                doc_data=doc_data,
                model_class=model_class.__name__,
                error=str(e)
            )
            raise ValidationError(
                message=f"Failed to deserialize document to {model_class.__name__}",
                code="DESERIALIZATION_ERROR",
                details=[str(e)]
            )
    
    async def create_document(
        self,
        collection: str,
        document_id: str,
        data: BaseModel
    ) -> str:
        """Create a new document in the collection."""
        try:
            doc_data = self._serialize_model(data)
            doc_ref = self.client.collection(collection).document(document_id)
            doc_ref.set(doc_data)
            
            logger.info(
                "Document created",
                collection=collection,
                document_id=document_id
            )
            return document_id
            
        except gcp_exceptions.AlreadyExists:
            raise ValidationError(
                message=f"Document {document_id} already exists",
                code="DOCUMENT_ALREADY_EXISTS"
            )
        except Exception as e:
            logger.error(
                "Failed to create document",
                collection=collection,
                document_id=document_id,
                error=str(e)
            )
            raise DatabaseError(
                message="Failed to create document",
                code="CREATE_DOCUMENT_ERROR",
                details=[str(e)]
            )
    
    async def get_document(
        self,
        collection: str,
        document_id: str,
        model_class: Type[T]
    ) -> T:
        """Get a document by ID."""
        try:
            doc_ref = self.client.collection(collection).document(document_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                raise NotFoundError(
                    message=f"Document {document_id} not found",
                    code="DOCUMENT_NOT_FOUND"
                )
            
            doc_data = doc.to_dict()
            doc_data["id"] = doc.id  # Ensure ID is included
            
            return self._deserialize_document(doc_data, model_class)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get document",
                collection=collection,
                document_id=document_id,
                error=str(e)
            )
            raise DatabaseError(
                message="Failed to retrieve document",
                code="GET_DOCUMENT_ERROR",
                details=[str(e)]
            )
    
    async def update_document(
        self,
        collection: str,
        document_id: str,
        data: BaseModel
    ) -> None:
        """Update an existing document."""
        try:
            doc_data = self._serialize_model(data)
            doc_ref = self.client.collection(collection).document(document_id)
            
            # Check if document exists
            if not doc_ref.get().exists:
                raise NotFoundError(
                    message=f"Document {document_id} not found",
                    code="DOCUMENT_NOT_FOUND"
                )
            
            doc_ref.update(doc_data)
            
            logger.info(
                "Document updated",
                collection=collection,
                document_id=document_id
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update document",
                collection=collection,
                document_id=document_id,
                error=str(e)
            )
            raise DatabaseError(
                message="Failed to update document",
                code="UPDATE_DOCUMENT_ERROR",
                details=[str(e)]
            )
    
    async def delete_document(
        self,
        collection: str,
        document_id: str
    ) -> None:
        """Delete a document."""
        try:
            doc_ref = self.client.collection(collection).document(document_id)
            
            # Check if document exists
            if not doc_ref.get().exists:
                raise NotFoundError(
                    message=f"Document {document_id} not found",
                    code="DOCUMENT_NOT_FOUND"
                )
            
            doc_ref.delete()
            
            logger.info(
                "Document deleted",
                collection=collection,
                document_id=document_id
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete document",
                collection=collection,
                document_id=document_id,
                error=str(e)
            )
            raise DatabaseError(
                message="Failed to delete document",
                code="DELETE_DOCUMENT_ERROR",
                details=[str(e)]
            )
    
    async def query_documents(
        self,
        collection: str,
        model_class: Type[T],
        where_clauses: Optional[List[tuple]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[T]:
        """Query documents with filters and pagination."""
        try:
            query = self.client.collection(collection)
            
            # Apply where clauses
            if where_clauses:
                for field, operator, value in where_clauses:
                    # Convert UUID to string for Firestore
                    if isinstance(value, UUID):
                        value = str(value)
                    query = query.where(field, operator, value)
            
            # Apply ordering
            if order_by:
                direction = Query.DESCENDING if order_by.startswith("-") else Query.ASCENDING
                field = order_by.lstrip("-")
                query = query.order_by(field, direction=direction)
            
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            # Execute query
            docs = query.stream()
            results = []
            
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data["id"] = doc.id
                result = self._deserialize_document(doc_data, model_class)
                results.append(result)
            
            logger.info(
                "Documents queried",
                collection=collection,
                count=len(results),
                filters=where_clauses,
                order_by=order_by,
                limit=limit,
                offset=offset
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Failed to query documents",
                collection=collection,
                error=str(e)
            )
            raise DatabaseError(
                message="Failed to query documents",
                code="QUERY_DOCUMENTS_ERROR",
                details=[str(e)]
            )
    
    async def count_documents(
        self,
        collection: str,
        where_clauses: Optional[List[tuple]] = None
    ) -> int:
        """Count documents matching the query."""
        try:
            query = self.client.collection(collection)
            
            # Apply where clauses
            if where_clauses:
                for field, operator, value in where_clauses:
                    if isinstance(value, UUID):
                        value = str(value)
                    query = query.where(field, operator, value)
            
            # Execute count query
            docs = list(query.stream())
            count = len(docs)
            
            logger.info(
                "Documents counted",
                collection=collection,
                count=count,
                filters=where_clauses
            )
            
            return count
            
        except Exception as e:
            logger.error(
                "Failed to count documents",
                collection=collection,
                error=str(e)
            )
            raise DatabaseError(
                message="Failed to count documents",
                code="COUNT_DOCUMENTS_ERROR",
                details=[str(e)]
            )
    
    async def batch_create(
        self,
        collection: str,
        documents: List[Tuple[str, BaseModel]]
    ) -> List[str]:
        """Create multiple documents in a batch."""
        try:
            batch = self.client.batch()
            document_ids = []
            
            for doc_id, data in documents:
                doc_data = self._serialize_model(data)
                doc_ref = self.client.collection(collection).document(doc_id)
                batch.set(doc_ref, doc_data)
                document_ids.append(doc_id)
            
            batch.commit()
            
            logger.info(
                "Batch create completed",
                collection=collection,
                count=len(documents)
            )
            
            return document_ids
            
        except Exception as e:
            logger.error(
                "Failed to batch create documents",
                collection=collection,
                count=len(documents),
                error=str(e)
            )
            raise DatabaseError(
                message="Failed to batch create documents",
                code="BATCH_CREATE_ERROR",
                details=[str(e)]
            )
    
    async def transaction_update(
        self,
        updates: List[Tuple[str, str, BaseModel]]  # collection, doc_id, data
    ) -> None:
        """Update multiple documents in a transaction."""
        try:
            transaction = self.client.transaction()
            
            @firestore.transactional
            def update_in_transaction(transaction_ref):
                for collection, doc_id, data in updates:
                    doc_data = self._serialize_model(data)
                    doc_ref = self.client.collection(collection).document(doc_id)
                    transaction_ref.update(doc_ref, doc_data)
            
            update_in_transaction(transaction)
            
            logger.info(
                "Transaction update completed",
                updates_count=len(updates)
            )
            
        except Exception as e:
            logger.error(
                "Failed to perform transaction update",
                updates_count=len(updates),
                error=str(e)
            )
            raise DatabaseError(
                message="Failed to perform transaction update",
                code="TRANSACTION_UPDATE_ERROR",
                details=[str(e)]
            )


# Global Firestore service instance
_firestore_service: Optional[FirestoreService] = None


def get_firestore() -> FirestoreService:
    """Get the global Firestore service instance."""
    global _firestore_service
    if _firestore_service is None:
        _firestore_service = FirestoreService()
    return _firestore_service


async def cleanup_firestore():
    """Cleanup Firestore connections."""
    global _firestore_service
    if _firestore_service and _firestore_service._client:
        _firestore_service._client.close()
        _firestore_service = None
        logger.info("Firestore client closed")