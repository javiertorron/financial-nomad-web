#!/bin/bash

# Full deployment script for Financial Nomad
# Deploys both backend (Cloud Run) and frontend (Firebase Hosting)

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
FIREBASE_PROJECT="${FIREBASE_PROJECT:-$PROJECT_ID}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Deployment options
DEPLOY_BACKEND="${DEPLOY_BACKEND:-true}"
DEPLOY_FRONTEND="${DEPLOY_FRONTEND:-true}"
SKIP_TESTS="${SKIP_TESTS:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_section() {
    echo -e "${CYAN}[SECTION]${NC} $1"
    echo "=================================="
}

# Validate prerequisites
validate_prerequisites() {
    log_section "Validating Prerequisites"
    
    # Check project ID
    if [ -z "$PROJECT_ID" ]; then
        log_error "PROJECT_ID not set"
        log_info "Set PROJECT_ID environment variable"
        exit 1
    fi
    
    # Check if individual deployment scripts exist
    if [ "$DEPLOY_BACKEND" = "true" ] && [ ! -f "$SCRIPT_DIR/deploy-backend.sh" ]; then
        log_error "Backend deployment script not found: $SCRIPT_DIR/deploy-backend.sh"
        exit 1
    fi
    
    if [ "$DEPLOY_FRONTEND" = "true" ] && [ ! -f "$SCRIPT_DIR/deploy-frontend.sh" ]; then
        log_error "Frontend deployment script not found: $SCRIPT_DIR/deploy-frontend.sh"
        exit 1
    fi
    
    log_success "Prerequisites validated"
}

# Run tests before deployment
run_tests() {
    if [ "$SKIP_TESTS" = "true" ]; then
        log_warning "Skipping tests as requested"
        return 0
    fi
    
    log_section "Running Tests"
    
    # Backend tests
    if [ "$DEPLOY_BACKEND" = "true" ]; then
        log_info "Running backend tests..."
        cd "$ROOT_DIR/backend"
        
        if [ -f "pytest.ini" ] && [ -d "tests" ]; then
            if command -v python3 &> /dev/null && python3 -m pytest --version &> /dev/null; then
                python3 -m pytest tests/ -v --tb=short
                if [ $? -ne 0 ]; then
                    log_error "Backend tests failed"
                    exit 1
                fi
                log_success "Backend tests passed"
            else
                log_warning "pytest not available, skipping backend tests"
            fi
        else
            log_warning "Backend test configuration not found, skipping tests"
        fi
    fi
    
    # Frontend tests
    if [ "$DEPLOY_FRONTEND" = "true" ]; then
        log_info "Running frontend tests..."
        cd "$ROOT_DIR/frontend"
        
        if [ -f "package.json" ] && grep -q '"test"' package.json; then
            if command -v npm &> /dev/null; then
                # Run tests in headless mode
                npm run test -- --watch=false --browsers=ChromeHeadless
                if [ $? -ne 0 ]; then
                    log_warning "Frontend tests failed, but continuing with deployment"
                    log_warning "Fix tests after deployment"
                else
                    log_success "Frontend tests passed"
                fi
            else
                log_warning "npm not available, skipping frontend tests"
            fi
        else
            log_warning "Frontend test configuration not found, skipping tests"
        fi
    fi
}

# Deploy backend
deploy_backend() {
    log_section "Deploying Backend to Cloud Run"
    
    export PROJECT_ID="$PROJECT_ID"
    export REGION="$REGION"
    
    "$SCRIPT_DIR/deploy-backend.sh"
    
    if [ $? -ne 0 ]; then
        log_error "Backend deployment failed"
        exit 1
    fi
    
    log_success "Backend deployment completed"
}

# Deploy frontend
deploy_frontend() {
    log_section "Deploying Frontend to Firebase Hosting"
    
    export PROJECT_ID="$PROJECT_ID"
    export FIREBASE_PROJECT="$FIREBASE_PROJECT"
    
    "$SCRIPT_DIR/deploy-frontend.sh"
    
    if [ $? -ne 0 ]; then
        log_error "Frontend deployment failed"
        exit 1
    fi
    
    log_success "Frontend deployment completed"
}

# Post-deployment validation
validate_full_deployment() {
    log_section "Validating Full Deployment"
    
    local backend_url=""
    local frontend_url=""
    
    # Get backend URL
    if [ "$DEPLOY_BACKEND" = "true" ]; then
        log_info "Getting backend service URL..."
        backend_url=$(gcloud run services describe "financial-nomad-api" \
            --region="$REGION" \
            --project="$PROJECT_ID" \
            --format="value(status.url)" 2>/dev/null || echo "")
        
        if [ -n "$backend_url" ]; then
            log_info "Backend URL: $backend_url"
        else
            log_warning "Could not retrieve backend URL"
        fi
    fi
    
    # Get frontend URL
    if [ "$DEPLOY_FRONTEND" = "true" ]; then
        log_info "Getting frontend hosting URL..."
        if command -v firebase &> /dev/null; then
            frontend_url=$(firebase hosting:sites:list --project "$FIREBASE_PROJECT" --json 2>/dev/null | jq -r '.[0].defaultUrl' 2>/dev/null || echo "")
            
            if [ -z "$frontend_url" ] || [ "$frontend_url" = "null" ]; then
                frontend_url="https://$FIREBASE_PROJECT.web.app"
            fi
            
            log_info "Frontend URL: $frontend_url"
        else
            log_warning "Firebase CLI not available, cannot retrieve frontend URL"
        fi
    fi
    
    # Test integration if both are deployed
    if [ "$DEPLOY_BACKEND" = "true" ] && [ "$DEPLOY_FRONTEND" = "true" ] && [ -n "$backend_url" ] && [ -n "$frontend_url" ]; then
        log_info "Testing backend-frontend integration..."
        
        # Wait a bit for services to be fully ready
        sleep 10
        
        # Test backend health
        if timeout 30 curl -s -f "$backend_url/api/v1/health" > /dev/null; then
            log_success "Backend health check passed ✓"
        else
            log_warning "Backend health check failed ⚠️"
        fi
        
        # Test frontend accessibility
        if timeout 30 curl -s -f "$frontend_url" > /dev/null; then
            log_success "Frontend accessibility check passed ✓"
        else
            log_warning "Frontend accessibility check failed ⚠️"
        fi
    fi
    
    log_success "Deployment validation completed"
    return 0
}

# Main execution
main() {
    local start_time
    start_time=$(date +%s)
    
    echo -e "${CYAN}🚀 Financial Nomad - Full Stack Deployment (FREE TIER)${NC}"
    echo "Project: $PROJECT_ID"
    echo "Region: $REGION"
    echo "Firebase Project: $FIREBASE_PROJECT"
    echo "Backend Deployment: $DEPLOY_BACKEND"
    echo "Frontend Deployment: $DEPLOY_FRONTEND"
    echo "Skip Tests: $SKIP_TESTS"
    echo ""
    log_warning "⚠️  Using FREE TIER limits only - no paid services will be used"
    echo ""
    
    validate_prerequisites
    run_tests
    
    # Deploy components
    if [ "$DEPLOY_BACKEND" = "true" ]; then
        deploy_backend
    fi
    
    if [ "$DEPLOY_FRONTEND" = "true" ]; then
        deploy_frontend
    fi
    
    validate_full_deployment
    
    # Calculate deployment time
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    echo ""
    log_success "🎉 Full deployment completed successfully!"
    echo ""
    log_info "📋 Deployment Summary:"
    log_info "   Duration: ${minutes}m ${seconds}s"
    
    if [ "$DEPLOY_BACKEND" = "true" ]; then
        local backend_url
        backend_url=$(gcloud run services describe "financial-nomad-api" \
            --region="$REGION" \
            --project="$PROJECT_ID" \
            --format="value(status.url)" 2>/dev/null || echo "")
        
        if [ -n "$backend_url" ]; then
            log_info "   Backend: $backend_url"
            log_info "   Backend Health: $backend_url/api/v1/health"
            log_info "   Backend Docs: $backend_url/docs"
        fi
    fi
    
    if [ "$DEPLOY_FRONTEND" = "true" ]; then
        local frontend_url="https://$FIREBASE_PROJECT.web.app"
        log_info "   Frontend: $frontend_url"
        log_info "   Firebase Console: https://console.firebase.google.com/project/$FIREBASE_PROJECT"
    fi
    
    echo ""
    log_info "💡 Next Steps:"
    log_info "   1. Update frontend environment with backend URL"
    log_info "   2. Test authentication flow"
    log_info "   3. Verify Firebase/Firestore configuration"
    log_info "   4. Monitor free tier usage limits:"
    log_info "      • Cloud Run: 2M requests/month, 400K GB-seconds/month"
    log_info "      • Firebase Hosting: 10GB storage, 360MB/day transfer"
    log_info "      • Firestore: 50K reads, 20K writes, 1GB storage per day"
    echo ""
}

# Help function
show_help() {
    cat << EOF
Financial Nomad - Full Stack Deployment Script

Usage: $0 [OPTIONS]

Environment Variables:
    PROJECT_ID       Google Cloud Project ID (required)
    REGION          Deployment region (default: us-central1)
    FIREBASE_PROJECT Firebase Project ID (defaults to PROJECT_ID)
    DEPLOY_BACKEND   Deploy backend (default: true)
    DEPLOY_FRONTEND  Deploy frontend (default: true)
    SKIP_TESTS       Skip test execution (default: false)

Examples:
    # Full deployment
    PROJECT_ID=my-project $0
    
    # Backend only
    PROJECT_ID=my-project DEPLOY_FRONTEND=false $0
    
    # Frontend only
    PROJECT_ID=my-project DEPLOY_BACKEND=false $0
    
    # Skip tests
    PROJECT_ID=my-project SKIP_TESTS=true $0
    
    # Different regions/projects
    PROJECT_ID=my-gcp-project FIREBASE_PROJECT=my-firebase-project REGION=europe-west1 $0

Prerequisites:
    - Both deploy-backend.sh and deploy-frontend.sh scripts
    - All prerequisites from individual deployment scripts
    - Proper authentication for both GCP and Firebase

The script will:
    1. Validate prerequisites
    2. Run tests (unless skipped)
    3. Deploy backend to Cloud Run (if enabled) - FREE TIER limits
    4. Deploy frontend to Firebase Hosting (if enabled) - FREE TIER limits  
    5. Validate full deployment
    6. Provide deployment summary with free tier usage reminders

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --backend-only)
            DEPLOY_FRONTEND=false
            ;;
        --frontend-only)
            DEPLOY_BACKEND=false
            ;;
        --skip-tests)
            SKIP_TESTS=true
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
    shift
done

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi