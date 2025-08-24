#!/bin/bash

# Production deployment script for Financial Nomad API
# Deploys to Google Cloud Run using Cloud Build

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="financial-nomad-api"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

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
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    # Check project ID
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
        if [ -z "$PROJECT_ID" ]; then
            log_error "PROJECT_ID not set and no default project configured"
            log_info "Set PROJECT_ID environment variable or run 'gcloud config set project PROJECT_ID'"
            exit 1
        fi
    fi
    
    log_success "Prerequisites validated. Project: $PROJECT_ID, Region: $REGION"
}

# Enable required APIs
enable_apis() {
    log_info "Enabling required Google Cloud APIs..."
    
    gcloud services enable \
        cloudbuild.googleapis.com \
        run.googleapis.com \
        containerregistry.googleapis.com \
        secretmanager.googleapis.com \
        firestore.googleapis.com \
        --project="$PROJECT_ID"
    
    log_success "APIs enabled successfully"
}

# Create service account if it doesn't exist
create_service_account() {
    local sa_email="financial-nomad-api@$PROJECT_ID.iam.gserviceaccount.com"
    
    log_info "Checking service account..."
    
    if ! gcloud iam service-accounts describe "$sa_email" --project="$PROJECT_ID" &>/dev/null; then
        log_info "Creating service account..."
        
        gcloud iam service-accounts create financial-nomad-api \
            --display-name="Financial Nomad API Service Account" \
            --description="Service account for Financial Nomad API on Cloud Run" \
            --project="$PROJECT_ID"
        
        # Grant necessary permissions
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$sa_email" \
            --role="roles/datastore.user"
        
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$sa_email" \
            --role="roles/secretmanager.secretAccessor"
        
        log_success "Service account created and configured"
    else
        log_info "Service account already exists"
    fi
}

# Create secrets if they don't exist
create_secrets() {
    log_info "Checking required secrets..."
    
    local secrets=("jwt-secret" "google-client-secret" "asana-client-secret")
    
    for secret in "${secrets[@]}"; do
        if ! gcloud secrets describe "$secret" --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Secret '$secret' does not exist. Creating placeholder..."
            echo "CHANGE_ME_$(date +%s)" | gcloud secrets create "$secret" \
                --data-file=- \
                --project="$PROJECT_ID"
            log_warning "Please update secret '$secret' with the actual value using:"
            log_warning "  gcloud secrets versions add $secret --data-file=path/to/secret"
        else
            log_info "Secret '$secret' already exists"
        fi
    done
    
    log_success "Secrets validated"
}

# Run the deployment
deploy() {
    log_info "Starting deployment to Cloud Run..."
    
    cd "$BACKEND_DIR"
    
    # Submit build to Cloud Build
    gcloud builds submit \
        --config=devops/production/cloudbuild.yaml \
        --substitutions=_REGION="$REGION" \
        --project="$PROJECT_ID" \
        .
    
    log_success "Deployment completed successfully"
}

# Get service URL and validate
validate_deployment() {
    log_info "Validating deployment..."
    
    # Get the service URL
    local service_url
    service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.url)")
    
    if [ -z "$service_url" ]; then
        log_error "Failed to get service URL"
        exit 1
    fi
    
    log_info "Service URL: $service_url"
    
    # Wait for service to be ready
    log_info "Waiting for service to be ready..."
    sleep 30
    
    # Test health endpoint
    if curl -s -f "$service_url/api/v1/health" > /dev/null; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        exit 1
    fi
    
    # Test documentation
    if curl -s -f "$service_url/docs" > /dev/null; then
        log_success "Documentation accessible"
    else
        log_warning "Documentation endpoint check failed"
    fi
    
    log_success "Deployment validation completed"
    echo ""
    log_success "🎉 Deployment successful!"
    log_info "Service URL: $service_url"
    log_info "Health Check: $service_url/api/v1/health"
    log_info "Documentation: $service_url/docs"
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Financial Nomad API - Production Deployment${NC}"
    echo "Project: $PROJECT_ID"
    echo "Region: $REGION"
    echo ""
    
    validate_prerequisites
    enable_apis
    create_service_account
    create_secrets
    deploy
    validate_deployment
}

# Help function
show_help() {
    cat << EOF
Financial Nomad API - Production Deployment Script

Usage: $0 [OPTIONS]

Environment Variables:
    PROJECT_ID      Google Cloud Project ID (required)
    REGION          Deployment region (default: us-central1)

Examples:
    PROJECT_ID=my-project $0                    # Deploy to my-project
    PROJECT_ID=my-project REGION=europe-west1 $0  # Deploy to Europe

Prerequisites:
    - gcloud CLI installed and authenticated
    - Required APIs will be enabled automatically
    - Service account will be created automatically
    - Secrets will be created with placeholders (update them manually)

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi