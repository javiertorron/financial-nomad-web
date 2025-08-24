"""
Data export service for generating exports in various formats (JSON, CSV, PDF, LLM snapshots).
"""
import asyncio
import csv
import gzip
import hashlib
import io
import json
import tempfile
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Union, Tuple
from uuid import uuid4

import aiofiles
import structlog
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from ..config import get_settings
from ..infrastructure import get_firestore
from ..models.backup import (
    ExportRequest,
    ExportRecord,
    ExportRecordResponse,
    ExportType,
    ExportFormat,
    BackupStatus,
    BackupMetadata
)
from ..models.financial import Transaction, Budget, RecurringTransaction
from ..models.auth import User
from ..models.financial import Account, Category
from ..utils.exceptions import (
    NotFoundError,
    ValidationError as AppValidationError,
    BusinessLogicError
)

logger = structlog.get_logger()


class ExportService:
    """Service for handling data exports."""
    
    def __init__(self):
        self.settings = get_settings()
        self.firestore = get_firestore()
        self.export_base_dir = tempfile.gettempdir()
    
    async def create_export(self, user_id: str, request: ExportRequest) -> ExportRecordResponse:
        """Create a new data export."""
        export_id = str(uuid4())
        started_at = datetime.utcnow()
        
        try:
            # Create export record
            export_record = ExportRecord(
                id=export_id,
                user_id=user_id,
                export_type=request.export_type,
                format=request.format,
                request_params=request,
                started_at=started_at,
                expires_at=started_at + timedelta(hours=24)  # 24-hour download window
            )
            
            await self.firestore.create_document(
                collection=f"exports/{user_id}/user_exports",
                document_id=export_id,
                data=export_record
            )
            
            # Collect data based on export type
            export_data = await self._collect_export_data(user_id, request)
            
            # Generate export file
            file_path, file_size = await self._generate_export_file(
                user_id, export_id, export_data, request
            )
            
            # Generate metadata
            metadata = await self._generate_export_metadata(export_data, request)
            
            # Generate checksum
            checksum = await self._generate_file_checksum(file_path)
            
            # Update export record
            completed_at = datetime.utcnow()
            
            update_data = {
                "status": BackupStatus.COMPLETED,
                "file_path": file_path,
                "file_size_bytes": file_size,
                "checksum": checksum,
                "metadata": metadata.dict(),
                "completed_at": completed_at
            }
            
            # Generate temporary download URL (in production, this would be a signed URL)
            download_url = f"/api/v1/exports/{export_id}/download"
            update_data["download_url"] = download_url
            
            await self.firestore.update_document(
                collection=f"exports/{user_id}/user_exports",
                document_id=export_id,
                data=update_data
            )
            
            logger.info(
                "Export completed successfully",
                user_id=user_id,
                export_id=export_id,
                export_type=request.export_type.value,
                format=request.format.value,
                file_size=file_size,
                duration_seconds=(completed_at - started_at).total_seconds()
            )
            
            return ExportRecordResponse(
                id=export_id,
                user_id=user_id,
                export_type=request.export_type,
                format=request.format,
                status=BackupStatus.COMPLETED,
                file_size_bytes=file_size,
                download_url=download_url,
                expires_at=export_record.expires_at,
                metadata=metadata,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
                error_message=None,
                created_at=export_record.created_at
            )
            
        except Exception as e:
            logger.error("Failed to create export", user_id=user_id, export_id=export_id, error=str(e))
            
            # Update export record with failure
            await self.firestore.update_document(
                collection=f"exports/{user_id}/user_exports",
                document_id=export_id,
                data={
                    "status": BackupStatus.FAILED,
                    "completed_at": datetime.utcnow(),
                    "error_message": str(e)
                }
            )
            
            raise AppValidationError(
                message="Failed to create export",
                details=[str(e)]
            )
    
    async def get_export(self, user_id: str, export_id: str) -> Optional[ExportRecordResponse]:
        """Get export record by ID."""
        try:
            export_record = await self.firestore.get_document(
                collection=f"exports/{user_id}/user_exports",
                document_id=export_id,
                model_class=ExportRecord
            )
            
            if not export_record:
                return None
            
            return ExportRecordResponse(
                id=export_record.id,
                user_id=export_record.user_id,
                export_type=export_record.export_type,
                format=export_record.format,
                status=export_record.status,
                file_size_bytes=export_record.file_size_bytes,
                download_url=export_record.download_url,
                expires_at=export_record.expires_at,
                metadata=export_record.metadata,
                started_at=export_record.started_at,
                completed_at=export_record.completed_at,
                duration_seconds=export_record.duration_seconds,
                error_message=export_record.error_message,
                created_at=export_record.created_at
            )
            
        except Exception as e:
            logger.error("Failed to get export", user_id=user_id, export_id=export_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve export",
                details=[str(e)]
            )
    
    async def list_exports(self, user_id: str, limit: int = 50) -> List[ExportRecordResponse]:
        """List user's export records."""
        try:
            export_records = await self.firestore.query_documents(
                collection=f"exports/{user_id}/user_exports",
                model_class=ExportRecord,
                order_by="created_at",
                limit=limit
            )
            
            responses = []
            for record in export_records:
                responses.append(ExportRecordResponse(
                    id=record.id,
                    user_id=record.user_id,
                    export_type=record.export_type,
                    format=record.format,
                    status=record.status,
                    file_size_bytes=record.file_size_bytes,
                    download_url=record.download_url,
                    expires_at=record.expires_at,
                    metadata=record.metadata,
                    started_at=record.started_at,
                    completed_at=record.completed_at,
                    duration_seconds=record.duration_seconds,
                    error_message=record.error_message,
                    created_at=record.created_at
                ))
            
            return responses
            
        except Exception as e:
            logger.error("Failed to list exports", user_id=user_id, error=str(e))
            raise AppValidationError(
                message="Failed to list exports",
                details=[str(e)]
            )
    
    async def delete_export(self, user_id: str, export_id: str) -> None:
        """Delete export record and file."""
        try:
            # Get export record
            export_record = await self.firestore.get_document(
                collection=f"exports/{user_id}/user_exports",
                document_id=export_id,
                model_class=ExportRecord
            )
            
            if not export_record:
                raise NotFoundError(
                    message="Export not found",
                    resource_type="export",
                    resource_id=export_id
                )
            
            # Delete file if exists
            if export_record.file_path and export_record.file_path.startswith('/'):
                try:
                    import os
                    if os.path.exists(export_record.file_path):
                        os.remove(export_record.file_path)
                except Exception as e:
                    logger.warning("Failed to delete export file", file_path=export_record.file_path, error=str(e))
            
            # Delete export record
            await self.firestore.delete_document(
                collection=f"exports/{user_id}/user_exports",
                document_id=export_id
            )
            
            logger.info("Export deleted", user_id=user_id, export_id=export_id)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete export", user_id=user_id, export_id=export_id, error=str(e))
            raise AppValidationError(
                message="Failed to delete export",
                details=[str(e)]
            )
    
    async def get_export_file(self, user_id: str, export_id: str) -> Tuple[str, bytes]:
        """Get export file content."""
        try:
            export_record = await self.firestore.get_document(
                collection=f"exports/{user_id}/user_exports",
                document_id=export_id,
                model_class=ExportRecord
            )
            
            if not export_record:
                raise NotFoundError(
                    message="Export not found",
                    resource_type="export",
                    resource_id=export_id
                )
            
            if export_record.status != BackupStatus.COMPLETED:
                raise BusinessLogicError(
                    message="Export is not ready for download",
                    details=[f"Export status: {export_record.status}"]
                )
            
            if datetime.utcnow() > export_record.expires_at:
                raise BusinessLogicError(
                    message="Export has expired",
                    details=["Please create a new export"]
                )
            
            # Read file content
            async with aiofiles.open(export_record.file_path, 'rb') as f:
                file_content = await f.read()
            
            # Generate filename
            timestamp = export_record.created_at.strftime("%Y%m%d_%H%M%S")
            filename = f"financial_nomad_{export_record.export_type.value}_{timestamp}.{export_record.format.value}"
            
            return filename, file_content
            
        except (NotFoundError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error("Failed to get export file", user_id=user_id, export_id=export_id, error=str(e))
            raise AppValidationError(
                message="Failed to retrieve export file",
                details=[str(e)]
            )
    
    # Private helper methods
    
    async def _collect_export_data(self, user_id: str, request: ExportRequest) -> Dict[str, Any]:
        """Collect data based on export request."""
        data = {
            "user_id": user_id,
            "export_timestamp": datetime.utcnow().isoformat(),
            "export_params": request.dict(),
            "data": {}
        }
        
        try:
            # Always include user profile for context
            user = await self.firestore.get_document(
                collection="users",
                document_id=user_id,
                model_class=User
            )
            if user and not request.anonymize_data:
                data["data"]["user"] = user.dict()
            
            # Collect data based on export type
            if request.export_type in [ExportType.FULL_BACKUP, ExportType.TRANSACTIONS_ONLY]:
                data["data"]["transactions"] = await self._collect_transactions(user_id, request)
            
            if request.export_type in [ExportType.FULL_BACKUP, ExportType.BUDGETS_ONLY]:
                data["data"]["budgets"] = await self._collect_budgets(user_id, request)
            
            if request.export_type == ExportType.FULL_BACKUP:
                data["data"]["accounts"] = await self._collect_accounts(user_id, request)
                data["data"]["categories"] = await self._collect_categories(user_id, request)
                data["data"]["recurring_transactions"] = await self._collect_recurring_transactions(user_id, request)
            
            if request.export_type == ExportType.LLM_SNAPSHOT:
                data = await self._prepare_llm_snapshot(user_id, request)
            
            if request.export_type == ExportType.FINANCIAL_SUMMARY:
                data["data"]["summary"] = await self._generate_financial_summary(user_id, request)
            
            # Apply anonymization if requested
            if request.anonymize_data and request.export_type != ExportType.LLM_SNAPSHOT:
                data = await self._anonymize_data(data)
            
            return data
            
        except Exception as e:
            logger.error("Failed to collect export data", user_id=user_id, error=str(e))
            raise
    
    async def _collect_transactions(self, user_id: str, request: ExportRequest) -> List[Dict[str, Any]]:
        """Collect transactions based on request filters."""
        where_clauses = []
        
        # Apply date filters
        if request.date_range_start:
            where_clauses.append(("transaction_date", ">=", request.date_range_start))
        if request.date_range_end:
            where_clauses.append(("transaction_date", "<=", request.date_range_end))
        
        # Apply category filters
        if request.include_categories:
            where_clauses.append(("category_id", "in", request.include_categories))
        
        # Apply account filters
        if request.include_accounts:
            where_clauses.append(("account_id", "in", request.include_accounts))
        
        transactions = await self.firestore.query_documents(
            collection=f"transactions/{user_id}/user_transactions",
            model_class=Transaction,
            where_clauses=where_clauses,
            order_by="transaction_date"
        )
        
        return [transaction.dict() for transaction in transactions]
    
    async def _collect_budgets(self, user_id: str, request: ExportRequest) -> List[Dict[str, Any]]:
        """Collect budgets based on request filters."""
        where_clauses = []
        
        # Apply category filters
        if request.include_categories:
            where_clauses.append(("category_id", "in", request.include_categories))
        
        budgets = await self.firestore.query_documents(
            collection=f"budgets/{user_id}/user_budgets",
            model_class=Budget,
            where_clauses=where_clauses,
            order_by="period_start"
        )
        
        return [budget.dict() for budget in budgets]
    
    async def _collect_accounts(self, user_id: str, request: ExportRequest) -> List[Dict[str, Any]]:
        """Collect bank accounts."""
        where_clauses = []
        
        if request.include_accounts:
            where_clauses.append(("id", "in", request.include_accounts))
        
        accounts = await self.firestore.query_documents(
            collection=f"accounts/{user_id}/bank_accounts",
            model_class=Account,
            where_clauses=where_clauses
        )
        
        return [account.dict() for account in accounts]
    
    async def _collect_categories(self, user_id: str, request: ExportRequest) -> List[Dict[str, Any]]:
        """Collect categories."""
        where_clauses = []
        
        if request.include_categories:
            where_clauses.append(("id", "in", request.include_categories))
        
        categories = await self.firestore.query_documents(
            collection=f"categories/{user_id}/user_categories",
            model_class=Category,
            where_clauses=where_clauses
        )
        
        return [category.dict() for category in categories]
    
    async def _collect_recurring_transactions(self, user_id: str, request: ExportRequest) -> List[Dict[str, Any]]:
        """Collect recurring transactions."""
        recurring = await self.firestore.query_documents(
            collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
            model_class=RecurringTransaction
        )
        
        return [rec.dict() for rec in recurring]
    
    async def _prepare_llm_snapshot(self, user_id: str, request: ExportRequest) -> Dict[str, Any]:
        """Prepare anonymized snapshot for LLM analysis."""
        # This creates a special format optimized for LLM consumption
        snapshot = {
            "snapshot_id": str(uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "date_range": {
                "start": request.date_range_start.isoformat() if request.date_range_start else None,
                "end": request.date_range_end.isoformat() if request.date_range_end else None
            },
            "instructions": "Analyze this financial data and provide insights on spending patterns, budget adherence, and recommendations for improvement.",
            "constraints": "Do not attempt to identify the user. Focus only on patterns and financial health metrics.",
            "data": {}
        }
        
        # Collect and anonymize data
        transactions = await self._collect_transactions(user_id, request)
        budgets = await self._collect_budgets(user_id, request)
        categories = await self._collect_categories(user_id, request)
        accounts = await self._collect_accounts(user_id, request)
        
        # Create category mapping for anonymization
        category_map = {}
        for i, category in enumerate(categories):
            category_map[category['id']] = f"CATEGORY_{i+1:03d}"
        
        # Create account mapping
        account_map = {}
        for i, account in enumerate(accounts):
            account_map[account['id']] = f"ACCOUNT_{i+1:03d}"
        
        # Anonymize and structure data
        snapshot["data"] = {
            "categories": [
                {
                    "id": category_map.get(cat['id'], cat['id']),
                    "type": cat.get('type'),
                    "name": f"Category {i+1}"
                }
                for i, cat in enumerate(categories)
            ],
            "accounts": [
                {
                    "id": account_map.get(acc['id'], acc['id']),
                    "type": acc.get('account_type'),
                    "name": f"Account {i+1}"
                }
                for i, acc in enumerate(accounts)
            ],
            "transactions": [
                {
                    "amount": txn.get('amount'),
                    "type": txn.get('transaction_type'),
                    "category": category_map.get(txn.get('category_id'), 'UNKNOWN'),
                    "account": account_map.get(txn.get('account_id'), 'UNKNOWN'),
                    "date": txn.get('transaction_date'),
                    "description_length": len(txn.get('description', ''))
                }
                for txn in transactions
            ],
            "budgets": [
                {
                    "category": category_map.get(budget.get('category_id'), 'UNKNOWN'),
                    "amount": budget.get('amount'),
                    "spent_amount": budget.get('spent_amount', 0),
                    "period_start": budget.get('period_start'),
                    "period_end": budget.get('period_end')
                }
                for budget in budgets
            ]
        }
        
        return snapshot
    
    async def _generate_financial_summary(self, user_id: str, request: ExportRequest) -> Dict[str, Any]:
        """Generate financial summary report."""
        transactions = await self._collect_transactions(user_id, request)
        budgets = await self._collect_budgets(user_id, request)
        
        # Calculate summary statistics
        total_income = sum(txn.get('amount', 0) for txn in transactions if txn.get('transaction_type') == 'income')
        total_expenses = sum(txn.get('amount', 0) for txn in transactions if txn.get('transaction_type') == 'expense')
        
        # Calculate monthly breakdowns
        monthly_stats = {}
        for txn in transactions:
            if txn.get('transaction_date'):
                month_key = txn['transaction_date'][:7]  # YYYY-MM format
                if month_key not in monthly_stats:
                    monthly_stats[month_key] = {'income': 0, 'expenses': 0}
                
                if txn.get('transaction_type') == 'income':
                    monthly_stats[month_key]['income'] += txn.get('amount', 0)
                else:
                    monthly_stats[month_key]['expenses'] += txn.get('amount', 0)
        
        return {
            "period": {
                "start": request.date_range_start.isoformat() if request.date_range_start else None,
                "end": request.date_range_end.isoformat() if request.date_range_end else None
            },
            "totals": {
                "income": total_income,
                "expenses": total_expenses,
                "net": total_income - total_expenses
            },
            "transactions_count": len(transactions),
            "budgets_count": len(budgets),
            "monthly_breakdown": monthly_stats,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def _generate_export_file(
        self, user_id: str, export_id: str, data: Dict[str, Any], request: ExportRequest
    ) -> Tuple[str, int]:
        """Generate export file in requested format."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{user_id}_{export_id}_{timestamp}"
        
        if request.format == ExportFormat.JSON:
            return await self._generate_json_file(filename, data, request.compress_output)
        elif request.format == ExportFormat.CSV:
            return await self._generate_csv_file(filename, data, request.compress_output)
        elif request.format == ExportFormat.YAML:
            return await self._generate_yaml_file(filename, data, request.compress_output)
        elif request.format == ExportFormat.PDF:
            return await self._generate_pdf_file(filename, data)
        else:
            raise ValueError(f"Unsupported export format: {request.format}")
    
    async def _generate_json_file(self, filename: str, data: Dict[str, Any], compress: bool) -> Tuple[str, int]:
        """Generate JSON export file."""
        json_content = json.dumps(data, default=str, indent=2)
        
        if compress:
            compressed_data = gzip.compress(json_content.encode('utf-8'))
            file_path = f"{self.export_base_dir}/{filename}.json.gz"
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(compressed_data)
            
            return file_path, len(compressed_data)
        else:
            file_path = f"{self.export_base_dir}/{filename}.json"
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json_content)
            
            return file_path, len(json_content.encode('utf-8'))
    
    async def _generate_csv_file(self, filename: str, data: Dict[str, Any], compress: bool) -> Tuple[str, int]:
        """Generate CSV export file."""
        # Create CSV content from transactions data
        output = io.StringIO()
        
        # Extract transactions for CSV format
        transactions = data.get('data', {}).get('transactions', [])
        if transactions:
            # CSV headers
            fieldnames = ['date', 'type', 'amount', 'description', 'category_id', 'account_id']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write transaction rows
            for txn in transactions:
                writer.writerow({
                    'date': txn.get('transaction_date', ''),
                    'type': txn.get('transaction_type', ''),
                    'amount': txn.get('amount', 0),
                    'description': txn.get('description', ''),
                    'category_id': txn.get('category_id', ''),
                    'account_id': txn.get('account_id', '')
                })
        
        csv_content = output.getvalue()
        output.close()
        
        if compress:
            compressed_data = gzip.compress(csv_content.encode('utf-8'))
            file_path = f"{self.export_base_dir}/{filename}.csv.gz"
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(compressed_data)
            
            return file_path, len(compressed_data)
        else:
            file_path = f"{self.export_base_dir}/{filename}.csv"
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(csv_content)
            
            return file_path, len(csv_content.encode('utf-8'))
    
    async def _generate_yaml_file(self, filename: str, data: Dict[str, Any], compress: bool) -> Tuple[str, int]:
        """Generate YAML export file."""
        import yaml
        
        yaml_content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        
        if compress:
            compressed_data = gzip.compress(yaml_content.encode('utf-8'))
            file_path = f"{self.export_base_dir}/{filename}.yaml.gz"
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(compressed_data)
            
            return file_path, len(compressed_data)
        else:
            file_path = f"{self.export_base_dir}/{filename}.yaml"
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(yaml_content)
            
            return file_path, len(yaml_content.encode('utf-8'))
    
    async def _generate_pdf_file(self, filename: str, data: Dict[str, Any]) -> Tuple[str, int]:
        """Generate PDF export file."""
        file_path = f"{self.export_base_dir}/{filename}.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.darkblue,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("Financial Nomad Export", title_style))
        story.append(Spacer(1, 12))
        
        # Export info
        export_info = data.get('export_params', {})
        info_text = f"Export Type: {export_info.get('export_type', 'Unknown')}<br/>"
        info_text += f"Generated: {data.get('export_timestamp', 'Unknown')}<br/>"
        story.append(Paragraph(info_text, styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Transactions table
        transactions = data.get('data', {}).get('transactions', [])
        if transactions:
            story.append(Paragraph("Transactions", styles['Heading2']))
            
            # Prepare table data
            table_data = [['Date', 'Type', 'Amount', 'Description']]
            for txn in transactions[:50]:  # Limit for PDF readability
                table_data.append([
                    txn.get('transaction_date', '')[:10],  # Date only
                    txn.get('transaction_type', ''),
                    f"${txn.get('amount', 0):.2f}",
                    (txn.get('description', '') or '')[:30]  # Truncate description
                ])
            
            # Create table
            table = Table(table_data, colWidths=[1.5*inch, 1*inch, 1*inch, 2.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
        
        # Build PDF
        doc.build(story)
        
        # Get file size
        import os
        file_size = os.path.getsize(file_path)
        
        return file_path, file_size
    
    async def _generate_export_metadata(self, data: Dict[str, Any], request: ExportRequest) -> BackupMetadata:
        """Generate metadata for export."""
        export_data = data.get('data', {})
        
        transactions = export_data.get('transactions', [])
        date_range_start = None
        date_range_end = None
        
        if transactions:
            dates = [t.get('transaction_date') for t in transactions if t.get('transaction_date')]
            if dates:
                date_range_start = min(dates)
                date_range_end = max(dates)
        
        return BackupMetadata(
            users_count=1,
            accounts_count=len(export_data.get('accounts', [])),
            transactions_count=len(transactions),
            categories_count=len(export_data.get('categories', [])),
            budgets_count=len(export_data.get('budgets', [])),
            date_range_start=date_range_start,
            date_range_end=date_range_end
        )
    
    async def _anonymize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize personal data in export."""
        # Remove or anonymize PII
        if 'data' in data and 'user' in data['data']:
            user_data = data['data']['user']
            user_data['email'] = "user@example.com"
            user_data['name'] = "Anonymous User"
            user_data['phone'] = None
        
        # Anonymize transaction descriptions
        if 'data' in data and 'transactions' in data['data']:
            for txn in data['data']['transactions']:
                if 'description' in txn and txn['description']:
                    # Replace with generic description based on category
                    txn['description'] = f"Transaction {txn.get('transaction_type', 'unknown')}"
        
        return data
    
    async def _generate_file_checksum(self, file_path: str) -> str:
        """Generate SHA-256 checksum of file."""
        hash_sha256 = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            async for chunk in f:
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()


# Global service instance
_export_service: Optional[ExportService] = None


def get_export_service() -> ExportService:
    """Get the global export service instance."""
    global _export_service
    if _export_service is None:
        _export_service = ExportService()
    return _export_service