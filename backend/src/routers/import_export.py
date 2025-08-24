"""
Import/Export endpoints for transactions.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header, File, UploadFile
from fastapi.responses import PlainTextResponse
import yaml
from typing import Optional

from ..models.auth import User
from ..models.import_models import (
    YAMLImportRequest,
    YAMLImportResponse,
    YAMLExportRequest,
    YAMLExportResponse
)
from ..services.import_service import get_import_export_service, ImportExportService
from ..services.auth import get_auth_service
from ..utils.exceptions import ValidationError as AppValidationError, AuthenticationError

router = APIRouter(prefix="/import-export", tags=["import-export"])


async def get_current_user(authorization: str = Header(None)) -> User:
    """Get current authenticated user from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format"
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    try:
        auth_service = get_auth_service()
        user, session = await auth_service.verify_jwt_token(token)
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": e.code,
                "message": e.message
            }
        )


@router.post(
    "/transactions/import/yaml",
    response_model=YAMLImportResponse,
    summary="Import Transactions from YAML",
    description="Import transactions from YAML data. Supports dry run mode for validation."
)
async def import_transactions_yaml(
    request: YAMLImportRequest,
    current_user: User = Depends(get_current_user),
    import_service: ImportExportService = Depends(get_import_export_service)
) -> YAMLImportResponse:
    """Import transactions from YAML data."""
    try:
        return await import_service.import_yaml_transactions(current_user.id, request)
    except AppValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )


@router.post(
    "/transactions/import/yaml/file",
    response_model=YAMLImportResponse,
    summary="Import Transactions from YAML File",
    description="Upload and import transactions from a YAML file."
)
async def import_transactions_yaml_file(
    file: UploadFile = File(..., description="YAML file containing transactions"),
    dry_run: bool = False,
    create_missing_categories: bool = False,
    default_category_type: str = "expense",
    current_user: User = Depends(get_current_user),
    import_service: ImportExportService = Depends(get_import_export_service)
) -> YAMLImportResponse:
    """Import transactions from uploaded YAML file."""
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.yaml', '.yml')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_FILE_TYPE",
                    "message": "File must be a YAML file with .yaml or .yml extension"
                }
            )
        
        # Read file content
        content = await file.read()
        
        # Parse YAML
        try:
            yaml_data = yaml.safe_load(content.decode('utf-8'))
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_YAML",
                    "message": f"Invalid YAML format: {str(e)}"
                }
            )
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_ENCODING",
                    "message": "File must be UTF-8 encoded"
                }
            )
        
        # Validate YAML structure
        if not isinstance(yaml_data, dict) or 'transactions' not in yaml_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_STRUCTURE",
                    "message": "YAML file must contain a 'transactions' key with a list of transactions"
                }
            )
        
        # Create import request
        request = YAMLImportRequest(
            transactions=yaml_data['transactions'],
            dry_run=dry_run,
            create_missing_categories=create_missing_categories,
            default_category_type=default_category_type
        )
        
        return await import_service.import_yaml_transactions(current_user.id, request)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "IMPORT_ERROR",
                "message": f"Failed to import YAML file: {str(e)}"
            }
        )


@router.post(
    "/transactions/export/yaml",
    response_model=YAMLExportResponse,
    summary="Export Transactions to YAML",
    description="Export transactions to YAML format with optional filters."
)
async def export_transactions_yaml(
    request: YAMLExportRequest,
    current_user: User = Depends(get_current_user),
    import_service: ImportExportService = Depends(get_import_export_service)
) -> YAMLExportResponse:
    """Export transactions to YAML format."""
    try:
        return await import_service.export_yaml_transactions(current_user.id, request)
    except AppValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )


@router.post(
    "/transactions/export/yaml/download",
    response_class=PlainTextResponse,
    summary="Download Transactions as YAML File",
    description="Export and download transactions as a YAML file."
)
async def download_transactions_yaml(
    request: YAMLExportRequest,
    current_user: User = Depends(get_current_user),
    import_service: ImportExportService = Depends(get_import_export_service)
) -> PlainTextResponse:
    """Export and download transactions as YAML file."""
    try:
        export_result = await import_service.export_yaml_transactions(current_user.id, request)
        
        return PlainTextResponse(
            content=export_result.yaml_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": f"attachment; filename={export_result.filename}"
            }
        )
        
    except AppValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )


@router.get(
    "/transactions/template/yaml",
    response_class=PlainTextResponse,
    summary="Get YAML Import Template",
    description="Download a template YAML file showing the expected format for imports."
)
async def get_yaml_template() -> PlainTextResponse:
    """Get YAML import template."""
    template = """# Transaction Import Template
# Copy this template and fill in your transaction data

transactions:
  - account_name: "Checking Account"           # Required: Name of the account (must exist)
    category_name: "Groceries"                # Optional: Category name (will be created if create_missing_categories=true)
    amount: -45.67                           # Required: Amount (negative for expenses, positive for income)
    description: "Weekly grocery shopping"    # Required: Transaction description
    date: "2024-01-15T10:30:00"             # Required: Transaction date in ISO format
    destination_account_name: null           # Optional: For transfers between accounts
    reference_number: "TXN001"              # Optional: Reference or check number
    notes: "Bought vegetables and fruits"    # Optional: Additional notes
    tags:                                   # Optional: List of tags
      - "food"
      - "weekly"
  
  - account_name: "Savings Account"
    category_name: "Salary"
    amount: 2500.00
    description: "Monthly salary"
    date: "2024-01-01T09:00:00"
    reference_number: "SAL202401"
    tags:
      - "income"
      - "monthly"
  
  - account_name: "Checking Account"
    amount: -500.00
    description: "Transfer to savings"
    date: "2024-01-02T14:00:00"
    destination_account_name: "Savings Account"
    category_name: null  # Transfers typically don't need a category
    tags:
      - "transfer"

# Notes:
# - All account names must match existing accounts in your system
# - Dates should be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
# - Negative amounts are expenses, positive amounts are income
# - Use destination_account_name for transfers between accounts
# - Tags are optional but can help with organization
"""
    
    return PlainTextResponse(
        content=template,
        media_type="application/x-yaml",
        headers={
            "Content-Disposition": "attachment; filename=transaction_import_template.yaml"
        }
    )