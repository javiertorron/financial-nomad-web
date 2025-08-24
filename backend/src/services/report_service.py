"""
Advanced Reporting Service.
Generates comprehensive financial reports in PDF and Excel formats
with charts, analytics, and customizable templates.
"""

import io
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from decimal import Decimal
import pandas as pd
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
import structlog

from src.config import settings

logger = structlog.get_logger()


class ReportType(Enum):
    """Types of financial reports."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"
    BUDGET_ANALYSIS = "budget_analysis"
    CASHFLOW = "cashflow"
    CATEGORY_BREAKDOWN = "category_breakdown"
    ACCOUNT_SUMMARY = "account_summary"
    TRENDS_ANALYSIS = "trends_analysis"
    COMPARATIVE = "comparative"


class ReportFormat(Enum):
    """Report output formats."""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"


class ChartType(Enum):
    """Chart types for reports."""
    PIE = "pie"
    BAR = "bar"
    LINE = "line"
    AREA = "area"
    DONUT = "donut"
    STACKED_BAR = "stacked_bar"


@dataclass
class ReportConfig:
    """Report generation configuration."""
    report_type: ReportType
    format: ReportFormat
    date_range: Tuple[datetime, datetime]
    user_id: str
    include_charts: bool = True
    include_summary: bool = True
    include_details: bool = True
    categories: Optional[List[str]] = None
    accounts: Optional[List[str]] = None
    currency: str = "USD"
    language: str = "en"
    template: str = "default"
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportData:
    """Report data structure."""
    config: ReportConfig
    summary: Dict[str, Any] = field(default_factory=dict)
    transactions: List[Dict[str, Any]] = field(default_factory=list)
    categories: List[Dict[str, Any]] = field(default_factory=list)
    accounts: List[Dict[str, Any]] = field(default_factory=list)
    budgets: List[Dict[str, Any]] = field(default_factory=list)
    charts: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


class DataAnalyzer:
    """Analyzes financial data for reporting."""
    
    def __init__(self):
        pass
    
    def analyze_transactions(self, transactions: List[Dict[str, Any]], 
                           date_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Analyze transaction data."""
        df = pd.DataFrame(transactions)
        
        if df.empty:
            return {
                "total_income": 0,
                "total_expenses": 0,
                "net_amount": 0,
                "transaction_count": 0,
                "avg_transaction": 0,
                "top_categories": [],
                "monthly_trend": []
            }
        
        # Convert amount to numeric
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'])
        
        # Filter by date range
        df = df[(df['date'] >= date_range[0]) & (df['date'] <= date_range[1])]
        
        # Separate income and expenses
        income_df = df[df['amount'] > 0]
        expense_df = df[df['amount'] < 0]
        
        total_income = income_df['amount'].sum()
        total_expenses = abs(expense_df['amount'].sum())
        net_amount = total_income - total_expenses
        
        # Category analysis
        category_summary = df.groupby('category').agg({
            'amount': ['sum', 'count', 'mean']
        }).round(2)
        
        top_categories = []
        for category in category_summary.index:
            total = category_summary.loc[category, ('amount', 'sum')]
            count = category_summary.loc[category, ('amount', 'count')]
            avg = category_summary.loc[category, ('amount', 'mean')]
            
            top_categories.append({
                "name": category,
                "total": float(total),
                "count": int(count),
                "average": float(avg),
                "percentage": (abs(total) / (total_income + total_expenses)) * 100 if (total_income + total_expenses) > 0 else 0
            })
        
        # Sort by absolute amount
        top_categories.sort(key=lambda x: abs(x['total']), reverse=True)
        
        # Monthly trend
        df['month'] = df['date'].dt.to_period('M')
        monthly_trend = df.groupby('month')['amount'].sum().to_dict()
        monthly_trend = [
            {"month": str(k), "amount": float(v)}
            for k, v in monthly_trend.items()
        ]
        
        return {
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net_amount": float(net_amount),
            "transaction_count": len(df),
            "avg_transaction": float(df['amount'].mean()) if len(df) > 0 else 0,
            "top_categories": top_categories[:10],
            "monthly_trend": monthly_trend
        }
    
    def analyze_budgets(self, budgets: List[Dict[str, Any]], 
                       transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze budget performance."""
        df = pd.DataFrame(transactions)
        
        if df.empty:
            return []
        
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'])
        
        budget_analysis = []
        
        for budget in budgets:
            # Filter transactions by category and date
            budget_transactions = df[
                (df['category'] == budget.get('category')) &
                (df['date'] >= pd.to_datetime(budget.get('start_date'))) &
                (df['date'] <= pd.to_datetime(budget.get('end_date'))) &
                (df['amount'] < 0)  # Only expenses
            ]
            
            spent = abs(budget_transactions['amount'].sum())
            budget_amount = budget.get('amount', 0)
            percentage_used = (spent / budget_amount * 100) if budget_amount > 0 else 0
            remaining = budget_amount - spent
            
            budget_analysis.append({
                "name": budget.get('name'),
                "category": budget.get('category'),
                "budget_amount": float(budget_amount),
                "spent_amount": float(spent),
                "remaining_amount": float(remaining),
                "percentage_used": float(percentage_used),
                "status": "over_budget" if percentage_used > 100 else "on_track" if percentage_used < 80 else "warning",
                "transaction_count": len(budget_transactions)
            })
        
        return budget_analysis
    
    def generate_chart_data(self, data: Dict[str, Any], chart_type: ChartType) -> Dict[str, Any]:
        """Generate chart data based on analysis."""
        if chart_type == ChartType.PIE:
            # Category pie chart
            categories = data.get('top_categories', [])[:8]  # Top 8 categories
            return {
                "type": "pie",
                "data": {
                    "labels": [cat['name'] for cat in categories],
                    "values": [abs(cat['total']) for cat in categories],
                    "colors": self._generate_colors(len(categories))
                },
                "title": "Expenses by Category"
            }
        
        elif chart_type == ChartType.LINE:
            # Monthly trend line chart
            trend = data.get('monthly_trend', [])
            return {
                "type": "line",
                "data": {
                    "labels": [item['month'] for item in trend],
                    "income": [max(0, item['amount']) for item in trend],
                    "expenses": [abs(min(0, item['amount'])) for item in trend]
                },
                "title": "Monthly Income vs Expenses Trend"
            }
        
        elif chart_type == ChartType.BAR:
            # Top categories bar chart
            categories = data.get('top_categories', [])[:10]
            return {
                "type": "bar",
                "data": {
                    "labels": [cat['name'] for cat in categories],
                    "values": [abs(cat['total']) for cat in categories],
                    "colors": self._generate_colors(len(categories))
                },
                "title": "Top Categories by Amount"
            }
        
        return {}
    
    def _generate_colors(self, count: int) -> List[str]:
        """Generate color palette for charts."""
        base_colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
        ]
        
        colors = []
        for i in range(count):
            colors.append(base_colors[i % len(base_colors)])
        
        return colors


class PDFReportGenerator:
    """Generates PDF reports."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1  # Center
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='Summary',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceBefore=10,
            spaceAfter=10,
            leftIndent=20
        ))
    
    def generate_report(self, report_data: ReportData) -> bytes:
        """Generate PDF report."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Title
        title = f"Financial Report - {report_data.config.report_type.value.title()}"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 12))
        
        # Report info
        date_range = f"{report_data.config.date_range[0].strftime('%B %d, %Y')} - {report_data.config.date_range[1].strftime('%B %d, %Y')}"
        story.append(Paragraph(f"<b>Period:</b> {date_range}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Generated:</b> {report_data.generated_at.strftime('%B %d, %Y at %H:%M')}", self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Executive Summary
        if report_data.config.include_summary:
            story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
            summary = report_data.summary
            
            summary_data = [
                ['Metric', 'Amount'],
                ['Total Income', f"${summary.get('total_income', 0):,.2f}"],
                ['Total Expenses', f"${summary.get('total_expenses', 0):,.2f}"],
                ['Net Amount', f"${summary.get('net_amount', 0):,.2f}"],
                ['Total Transactions', f"{summary.get('transaction_count', 0):,}"],
                ['Average Transaction', f"${summary.get('avg_transaction', 0):,.2f}"]
            ]
            
            summary_table = Table(summary_data)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 20))
        
        # Category Breakdown
        if report_data.categories:
            story.append(Paragraph("Category Breakdown", self.styles['SectionHeader']))
            
            category_data = [['Category', 'Amount', 'Transactions', 'Percentage']]
            for cat in report_data.summary.get('top_categories', [])[:10]:
                category_data.append([
                    cat['name'],
                    f"${abs(cat['total']):,.2f}",
                    str(cat['count']),
                    f"{cat['percentage']:.1f}%"
                ])
            
            category_table = Table(category_data)
            category_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(category_table)
            story.append(Spacer(1, 20))
        
        # Budget Analysis
        if report_data.budgets:
            story.append(Paragraph("Budget Performance", self.styles['SectionHeader']))
            
            budget_data = [['Budget', 'Allocated', 'Spent', 'Remaining', 'Status']]
            for budget in report_data.budgets:
                status_color = colors.red if budget['status'] == 'over_budget' else colors.orange if budget['status'] == 'warning' else colors.green
                budget_data.append([
                    budget['name'],
                    f"${budget['budget_amount']:,.2f}",
                    f"${budget['spent_amount']:,.2f}",
                    f"${budget['remaining_amount']:,.2f}",
                    budget['status'].replace('_', ' ').title()
                ])
            
            budget_table = Table(budget_data)
            budget_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(budget_table)
            story.append(Spacer(1, 20))
        
        # Charts section
        if report_data.config.include_charts and report_data.charts:
            story.append(Paragraph("Charts and Visualizations", self.styles['SectionHeader']))
            
            for chart_data in report_data.charts:
                if chart_data['type'] == 'pie':
                    chart = self._create_pie_chart(chart_data)
                    story.append(chart)
                    story.append(Spacer(1, 20))
        
        # Transaction Details
        if report_data.config.include_details and report_data.transactions:
            story.append(Paragraph("Recent Transactions", self.styles['SectionHeader']))
            
            transaction_data = [['Date', 'Description', 'Category', 'Amount']]
            for trans in report_data.transactions[-20:]:  # Last 20 transactions
                amount_str = f"${abs(float(trans['amount'])):,.2f}"
                if float(trans['amount']) < 0:
                    amount_str = f"({amount_str})"
                
                transaction_data.append([
                    datetime.fromisoformat(trans['date']).strftime('%m/%d/%Y'),
                    trans.get('description', 'N/A')[:30],
                    trans.get('category', 'N/A'),
                    amount_str
                ])
            
            transaction_table = Table(transaction_data)
            transaction_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),  # Amount column right-aligned
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(transaction_table)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
    
    def _create_pie_chart(self, chart_data: Dict[str, Any]) -> Drawing:
        """Create pie chart for PDF."""
        drawing = Drawing(400, 200)
        
        pie = Pie()
        pie.x = 50
        pie.y = 50
        pie.width = 100
        pie.height = 100
        pie.data = chart_data['data']['values']
        pie.labels = chart_data['data']['labels']
        pie.slices.strokeWidth = 0.5
        
        # Set colors
        colors_list = [getattr(colors, c.replace('#', ''), colors.blue) for c in chart_data['data']['colors']]
        for i, color in enumerate(colors_list):
            pie.slices[i].fillColor = color
        
        drawing.add(pie)
        return drawing


class ExcelReportGenerator:
    """Generates Excel reports."""
    
    def __init__(self):
        pass
    
    def generate_report(self, report_data: ReportData) -> bytes:
        """Generate Excel report."""
        buffer = io.BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Summary sheet
            self._create_summary_sheet(report_data, writer)
            
            # Transactions sheet
            if report_data.transactions:
                self._create_transactions_sheet(report_data, writer)
            
            # Category analysis sheet
            if report_data.summary.get('top_categories'):
                self._create_category_sheet(report_data, writer)
            
            # Budget analysis sheet
            if report_data.budgets:
                self._create_budget_sheet(report_data, writer)
            
            # Monthly trend sheet
            if report_data.summary.get('monthly_trend'):
                self._create_trend_sheet(report_data, writer)
        
        buffer.seek(0)
        return buffer.read()
    
    def _create_summary_sheet(self, report_data: ReportData, writer):
        """Create summary sheet."""
        summary = report_data.summary
        
        summary_data = {
            'Metric': [
                'Report Type',
                'Date Range',
                'Total Income',
                'Total Expenses',
                'Net Amount',
                'Total Transactions',
                'Average Transaction',
                'Generated At'
            ],
            'Value': [
                report_data.config.report_type.value.title(),
                f"{report_data.config.date_range[0].strftime('%Y-%m-%d')} to {report_data.config.date_range[1].strftime('%Y-%m-%d')}",
                summary.get('total_income', 0),
                summary.get('total_expenses', 0),
                summary.get('net_amount', 0),
                summary.get('transaction_count', 0),
                summary.get('avg_transaction', 0),
                report_data.generated_at.strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
        
        df = pd.DataFrame(summary_data)
        df.to_excel(writer, sheet_name='Summary', index=False)
    
    def _create_transactions_sheet(self, report_data: ReportData, writer):
        """Create transactions sheet."""
        df = pd.DataFrame(report_data.transactions)
        df.to_excel(writer, sheet_name='Transactions', index=False)
    
    def _create_category_sheet(self, report_data: ReportData, writer):
        """Create category analysis sheet."""
        categories = report_data.summary.get('top_categories', [])
        df = pd.DataFrame(categories)
        df.to_excel(writer, sheet_name='Categories', index=False)
    
    def _create_budget_sheet(self, report_data: ReportData, writer):
        """Create budget analysis sheet."""
        df = pd.DataFrame(report_data.budgets)
        df.to_excel(writer, sheet_name='Budget Analysis', index=False)
    
    def _create_trend_sheet(self, report_data: ReportData, writer):
        """Create monthly trend sheet."""
        trend = report_data.summary.get('monthly_trend', [])
        df = pd.DataFrame(trend)
        df.to_excel(writer, sheet_name='Monthly Trend', index=False)


class ReportService:
    """Main report generation service."""
    
    def __init__(self):
        self.analyzer = DataAnalyzer()
        self.pdf_generator = PDFReportGenerator()
        self.excel_generator = ExcelReportGenerator()
        
        logger.info("Report service initialized")
    
    async def generate_report(self, config: ReportConfig,
                            transactions: List[Dict[str, Any]] = None,
                            budgets: List[Dict[str, Any]] = None,
                            accounts: List[Dict[str, Any]] = None) -> bytes:
        """Generate report based on configuration."""
        
        # Prepare data
        transactions = transactions or []
        budgets = budgets or []
        accounts = accounts or []
        
        # Analyze data
        summary = self.analyzer.analyze_transactions(transactions, config.date_range)
        budget_analysis = self.analyzer.analyze_budgets(budgets, transactions)
        
        # Generate charts
        charts = []
        if config.include_charts:
            charts.append(self.analyzer.generate_chart_data(summary, ChartType.PIE))
            charts.append(self.analyzer.generate_chart_data(summary, ChartType.LINE))
            charts.append(self.analyzer.generate_chart_data(summary, ChartType.BAR))
        
        # Create report data
        report_data = ReportData(
            config=config,
            summary=summary,
            transactions=transactions,
            budgets=budget_analysis,
            accounts=accounts,
            charts=charts
        )
        
        # Generate report based on format
        if config.format == ReportFormat.PDF:
            return self.pdf_generator.generate_report(report_data)
        elif config.format == ReportFormat.EXCEL:
            return self.excel_generator.generate_report(report_data)
        elif config.format == ReportFormat.CSV:
            return self._generate_csv_report(report_data)
        elif config.format == ReportFormat.JSON:
            return self._generate_json_report(report_data)
        else:
            raise ValueError(f"Unsupported format: {config.format}")
    
    def _generate_csv_report(self, report_data: ReportData) -> bytes:
        """Generate CSV report."""
        df = pd.DataFrame(report_data.transactions)
        csv_data = df.to_csv(index=False)
        return csv_data.encode('utf-8')
    
    def _generate_json_report(self, report_data: ReportData) -> bytes:
        """Generate JSON report."""
        data = {
            "summary": report_data.summary,
            "transactions": report_data.transactions,
            "budgets": report_data.budgets,
            "accounts": report_data.accounts,
            "generated_at": report_data.generated_at.isoformat()
        }
        return json.dumps(data, indent=2, default=str).encode('utf-8')
    
    async def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get available report templates."""
        return [
            {
                "id": "default",
                "name": "Standard Financial Report",
                "description": "Comprehensive financial overview with income, expenses, and budget analysis",
                "supported_formats": ["pdf", "excel", "csv"],
                "includes_charts": True
            },
            {
                "id": "executive",
                "name": "Executive Summary",
                "description": "High-level financial summary for executives and stakeholders",
                "supported_formats": ["pdf", "excel"],
                "includes_charts": True
            },
            {
                "id": "detailed",
                "name": "Detailed Transaction Report",
                "description": "Complete transaction listing with full details and categorization",
                "supported_formats": ["excel", "csv"],
                "includes_charts": False
            },
            {
                "id": "budget_focused",
                "name": "Budget Analysis Report",
                "description": "Focus on budget performance and variance analysis",
                "supported_formats": ["pdf", "excel"],
                "includes_charts": True
            }
        ]
    
    async def validate_report_config(self, config: ReportConfig) -> List[str]:
        """Validate report configuration."""
        errors = []
        
        # Date range validation
        if config.date_range[0] >= config.date_range[1]:
            errors.append("Start date must be before end date")
        
        if config.date_range[1] > datetime.now():
            errors.append("End date cannot be in the future")
        
        # Format validation
        if config.format not in ReportFormat:
            errors.append(f"Invalid format: {config.format}")
        
        return errors


# Global report service
_report_service = None


def get_report_service() -> ReportService:
    """Get global report service."""
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service


# Convenience functions
async def generate_monthly_report(user_id: str, year: int, month: int,
                                format: ReportFormat = ReportFormat.PDF) -> bytes:
    """Generate monthly report for user."""
    service = get_report_service()
    
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year + 1, 1, 1) - timedelta(days=1)
    
    config = ReportConfig(
        report_type=ReportType.MONTHLY,
        format=format,
        date_range=(start_date, end_date),
        user_id=user_id
    )
    
    # In real implementation, fetch data from database
    transactions = []
    budgets = []
    accounts = []
    
    return await service.generate_report(config, transactions, budgets, accounts)


async def generate_budget_analysis_report(user_id: str, budget_ids: List[str],
                                        format: ReportFormat = ReportFormat.PDF) -> bytes:
    """Generate budget analysis report."""
    service = get_report_service()
    
    config = ReportConfig(
        report_type=ReportType.BUDGET_ANALYSIS,
        format=format,
        date_range=(datetime.now() - timedelta(days=90), datetime.now()),
        user_id=user_id,
        template="budget_focused"
    )
    
    # In real implementation, fetch data from database
    transactions = []
    budgets = []
    
    return await service.generate_report(config, transactions, budgets)