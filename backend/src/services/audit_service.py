"""
Advanced Audit and Compliance Service.
Provides comprehensive audit logging, compliance monitoring, and regulatory
reporting capabilities for financial data and user activities.
"""

import asyncio
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
import structlog
from ipaddress import IPv4Address, IPv6Address, AddressValueError

from src.config import settings

logger = structlog.get_logger()


class AuditEventType(Enum):
    """Types of audit events."""
    # Authentication Events
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTER = "user.register"
    PASSWORD_CHANGE = "user.password_change"
    PASSWORD_RESET = "user.password_reset"
    MFA_ENABLED = "user.mfa_enabled"
    MFA_DISABLED = "user.mfa_disabled"
    
    # Data Operations
    TRANSACTION_CREATE = "transaction.create"
    TRANSACTION_UPDATE = "transaction.update"
    TRANSACTION_DELETE = "transaction.delete"
    ACCOUNT_CREATE = "account.create"
    ACCOUNT_UPDATE = "account.update"
    ACCOUNT_DELETE = "account.delete"
    CATEGORY_CREATE = "category.create"
    CATEGORY_UPDATE = "category.update"
    CATEGORY_DELETE = "category.delete"
    BUDGET_CREATE = "budget.create"
    BUDGET_UPDATE = "budget.update"
    BUDGET_DELETE = "budget.delete"
    
    # Data Access
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"
    REPORT_GENERATE = "report.generate"
    BACKUP_CREATE = "backup.create"
    BACKUP_RESTORE = "backup.restore"
    
    # Administrative
    USER_PROMOTE = "admin.user_promote"
    USER_DEMOTE = "admin.user_demote"
    USER_SUSPEND = "admin.user_suspend"
    USER_ACTIVATE = "admin.user_activate"
    SYSTEM_CONFIG = "admin.system_config"
    
    # Security Events
    LOGIN_FAILURE = "security.login_failure"
    RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "security.suspicious_activity"
    DATA_BREACH_ATTEMPT = "security.breach_attempt"
    UNAUTHORIZED_ACCESS = "security.unauthorized_access"
    
    # Compliance
    GDPR_REQUEST = "compliance.gdpr_request"
    DATA_RETENTION = "compliance.data_retention"
    PRIVACY_SETTING = "compliance.privacy_setting"


class AuditSeverity(Enum):
    """Audit event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(Enum):
    """Supported compliance frameworks."""
    GDPR = "gdpr"
    CCPA = "ccpa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    HIPAA = "hipaa"


class AuditStatus(Enum):
    """Audit record status."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    QUARANTINED = "quarantined"


@dataclass
class AuditContext:
    """Context information for audit events."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    geo_location: Optional[Dict[str, str]] = None
    device_info: Optional[Dict[str, str]] = None
    api_version: Optional[str] = None
    client_info: Optional[Dict[str, str]] = None


@dataclass
class AuditEvent:
    """Comprehensive audit event record."""
    id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    description: str
    
    # Event Details
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    context: Optional[AuditContext] = None
    
    # Compliance
    compliance_frameworks: List[ComplianceFramework] = field(default_factory=list)
    retention_period_days: int = 2555  # 7 years default
    
    # Status and Integrity
    status: AuditStatus = AuditStatus.ACTIVE
    checksum: Optional[str] = None
    encrypted: bool = False
    
    # Relationships
    parent_event_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate checksum after initialization."""
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate integrity checksum for the audit record."""
        data = {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "description": self.description,
            "old_values": self.old_values,
            "new_values": self.new_values
        }
        
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify the integrity of the audit record."""
        if not self.checksum:
            return False
        
        current_checksum = self._calculate_checksum()
        return current_checksum == self.checksum


@dataclass
class ComplianceRule:
    """Compliance monitoring rule."""
    id: str
    name: str
    framework: ComplianceFramework
    rule_type: str
    description: str
    query_pattern: Dict[str, Any]
    threshold_config: Optional[Dict[str, Any]] = None
    notification_config: Optional[Dict[str, Any]] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComplianceViolation:
    """Compliance violation record."""
    id: str
    rule_id: str
    rule_name: str
    framework: ComplianceFramework
    severity: AuditSeverity
    description: str
    violation_data: Dict[str, Any]
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    status: str = "open"  # open, investigating, resolved, false_positive


