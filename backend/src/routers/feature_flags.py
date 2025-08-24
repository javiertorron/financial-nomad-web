"""
Feature flags management endpoints.
Provides dynamic feature flag configuration and evaluation.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, status, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional
from src.services.feature_flags import (
    get_feature_flags_service,
    FeatureFlag,
    FlagType,
    FlagVariant,
    FlagTarget,
    TargetingRule,
    is_feature_enabled,
    get_feature_variant,
    get_user_features
)

logger = structlog.get_logger()
router = APIRouter()


class FlagVariantRequest(BaseModel):
    """Feature flag variant request model."""
    key: str = Field(..., description="Variant key")
    value: Any = Field(..., description="Variant value")
    weight: int = Field(default=100, description="Variant weight for percentage rollouts")
    description: str = Field(default="", description="Variant description")


class FlagTargetRequest(BaseModel):
    """Feature flag targeting rule request model."""
    rule: str = Field(..., description="Targeting rule type")
    operator: str = Field(..., description="Comparison operator")
    values: List[str] = Field(..., description="Target values")
    variant_key: Optional[str] = Field(None, description="Variant to serve")


class FeatureFlagRequest(BaseModel):
    """Feature flag creation/update request model."""
    key: str = Field(..., description="Feature flag key")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Flag description")
    type: str = Field(default="boolean", description="Flag type")
    enabled: bool = Field(default=True, description="Flag enabled status")
    default_variant: str = Field(default="control", description="Default variant")
    variants: List[FlagVariantRequest] = Field(default_factory=list, description="Flag variants")
    targeting_rules: List[FlagTargetRequest] = Field(default_factory=list, description="Targeting rules")
    rollout_percentage: int = Field(default=100, description="Rollout percentage")
    environment_filters: List[str] = Field(default_factory=list, description="Environment filters")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    tags: List[str] = Field(default_factory=list, description="Flag tags")


class FeatureFlagResponse(BaseModel):
    """Feature flag response model."""
    key: str
    name: str
    description: str
    type: str
    enabled: bool
    default_variant: str
    variants: List[Dict[str, Any]]
    targeting_rules: List[Dict[str, Any]]
    rollout_percentage: int
    environment_filters: List[str]
    start_date: Optional[str]
    end_date: Optional[str]
    created_at: str
    updated_at: str
    created_by: str
    tags: List[str]


class FlagEvaluationRequest(BaseModel):
    """Feature flag evaluation request model."""
    flags: List[str] = Field(..., description="Flag keys to evaluate")
    context: Dict[str, Any] = Field(default_factory=dict, description="User context for evaluation")


class FlagEvaluationResponse(BaseModel):
    """Feature flag evaluation response model."""
    flags: Dict[str, Any] = Field(..., description="Evaluated flag values")
    context_used: Dict[str, Any] = Field(..., description="Context used for evaluation")
    timestamp: str = Field(..., description="Evaluation timestamp")


@router.get(
    "/flags",
    status_code=status.HTTP_200_OK,
    summary="List All Feature Flags",
    description="Returns all feature flags with their configurations",
    response_model=List[FeatureFlagResponse],
    tags=["Feature Flags"]
)
async def list_feature_flags(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[FeatureFlagResponse]:
    """
    **List all feature flags**
    
    Returns comprehensive information about all feature flags including:
    - Flag configuration and variants
    - Targeting rules and rollout settings
    - Environment and date filters
    - Creation and update metadata
    
    This endpoint is useful for:
    - Feature flag management dashboards
    - Configuration auditing
    - Development and testing
    """
    try:
        service = get_feature_flags_service()
        flags_info = service.list_all_flags()
        
        return [FeatureFlagResponse(**flag_info) for flag_info in flags_info]
        
    except Exception as e:
        logger.error("Failed to list feature flags", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feature flags"
        )


@router.get(
    "/flags/{flag_key}",
    status_code=status.HTTP_200_OK,
    summary="Get Feature Flag Details",
    description="Returns detailed information about a specific feature flag",
    response_model=FeatureFlagResponse,
    tags=["Feature Flags"]
)
async def get_feature_flag(
    flag_key: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> FeatureFlagResponse:
    """
    **Get feature flag details**
    
    Returns comprehensive information about a specific feature flag:
    - Current configuration and status
    - All variants and their values
    - Targeting rules and conditions
    - Rollout and environment settings
    """
    try:
        service = get_feature_flags_service()
        flag_info = service.get_flag_info(flag_key)
        
        if not flag_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag '{flag_key}' not found"
            )
        
        return FeatureFlagResponse(**flag_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get feature flag", flag_key=flag_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feature flag '{flag_key}'"
        )


@router.post(
    "/flags",
    status_code=status.HTTP_201_CREATED,
    summary="Create Feature Flag",
    description="Creates a new feature flag with the specified configuration",
    response_model=FeatureFlagResponse,
    tags=["Feature Flags"]
)
async def create_feature_flag(
    flag_request: FeatureFlagRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> FeatureFlagResponse:
    """
    **Create new feature flag**
    
    Creates a feature flag with:
    - Basic configuration (name, description, type)
    - Variants with different values
    - Targeting rules for specific users/conditions
    - Rollout percentage for gradual deployment
    - Environment and date filters
    
    Requires administrative privileges in production.
    """
    try:
        # Check permissions (in production, require admin role)
        if settings.is_production and (not current_user or current_user.get('role') != 'admin'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to create feature flags"
            )
        
        service = get_feature_flags_service()
        
        # Convert request to FeatureFlag
        flag = FeatureFlag(
            key=flag_request.key,
            name=flag_request.name,
            description=flag_request.description,
            type=FlagType(flag_request.type),
            enabled=flag_request.enabled,
            default_variant=flag_request.default_variant,
            variants=[
                FlagVariant(
                    key=v.key,
                    value=v.value,
                    weight=v.weight,
                    description=v.description
                ) for v in flag_request.variants
            ],
            targeting_rules=[
                FlagTarget(
                    rule=TargetingRule(t.rule),
                    operator=t.operator,
                    values=t.values,
                    variant_key=t.variant_key
                ) for t in flag_request.targeting_rules
            ],
            rollout_percentage=flag_request.rollout_percentage,
            environment_filters=flag_request.environment_filters,
            start_date=datetime.fromisoformat(flag_request.start_date) if flag_request.start_date else None,
            end_date=datetime.fromisoformat(flag_request.end_date) if flag_request.end_date else None,
            created_by=current_user.get('email', 'unknown') if current_user else 'system',
            tags=flag_request.tags
        )
        
        success = service.create_flag(flag)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create feature flag '{flag_request.key}' - may already exist"
            )
        
        # Return created flag
        flag_info = service.get_flag_info(flag_request.key)
        return FeatureFlagResponse(**flag_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create feature flag", flag_key=flag_request.key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create feature flag '{flag_request.key}'"
        )


@router.put(
    "/flags/{flag_key}",
    status_code=status.HTTP_200_OK,
    summary="Update Feature Flag",
    description="Updates an existing feature flag configuration",
    response_model=FeatureFlagResponse,
    tags=["Feature Flags"]
)
async def update_feature_flag(
    flag_key: str,
    updates: Dict[str, Any],
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> FeatureFlagResponse:
    """
    **Update feature flag**
    
    Updates feature flag configuration:
    - Enable/disable flags
    - Modify variants and targeting rules
    - Adjust rollout percentages
    - Update environment filters
    
    Requires administrative privileges in production.
    """
    try:
        # Check permissions
        if settings.is_production and (not current_user or current_user.get('role') != 'admin'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to update feature flags"
            )
        
        service = get_feature_flags_service()
        
        success = service.update_flag(flag_key, updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag '{flag_key}' not found"
            )
        
        # Return updated flag
        flag_info = service.get_flag_info(flag_key)
        return FeatureFlagResponse(**flag_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update feature flag", flag_key=flag_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update feature flag '{flag_key}'"
        )


@router.delete(
    "/flags/{flag_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Feature Flag",
    description="Deletes a feature flag",
    tags=["Feature Flags"]
)
async def delete_feature_flag(
    flag_key: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """
    **Delete feature flag**
    
    Permanently removes a feature flag from the system.
    Use with caution as this cannot be undone.
    
    Requires administrative privileges.
    """
    try:
        # Check permissions
        if not current_user or current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to delete feature flags"
            )
        
        service = get_feature_flags_service()
        
        success = service.delete_flag(flag_key)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag '{flag_key}' not found"
            )
        
        logger.info("Feature flag deleted", flag_key=flag_key, 
                   deleted_by=current_user.get('email', 'unknown'))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete feature flag", flag_key=flag_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete feature flag '{flag_key}'"
        )


@router.post(
    "/evaluate",
    status_code=status.HTTP_200_OK,
    summary="Evaluate Feature Flags",
    description="Evaluates feature flags for a given user context",
    response_model=FlagEvaluationResponse,
    tags=["Feature Flags"]
)
async def evaluate_feature_flags(
    evaluation_request: FlagEvaluationRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> FlagEvaluationResponse:
    """
    **Evaluate feature flags**
    
    Evaluates feature flags based on user context:
    - User attributes and preferences
    - Targeting rules and conditions
    - Rollout percentages
    - Environment and date filters
    
    Returns the actual values that should be used by the application.
    """
    try:
        service = get_feature_flags_service()
        
        # Merge current user context with provided context
        user_context = evaluation_request.context.copy()
        if current_user:
            user_context.update({
                'user_id': current_user.get('id'),
                'user_email': current_user.get('email'),
                'user_role': current_user.get('role', 'user')
            })
        
        # Evaluate requested flags
        flag_results = {}
        for flag_key in evaluation_request.flags:
            flag_results[flag_key] = service.get_variant(flag_key, user_context)
        
        return FlagEvaluationResponse(
            flags=flag_results,
            context_used=user_context,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        logger.error("Failed to evaluate feature flags", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate feature flags"
        )


@router.get(
    "/evaluate/{flag_key}",
    status_code=status.HTTP_200_OK,
    summary="Evaluate Single Feature Flag",
    description="Evaluates a single feature flag for the current user",
    tags=["Feature Flags"]
)
async def evaluate_single_flag(
    flag_key: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Evaluate single feature flag**
    
    Quick evaluation of a single feature flag using current user context.
    Useful for client-side feature checks and API integrations.
    """
    try:
        # Build user context
        user_context = {}
        if current_user:
            user_context = {
                'user_id': current_user.get('id'),
                'user_email': current_user.get('email'),
                'user_role': current_user.get('role', 'user')
            }
        
        service = get_feature_flags_service()
        value = service.get_variant(flag_key, user_context)
        
        return {
            "flag_key": flag_key,
            "value": value,
            "enabled": bool(value) if isinstance(value, bool) else value is not None,
            "context": user_context,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error("Failed to evaluate feature flag", flag_key=flag_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate feature flag '{flag_key}'"
        )


@router.get(
    "/user/features",
    status_code=status.HTTP_200_OK,
    summary="Get User's Feature Flags",
    description="Returns all feature flags evaluated for the current user",
    tags=["Feature Flags"]
)
async def get_user_feature_flags(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Get all features for current user**
    
    Returns all feature flags evaluated for the current user context.
    This is the primary endpoint for client applications to get
    their feature configuration.
    
    Includes:
    - All enabled features
    - User-specific variants
    - Contextual configurations
    """
    try:
        # Build user context
        user_context = {}
        if current_user:
            user_context = {
                'user_id': current_user.get('id'),
                'user_email': current_user.get('email'),
                'user_role': current_user.get('role', 'user'),
                'subscription_tier': current_user.get('subscription_tier', 'free'),
                'registration_date': current_user.get('created_at')
            }
        
        features = get_user_features(user_context)
        
        return {
            "features": features,
            "context": user_context,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_authenticated": current_user is not None
        }
        
    except Exception as e:
        logger.error("Failed to get user features", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user features"
        )


@router.post(
    "/flags/{flag_key}/toggle",
    status_code=status.HTTP_200_OK,
    summary="Toggle Feature Flag",
    description="Quickly enable or disable a feature flag",
    tags=["Feature Flags"]
)
async def toggle_feature_flag(
    flag_key: str,
    enabled: bool = Query(..., description="Enable or disable the flag"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Toggle feature flag**
    
    Quick enable/disable operation for feature flags.
    Useful for emergency shutoffs or quick feature activation.
    
    Requires administrative privileges.
    """
    try:
        # Check permissions
        if settings.is_production and (not current_user or current_user.get('role') != 'admin'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to toggle feature flags"
            )
        
        service = get_feature_flags_service()
        
        success = service.update_flag(flag_key, {'enabled': enabled})
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag '{flag_key}' not found"
            )
        
        logger.info("Feature flag toggled", 
                   flag_key=flag_key, enabled=enabled,
                   toggled_by=current_user.get('email', 'unknown') if current_user else 'system')
        
        return {
            "flag_key": flag_key,
            "enabled": enabled,
            "message": f"Feature flag '{flag_key}' {'enabled' if enabled else 'disabled'}",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to toggle feature flag", flag_key=flag_key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle feature flag '{flag_key}'"
        )