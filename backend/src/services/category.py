"""
Category service for managing financial categories.
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

import structlog

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.financial import (
    Category,
    CategoryCreateRequest,
    CategoryUpdateRequest,
    CategoryResponse,
    CategorySummary
)
from ..utils.exceptions import NotFoundError, ValidationError as AppValidationError

logger = structlog.get_logger()


class CategoryService:
    """Service for category operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
    
    async def create_category(self, user_id: str, request: CategoryCreateRequest) -> CategoryResponse:
        """Create a new category."""
        try:
            # Validate parent category exists if specified
            if request.parent_id:
                parent_category = await self.firestore.get_document(
                    collection=f"categories/{user_id}/user_categories",
                    document_id=request.parent_id,
                    model_class=Category
                )
                if not parent_category:
                    raise AppValidationError(
                        message="Parent category not found",
                        details=[f"Parent category {request.parent_id} does not exist"]
                    )
            
            # Create category model
            category = Category(
                user_id=user_id,
                name=request.name,
                category_type=request.category_type,
                parent_id=request.parent_id,
                color=request.color,
                icon=request.icon,
                is_system=False  # User-created categories are never system categories
            )
            
            # Generate category ID and save to Firestore
            category_id = str(uuid4())
            category.id = category_id
            
            await self.firestore.create_document(
                collection=f"categories/{user_id}/user_categories",
                document_id=category_id,
                data=category
            )
            
            logger.info(
                "Category created successfully",
                user_id=user_id,
                category_id=category_id,
                category_name=category.name
            )
            
            # Return response
            return CategoryResponse(
                id=category.id,
                name=category.name,
                category_type=category.category_type,
                parent_id=category.parent_id,
                color=category.color,
                icon=category.icon,
                is_system=category.is_system,
                is_active=category.is_active,
                created_at=category.created_at,
                updated_at=category.updated_at
            )
            
        except Exception as e:
            logger.error("Failed to create category", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to create category",
                details=[str(e)]
            )
    
    async def get_category(self, user_id: str, category_id: str) -> CategoryResponse:
        """Get category by ID."""
        try:
            category = await self.firestore.get_document(
                collection=f"categories/{user_id}/user_categories",
                document_id=category_id,
                model_class=Category
            )
            
            if not category:
                raise NotFoundError(
                    message="Category not found",
                    resource_type="category",
                    resource_id=category_id
                )
            
            return CategoryResponse(
                id=category.id,
                name=category.name,
                category_type=category.category_type,
                parent_id=category.parent_id,
                color=category.color,
                icon=category.icon,
                is_system=category.is_system,
                is_active=category.is_active,
                created_at=category.created_at,
                updated_at=category.updated_at
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get category", user_id=user_id, category_id=category_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve category",
                details=[str(e)]
            )
    
    async def list_categories(
        self, 
        user_id: str, 
        category_type: Optional[str] = None,
        parent_id: Optional[str] = None,
        active_only: bool = False
    ) -> List[CategorySummary]:
        """List user categories with optional filters."""
        try:
            where_clauses = []
            
            if category_type:
                where_clauses.append(("category_type", "==", category_type))
            if parent_id:
                where_clauses.append(("parent_id", "==", parent_id))
            if active_only:
                where_clauses.append(("is_active", "==", True))
            
            categories = await self.firestore.query_documents(
                collection=f"categories/{user_id}/user_categories",
                model_class=Category,
                where_clauses=where_clauses,
                order_by=[("name", "asc")]
            )
            
            return [
                CategorySummary(
                    id=category.id,
                    name=category.name,
                    category_type=category.category_type,
                    parent_id=category.parent_id,
                    color=category.color,
                    icon=category.icon,
                    is_system=category.is_system,
                    is_active=category.is_active
                )
                for category in categories
            ]
            
        except Exception as e:
            logger.error("Failed to list categories", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve categories",
                details=[str(e)]
            )
    
    async def update_category(
        self, 
        user_id: str, 
        category_id: str, 
        request: CategoryUpdateRequest
    ) -> CategoryResponse:
        """Update category."""
        try:
            # Get existing category
            category = await self.firestore.get_document(
                collection=f"categories/{user_id}/user_categories",
                document_id=category_id,
                model_class=Category
            )
            
            if not category:
                raise NotFoundError(
                    message="Category not found",
                    resource_type="category",
                    resource_id=category_id
                )
            
            # System categories cannot be modified
            if category.is_system:
                raise AppValidationError(
                    message="Cannot modify system categories",
                    details=["System categories are read-only"]
                )
            
            # Validate parent category if being changed
            if request.parent_id and request.parent_id != category.parent_id:
                # Check parent exists
                parent_category = await self.firestore.get_document(
                    collection=f"categories/{user_id}/user_categories",
                    document_id=request.parent_id,
                    model_class=Category
                )
                if not parent_category:
                    raise AppValidationError(
                        message="Parent category not found",
                        details=[f"Parent category {request.parent_id} does not exist"]
                    )
                
                # Prevent circular references
                if request.parent_id == category_id:
                    raise AppValidationError(
                        message="Cannot set category as its own parent",
                        details=["Circular reference detected"]
                    )
            
            # Update fields
            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.parent_id is not None:
                update_data["parent_id"] = request.parent_id
            if request.color is not None:
                update_data["color"] = request.color
            if request.icon is not None:
                update_data["icon"] = request.icon
            if request.is_active is not None:
                update_data["is_active"] = request.is_active
            
            # Update timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            # Apply updates to model
            for field, value in update_data.items():
                setattr(category, field, value)
            
            # Save to Firestore
            await self.firestore.update_document(
                collection=f"categories/{user_id}/user_categories",
                document_id=category_id,
                data=category
            )
            
            logger.info(
                "Category updated successfully",
                user_id=user_id,
                category_id=category_id,
                fields_updated=list(update_data.keys())
            )
            
            return CategoryResponse(
                id=category.id,
                name=category.name,
                category_type=category.category_type,
                parent_id=category.parent_id,
                color=category.color,
                icon=category.icon,
                is_system=category.is_system,
                is_active=category.is_active,
                created_at=category.created_at,
                updated_at=category.updated_at
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to update category", user_id=user_id, category_id=category_id, error=str(e))
            raise AppValidationError(
                message="Failed to update category",
                details=[str(e)]
            )
    
    async def delete_category(self, user_id: str, category_id: str) -> None:
        """Soft delete category."""
        try:
            # Get existing category
            category = await self.firestore.get_document(
                collection=f"categories/{user_id}/user_categories",
                document_id=category_id,
                model_class=Category
            )
            
            if not category:
                raise NotFoundError(
                    message="Category not found",
                    resource_type="category",
                    resource_id=category_id
                )
            
            # System categories cannot be deleted
            if category.is_system:
                raise AppValidationError(
                    message="Cannot delete system categories",
                    details=["System categories are protected"]
                )
            
            # Check if category has subcategories
            subcategories = await self.firestore.query_documents(
                collection=f"categories/{user_id}/user_categories",
                model_class=Category,
                where_clauses=[("parent_id", "==", category_id)]
            )
            
            if subcategories:
                raise AppValidationError(
                    message="Cannot delete category with subcategories",
                    details=[f"Category has {len(subcategories)} subcategories"]
                )
            
            # Soft delete
            category.soft_delete()
            
            # Save to Firestore
            await self.firestore.update_document(
                collection=f"categories/{user_id}/user_categories",
                document_id=category_id,
                data=category
            )
            
            logger.info(
                "Category deleted successfully",
                user_id=user_id,
                category_id=category_id,
                category_name=category.name
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete category", user_id=user_id, category_id=category_id, error=str(e))
            raise AppValidationError(
                message="Failed to delete category",
                details=[str(e)]
            )


# Global service instance
_category_service: Optional[CategoryService] = None


def get_category_service() -> CategoryService:
    """Get the global category service instance."""
    global _category_service
    if _category_service is None:
        _category_service = CategoryService()
    return _category_service