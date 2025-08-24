#!/bin/bash

# Quick deployment script for Financial Nomad API
# Usage: ./scripts/quick-deploy.sh [environment]
# Environment: staging (default) or production

set -euo pipefail

# Configuration
ENVIRONMENT="${1:-staging}"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-financial-nomad-dev}"
SERVICE_NAME="financial-nomad-api"

# Set region and other configs based on environment
if [[ "${ENVIRONMENT}" == "production" ]]; then
    REGION="us-central1"
    MIN_INSTANCES=1
    MAX_INSTANCES=100
    MEMORY="2Gi"
    CPU="1000m"
    ALLOW_UNAUTH="false"
else
    REGION="us-central1"
    MIN_INSTANCES=0
    MAX_INSTANCES=10
    MEMORY="1Gi"
    CPU="500m"
    ALLOW_UNAUTH="true"
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Quick Deploy - Financial Nomad API${NC}"
echo -e "Environment: ${ENVIRONMENT}"
echo -e "Project: ${PROJECT_ID}"
echo -e "Region: ${REGION}"
echo ""

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Not authenticated with gcloud${NC}"
    echo "Run: gcloud auth login"
    exit 1
fi

# Set project
gcloud config set project "${PROJECT_ID}"

echo -e "${BLUE}📦 Building and deploying...${NC}"

# Deploy using gcloud run deploy with source
gcloud run deploy "${SERVICE_NAME}" \
    --source . \
    --region="${REGION}" \
    --platform=managed \
    --memory="${MEMORY}" \
    --cpu="${CPU}" \
    --timeout=300 \
    --concurrency=80 \
    --min-instances="${MIN_INSTANCES}" \
    --max-instances="${MAX_INSTANCES}" \
    --port=8080 \
    --set-env-vars="ENVIRONMENT=${ENVIRONMENT},GOOGLE_CLOUD_PROJECT=${PROJECT_ID},FIRESTORE_PROJECT_ID=${PROJECT_ID}" \
    --execution-environment=gen2 \
    --cpu-throttling \
    --session-affinity \
    --quiet

# Configure authentication
if [[ "${ALLOW_UNAUTH}" == "true" ]]; then
    echo -e "${BLUE}🔓 Allowing unauthenticated access...${NC}"
    gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --region="${REGION}" \
        --quiet
fi

# Get service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --format="value(status.url)")

echo ""
echo -e "${GREEN}✅ Deployment completed!${NC}"
echo -e "🌐 Service URL: ${SERVICE_URL}"
echo -e "🏥 Health Check: ${SERVICE_URL}/api/v1/health"
echo -e "📖 API Docs: ${SERVICE_URL}/docs"

# Test health endpoint
echo -e "${BLUE}🔍 Testing health endpoint...${NC}"
if curl -sS --max-time 10 "${SERVICE_URL}/api/v1/health" >/dev/null; then
    echo -e "${GREEN}✅ Service is healthy!${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Deployment successful!${NC}"