#!/bin/bash

# Production deployment script for Financial Nomad API to Cloud Run
# This script handles the complete deployment process including:
# - Building and pushing Docker image
# - Deploying to Cloud Run
# - Configuring domain and SSL

set -euo pipefail

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${DEPLOY_REGION:-us-central1}"
SERVICE_NAME="financial-nomad-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
DOMAIN="${CUSTOM_DOMAIN:-api.financial-nomad.com}"

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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Validation functions
validate_prerequisites() {
    log_info "Validating prerequisites..."
    
    # Check required tools
    command -v gcloud >/dev/null 2>&1 || log_error "gcloud CLI not found. Please install Google Cloud SDK."
    command -v docker >/dev/null 2>&1 || log_error "Docker not found. Please install Docker."
    
    # Check if logged into gcloud
    gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q . || log_error "Not logged into gcloud. Run 'gcloud auth login'"
    
    # Validate project ID
    if [[ -z "${PROJECT_ID}" ]]; then
        log_error "GOOGLE_CLOUD_PROJECT environment variable not set"
    fi
    
    # Validate project exists and is accessible
    gcloud projects describe "${PROJECT_ID}" >/dev/null 2>&1 || log_error "Cannot access project ${PROJECT_ID}"
    
    log_success "Prerequisites validated"
}

enable_apis() {
    log_info "Enabling required Google Cloud APIs..."
    
    gcloud services enable \
        cloudbuild.googleapis.com \
        run.googleapis.com \
        containerregistry.googleapis.com \
        firestore.googleapis.com \
        secretmanager.googleapis.com \
        --project="${PROJECT_ID}" \
        --quiet
        
    log_success "APIs enabled"
}

build_and_push_image() {
    log_info "Building and pushing Docker image..."
    
    # Get git commit hash for tagging
    local git_hash=""
    if git rev-parse --git-dir > /dev/null 2>&1; then
        git_hash=$(git rev-parse --short HEAD)
    else
        git_hash="unknown"
    fi
    
    local image_tag="${IMAGE_NAME}:${git_hash}"
    local latest_tag="${IMAGE_NAME}:latest"
    
    # Build image using Cloud Build for better performance
    log_info "Building image with Cloud Build..."
    gcloud builds submit \
        --config=cloudbuild.yaml \
        --substitutions=_IMAGE_NAME="${image_tag}" \
        --project="${PROJECT_ID}" \
        .
    
    # Tag as latest
    gcloud container images add-tag "${image_tag}" "${latest_tag}" --quiet
    
    log_success "Image built and pushed: ${image_tag}"
    echo "IMAGE_TAG=${image_tag}" > .deployment-vars
}

create_service_account() {
    log_info "Creating service account for Cloud Run..."
    
    local sa_name="financial-nomad-service"
    local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Create service account if it doesn't exist
    if ! gcloud iam service-accounts describe "${sa_email}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
        gcloud iam service-accounts create "${sa_name}" \
            --display-name="Financial Nomad API Service Account" \
            --description="Service account for Financial Nomad API running on Cloud Run" \
            --project="${PROJECT_ID}"
    fi
    
    # Grant necessary roles
    local roles=(
        "roles/datastore.user"
        "roles/secretmanager.secretAccessor" 
        "roles/cloudsql.client"
        "roles/monitoring.metricWriter"
        "roles/logging.logWriter"
        "roles/cloudtrace.agent"
    )
    
    for role in "${roles[@]}"; do
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
            --member="serviceAccount:${sa_email}" \
            --role="${role}" \
            --quiet
    done
    
    log_success "Service account configured: ${sa_email}"
}

deploy_to_cloud_run() {
    log_info "Deploying to Cloud Run..."
    
    # Source deployment variables
    if [[ -f .deployment-vars ]]; then
        source .deployment-vars
    else
        IMAGE_TAG="${IMAGE_NAME}:latest"
    fi
    
    # Replace placeholders in service config
    sed "s/PROJECT_ID/${PROJECT_ID}/g" cloudrun-service.yaml > cloudrun-service-deploy.yaml
    sed -i "s|gcr.io/PROJECT_ID/financial-nomad-api:latest|${IMAGE_TAG}|g" cloudrun-service-deploy.yaml
    
    # Deploy service
    gcloud run services replace cloudrun-service-deploy.yaml \
        --region="${REGION}" \
        --project="${PROJECT_ID}"
    
    # Allow unauthenticated access (adjust based on your needs)
    gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --region="${REGION}" \
        --project="${PROJECT_ID}"
    
    # Get service URL
    local service_url
    service_url=$(gcloud run services describe "${SERVICE_NAME}" \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --format="value(status.url)")
    
    log_success "Service deployed: ${service_url}"
    
    # Cleanup
    rm -f cloudrun-service-deploy.yaml .deployment-vars
    
    echo "SERVICE_URL=${service_url}" > .deployment-output
}

configure_domain() {
    log_info "Configuring custom domain..."
    
    if [[ -n "${DOMAIN:-}" ]]; then
        # Map domain to service
        gcloud run domain-mappings create \
            --service="${SERVICE_NAME}" \
            --domain="${DOMAIN}" \
            --region="${REGION}" \
            --project="${PROJECT_ID}" || log_warning "Domain mapping might already exist"
            
        log_success "Domain configured: https://${DOMAIN}"
        log_info "Please ensure DNS is configured to point to Cloud Run"
    else
        log_info "No custom domain specified, skipping domain configuration"
    fi
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Source service URL
    if [[ -f .deployment-output ]]; then
        source .deployment-output
    fi
    
    local health_url="${SERVICE_URL}/api/v1/health"
    
    # Wait for service to be ready
    local max_attempts=30
    local attempt=1
    
    while [[ ${attempt} -le ${max_attempts} ]]; do
        log_info "Checking health endpoint (attempt ${attempt}/${max_attempts})..."
        
        if curl -sS --max-time 10 "${health_url}" >/dev/null 2>&1; then
            log_success "Service is healthy and responding"
            break
        fi
        
        if [[ ${attempt} -eq ${max_attempts} ]]; then
            log_error "Service health check failed after ${max_attempts} attempts"
        fi
        
        ((attempt++))
        sleep 10
    done
    
    # Show service info
    log_info "Deployment Summary:"
    echo "  Service: ${SERVICE_NAME}"
    echo "  Project: ${PROJECT_ID}"
    echo "  Region: ${REGION}"
    echo "  URL: ${SERVICE_URL}"
    echo "  Health: ${health_url}"
    
    if [[ -n "${DOMAIN:-}" ]]; then
        echo "  Domain: https://${DOMAIN}"
    fi
    
    # Cleanup
    rm -f .deployment-output
}

# Main execution
main() {
    log_info "Starting production deployment for Financial Nomad API"
    log_info "Project: ${PROJECT_ID}, Region: ${REGION}"
    
    validate_prerequisites
    enable_apis
    create_service_account
    build_and_push_image
    deploy_to_cloud_run
    configure_domain
    verify_deployment
    
    log_success "Deployment completed successfully!"
    log_info "Your API is now running on Cloud Run"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi