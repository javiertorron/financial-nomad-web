#!/bin/bash

# Frontend deployment script for Financial Nomad
# Builds Angular app and deploys to Firebase Hosting

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-}"
FIREBASE_PROJECT="${FIREBASE_PROJECT:-$PROJECT_ID}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
FRONTEND_DIR="$ROOT_DIR/frontend"

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
    
    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed. Please install Node.js 18 or higher."
        log_info "Download from: https://nodejs.org/"
        exit 1
    fi
    
    # Check Node.js version
    local node_version
    node_version=$(node --version | sed 's/v//')
    local major_version
    major_version=$(echo "$node_version" | cut -d. -f1)
    
    if [ "$major_version" -lt 18 ]; then
        log_error "Node.js version must be 18 or higher. Current: v$node_version"
        exit 1
    fi
    
    # Check if npm is installed
    if ! command -v npm &> /dev/null; then
        log_error "npm is not installed."
        exit 1
    fi
    
    # Check if Angular CLI is available
    if ! command -v ng &> /dev/null && ! npx -p @angular/cli ng version &> /dev/null; then
        log_error "Angular CLI is not available."
        log_info "Install globally: npm install -g @angular/cli"
        log_info "Or it will be used via npx"
    fi
    
    # Check if Firebase CLI is installed
    if ! command -v firebase &> /dev/null; then
        log_error "Firebase CLI is not installed. Please install it first."
        log_info "Install: npm install -g firebase-tools"
        exit 1
    fi
    
    # Check if authenticated with Firebase
    if ! firebase projects:list &> /dev/null; then
        log_error "Not authenticated with Firebase. Please run 'firebase login'"
        exit 1
    fi
    
    # Check project ID
    if [ -z "$FIREBASE_PROJECT" ]; then
        log_error "FIREBASE_PROJECT not set"
        log_info "Set PROJECT_ID or FIREBASE_PROJECT environment variable"
        exit 1
    fi
    
    # Check frontend directory exists
    if [ ! -d "$FRONTEND_DIR" ]; then
        log_error "Frontend directory not found: $FRONTEND_DIR"
        exit 1
    fi
    
    # Check required files
    if [ ! -f "$FRONTEND_DIR/package.json" ]; then
        log_error "package.json not found in frontend directory"
        exit 1
    fi
    
    if [ ! -f "$FRONTEND_DIR/angular.json" ]; then
        log_error "angular.json not found in frontend directory"
        exit 1
    fi
    
    log_success "Prerequisites validated. Firebase Project: $FIREBASE_PROJECT"
}

# Install dependencies
install_dependencies() {
    log_info "Installing frontend dependencies..."
    
    cd "$FRONTEND_DIR"
    
    # Clean install to ensure consistency (free tier optimized)
    if [ -d "node_modules" ]; then
        log_info "Cleaning existing node_modules..."
        rm -rf node_modules
    fi
    
    # Use npm ci for faster, reliable installs
    if [ -f "package-lock.json" ]; then
        npm ci --prefer-offline --no-audit --silent
    else
        npm install --no-audit --silent
    fi
    
    log_success "Dependencies installed successfully"
}

# Build the Angular application
build_app() {
    log_info "Building Angular application for production..."
    
    cd "$FRONTEND_DIR"
    
    # Determine if we should use ng or npx ng
    local ng_cmd="ng"
    if ! command -v ng &> /dev/null; then
        ng_cmd="npx ng"
        log_info "Using Angular CLI via npx"
    fi
    
    # Build for production (optimized for free tier)
    $ng_cmd build --configuration=production --optimization --build-optimizer
    
    if [ $? -ne 0 ]; then
        log_error "Angular build failed"
        exit 1
    fi
    
    # Verify dist folder exists
    if [ ! -d "dist" ]; then
        log_error "Build output directory 'dist' not found"
        exit 1
    fi
    
    # Check if build generated files
    local build_files
    build_files=$(find dist -name "*.js" -o -name "*.css" -o -name "*.html" | wc -l)
    
    if [ "$build_files" -eq 0 ]; then
        log_error "No build files found in dist directory"
        exit 1
    fi
    
    log_success "Angular application built successfully"
    log_info "Generated $build_files files"
}

# Setup Firebase configuration
setup_firebase() {
    log_info "Setting up Firebase configuration..."
    
    cd "$ROOT_DIR"
    
    # Check if firebase.json exists
    if [ ! -f "firebase.json" ]; then
        log_warning "firebase.json not found. Creating basic configuration..."
        cat > firebase.json << EOF
{
  "hosting": {
    "public": "frontend/dist",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "/ngsw-worker.js",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "no-cache"
          }
        ]
      },
      {
        "source": "**/*.@(js|css)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "max-age=3600"
          }
        ]
      }
    ]
  },
  "firestore": {
    "rules": "firestore.rules",
    "indexes": "firestore.indexes.json"
  }
}
EOF
        log_info "Basic firebase.json created"
    fi
    
    # Set Firebase project
    firebase use "$FIREBASE_PROJECT" --non-interactive
    
    log_success "Firebase configuration completed"
}

# Deploy to Firebase Hosting
deploy() {
    log_info "Deploying to Firebase Hosting..."
    
    cd "$ROOT_DIR"
    
    # Deploy only hosting
    firebase deploy --only hosting --project "$FIREBASE_PROJECT" --non-interactive
    
    if [ $? -ne 0 ]; then
        log_error "Firebase deployment failed"
        exit 1
    fi
    
    log_success "Deployment to Firebase Hosting completed"
}

# Validate deployment
validate_deployment() {
    log_info "Validating deployment..."
    
    # Get hosting URL
    local hosting_url
    hosting_url=$(firebase hosting:sites:list --project "$FIREBASE_PROJECT" --json | jq -r '.[0].defaultUrl' 2>/dev/null)
    
    if [ -z "$hosting_url" ] || [ "$hosting_url" = "null" ]; then
        # Fallback to project URL format
        hosting_url="https://$FIREBASE_PROJECT.web.app"
    fi
    
    log_info "Hosting URL: $hosting_url"
    
    # Wait for deployment to propagate
    log_info "Waiting for deployment to propagate..."
    sleep 15
    
    # Test main page
    log_info "Testing main page accessibility..."
    if timeout 30 curl -s -f "$hosting_url" > /dev/null; then
        log_success "Main page accessible ✓"
    else
        log_warning "Main page test failed, but deployment may still be successful"
        log_info "Sometimes it takes a few minutes for changes to propagate globally"
    fi
    
    # Check if service worker is available (PWA)
    log_info "Checking PWA service worker..."
    if timeout 30 curl -s -f "$hosting_url/ngsw-worker.js" > /dev/null; then
        log_success "Service worker accessible ✓"
    else
        log_info "Service worker not found (this is fine if PWA is not enabled)"
    fi
    
    log_success "Deployment validation completed"
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Financial Nomad Frontend - Firebase Hosting Deployment${NC}"
    echo "Firebase Project: $FIREBASE_PROJECT"
    echo ""
    
    validate_prerequisites
    install_dependencies
    build_app
    setup_firebase
    deploy
    validate_deployment
    
    echo ""
    log_success "🎉 Frontend deployment successful!"
    
    # Get final hosting URL
    local hosting_url
    hosting_url=$(firebase hosting:sites:list --project "$FIREBASE_PROJECT" --json 2>/dev/null | jq -r '.[0].defaultUrl' 2>/dev/null)
    
    if [ -z "$hosting_url" ] || [ "$hosting_url" = "null" ]; then
        hosting_url="https://$FIREBASE_PROJECT.web.app"
    fi
    
    echo ""
    log_info "📋 Deployment Information:"
    log_info "   URL: $hosting_url"
    log_info "   Console: https://console.firebase.google.com/project/$FIREBASE_PROJECT/hosting"
    log_info "   Logs: firebase hosting:clone --project $FIREBASE_PROJECT"
    echo ""
}

# Help function
show_help() {
    cat << EOF
Financial Nomad Frontend - Firebase Hosting Deployment Script

Usage: $0 [OPTIONS]

Environment Variables:
    PROJECT_ID       Google Cloud Project ID / Firebase Project ID
    FIREBASE_PROJECT Firebase Project ID (defaults to PROJECT_ID)

Examples:
    PROJECT_ID=my-project $0
    FIREBASE_PROJECT=my-firebase-project $0

Prerequisites:
    - Node.js 18+ and npm installed
    - Firebase CLI installed and authenticated
    - Frontend code in ../frontend/ directory
    - Valid Angular project with package.json and angular.json

The script will:
    1. Validate prerequisites and dependencies
    2. Install npm dependencies (clean install, optimized)
    3. Build Angular app for production (free tier optimized)
    4. Setup Firebase hosting configuration (free tier limits)
    5. Deploy to Firebase Hosting (free tier: 10GB storage, 360MB/day transfer)
    6. Validate deployment

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