"""
Advanced Reports endpoints.
Handles report generation, templates, and analytics for financial data.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, status, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel, Field, validator
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional
from src.services.report_service import (
    get_report_service,
    ReportConfig,
    ReportType,
    ReportFormat,
    generate_monthly_report,
    generate_budget_analysis_report
)

logger = structlog.get_logger()
router = APIRouter()


class GenerateReportRequest(BaseModel):
    """Generate report request."""
    report_type: str = Field(..., description="Type of report to generate")
    format: str = Field(default="pdf", description="Report format (pdf, excel, csv, json)")
    start_date: str = Field(..., description="Start date (ISO format)")
    end_date: str = Field(..., description="End date (ISO format)")
    include_charts: bool = Field(default=True, description="Include charts in report")
    include_summary: bool = Field(default=True, description="Include summary section")
    include_details: bool = Field(default=True, description="Include detailed data")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    accounts: Optional[List[str]] = Field(None, description="Filter by accounts")
    template: str = Field(default="default", description="Report template")
    
    @validator('report_type')
    def validate_report_type(cls, v):
        valid_types = [rt.value for rt in ReportType]
        if v not in valid_types:
            raise ValueError(f'Invalid report type. Must be one of: {valid_types}')
        return v
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = [rf.value for rf in ReportFormat]
        if v not in valid_formats:
            raise ValueError(f'Invalid format. Must be one of: {valid_formats}')
        return v


class ReportTemplateResponse(BaseModel):
    """Report template response."""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    supported_formats: List[str] = Field(..., description="Supported output formats")
    includes_charts: bool = Field(..., description="Whether template includes charts")


class ReportStatusResponse(BaseModel):
    """Report generation status response."""
    status: str = Field(..., description="Generation status")
    message: str = Field(..., description="Status message")
    report_id: Optional[str] = Field(None, description="Report ID if completed")
    progress: int = Field(default=0, description="Generation progress percentage")
    estimated_completion: Optional[str] = Field(None, description="Estimated completion time")


class QuickReportRequest(BaseModel):
    """Quick report request."""
    period: str = Field(..., description="Report period (current_month, last_month, quarter, year)")
    format: str = Field(default="pdf", description="Report format")
    
    @validator('period')
    def validate_period(cls, v):
        valid_periods = ['current_month', 'last_month', 'last_3_months', 'quarter', 'year', 'ytd']
        if v not in valid_periods:
            raise ValueError(f'Invalid period. Must be one of: {valid_periods}')
        return v


@router.get(
    "/templates",
    status_code=status.HTTP_200_OK,
    summary="List Report Templates",
    description="Returns available report templates with their configurations",
    response_model=List[ReportTemplateResponse],
    tags=["Reports"]
)
async def list_report_templates(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[ReportTemplateResponse]:
    """
    **List available report templates**
    
    Returns all available report templates with their configurations:
    - Template metadata and descriptions
    - Supported output formats
    - Chart and visualization options
    - Customization capabilities
    
    Useful for understanding available reporting options.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_report_service()
        templates = await service.get_available_templates()
        
        return [
            ReportTemplateResponse(
                id=template['id'],
                name=template['name'],
                description=template['description'],
                supported_formats=template['supported_formats'],
                includes_charts=template['includes_charts']
            )
            for template in templates
        ]
        
    except Exception as e:
        logger.error("Failed to list report templates", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve report templates"
        )


@router.post(
    "/generate",
    status_code=status.HTTP_200_OK,
    summary="Generate Custom Report",
    description="Generates a custom financial report based on specified parameters",
    tags=["Reports"]
)
async def generate_custom_report(
    request: GenerateReportRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Response:
    """
    **Generate custom financial report**
    
    Creates a comprehensive financial report with:
    - Customizable date ranges and filters
    - Multiple output formats (PDF, Excel, CSV, JSON)
    - Chart and visualization options
    - Template-based formatting
    - Category and account filtering
    
    Returns the report as a downloadable file.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_report_service()
        
        # Parse dates
        start_date = datetime.fromisoformat(request.start_date)
        end_date = datetime.fromisoformat(request.end_date)
        
        # Create report configuration
        config = ReportConfig(
            report_type=ReportType(request.report_type),
            format=ReportFormat(request.format),
            date_range=(start_date, end_date),
            user_id=current_user.get('id'),
            include_charts=request.include_charts,
            include_summary=request.include_summary,
            include_details=request.include_details,
            categories=request.categories,
            accounts=request.accounts,
            template=request.template
        )
        
        # Validate configuration
        validation_errors = await service.validate_report_config(config)
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Configuration errors: {'; '.join(validation_errors)}"
            )
        
        # In real implementation, fetch user's data from database
        # For now, using mock data
        transactions = []
        budgets = []
        accounts = []
        
        # Generate report
        report_data = await service.generate_report(config, transactions, budgets, accounts)
        
        # Determine content type and filename
        if config.format == ReportFormat.PDF:
            content_type = "application/pdf"
            filename = f"financial_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
        elif config.format == ReportFormat.EXCEL:
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"financial_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
        elif config.format == ReportFormat.CSV:
            content_type = "text/csv"
            filename = f"financial_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        elif config.format == ReportFormat.JSON:
            content_type = "application/json"
            filename = f"financial_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.json"
        
        logger.info("Custom report generated",
                   user_id=current_user.get('id'),
                   report_type=request.report_type,
                   format=request.format,
                   size=len(report_data))
        
        return Response(
            content=report_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(report_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate custom report",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


@router.post(
    "/quick",
    status_code=status.HTTP_200_OK,
    summary="Generate Quick Report",
    description="Generates a quick report for common time periods",
    tags=["Reports"]
)
async def generate_quick_report(
    request: QuickReportRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Response:
    """
    **Generate quick report**
    
    Creates pre-configured reports for common time periods:
    - Current month
    - Last month
    - Last 3 months
    - Current quarter
    - Current year
    - Year-to-date
    
    Perfect for regular reporting needs without custom configuration.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Determine date range based on period
        now = datetime.now()
        
        if request.period == "current_month":
            start_date = datetime(now.year, now.month, 1)
            end_date = now
        elif request.period == "last_month":
            if now.month == 1:
                start_date = datetime(now.year - 1, 12, 1)
                end_date = datetime(now.year, 1, 1) - timedelta(days=1)
            else:
                start_date = datetime(now.year, now.month - 1, 1)
                end_date = datetime(now.year, now.month, 1) - timedelta(days=1)
        elif request.period == "last_3_months":
            start_date = now - timedelta(days=90)
            end_date = now
        elif request.period == "quarter":
            quarter = (now.month - 1) // 3 + 1
            start_date = datetime(now.year, (quarter - 1) * 3 + 1, 1)
            end_date = now
        elif request.period == "year":
            start_date = datetime(now.year, 1, 1)
            end_date = now
        elif request.period == "ytd":
            start_date = datetime(now.year, 1, 1)
            end_date = now
        
        # Create report configuration
        config = ReportConfig(
            report_type=ReportType.MONTHLY if "month" in request.period else ReportType.QUARTERLY if "quarter" in request.period else ReportType.ANNUAL,
            format=ReportFormat(request.format),
            date_range=(start_date, end_date),
            user_id=current_user.get('id'),
            template="default"
        )
        
        service = get_report_service()
        
        # In real implementation, fetch user's data from database
        transactions = []
        budgets = []
        accounts = []
        
        # Generate report
        report_data = await service.generate_report(config, transactions, budgets, accounts)
        
        # Determine content type and filename
        if config.format == ReportFormat.PDF:
            content_type = "application/pdf"
            filename = f"quick_report_{request.period}_{now.strftime('%Y%m%d')}.pdf"
        elif config.format == ReportFormat.EXCEL:
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"quick_report_{request.period}_{now.strftime('%Y%m%d')}.xlsx"
        
        logger.info("Quick report generated",
                   user_id=current_user.get('id'),
                   period=request.period,
                   format=request.format)
        
        return Response(
            content=report_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(report_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate quick report",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate quick report"
        )


@router.get(
    "/monthly/{year}/{month}",
    status_code=status.HTTP_200_OK,
    summary="Generate Monthly Report",
    description="Generates a monthly report for specified year and month",
    tags=["Reports"]
)
async def get_monthly_report(
    year: int,
    month: int,
    format: str = Query(default="pdf", description="Report format"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Response:
    """
    **Generate monthly report**
    
    Creates a comprehensive monthly financial report:
    - Income and expense analysis
    - Budget performance
    - Category breakdowns
    - Transaction summaries
    - Charts and visualizations
    
    Specified by year and month parameters.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Validate parameters
    if not (1 <= month <= 12):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Month must be between 1 and 12"
        )
    
    if not (2000 <= year <= datetime.now().year):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid year"
        )
    
    try:
        report_format = ReportFormat(format)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format. Must be one of: {[rf.value for rf in ReportFormat]}"
        )
    
    try:
        # Generate monthly report
        report_data = await generate_monthly_report(
            current_user.get('id'),
            year,
            month,
            report_format
        )
        
        # Determine content type and filename
        if report_format == ReportFormat.PDF:
            content_type = "application/pdf"
            filename = f"monthly_report_{year}_{month:02d}.pdf"
        elif report_format == ReportFormat.EXCEL:
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"monthly_report_{year}_{month:02d}.xlsx"
        
        logger.info("Monthly report generated",
                   user_id=current_user.get('id'),
                   year=year,
                   month=month,
                   format=format)
        
        return Response(
            content=report_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(report_data))
            }
        )
        
    except Exception as e:
        logger.error("Failed to generate monthly report",
                    user_id=current_user.get('id'),
                    year=year,
                    month=month,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate monthly report"
        )


@router.get(
    "/budget-analysis",
    status_code=status.HTTP_200_OK,
    summary="Generate Budget Analysis Report",
    description="Generates a comprehensive budget performance analysis report",
    tags=["Reports"]
)
async def get_budget_analysis_report(
    budget_ids: Optional[str] = Query(None, description="Comma-separated budget IDs"),
    format: str = Query(default="pdf", description="Report format"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Response:
    """
    **Generate budget analysis report**
    
    Creates a detailed budget performance analysis:
    - Budget vs actual spending
    - Variance analysis
    - Trend analysis
    - Performance metrics
    - Recommendations
    
    Can filter by specific budget IDs.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        report_format = ReportFormat(format)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format. Must be one of: {[rf.value for rf in ReportFormat]}"
        )
    
    try:
        # Parse budget IDs
        budget_id_list = []
        if budget_ids:
            budget_id_list = [id.strip() for id in budget_ids.split(",")]
        
        # Generate budget analysis report
        report_data = await generate_budget_analysis_report(
            current_user.get('id'),
            budget_id_list,
            report_format
        )
        
        # Determine content type and filename
        if report_format == ReportFormat.PDF:
            content_type = "application/pdf"
            filename = f"budget_analysis_{datetime.now().strftime('%Y%m%d')}.pdf"
        elif report_format == ReportFormat.EXCEL:
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"budget_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        logger.info("Budget analysis report generated",
                   user_id=current_user.get('id'),
                   budget_ids=budget_id_list,
                   format=format)
        
        return Response(
            content=report_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(report_data))
            }
        )
        
    except Exception as e:
        logger.error("Failed to generate budget analysis report",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate budget analysis report"
        )


