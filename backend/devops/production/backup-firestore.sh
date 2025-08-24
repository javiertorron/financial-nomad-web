#!/bin/bash

# Firestore backup script for Financial Nomad API
# Creates manual backups and manages retention

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-}"
BACKUP_BUCKET="${BACKUP_BUCKET:-financial-nomad-backups}"
DATABASE_ID="${DATABASE_ID:-(default)}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check project ID
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
        if [ -z "$PROJECT_ID" ]; then
            log_error "PROJECT_ID not set and no default project configured"
            exit 1
        fi
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    log_success "Prerequisites validated. Project: $PROJECT_ID"
}

# Create backup bucket if it doesn't exist
ensure_backup_bucket() {
    log_info "Checking backup bucket..."
    
    if ! gsutil ls -b "gs://$BACKUP_BUCKET" &>/dev/null; then
        log_info "Creating backup bucket: $BACKUP_BUCKET"
        gsutil mb -p "$PROJECT_ID" -c STANDARD -l us-central1 "gs://$BACKUP_BUCKET"
        
        # Set lifecycle policy for cost optimization
        cat > /tmp/lifecycle-policy.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {
          "type": "SetStorageClass",
          "storageClass": "NEARLINE"
        },
        "condition": {
          "age": 30
        }
      },
      {
        "action": {
          "type": "SetStorageClass", 
          "storageClass": "COLDLINE"
        },
        "condition": {
          "age": 90
        }
      },
      {
        "action": {
          "type": "Delete"
        },
        "condition": {
          "age": 365
        }
      }
    ]
  }
}
EOF
        gsutil lifecycle set /tmp/lifecycle-policy.json "gs://$BACKUP_BUCKET"
        rm /tmp/lifecycle-policy.json
        
        log_success "Backup bucket created with lifecycle policy"
    else
        log_info "Backup bucket already exists"
    fi
}

# Create Firestore backup
create_backup() {
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_path="gs://$BACKUP_BUCKET/firestore/$timestamp"
    
    log_info "Creating Firestore backup..."
    log_info "Backup location: $backup_path"
    
    # Start the export operation
    local operation_name
    operation_name=$(gcloud firestore export "$backup_path" \
        --database="$DATABASE_ID" \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --async)
    
    if [ -z "$operation_name" ]; then
        log_error "Failed to start backup operation"
        exit 1
    fi
    
    log_info "Backup operation started: $operation_name"
    
    # Wait for completion (optional)
    if [ "${WAIT_FOR_COMPLETION:-false}" = "true" ]; then
        log_info "Waiting for backup to complete..."
        
        while true; do
            local status
            status=$(gcloud firestore operations describe "$operation_name" \
                --project="$PROJECT_ID" \
                --format="value(done)" 2>/dev/null || echo "false")
            
            if [ "$status" = "True" ]; then
                log_success "Backup completed successfully"
                break
            elif [ "$status" = "false" ]; then
                log_info "Backup in progress..."
                sleep 30
            else
                log_error "Failed to check backup status"
                exit 1
            fi
        done
        
        # Check if backup was successful
        local error
        error=$(gcloud firestore operations describe "$operation_name" \
            --project="$PROJECT_ID" \
            --format="value(error)" 2>/dev/null || echo "")
        
        if [ -n "$error" ] && [ "$error" != "null" ]; then
            log_error "Backup failed: $error"
            exit 1
        fi
    else
        log_info "Backup operation running asynchronously"
        log_info "Check status with: gcloud firestore operations describe $operation_name"
    fi
    
    # Record backup metadata
    create_backup_metadata "$backup_path" "$operation_name"
    
    echo "$backup_path"
}

# Create backup metadata
create_backup_metadata() {
    local backup_path="$1"
    local operation_name="$2"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    local metadata_file="/tmp/backup-metadata-$(date +%Y%m%d-%H%M%S).json"
    
    cat > "$metadata_file" << EOF
{
  "backup_path": "$backup_path",
  "operation_name": "$operation_name",
  "project_id": "$PROJECT_ID",
  "database_id": "$DATABASE_ID",
  "created_at": "$timestamp",
  "type": "manual",
  "retention_days": $RETENTION_DAYS,
  "script_version": "1.0"
}
EOF
    
    # Upload metadata to backup bucket
    gsutil cp "$metadata_file" "$backup_path/metadata.json"
    rm "$metadata_file"
    
    log_success "Backup metadata created"
}

# List existing backups
list_backups() {
    log_info "Listing existing backups..."
    
    if ! gsutil ls "gs://$BACKUP_BUCKET/firestore/" &>/dev/null; then
        log_warning "No backups found"
        return 0
    fi
    
    echo ""
    echo "Existing backups:"
    echo "=================="
    
    # List backup directories
    gsutil ls "gs://$BACKUP_BUCKET/firestore/" | while read -r backup_dir; do
        # Extract timestamp from path
        local backup_name
        backup_name=$(basename "$backup_dir")
        
        # Get backup size (approximate)
        local size
        size=$(gsutil du -s "$backup_dir" 2>/dev/null | awk '{print $1}' || echo "unknown")
        
        # Check if metadata exists
        local metadata_info=""
        if gsutil ls "$backup_dir/metadata.json" &>/dev/null; then
            metadata_info=" (with metadata)"
        fi
        
        echo "  $backup_name - Size: ${size} bytes${metadata_info}"
    done
    
    echo ""
}

# Clean up old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local cutoff_date
    cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)
    
    local deleted_count=0
    
    # List and process each backup
    gsutil ls "gs://$BACKUP_BUCKET/firestore/" 2>/dev/null | while read -r backup_dir; do
        local backup_name
        backup_name=$(basename "$backup_dir")
        
        # Extract date from backup name (format: YYYYMMDD-HHMMSS)
        local backup_date
        backup_date=$(echo "$backup_name" | cut -d'-' -f1)
        
        # Check if backup is older than retention period
        if [ "$backup_date" -lt "$cutoff_date" ]; then
            log_info "Deleting old backup: $backup_name"
            gsutil -m rm -r "$backup_dir"
            ((deleted_count++))
        fi
    done
    
    if [ $deleted_count -gt 0 ]; then
        log_success "Deleted $deleted_count old backups"
    else
        log_info "No old backups to delete"
    fi
}

# Verify backup integrity
verify_backup() {
    local backup_path="$1"
    
    log_info "Verifying backup integrity..."
    
    # Check if backup directory exists
    if ! gsutil ls "$backup_path/" &>/dev/null; then
        log_error "Backup directory not found: $backup_path"
        return 1
    fi
    
    # Check for required files
    local required_files=("all_namespaces" "all_kinds" "output-0")
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if ! gsutil ls "$backup_path/all_namespaces/all_kinds/$file" &>/dev/null; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        log_error "Backup verification failed. Missing files: ${missing_files[*]}"
        return 1
    fi
    
    # Check metadata
    if gsutil ls "$backup_path/metadata.json" &>/dev/null; then
        log_info "Metadata file found"
    else
        log_warning "Metadata file not found (older backup format)"
    fi
    
    log_success "Backup verification passed"
    return 0
}

# Restore from backup (dry run by default)
restore_backup() {
    local backup_path="$1"
    local dry_run="${2:-true}"
    
    if [ "$dry_run" = "true" ]; then
        log_warning "DRY RUN MODE - No actual restore will be performed"
    fi
    
    log_info "Preparing to restore from: $backup_path"
    
    # Verify backup exists and is valid
    if ! verify_backup "$backup_path"; then
        log_error "Backup verification failed, aborting restore"
        exit 1
    fi
    
    if [ "$dry_run" = "false" ]; then
        log_warning "This will overwrite existing data in the database!"
        read -p "Are you sure you want to continue? (yes/no): " confirm
        
        if [ "$confirm" != "yes" ]; then
            log_info "Restore cancelled"
            exit 0
        fi
        
        log_info "Starting restore operation..."
        gcloud firestore import "$backup_path" \
            --database="$DATABASE_ID" \
            --project="$PROJECT_ID" \
            --async
        
        log_success "Restore operation started"
        log_info "Monitor progress with: gcloud firestore operations list"
    else
        log_info "Restore command (dry run):"
        echo "gcloud firestore import $backup_path --database=$DATABASE_ID --project=$PROJECT_ID"
    fi
}

# Main execution
main() {
    local action="${1:-backup}"
    
    echo -e "${BLUE}🗄️ Financial Nomad API - Firestore Backup Tool${NC}"
    echo "Project: $PROJECT_ID"
    echo "Database: $DATABASE_ID"
    echo "Backup Bucket: $BACKUP_BUCKET"
    echo ""
    
    validate_prerequisites
    
    case "$action" in
        "backup")
            ensure_backup_bucket
            local backup_path
            backup_path=$(create_backup)
            cleanup_old_backups
            log_success "Backup completed: $backup_path"
            ;;
        "list")
            list_backups
            ;;
        "cleanup")
            cleanup_old_backups
            ;;
        "verify")
            local backup_path="${2:-}"
            if [ -z "$backup_path" ]; then
                log_error "Backup path required for verify action"
                show_help
                exit 1
            fi
            verify_backup "$backup_path"
            ;;
        "restore")
            local backup_path="${2:-}"
            local dry_run="${3:-true}"
            if [ -z "$backup_path" ]; then
                log_error "Backup path required for restore action"
                show_help
                exit 1
            fi
            restore_backup "$backup_path" "$dry_run"
            ;;
        *)
            log_error "Unknown action: $action"
            show_help
            exit 1
            ;;
    esac
}

# Help function
show_help() {
    cat << EOF
Financial Nomad API - Firestore Backup Tool

Usage: $0 [ACTION] [OPTIONS]

Actions:
    backup              Create a new backup (default)
    list                List existing backups
    cleanup             Remove old backups based on retention policy
    verify BACKUP_PATH  Verify backup integrity
    restore BACKUP_PATH [DRY_RUN]  Restore from backup (dry_run: true/false)

Environment Variables:
    PROJECT_ID          Google Cloud Project ID
    BACKUP_BUCKET       Backup storage bucket (default: financial-nomad-backups)
    DATABASE_ID         Firestore database ID (default: (default))
    RETENTION_DAYS      Backup retention in days (default: 30)
    WAIT_FOR_COMPLETION Wait for backup to complete (default: false)

Examples:
    $0 backup                                    # Create backup
    $0 list                                      # List backups
    $0 verify gs://bucket/firestore/20240115    # Verify backup
    $0 restore gs://bucket/firestore/20240115 true   # Dry run restore
    $0 restore gs://bucket/firestore/20240115 false  # Actual restore

EOF
}

# Parse command line arguments
if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi