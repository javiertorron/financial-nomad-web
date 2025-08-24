#!/bin/bash

# Setup monitoring and alerting for Financial Nomad API
# Creates alert policies, uptime checks, and log-based metrics

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-}"
API_DOMAIN="${API_DOMAIN:-}"
NOTIFICATION_EMAIL="${NOTIFICATION_EMAIL:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
    
    # Check API domain
    if [ -z "$API_DOMAIN" ]; then
        log_error "API_DOMAIN not set. Please provide the domain of your deployed API"
        log_info "Example: API_DOMAIN=your-service-url.run.app"
        exit 1
    fi
    
    # Check notification email
    if [ -z "$NOTIFICATION_EMAIL" ]; then
        log_warning "NOTIFICATION_EMAIL not set. Alerts will be created without notification channels"
    fi
    
    log_success "Prerequisites validated. Project: $PROJECT_ID, Domain: $API_DOMAIN"
}

# Enable monitoring API
enable_monitoring_api() {
    log_info "Enabling monitoring API..."
    
    gcloud services enable \
        monitoring.googleapis.com \
        logging.googleapis.com \
        --project="$PROJECT_ID"
    
    log_success "Monitoring API enabled"
}

# Create notification channel
create_notification_channel() {
    if [ -z "$NOTIFICATION_EMAIL" ]; then
        log_warning "Skipping notification channel creation (no email provided)"
        return 0
    fi
    
    log_info "Creating notification channel for $NOTIFICATION_EMAIL..."
    
    # Check if notification channel already exists
    local channel_id
    channel_id=$(gcloud alpha monitoring channels list \
        --filter="displayName:'Financial Nomad API Alerts' AND type:'email'" \
        --format="value(name)" \
        --project="$PROJECT_ID" || echo "")
    
    if [ -n "$channel_id" ]; then
        log_info "Notification channel already exists: $channel_id"
        echo "$channel_id"
        return 0
    fi
    
    # Create notification channel
    cat > /tmp/notification-channel.yaml << EOF
type: email
displayName: "Financial Nomad API Alerts"
description: "Email notifications for Financial Nomad API alerts"
labels:
  email_address: "$NOTIFICATION_EMAIL"
enabled: true
EOF
    
    channel_id=$(gcloud alpha monitoring channels create \
        --channel-content-from-file=/tmp/notification-channel.yaml \
        --project="$PROJECT_ID" \
        --format="value(name)")
    
    rm /tmp/notification-channel.yaml
    
    log_success "Notification channel created: $channel_id"
    echo "$channel_id"
}

# Create uptime check
create_uptime_check() {
    log_info "Creating uptime check for $API_DOMAIN..."
    
    # Check if uptime check already exists
    local check_id
    check_id=$(gcloud monitoring uptime list \
        --filter="displayName:'Financial Nomad API Health Check'" \
        --format="value(name)" \
        --project="$PROJECT_ID" || echo "")
    
    if [ -n "$check_id" ]; then
        log_info "Uptime check already exists: $check_id"
        return 0
    fi
    
    # Create uptime check configuration
    cat > /tmp/uptime-check.yaml << EOF
displayName: "Financial Nomad API Health Check"
monitoredResource:
  type: "uptime_url"
  labels:
    project_id: "$PROJECT_ID"
    host: "$API_DOMAIN"
httpCheck:
  path: "/api/v1/health"
  port: 443
  useSsl: true
  validateSsl: true
period: "300s"
timeout: "10s"
checkerType: STATIC_IP_CHECKERS
selectedRegions:
  - USA
  - EUROPE
  - ASIA_PACIFIC
EOF
    
    check_id=$(gcloud monitoring uptime create \
        --uptime-check-from-file=/tmp/uptime-check.yaml \
        --project="$PROJECT_ID" \
        --format="value(name)")
    
    rm /tmp/uptime-check.yaml
    
    log_success "Uptime check created: $check_id"
}

# Create log-based metrics
create_log_metrics() {
    log_info "Creating log-based metrics..."
    
    # Error count metric
    log_info "Creating error count metric..."
    gcloud logging metrics create financial_nomad_api_errors \
        --description="Count of API errors by status code" \
        --log-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="financial-nomad-api" AND httpRequest.status>=400' \
        --project="$PROJECT_ID" || log_warning "Error metric may already exist"
    
    # Authentication failures metric
    log_info "Creating authentication failures metric..."
    gcloud logging metrics create financial_nomad_api_auth_failures \
        --description="Count of authentication failures" \
        --log-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="financial-nomad-api" AND httpRequest.status=401' \
        --project="$PROJECT_ID" || log_warning "Auth failures metric may already exist"
    
    log_success "Log-based metrics created"
}

