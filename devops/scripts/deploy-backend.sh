#!/bin/bash

# Backend deployment script for Financial Nomad
# Deploys FastAPI backend to Google Cloud Run

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="financial-nomad-api"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
BACKEND_DIR="$ROOT_DIR/backend"

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
        log_info "Install from: https://cloud.google.com/sdk/docs/install"
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
    
    # Check backend directory exists
    if [ ! -d "$BACKEND_DIR" ]; then
        log_error "Backend directory not found: $BACKEND_DIR"
        exit 1
    fi
    
    # Check required files
    if [ ! -f "$BACKEND_DIR/Dockerfile.production" ]; then
        log_error "Dockerfile.production not found in backend directory"
        exit 1
    fi
    
    if [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
        log_error "requirements.txt not found in backend directory"
        exit 1
    fi
    
    log_success "Prerequisites validated. Project: $PROJECT_ID, Region: $REGION"
}

# Enable required APIs (Free tier only)
enable_apis() {
    log_info "Enabling required Google Cloud APIs (free tier only)..."
    
    gcloud services enable \
        cloudbuild.googleapis.com \
        run.googleapis.com \
        containerregistry.googleapis.com \
        secretmanager.googleapis.com \
        firestore.googleapis.com \
        --project="$PROJECT_ID" \
        --quiet
    
    log_success "APIs enabled successfully"
}

# Setup Container Registry (Free tier - no Artifact Registry)
setup_container_registry() {
    log_info "Setting up Container Registry (free tier)..."
    
    # Container Registry is automatically available, just verify authentication
    gcloud auth configure-docker --quiet
    
    log_success "Container Registry configured"
}

# Create service account if it doesn't exist
create_service_account() {
    local sa_name="financial-nomad-api"
    local sa_email="$sa_name@$PROJECT_ID.iam.gserviceaccount.com"
    
    log_info "Setting up service account..."
    
    if ! gcloud iam service-accounts describe "$sa_email" --project="$PROJECT_ID" &>/dev/null; then
        log_info "Creating service account..."
        
        gcloud iam service-accounts create "$sa_name" \
            --display-name="Financial Nomad API Service Account" \
            --description="Service account for Financial Nomad API on Cloud Run" \
            --project="$PROJECT_ID"
        
        # Grant necessary permissions (free tier only)
        local roles=(
            "roles/datastore.user"
            "roles/secretmanager.secretAccessor"
        )
        
        for role in "${roles[@]}"; do
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:$sa_email" \
                --role="$role" \
                --quiet
        done
        
        log_success "Service account created and configured"
    else
        log_info "Service account already exists"
    fi
}

# Create secrets if they don't exist
setup_secrets() {
    log_info "Setting up required secrets..."
    
    local secrets=(
        "jwt-secret-key"
        "session-secret-key"
        "asana-client-secret"
        "google-service-account-key"
    )
    
    for secret in "${secrets[@]}"; do
        if ! gcloud secrets describe "$secret" --project="$PROJECT_ID" &>/dev/null; then
            log_warning "Secret '$secret' does not exist. Creating placeholder..."
            echo "CHANGE_ME_$(date +%s)_$(openssl rand -hex 16)" | \
                gcloud secrets create "$secret" \
                    --data-file=- \
                    --project="$PROJECT_ID"
            
            log_warning "⚠️  Please update secret '$secret' with the actual value:"
            log_warning "   gcloud secrets versions add $secret --data-file=path/to/secret --project=$PROJECT_ID"
        else
            log_info "Secret '$secret' already exists"
        fi
    done
    
    log_success "Secrets setup completed"
}

# Build and deploy to Cloud Run
deploy() {
    log_info "Starting deployment to Cloud Run..."
    
    cd "$BACKEND_DIR"
    
    local image_name="gcr.io/$PROJECT_ID/financial-nomad-api:latest"
    
    # Build the container image
    log_info "Building container image..."
    gcloud builds submit \
        --tag="$image_name" \
        --file="Dockerfile.production" \
        --project="$PROJECT_ID" \
        --quiet \
        .
    
    log_success "Container image built successfully"
    
    # Deploy to Cloud Run
    log_info "Deploying to Cloud Run..."
    gcloud run deploy "$SERVICE_NAME" \
        --image="$image_name" \
        --platform=managed \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --service-account="financial-nomad-api@$PROJECT_ID.iam.gserviceaccount.com" \
        --set-env-vars="PROJECT_ID=$PROJECT_ID" \
        --set-secrets="JWT_SECRET_KEY=jwt-secret-key:latest,SESSION_SECRET_KEY=session-secret-key:latest,ASANA_CLIENT_SECRET=asana-client-secret:latest,GOOGLE_APPLICATION_CREDENTIALS_JSON=google-service-account-key:latest" \
        --memory=512Mi \
        --cpu=1 \
        --min-instances=0 \
        --max-instances=1 \
        --timeout=300s \
        --concurrency=1000 \
        --port=8080 \
        --allow-unauthenticated \
        --no-traffic \
        --quiet
    
    log_success "Deployment to Cloud Run completed"
}

# Validate deployment
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
    
    # Route traffic to new revision
    log_info "Routing traffic to new revision..."
    gcloud run services update-traffic "$SERVICE_NAME" \
        --to-latest \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --quiet
    
    # Wait for service to be ready
    log_info "Waiting for service to be ready..."
    sleep 30
    
    # Test health endpoint
    log_info "Testing health endpoint..."
    local health_url="$service_url/api/v1/health"
    if timeout 30 curl -s -f "$health_url" > /dev/null; then
        log_success "Health check passed ✓"
    else
        log_error "Health check failed ✗"
        log_warning "Check service logs: gcloud logs read --project=$PROJECT_ID --filter=\"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\""
        exit 1
    fi
    
    # Test OpenAPI documentation
    log_info "Testing OpenAPI documentation..."
    local docs_url="$service_url/docs"
    if timeout 30 curl -s -f "$docs_url" > /dev/null; then
        log_success "Documentation accessible ✓"
    else
        log_warning "Documentation endpoint check failed"
    fi
    
    log_success "Deployment validation completed"
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Financial Nomad Backend - Cloud Run Deployment${NC}"
    echo "Project: $PROJECT_ID"
    echo "Region: $REGION"
    echo "Service: $SERVICE_NAME"
    echo ""
    
    validate_prerequisites
    enable_apis
    setup_container_registry
    create_service_account
    setup_secrets
    deploy
    validate_deployment
    
    echo ""
    log_success "🎉 Backend deployment successful!"
    
    local service_url
    service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.url)")
    
    echo ""
    log_info "📋 Service Information:"
    log_info "   URL: $service_url"
    log_info "   Health: $service_url/api/v1/health"
    log_info "   Docs: $service_url/docs"
    log_info "   Logs: gcloud logs read --project=$PROJECT_ID --filter=\"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\""
    echo ""
    log_warning "⚠️  Remember to update the secrets with actual values!"
}

# Help function
show_help() {
    cat << EOF
Financial Nomad Backend - Cloud Run Deployment Script

Usage: $0 [OPTIONS]

Environment Variables:
    PROJECT_ID      Google Cloud Project ID (required)
    REGION          Deployment region (default: us-central1)

Examples:
    PROJECT_ID=my-project $0
    PROJECT_ID=my-project REGION=europe-west1 $0

Prerequisites:
    - gcloud CLI installed and authenticated
    - Backend code in ../backend/ directory
    - Dockerfile.production in backend directory

The script will:
    1. Enable required APIs (free tier only)
    2. Setup Container Registry authentication
    3. Create service account with minimal permissions
    4. Create secrets (with placeholders)
    5. Build container image using Cloud Build (free tier)
    6. Deploy to Cloud Run (free tier limits)
    7. Validate deployment

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
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi