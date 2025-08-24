"""
Dynamic feature flags service.
Allows enabling/disabling features at runtime without deployment.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field, asdict
from threading import Lock
import structlog

from src.config import settings

logger = structlog.get_logger()


class FlagType(Enum):
    """Types of feature flags."""
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"
    PERCENTAGE = "percentage"


class TargetingRule(Enum):
    """User targeting rules."""
    USER_ID = "user_id"
    USER_EMAIL = "user_email" 
    USER_ROLE = "user_role"
    IP_ADDRESS = "ip_address"
    COUNTRY = "country"
    SUBSCRIPTION_TIER = "subscription_tier"
    REGISTRATION_DATE = "registration_date"
    CUSTOM_ATTRIBUTE = "custom_attribute"


@dataclass
class FlagVariant:
    """Feature flag variant/option."""
    key: str
    value: Any
    weight: int = 100  # For percentage rollouts
    description: str = ""


@dataclass
class FlagTarget:
    """Feature flag targeting rule."""
    rule: TargetingRule
    operator: str  # eq, ne, in, not_in, gt, lt, gte, lte, contains, regex
    values: List[str]
    variant_key: Optional[str] = None  # Which variant to serve


@dataclass
class FeatureFlag:
    """Feature flag configuration."""
    key: str
    name: str
    description: str
    type: FlagType
    enabled: bool = True
    default_variant: str = "control"
    variants: List[FlagVariant] = field(default_factory=list)
    targeting_rules: List[FlagTarget] = field(default_factory=list)
    rollout_percentage: int = 100  # Percentage of users to include
    environment_filters: List[str] = field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    tags: List[str] = field(default_factory=list)


class FeatureFlagsService:
    """Service for managing dynamic feature flags."""
    
    def __init__(self):
        self.flags: Dict[str, FeatureFlag] = {}
        self.flag_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_lock = Lock()
        self.cache_ttl = 300  # 5 minutes cache TTL
        
        # Initialize with default flags
        self._initialize_default_flags()
        
        logger.info("Feature flags service initialized")

    def _initialize_default_flags(self):
        """Initialize with default feature flags."""
        default_flags = [
            FeatureFlag(
                key="asana_integration",
                name="Asana Integration",
                description="Enable Asana task synchronization features",
                type=FlagType.BOOLEAN,
                enabled=True,
                variants=[
                    FlagVariant("enabled", True, description="Full Asana integration"),
                    FlagVariant("disabled", False, description="Asana integration disabled")
                ]
            ),
            FeatureFlag(
                key="advanced_analytics", 
                name="Advanced Analytics",
                description="Enable advanced financial analytics and reporting",
                type=FlagType.BOOLEAN,
                enabled=not settings.is_testing,
                variants=[
                    FlagVariant("enabled", True, description="Full analytics suite"),
                    FlagVariant("disabled", False, description="Basic analytics only")
                ]
            ),
            FeatureFlag(
                key="export_features",
                name="Export Features", 
                description="Enable data export functionality",
                type=FlagType.BOOLEAN,
                enabled=True,
                variants=[
                    FlagVariant("full", True, description="All export formats"),
                    FlagVariant("limited", {"formats": ["json"]}, description="JSON export only"),
                    FlagVariant("disabled", False, description="No exports")
                ]
            ),
            FeatureFlag(
                key="new_dashboard",
                name="New Dashboard UI",
                description="Enable new dashboard interface",
                type=FlagType.BOOLEAN,
                enabled=False,
                rollout_percentage=25,  # Gradual rollout
                variants=[
                    FlagVariant("enabled", True, description="New dashboard UI"),
                    FlagVariant("disabled", False, description="Legacy dashboard")
                ]
            ),
            FeatureFlag(
                key="api_rate_limit",
                name="API Rate Limiting",
                description="Dynamic API rate limiting configuration",
                type=FlagType.JSON,
                enabled=True,
                variants=[
                    FlagVariant("standard", {"requests_per_minute": 100, "burst": 20}),
                    FlagVariant("premium", {"requests_per_minute": 500, "burst": 50}),
                    FlagVariant("unlimited", {"requests_per_minute": -1, "burst": -1})
                ],
                targeting_rules=[
                    FlagTarget(
                        rule=TargetingRule.USER_ROLE,
                        operator="in",
                        values=["premium", "admin"],
                        variant_key="premium"
                    )
                ]
            ),
            FeatureFlag(
                key="maintenance_mode",
                name="Maintenance Mode",
                description="Put application in maintenance mode",
                type=FlagType.BOOLEAN,
                enabled=False,
                variants=[
                    FlagVariant("enabled", True, description="Maintenance mode active"),
                    FlagVariant("disabled", False, description="Normal operation")
                ]
            )
        ]
        
        for flag in default_flags:
            self.flags[flag.key] = flag

    def create_flag(self, flag: FeatureFlag) -> bool:
        """Create a new feature flag."""
        try:
            if flag.key in self.flags:
                logger.warning("Feature flag already exists", flag_key=flag.key)
                return False
            
            flag.created_at = datetime.utcnow()
            flag.updated_at = datetime.utcnow()
            
            self.flags[flag.key] = flag
            self._clear_cache(flag.key)
            
            logger.info("Feature flag created", flag_key=flag.key, name=flag.name)
            return True
            
        except Exception as e:
            logger.error("Failed to create feature flag", flag_key=flag.key, error=str(e))
            return False

    def update_flag(self, flag_key: str, updates: Dict[str, Any]) -> bool:
        """Update an existing feature flag."""
        try:
            if flag_key not in self.flags:
                logger.warning("Feature flag not found", flag_key=flag_key)
                return False
            
            flag = self.flags[flag_key]
            
            # Update allowed fields
            for field_name, value in updates.items():
                if hasattr(flag, field_name):
                    setattr(flag, field_name, value)
            
            flag.updated_at = datetime.utcnow()
            self._clear_cache(flag_key)
            
            logger.info("Feature flag updated", flag_key=flag_key, updates=list(updates.keys()))
            return True
            
        except Exception as e:
            logger.error("Failed to update feature flag", flag_key=flag_key, error=str(e))
            return False

    def delete_flag(self, flag_key: str) -> bool:
        """Delete a feature flag."""
        try:
            if flag_key not in self.flags:
                logger.warning("Feature flag not found for deletion", flag_key=flag_key)
                return False
            
            del self.flags[flag_key]
            self._clear_cache(flag_key)
            
            logger.info("Feature flag deleted", flag_key=flag_key)
            return True
            
        except Exception as e:
            logger.error("Failed to delete feature flag", flag_key=flag_key, error=str(e))
            return False

    def is_enabled(self, flag_key: str, user_context: Optional[Dict[str, Any]] = None, 
                   default: bool = False) -> bool:
        """Check if a feature flag is enabled for the given context."""
        try:
            result = self.get_variant(flag_key, user_context)
            
            if result is None:
                return default
            
            # Handle boolean flags
            if isinstance(result, bool):
                return result
            
            # Handle other types - consider enabled if not False/None
            return result is not False and result is not None
            
        except Exception as e:
            logger.error("Error checking feature flag", flag_key=flag_key, error=str(e))
            return default

    def get_variant(self, flag_key: str, user_context: Optional[Dict[str, Any]] = None) -> Any:
        """Get the variant value for a feature flag given the user context."""
        try:
            # Check cache first
            cache_key = self._get_cache_key(flag_key, user_context)
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Get flag
            flag = self.flags.get(flag_key)
            if not flag:
                logger.debug("Feature flag not found", flag_key=flag_key)
                return None
            
            # Check if flag is globally enabled
            if not flag.enabled:
                result = self._get_variant_value(flag, flag.default_variant)
                self._cache_result(cache_key, result)
                return result
            
            # Check environment filters
            if flag.environment_filters and settings.environment not in flag.environment_filters:
                result = self._get_variant_value(flag, flag.default_variant)
                self._cache_result(cache_key, result)
                return result
            
            # Check date range
            now = datetime.utcnow()
            if flag.start_date and now < flag.start_date:
                result = self._get_variant_value(flag, flag.default_variant)
                self._cache_result(cache_key, result)
                return result
            
            if flag.end_date and now > flag.end_date:
                result = self._get_variant_value(flag, flag.default_variant)
                self._cache_result(cache_key, result)
                return result
            
            # Check targeting rules
            target_variant = self._evaluate_targeting_rules(flag, user_context)
            if target_variant:
                result = self._get_variant_value(flag, target_variant)
                self._cache_result(cache_key, result)
                return result
            
            # Check rollout percentage
            if not self._is_in_rollout(flag, user_context):
                result = self._get_variant_value(flag, flag.default_variant)
                self._cache_result(cache_key, result)
                return result
            
            # Return default variant
            result = self._get_variant_value(flag, flag.default_variant)
            self._cache_result(cache_key, result)
            return result
            
        except Exception as e:
            logger.error("Error evaluating feature flag", flag_key=flag_key, error=str(e))
            return None

    def get_all_flags(self, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get all feature flags evaluated for the given context."""
        result = {}
        
        for flag_key in self.flags.keys():
            result[flag_key] = self.get_variant(flag_key, user_context)
        
        return result

    def get_flag_info(self, flag_key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a feature flag."""
        flag = self.flags.get(flag_key)
        if not flag:
            return None
        
        return {
            "key": flag.key,
            "name": flag.name,
            "description": flag.description,
            "type": flag.type.value,
            "enabled": flag.enabled,
            "default_variant": flag.default_variant,
            "variants": [asdict(v) for v in flag.variants],
            "targeting_rules": [
                {
                    "rule": t.rule.value,
                    "operator": t.operator,
                    "values": t.values,
                    "variant_key": t.variant_key
                } 
                for t in flag.targeting_rules
            ],
            "rollout_percentage": flag.rollout_percentage,
            "environment_filters": flag.environment_filters,
            "start_date": flag.start_date.isoformat() if flag.start_date else None,
            "end_date": flag.end_date.isoformat() if flag.end_date else None,
            "created_at": flag.created_at.isoformat(),
            "updated_at": flag.updated_at.isoformat(),
            "created_by": flag.created_by,
            "tags": flag.tags
        }

    def list_all_flags(self) -> List[Dict[str, Any]]:
        """List all feature flags with their configurations."""
        return [self.get_flag_info(flag_key) for flag_key in self.flags.keys()]

    def _evaluate_targeting_rules(self, flag: FeatureFlag, user_context: Optional[Dict[str, Any]]) -> Optional[str]:
        """Evaluate targeting rules to determine variant."""
        if not user_context or not flag.targeting_rules:
            return None
        
        for target in flag.targeting_rules:
            if self._matches_targeting_rule(target, user_context):
                return target.variant_key or flag.default_variant
        
        return None

    def _matches_targeting_rule(self, target: FlagTarget, user_context: Dict[str, Any]) -> bool:
        """Check if user context matches a targeting rule."""
        context_value = user_context.get(target.rule.value)
        if context_value is None:
            return False
        
        context_str = str(context_value)
        
        if target.operator == "eq":
            return context_str in target.values
        elif target.operator == "ne":
            return context_str not in target.values
        elif target.operator == "in":
            return context_str in target.values
        elif target.operator == "not_in":
            return context_str not in target.values
        elif target.operator == "contains":
            return any(val in context_str for val in target.values)
        elif target.operator == "regex":
            import re
            return any(re.match(pattern, context_str) for pattern in target.values)
        elif target.operator in ["gt", "lt", "gte", "lte"]:
            try:
                context_num = float(context_value)
                target_num = float(target.values[0]) if target.values else 0
                
                if target.operator == "gt":
                    return context_num > target_num
                elif target.operator == "lt":
                    return context_num < target_num
                elif target.operator == "gte":
                    return context_num >= target_num
                elif target.operator == "lte":
                    return context_num <= target_num
            except (ValueError, IndexError):
                return False
        
        return False

    def _is_in_rollout(self, flag: FeatureFlag, user_context: Optional[Dict[str, Any]]) -> bool:
        """Check if user is in the rollout percentage."""
        if flag.rollout_percentage >= 100:
            return True
        
        if flag.rollout_percentage <= 0:
            return False
        
        # Use user ID for consistent bucketing
        user_id = user_context.get('user_id', 'anonymous') if user_context else 'anonymous'
        
        # Simple hash-based bucketing
        import hashlib
        hash_input = f"{flag.key}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = hash_value % 100
        
        return bucket < flag.rollout_percentage

    def _get_variant_value(self, flag: FeatureFlag, variant_key: str) -> Any:
        """Get the value for a specific variant."""
        for variant in flag.variants:
            if variant.key == variant_key:
                return variant.value
        
        # Fallback to default boolean value
        return True if variant_key == "enabled" else False

    def _get_cache_key(self, flag_key: str, user_context: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for flag evaluation."""
        context_str = ""
        if user_context:
            # Sort keys for consistent cache keys
            sorted_context = sorted(user_context.items())
            context_str = json.dumps(sorted_context, sort_keys=True)
        
        return f"{flag_key}:{hash(context_str)}"

    def _get_cached_result(self, cache_key: str) -> Any:
        """Get cached flag result."""
        with self.cache_lock:
            cached = self.flag_cache.get(cache_key)
            if cached and time.time() - cached['timestamp'] < self.cache_ttl:
                return cached['value']
        return None

    def _cache_result(self, cache_key: str, result: Any):
        """Cache flag evaluation result."""
        with self.cache_lock:
            self.flag_cache[cache_key] = {
                'value': result,
                'timestamp': time.time()
            }
            
            # Clean old cache entries
            self._cleanup_cache()

    def _clear_cache(self, flag_key: str):
        """Clear cache entries for a specific flag."""
        with self.cache_lock:
            keys_to_remove = [key for key in self.flag_cache.keys() if key.startswith(f"{flag_key}:")]
            for key in keys_to_remove:
                del self.flag_cache[key]

    def _cleanup_cache(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, data in self.flag_cache.items()
            if current_time - data['timestamp'] >= self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.flag_cache[key]


# Global instance
_feature_flags_service = None


def get_feature_flags_service() -> FeatureFlagsService:
    """Get global feature flags service instance."""
    global _feature_flags_service
    if _feature_flags_service is None:
        _feature_flags_service = FeatureFlagsService()
    return _feature_flags_service


# Convenience functions
def is_feature_enabled(flag_key: str, user_context: Optional[Dict[str, Any]] = None, default: bool = False) -> bool:
    """Check if a feature is enabled."""
    service = get_feature_flags_service()
    return service.is_enabled(flag_key, user_context, default)


def get_feature_variant(flag_key: str, user_context: Optional[Dict[str, Any]] = None) -> Any:
    """Get feature variant value."""
    service = get_feature_flags_service()
    return service.get_variant(flag_key, user_context)


def get_user_features(user_context: Dict[str, Any]) -> Dict[str, Any]:
    """Get all features for a user context."""
    service = get_feature_flags_service()
    return service.get_all_flags(user_context)