# Create alert policies
create_alert_policies() {
    local notification_channel="$1"
    
    log_info "Creating alert policies..."
    
    # High error rate alert
    log_info "Creating high error rate alert..."
    cat > /tmp/error-rate-alert.yaml << EOF
displayName: "Financial Nomad API - High Error Rate"
documentation:
  content: "Alert when API error rate exceeds 5% over 5 minutes"
  mimeType: "text/markdown"
conditions:
  - displayName: "Error rate > 5%"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND resource.labels.service_name="financial-nomad-api" AND httpRequest.status>=400'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.05
      duration: "300s"
      aggregations:
        - alignmentPeriod: "300s"
          perSeriesAligner: ALIGN_RATE
          crossSeriesReducer: REDUCE_MEAN
          groupByFields:
            - "resource.label.service_name"
enabled: true
EOF
    
    if [ -n "$notification_channel" ]; then
        echo "notificationChannels: ['$notification_channel']" >> /tmp/error-rate-alert.yaml
    fi
    
    gcloud alpha monitoring policies create \
        --policy-from-file=/tmp/error-rate-alert.yaml \
        --project="$PROJECT_ID" || log_warning "Error rate alert may already exist"
    
    rm /tmp/error-rate-alert.yaml
    
    # Service down alert (based on uptime check)
    log_info "Creating service down alert..."
    cat > /tmp/service-down-alert.yaml << EOF
displayName: "Financial Nomad API - Service Down"
documentation:
  content: "Alert when API health checks fail"
  mimeType: "text/markdown"
conditions:
  - displayName: "Health check failures"
    conditionThreshold:
      filter: 'resource.type="uptime_url" AND resource.labels.host="$API_DOMAIN"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0
      duration: "60s"
      aggregations:
        - alignmentPeriod: "60s"
          perSeriesAligner: ALIGN_COUNT_FALSE
          crossSeriesReducer: REDUCE_COUNT_FALSE
enabled: true
EOF
    
    if [ -n "$notification_channel" ]; then
        echo "notificationChannels: ['$notification_channel']" >> /tmp/service-down-alert.yaml
    fi
    
    gcloud alpha monitoring policies create \
        --policy-from-file=/tmp/service-down-alert.yaml \
        --project="$PROJECT_ID" || log_warning "Service down alert may already exist"
    
    rm /tmp/service-down-alert.yaml
    
    log_success "Alert policies created"
}

# Main execution
main() {
    echo -e "${BLUE}🔔 Financial Nomad API - Monitoring Setup${NC}"
    echo "Project: $PROJECT_ID"
    echo "API Domain: $API_DOMAIN"
    echo "Notification Email: ${NOTIFICATION_EMAIL:-'Not provided'}"
    echo ""
    
    validate_prerequisites
    enable_monitoring_api
    
    local notification_channel=""
    notification_channel=$(create_notification_channel)
    
    create_uptime_check
    create_log_metrics
    create_alert_policies "$notification_channel"
    
    echo ""
    log_success "🎉 Monitoring setup completed!"
    log_info "Next steps:"
    log_info "1. Visit Google Cloud Console > Monitoring to view dashboards"
    log_info "2. Test alerts by temporarily stopping your service"
    log_info "3. Customize thresholds as needed based on your usage patterns"
    log_info "4. Consider setting up additional metrics specific to your application"
}

# Help function
show_help() {
    cat << EOF
Financial Nomad API - Monitoring Setup Script

Usage: $0

Environment Variables (required):
    PROJECT_ID          Google Cloud Project ID
    API_DOMAIN          Domain of your deployed API (e.g., your-service.run.app)
    
Environment Variables (optional):
    NOTIFICATION_EMAIL  Email for alert notifications

Examples:
    PROJECT_ID=my-project API_DOMAIN=my-api.run.app $0
    PROJECT_ID=my-project API_DOMAIN=my-api.run.app NOTIFICATION_EMAIL=alerts@company.com $0

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