@router.get(
    "/analytics/summary",
    status_code=status.HTTP_200_OK,
    summary="Get Reporting Analytics",
    description="Returns analytics data for report insights",
    tags=["Reports"]
)
async def get_reporting_analytics(
    start_date: str = Query(..., description="Start date (ISO format)"),
    end_date: str = Query(..., description="End date (ISO format)"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Get reporting analytics**
    
    Returns analytical insights for reporting:
    - Financial trend analysis
    - Category performance
    - Budget efficiency metrics
    - Spending patterns
    - Key performance indicators
    
    Useful for dashboard widgets and report previews.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        if start_dt >= end_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        # In real implementation, fetch and analyze user's data
        # For now, returning mock analytics
        analytics = {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": (end_dt - start_dt).days
            },
            "financial_summary": {
                "total_income": 5250.00,
                "total_expenses": 4180.50,
                "net_amount": 1069.50,
                "transaction_count": 127,
                "avg_transaction": 32.89
            },
            "trends": {
                "income_trend": "increasing",
                "expense_trend": "stable",
                "savings_rate": 20.4
            },
            "top_categories": [
                {"name": "Food & Dining", "amount": 1250.00, "percentage": 29.9},
                {"name": "Transportation", "amount": 850.00, "percentage": 20.3},
                {"name": "Shopping", "amount": 680.50, "percentage": 16.3},
                {"name": "Entertainment", "amount": 420.00, "percentage": 10.0},
                {"name": "Utilities", "amount": 380.00, "percentage": 9.1}
            ],
            "budget_performance": {
                "total_budgets": 6,
                "on_track": 4,
                "warning": 1,
                "over_budget": 1,
                "overall_performance": 75.5
            },
            "insights": [
                "Spending on Food & Dining increased by 15% compared to last month",
                "You're saving 20.4% of your income, which is above the recommended 20%",
                "Transportation expenses are 12% under budget",
                "Consider reviewing your Shopping category - it's 25% over budget"
            ]
        }
        
        logger.info("Reporting analytics retrieved",
                   user_id=current_user.get('id'),
                   start_date=start_date,
                   end_date=end_date)
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get reporting analytics",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reporting analytics"
        )