class AuditEncryption:
    """Handles encryption of sensitive audit data."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key or settings.backup_encryption_key
    
    def encrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in audit data."""
        # In real implementation, use proper encryption like Fernet
        # For now, just mark sensitive fields
        sensitive_fields = ['password', 'ssn', 'credit_card', 'bank_account']
        
        encrypted_data = data.copy()
        for field in sensitive_fields:
            if field in encrypted_data:
                encrypted_data[field] = "***ENCRYPTED***"
        
        return encrypted_data
    
    def decrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in audit data."""
        # In real implementation, decrypt using proper key management
        return data


class ComplianceMonitor:
    """Monitors audit events for compliance violations."""
    
    def __init__(self):
        self.rules: Dict[str, ComplianceRule] = {}
        self.violations: List[ComplianceViolation] = []
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default compliance rules."""
        # GDPR Rules
        gdpr_rules = [
            ComplianceRule(
                id="gdpr_data_access_logging",
                name="GDPR Data Access Logging",
                framework=ComplianceFramework.GDPR,
                rule_type="data_access",
                description="All personal data access must be logged",
                query_pattern={"event_type": ["transaction.create", "transaction.update", "account.create"]},
                threshold_config={"required": True}
            ),
            ComplianceRule(
                id="gdpr_data_retention",
                name="GDPR Data Retention",
                framework=ComplianceFramework.GDPR,
                rule_type="retention",
                description="Personal data must not be retained beyond necessary period",
                query_pattern={"retention_check": True},
                threshold_config={"max_days": 2555}  # 7 years
            )
        ]
        
        # SOX Rules
        sox_rules = [
            ComplianceRule(
                id="sox_financial_changes",
                name="SOX Financial Data Changes",
                framework=ComplianceFramework.SOX,
                rule_type="financial_audit",
                description="All financial data changes must be audited with approval chain",
                query_pattern={"event_type": ["transaction.update", "transaction.delete"]},
                threshold_config={"requires_approval": True}
            )
        ]
        
        # PCI DSS Rules
        pci_rules = [
            ComplianceRule(
                id="pci_payment_logging",
                name="PCI Payment Data Access",
                framework=ComplianceFramework.PCI_DSS,
                rule_type="payment_security",
                description="All payment data access must be logged and encrypted",
                query_pattern={"resource_type": "payment", "encrypted": True},
                threshold_config={"encryption_required": True}
            )
        ]
        
        all_rules = gdpr_rules + sox_rules + pci_rules
        for rule in all_rules:
            self.rules[rule.id] = rule
    
    def check_compliance(self, audit_event: AuditEvent) -> List[ComplianceViolation]:
        """Check if audit event violates any compliance rules."""
        violations = []
        
        for rule in self.rules.values():
            if not rule.is_active:
                continue
            
            if self._matches_rule_pattern(audit_event, rule):
                violation = self._evaluate_rule_violation(audit_event, rule)
                if violation:
                    violations.append(violation)
                    self.violations.append(violation)
        
        return violations
    
    def _matches_rule_pattern(self, event: AuditEvent, rule: ComplianceRule) -> bool:
        """Check if event matches rule pattern."""
        pattern = rule.query_pattern
        
        # Check event type
        if "event_type" in pattern:
            if event.event_type.value not in pattern["event_type"]:
                return False
        
        # Check resource type
        if "resource_type" in pattern:
            if event.resource_type != pattern["resource_type"]:
                return False
        
        # Check severity
        if "severity" in pattern:
            if event.severity.value not in pattern["severity"]:
                return False
        
        return True
    
    def _evaluate_rule_violation(self, event: AuditEvent, rule: ComplianceRule) -> Optional[ComplianceViolation]:
        """Evaluate if event violates the rule."""
        threshold_config = rule.threshold_config or {}
        
        # GDPR Data Access Logging
        if rule.id == "gdpr_data_access_logging":
            if not event.user_id:
                return ComplianceViolation(
                    id=f"violation_{uuid.uuid4().hex[:12]}",
                    rule_id=rule.id,
                    rule_name=rule.name,
                    framework=rule.framework,
                    severity=AuditSeverity.HIGH,
                    description="Personal data access without proper user identification",
                    violation_data={"event_id": event.id, "missing": "user_id"},
                    detected_at=datetime.utcnow()
                )
        
        # SOX Financial Changes
        if rule.id == "sox_financial_changes":
            if event.event_type in [AuditEventType.TRANSACTION_UPDATE, AuditEventType.TRANSACTION_DELETE]:
                if not event.metadata.get("approval_required"):
                    return ComplianceViolation(
                        id=f"violation_{uuid.uuid4().hex[:12]}",
                        rule_id=rule.id,
                        rule_name=rule.name,
                        framework=rule.framework,
                        severity=AuditSeverity.CRITICAL,
                        description="Financial data change without proper approval documentation",
                        violation_data={"event_id": event.id, "missing": "approval_chain"},
                        detected_at=datetime.utcnow()
                    )
        
        # PCI Payment Data
        if rule.id == "pci_payment_logging":
            if event.resource_type == "payment" and not event.encrypted:
                return ComplianceViolation(
                    id=f"violation_{uuid.uuid4().hex[:12]}",
                    rule_id=rule.id,
                    rule_name=rule.name,
                    framework=rule.framework,
                    severity=AuditSeverity.CRITICAL,
                    description="Payment data accessed without proper encryption",
                    violation_data={"event_id": event.id, "missing": "encryption"},
                    detected_at=datetime.utcnow()
                )
        
        return None
    
    def get_violations_by_framework(self, framework: ComplianceFramework) -> List[ComplianceViolation]:
        """Get violations for specific compliance framework."""
        return [v for v in self.violations if v.framework == framework]
    
    def resolve_violation(self, violation_id: str, resolution_notes: str):
        """Mark violation as resolved."""
        for violation in self.violations:
            if violation.id == violation_id:
                violation.status = "resolved"
                violation.resolved_at = datetime.utcnow()
                violation.resolution_notes = resolution_notes
                break


class AuditRetention:
    """Handles audit data retention and archival."""
    
    def __init__(self):
        self.retention_policies = self._load_retention_policies()
    
    def _load_retention_policies(self) -> Dict[ComplianceFramework, int]:
        """Load retention policies for different frameworks."""
        return {
            ComplianceFramework.GDPR: 2555,      # 7 years
            ComplianceFramework.SOX: 2555,       # 7 years
            ComplianceFramework.PCI_DSS: 365,    # 1 year
            ComplianceFramework.ISO_27001: 1095, # 3 years
            ComplianceFramework.HIPAA: 2190,     # 6 years
            ComplianceFramework.CCPA: 1095       # 3 years
        }
    
    def should_retain(self, audit_event: AuditEvent) -> bool:
        """Check if audit event should still be retained."""
        age_days = (datetime.utcnow() - audit_event.timestamp).days
        
        # Use the longest retention period from applicable frameworks
        max_retention = audit_event.retention_period_days
        
        for framework in audit_event.compliance_frameworks:
            framework_retention = self.retention_policies.get(framework, 2555)
            max_retention = max(max_retention, framework_retention)
        
        return age_days < max_retention
    
    def archive_old_events(self, events: List[AuditEvent]) -> List[str]:
        """Archive events that exceed retention period."""
        archived_ids = []
        
        for event in events:
            if not self.should_retain(event) and event.status == AuditStatus.ACTIVE:
                event.status = AuditStatus.ARCHIVED
                archived_ids.append(event.id)
                logger.info("Audit event archived", 
                           event_id=event.id, 
                           age_days=(datetime.utcnow() - event.timestamp).days)
        
        return archived_ids


class AuditReporter:
    """Generates compliance and audit reports."""
    
    def __init__(self):
        pass
    
    def generate_compliance_report(self, framework: ComplianceFramework,
                                 start_date: datetime, end_date: datetime,
                                 events: List[AuditEvent]) -> Dict[str, Any]:
        """Generate compliance report for specific framework."""
        framework_events = [
            e for e in events 
            if framework in e.compliance_frameworks
            and start_date <= e.timestamp <= end_date
        ]
        
        # Event statistics
        event_stats = {}
        for event in framework_events:
            event_type = event.event_type.value
            if event_type not in event_stats:
                event_stats[event_type] = {"count": 0, "severities": {}}
            event_stats[event_type]["count"] += 1
            
            severity = event.severity.value
            if severity not in event_stats[event_type]["severities"]:
                event_stats[event_type]["severities"][severity] = 0
            event_stats[event_type]["severities"][severity] += 1
        
        # User activity
        user_activity = {}
        for event in framework_events:
            if event.user_id:
                if event.user_id not in user_activity:
                    user_activity[event.user_id] = {"count": 0, "last_activity": None}
                user_activity[event.user_id]["count"] += 1
                if not user_activity[event.user_id]["last_activity"] or event.timestamp > user_activity[event.user_id]["last_activity"]:
                    user_activity[event.user_id]["last_activity"] = event.timestamp
        
        # Security events
        security_events = [
            e for e in framework_events
            if e.event_type.value.startswith("security.")
        ]
        
        report = {
            "framework": framework.value,
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_events": len(framework_events),
                "unique_users": len(user_activity),
                "security_events": len(security_events),
                "critical_events": len([e for e in framework_events if e.severity == AuditSeverity.CRITICAL])
            },
            "event_statistics": event_stats,
            "user_activity": {
                k: {
                    "count": v["count"],
                    "last_activity": v["last_activity"].isoformat() if v["last_activity"] else None
                }
                for k, v in user_activity.items()
            },
            "security_summary": {
                "total_security_events": len(security_events),
                "by_type": {}
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Security event breakdown
        for event in security_events:
            event_type = event.event_type.value
            if event_type not in report["security_summary"]["by_type"]:
                report["security_summary"]["by_type"][event_type] = 0
            report["security_summary"]["by_type"][event_type] += 1
        
        return report
    
    def generate_user_activity_report(self, user_id: str, start_date: datetime, 
                                    end_date: datetime, events: List[AuditEvent]) -> Dict[str, Any]:
        """Generate detailed user activity report."""
        user_events = [
            e for e in events
            if e.user_id == user_id
            and start_date <= e.timestamp <= end_date
        ]
        
        # Activity timeline
        daily_activity = {}
        for event in user_events:
            date_key = event.timestamp.date().isoformat()
            if date_key not in daily_activity:
                daily_activity[date_key] = {"count": 0, "events": []}
            daily_activity[date_key]["count"] += 1
            daily_activity[date_key]["events"].append({
                "time": event.timestamp.time().isoformat(),
                "type": event.event_type.value,
                "action": event.action,
                "resource": f"{event.resource_type}:{event.resource_id}" if event.resource_type else None
            })
        
        return {
            "user_id": user_id,
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_events": len(user_events),
                "active_days": len(daily_activity),
                "event_types": len(set(e.event_type.value for e in user_events))
            },
            "daily_activity": daily_activity,
            "event_breakdown": {
                event_type: len([e for e in user_events if e.event_type.value == event_type])
                for event_type in set(e.event_type.value for e in user_events)
            },
            "generated_at": datetime.utcnow().isoformat()
        }


