"""
Audit and Compliance endpoints.
Handles audit log access, compliance monitoring, and regulatory reporting.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, status, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional
from src.services.audit_service import (
    get_audit_service,
    AuditEventType,
    AuditSeverity,
    ComplianceFramework,
    AuditContext
)

logger = structlog.get_logger()
router = APIRouter()


class AuditEventResponse(BaseModel):
    """Audit event response model."""
    id: str = Field(..., description="Audit event ID")
    event_type: str = Field(..., description="Type of audit event")
    severity: str = Field(..., description="Event severity level")
    timestamp: str = Field(..., description="Event timestamp")
    user_id: Optional[str] = Field(None, description="User ID")
    resource_type: Optional[str] = Field(None, description="Resource type")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    action: str = Field(..., description="Action performed")
    description: str = Field(..., description="Event description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    compliance_frameworks: List[str] = Field(default_factory=list, description="Applicable compliance frameworks")
    checksum: Optional[str] = Field(None, description="Integrity checksum")


class ComplianceViolationResponse(BaseModel):
    """Compliance violation response model."""
    id: str = Field(..., description="Violation ID")
    rule_id: str = Field(..., description="Violated rule ID")
    rule_name: str = Field(..., description="Rule name")
    framework: str = Field(..., description="Compliance framework")
    severity: str = Field(..., description="Violation severity")
    description: str = Field(..., description="Violation description")
    detected_at: str = Field(..., description="Detection timestamp")
    resolved_at: Optional[str] = Field(None, description="Resolution timestamp")
    status: str = Field(..., description="Violation status")


class AuditFilters(BaseModel):
    """Audit event filters."""
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    event_type: Optional[str] = Field(None, description="Filter by event type")
    severity: Optional[str] = Field(None, description="Filter by severity")
    start_date: Optional[str] = Field(None, description="Start date filter (ISO format)")
    end_date: Optional[str] = Field(None, description="End date filter (ISO format)")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    
    @validator('event_type')
    def validate_event_type(cls, v):
        if v and v not in [e.value for e in AuditEventType]:
            raise ValueError(f'Invalid event type: {v}')
        return v
    
    @validator('severity')
    def validate_severity(cls, v):
        if v and v not in [s.value for s in AuditSeverity]:
            raise ValueError(f'Invalid severity: {v}')
        return v


class ComplianceReportRequest(BaseModel):
    """Compliance report request."""
    framework: str = Field(..., description="Compliance framework")
    start_date: str = Field(..., description="Report start date (ISO format)")
    end_date: str = Field(..., description="Report end date (ISO format)")
    
    @validator('framework')
    def validate_framework(cls, v):
        if v not in [f.value for f in ComplianceFramework]:
            raise ValueError(f'Invalid framework: {v}')
        return v


class AuditStatsResponse(BaseModel):
    """Audit statistics response."""
    total_events: int = Field(..., description="Total audit events")
    recent_events_24h: int = Field(..., description="Events in last 24 hours")
    severity_distribution: Dict[str, int] = Field(..., description="Events by severity")
    event_type_distribution: Dict[str, int] = Field(..., description="Events by type")
    active_violations: int = Field(..., description="Active compliance violations")
    total_violations: int = Field(..., description="Total violations")


@router.get(
    "/events",
    status_code=status.HTTP_200_OK,
    summary="Get Audit Events",
    description="Returns audit events with filtering and pagination",
    response_model=List[AuditEventResponse],
    tags=["Audit"]
)
async def get_audit_events(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of events"),
    offset: int = Query(default=0, ge=0, description="Number of events to skip"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[AuditEventResponse]:
    """
    **Get audit events**
    
    Returns audit events with comprehensive filtering options:
    - Filter by user, event type, severity, and date range
    - Pagination support for large result sets
    - Resource-specific filtering
    - Chronological ordering (newest first)
    
    Requires administrative privileges or user can only see their own events.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Check if user has admin privileges or restrict to own events
    if current_user.get('role') != 'admin' and user_id != current_user.get('id'):
        # Non-admin users can only see their own events
        user_id = current_user.get('id')
    
    try:
        service = get_audit_service()
        
        # Build filters
        filters = {}
        if user_id:
            filters['user_id'] = user_id
        if event_type:
            filters['event_type'] = event_type
        if severity:
            filters['severity'] = severity
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        if resource_type:
            filters['resource_type'] = resource_type
        
        # Get events
        events = await service.get_events(filters, limit, offset)
        
        # Convert to response format
        result = []
        for event in events:
            result.append(AuditEventResponse(
                id=event.id,
                event_type=event.event_type.value,
                severity=event.severity.value,
                timestamp=event.timestamp.isoformat() + "Z",
                user_id=event.user_id,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                action=event.action,
                description=event.description,
                metadata=event.metadata,
                compliance_frameworks=[f.value for f in event.compliance_frameworks],
                checksum=event.checksum
            ))
        
        logger.info("Audit events retrieved",
                   requester=current_user.get('id'),
                   filters=filters,
                   result_count=len(result))
        
        return result
        
    except Exception as e:
        logger.error("Failed to get audit events",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit events"
        )


@router.get(
    "/events/{event_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Audit Event",
    description="Returns details of a specific audit event",
    response_model=AuditEventResponse,
    tags=["Audit"]
)
async def get_audit_event(
    event_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> AuditEventResponse:
    """
    **Get audit event details**
    
    Returns comprehensive details of a specific audit event:
    - Complete event information and context
    - Integrity verification status
    - Compliance framework associations
    - Metadata and correlation information
    
    Access restricted based on user permissions and event ownership.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_audit_service()
        
        # Get event
        events = await service.get_events({"event_id": event_id}, limit=1)
        if not events:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit event not found"
            )
        
        event = events[0]
        
        # Check access permissions
        if (current_user.get('role') != 'admin' and 
            event.user_id != current_user.get('id')):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to access this audit event"
            )
        
        # Verify integrity
        integrity_valid = await service.verify_audit_integrity(event_id)
        
        result = AuditEventResponse(
            id=event.id,
            event_type=event.event_type.value,
            severity=event.severity.value,
            timestamp=event.timestamp.isoformat() + "Z",
            user_id=event.user_id,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            action=event.action,
            description=event.description,
            metadata={**event.metadata, "integrity_valid": integrity_valid},
            compliance_frameworks=[f.value for f in event.compliance_frameworks],
            checksum=event.checksum
        )
        
        logger.info("Audit event retrieved",
                   event_id=event_id,
                   requester=current_user.get('id'),
                   integrity_valid=integrity_valid)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get audit event",
                    event_id=event_id,
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit event"
        )


@router.get(
    "/compliance/violations",
    status_code=status.HTTP_200_OK,
    summary="Get Compliance Violations",
    description="Returns compliance violations with filtering options",
    response_model=List[ComplianceViolationResponse],
    tags=["Compliance"]
)
async def get_compliance_violations(
    framework: Optional[str] = Query(None, description="Filter by compliance framework"),
    status_filter: str = Query(default="all", description="Filter by status (open, resolved, all)"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[ComplianceViolationResponse]:
    """
    **Get compliance violations**
    
    Returns compliance violations with filtering:
    - Filter by compliance framework (GDPR, SOX, PCI DSS, etc.)
    - Filter by resolution status
    - Severity-based prioritization
    - Detailed violation information
    
    Requires administrative privileges for full access.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for compliance violations
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        service = get_audit_service()
        
        # Get violations
        framework_filter = None
        if framework:
            framework_filter = ComplianceFramework(framework)
        
        violations = await service.get_compliance_violations(framework_filter)
        
        # Apply status filter
        if status_filter != "all":
            violations = [v for v in violations if v.status == status_filter]
        
        # Convert to response format
        result = []
        for violation in violations:
            result.append(ComplianceViolationResponse(
                id=violation.id,
                rule_id=violation.rule_id,
                rule_name=violation.rule_name,
                framework=violation.framework.value,
                severity=violation.severity.value,
                description=violation.description,
                detected_at=violation.detected_at.isoformat() + "Z",
                resolved_at=violation.resolved_at.isoformat() + "Z" if violation.resolved_at else None,
                status=violation.status
            ))
        
        logger.info("Compliance violations retrieved",
                   requester=current_user.get('id'),
                   framework=framework,
                   status_filter=status_filter,
                   count=len(result))
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to get compliance violations",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve compliance violations"
        )


@router.post(
    "/compliance/reports",
    status_code=status.HTTP_200_OK,
    summary="Generate Compliance Report",
    description="Generates comprehensive compliance report for specified framework",
    tags=["Compliance"]
)
async def generate_compliance_report(
    request: ComplianceReportRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Generate compliance report**
    
    Creates comprehensive compliance reports:
    - Framework-specific analysis (GDPR, SOX, PCI DSS, etc.)
    - Event statistics and user activity
    - Security event summaries
    - Violation tracking and resolution status
    - Regulatory compliance metrics
    
    Essential for audit preparation and regulatory compliance.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for compliance reports
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        service = get_audit_service()
        
        # Parse dates
        start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
        
        # Validate date range
        if start_date >= end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        # Generate report
        framework = ComplianceFramework(request.framework)
        report = await service.generate_compliance_report(framework, start_date, end_date)
        
        logger.info("Compliance report generated",
                   requester=current_user.get('id'),
                   framework=request.framework,
                   start_date=request.start_date,
                   end_date=request.end_date)
        
        return report
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to generate compliance report",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate compliance report"
        )


@router.get(
    "/user-activity/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Get User Activity Report",
    description="Generates detailed user activity report",
    tags=["Audit"]
)
async def get_user_activity_report(
    user_id: str,
    start_date: str = Query(..., description="Start date (ISO format)"),
    end_date: str = Query(..., description="End date (ISO format)"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Get user activity report**
    
    Generates detailed user activity analysis:
    - Chronological activity timeline
    - Event type distribution
    - Daily activity patterns
    - Resource access patterns
    - Security-relevant activities
    
    Users can access their own reports, admins can access any user.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Check permissions
    if (current_user.get('role') != 'admin' and 
        user_id != current_user.get('id')):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only access your own activity report"
        )
    
    try:
        service = get_audit_service()
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Generate report
        report = await service.generate_user_activity_report(user_id, start_dt, end_dt)
        
        logger.info("User activity report generated",
                   requester=current_user.get('id'),
                   target_user=user_id,
                   start_date=start_date,
                   end_date=end_date)
        
        return report
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to generate user activity report",
                    user_id=current_user.get('id'),
                    target_user=user_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate user activity report"
        )


@router.get(
    "/statistics",
    status_code=status.HTTP_200_OK,
    summary="Get Audit Statistics",
    description="Returns comprehensive audit system statistics",
    response_model=AuditStatsResponse,
    tags=["Audit"]
)
async def get_audit_statistics(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> AuditStatsResponse:
    """
    **Get audit statistics**
    
    Returns comprehensive audit system metrics:
    - Total event counts and recent activity
    - Distribution by severity and event type
    - Compliance violation statistics
    - System health indicators
    - Trending analysis
    
    Provides overview of audit system health and activity patterns.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for system statistics
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        service = get_audit_service()
        stats = service.get_audit_statistics()
        
        logger.info("Audit statistics retrieved",
                   requester=current_user.get('id'))
        
        return AuditStatsResponse(**stats)
        
    except Exception as e:
        logger.error("Failed to get audit statistics",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit statistics"
        )


@router.post(
    "/events/{event_id}/verify",
    status_code=status.HTTP_200_OK,
    summary="Verify Audit Event Integrity",
    description="Verifies the integrity of an audit event record",
    tags=["Audit"]
)
async def verify_audit_event_integrity(
    event_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Verify audit event integrity**
    
    Verifies the cryptographic integrity of audit records:
    - Checksum validation
    - Tamper detection
    - Data consistency verification
    - Audit trail validation
    
    Critical for forensic analysis and compliance requirements.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for integrity verification
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        service = get_audit_service()
        
        # Verify integrity
        is_valid = await service.verify_audit_integrity(event_id)
        
        result = {
            "event_id": event_id,
            "integrity_valid": is_valid,
            "verified_at": datetime.utcnow().isoformat() + "Z",
            "verified_by": current_user.get('id')
        }
        
        if not is_valid:
            result["warning"] = "Audit record integrity check failed - possible tampering detected"
            logger.warning("Audit integrity check failed",
                          event_id=event_id,
                          verified_by=current_user.get('id'))
        else:
            logger.info("Audit integrity verified",
                       event_id=event_id,
                       verified_by=current_user.get('id'))
        
        return result
        
    except Exception as e:
        logger.error("Failed to verify audit integrity",
                    event_id=event_id,
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify audit event integrity"
        )


@router.post(
    "/maintenance/archive",
    status_code=status.HTTP_200_OK,
    summary="Archive Old Audit Events",
    description="Archives audit events that exceed retention periods",
    tags=["Maintenance"]
)
async def archive_old_audit_events(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Archive old audit events**
    
    Archives audit events based on retention policies:
    - Compliance framework requirements
    - Data retention policies
    - Storage optimization
    - Regulatory compliance
    
    Maintains audit history while managing storage resources.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Require admin role for maintenance operations
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    try:
        service = get_audit_service()
        
        # Archive old events
        archived_count = await service.archive_old_events()
        
        result = {
            "archived_events": archived_count,
            "archived_at": datetime.utcnow().isoformat() + "Z",
            "archived_by": current_user.get('id'),
            "message": f"Successfully archived {archived_count} audit events"
        }
        
        logger.info("Audit events archived",
                   archived_count=archived_count,
                   archived_by=current_user.get('id'))
        
        return result
        
    except Exception as e:
        logger.error("Failed to archive audit events",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive audit events"
        )