class AuditService:
    """Main audit and compliance service."""
    
    def __init__(self):
        self.events: Dict[str, AuditEvent] = {}
        self.encryption = AuditEncryption()
        self.compliance_monitor = ComplianceMonitor()
        self.retention_manager = AuditRetention()
        self.reporter = AuditReporter()
        
        logger.info("Audit service initialized")
    
    async def log_event(self, event_type: AuditEventType, user_id: Optional[str],
                       action: str, description: str,
                       resource_type: Optional[str] = None,
                       resource_id: Optional[str] = None,
                       old_values: Optional[Dict[str, Any]] = None,
                       new_values: Optional[Dict[str, Any]] = None,
                       context: Optional[AuditContext] = None,
                       severity: AuditSeverity = AuditSeverity.MEDIUM,
                       compliance_frameworks: List[ComplianceFramework] = None,
                       metadata: Dict[str, Any] = None) -> str:
        """Log audit event with comprehensive tracking."""
        
        event_id = f"audit_{uuid.uuid4().hex[:12]}"
        
        # Encrypt sensitive data
        encrypted_old = self.encryption.encrypt_sensitive_data(old_values or {})
        encrypted_new = self.encryption.encrypt_sensitive_data(new_values or {})
        
        # Create audit event
        audit_event = AuditEvent(
            id=event_id,
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            description=description,
            old_values=encrypted_old,
            new_values=encrypted_new,
            metadata=metadata or {},
            context=context,
            compliance_frameworks=compliance_frameworks or [],
            encrypted=True if (old_values or new_values) else False
        )
        
        # Store event
        self.events[event_id] = audit_event
        
        # Check compliance
        violations = self.compliance_monitor.check_compliance(audit_event)
        if violations:
            logger.warning("Compliance violations detected",
                          event_id=event_id,
                          violations=[v.id for v in violations])
        
        logger.info("Audit event logged",
                   event_id=event_id,
                   event_type=event_type.value,
                   user_id=user_id,
                   severity=severity.value)
        
        return event_id
    
    async def get_events(self, filters: Dict[str, Any] = None,
                        limit: int = 100, offset: int = 0) -> List[AuditEvent]:
        """Get audit events with filtering."""
        events = list(self.events.values())
        
        if filters:
            # Apply filters
            if "user_id" in filters:
                events = [e for e in events if e.user_id == filters["user_id"]]
            
            if "event_type" in filters:
                events = [e for e in events if e.event_type.value == filters["event_type"]]
            
            if "severity" in filters:
                events = [e for e in events if e.severity.value == filters["severity"]]
            
            if "start_date" in filters:
                start_date = datetime.fromisoformat(filters["start_date"])
                events = [e for e in events if e.timestamp >= start_date]
            
            if "end_date" in filters:
                end_date = datetime.fromisoformat(filters["end_date"])
                events = [e for e in events if e.timestamp <= end_date]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply pagination
        return events[offset:offset + limit]
    
    async def get_compliance_violations(self, framework: Optional[ComplianceFramework] = None) -> List[ComplianceViolation]:
        """Get compliance violations."""
        if framework:
            return self.compliance_monitor.get_violations_by_framework(framework)
        return self.compliance_monitor.violations
    
    async def generate_compliance_report(self, framework: ComplianceFramework,
                                       start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate compliance report."""
        events = list(self.events.values())
        return self.reporter.generate_compliance_report(framework, start_date, end_date, events)
    
    async def generate_user_activity_report(self, user_id: str,
                                          start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate user activity report."""
        events = list(self.events.values())
        return self.reporter.generate_user_activity_report(user_id, start_date, end_date, events)
    
    async def verify_audit_integrity(self, event_id: str) -> bool:
        """Verify audit record integrity."""
        event = self.events.get(event_id)
        if not event:
            return False
        
        return event.verify_integrity()
    
    async def archive_old_events(self) -> int:
        """Archive events that exceed retention period."""
        events = list(self.events.values())
        archived_ids = self.retention_manager.archive_old_events(events)
        
        logger.info("Audit events archived", count=len(archived_ids))
        return len(archived_ids)
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit service statistics."""
        events = list(self.events.values())
        total_events = len(events)
        
        # Count by severity
        severity_counts = {}
        for severity in AuditSeverity:
            severity_counts[severity.value] = len([e for e in events if e.severity == severity])
        
        # Count by event type
        event_type_counts = {}
        for event_type in AuditEventType:
            event_type_counts[event_type.value] = len([e for e in events if e.event_type == event_type])
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_events = len([e for e in events if e.timestamp >= yesterday])
        
        return {
            "total_events": total_events,
            "recent_events_24h": recent_events,
            "severity_distribution": severity_counts,
            "event_type_distribution": event_type_counts,
            "active_violations": len([v for v in self.compliance_monitor.violations if v.status == "open"]),
            "total_violations": len(self.compliance_monitor.violations),
            "compliance_frameworks": len(self.compliance_monitor.rules)
        }


# Global audit service
_audit_service = None


def get_audit_service() -> AuditService:
    """Get global audit service."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service


# Convenience functions for common audit events
async def log_user_login(user_id: str, context: AuditContext) -> str:
    """Log user login event."""
    service = get_audit_service()
    return await service.log_event(
        event_type=AuditEventType.USER_LOGIN,
        user_id=user_id,
        action="login",
        description=f"User {user_id} logged in",
        context=context,
        severity=AuditSeverity.LOW,
        compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.SOX]
    )


async def log_transaction_create(user_id: str, transaction_id: str, 
                               transaction_data: Dict[str, Any], context: AuditContext) -> str:
    """Log transaction creation event."""
    service = get_audit_service()
    return await service.log_event(
        event_type=AuditEventType.TRANSACTION_CREATE,
        user_id=user_id,
        action="create",
        description=f"Transaction {transaction_id} created",
        resource_type="transaction",
        resource_id=transaction_id,
        new_values=transaction_data,
        context=context,
        severity=AuditSeverity.MEDIUM,
        compliance_frameworks=[ComplianceFramework.SOX, ComplianceFramework.GDPR]
    )


async def log_data_export(user_id: str, export_type: str, 
                         context: AuditContext) -> str:
    """Log data export event."""
    service = get_audit_service()
    return await service.log_event(
        event_type=AuditEventType.DATA_EXPORT,
        user_id=user_id,
        action="export",
        description=f"Data exported: {export_type}",
        resource_type="data_export",
        context=context,
        severity=AuditSeverity.HIGH,
        compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.CCPA]
    )


async def log_security_event(event_type: AuditEventType, description: str,
                           user_id: Optional[str] = None, context: Optional[AuditContext] = None) -> str:
    """Log security event."""
    service = get_audit_service()
    return await service.log_event(
        event_type=event_type,
        user_id=user_id,
        action="security_event",
        description=description,
        context=context,
        severity=AuditSeverity.CRITICAL,
        compliance_frameworks=[ComplianceFramework.ISO_27001, ComplianceFramework.SOX]
    )