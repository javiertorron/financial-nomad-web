# Financial Nomad API - Deployment Guide

## Overview

This guide covers the complete deployment process for the Financial Nomad API to Google Cloud Run. The API is designed to run in a serverless environment with auto-scaling capabilities.

## Prerequisites

### Required Tools

- **Google Cloud SDK** (gcloud CLI)
- **Docker** (for local building)
- **Git** (for version control)

### Required Permissions

Your Google Cloud account needs the following IAM roles:

- `Cloud Run Admin`
- `Service Account Admin`
- `Container Registry Admin`
- `Cloud Build Editor`
- `Project IAM Admin`

### Environment Setup

1. **Install Google Cloud SDK**:
   ```bash
   # macOS
   brew install --cask google-cloud-sdk
   
   # Ubuntu/Debian
   curl https://sdk.cloud.google.com | bash
   ```

2. **Authenticate with Google Cloud**:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Enable Required APIs**:
   ```bash
   gcloud services enable \
     cloudbuild.googleapis.com \
     run.googleapis.com \
     containerregistry.googleapis.com \
     firestore.googleapis.com \
     secretmanager.googleapis.com
   ```

## Deployment Methods

### Method 1: Quick Deploy (Recommended for Development)

The quickest way to deploy for testing and development:

```bash
# Deploy to staging
./scripts/quick-deploy.sh staging

# Deploy to production
./scripts/quick-deploy.sh production
```

**Features:**
- Uses Cloud Build for containerization
- Automatic scaling configuration
- Environment-specific settings
- Health check validation

### Method 2: Full Production Deploy

For production deployments with full control:

```bash
# Set environment variables
export GOOGLE_CLOUD_PROJECT="your-project-id"
export DEPLOY_REGION="us-central1"
export CUSTOM_DOMAIN="api.your-domain.com"

# Run full deployment
./scripts/deploy-production.sh
```

**Features:**
- Custom Docker image building
- Service account management
- Domain mapping
- Security scanning
- Comprehensive validation

### Method 3: Manual Deployment

For maximum control over the deployment process:

1. **Build and Push Image**:
   ```bash
   # Build production image
   docker build -f Dockerfile.production -t gcr.io/PROJECT_ID/financial-nomad-api .
   
   # Push to Container Registry
   docker push gcr.io/PROJECT_ID/financial-nomad-api
   ```

2. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy financial-nomad-api \
     --image=gcr.io/PROJECT_ID/financial-nomad-api \
     --region=us-central1 \
     --memory=2Gi \
     --cpu=1 \
     --max-instances=100 \
     --port=8080
   ```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Deployment environment | `production` | Yes |
| `DEBUG` | Enable debug mode | `false` | No |
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID | - | Yes |
| `FIRESTORE_PROJECT_ID` | Firestore Project ID | Same as GCP Project | No |
| `JWT_SECRET_KEY` | JWT signing secret | - | Yes |
| `GOOGLE_CLIENT_ID` | OAuth client ID | - | Yes |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret | - | Yes |
| `CORS_ORIGINS` | Allowed CORS origins | - | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |

### Service Account

The API requires a service account with the following roles:

- `roles/datastore.user` - For Firestore access
- `roles/secretmanager.secretAccessor` - For accessing secrets
- `roles/monitoring.metricWriter` - For metrics
- `roles/logging.logWriter` - For logging

### Resource Configuration

#### Staging Environment

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "512Mi"
  limits:
    cpu: "500m"
    memory: "1Gi"

scaling:
  minInstances: 0
  maxInstances: 10
  concurrency: 80
```

#### Production Environment

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "1000m"
    memory: "2Gi"

scaling:
  minInstances: 1
  maxInstances: 100
  concurrency: 80
```

## Health Checks

The API implements comprehensive health checks:

### Endpoints

- **`/api/v1/health`** - Basic health check
- **`/api/v1/health/detailed`** - Detailed health with dependencies
- **`/api/v1/ready`** - Readiness probe
- **`/api/v1/live`** - Liveness probe

### Cloud Run Configuration

```yaml
startupProbe:
  httpGet:
    path: /api/v1/health
    port: 8080
  initialDelaySeconds: 10
  timeoutSeconds: 5
  periodSeconds: 10
  failureThreshold: 3

livenessProbe:
  httpGet:
    path: /api/v1/live
    port: 8080
  initialDelaySeconds: 30
  timeoutSeconds: 5
  periodSeconds: 30
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/v1/ready
    port: 8080
  initialDelaySeconds: 5
  timeoutSeconds: 5
  periodSeconds: 10
```

## Domain Configuration

### Custom Domain Setup

1. **Map Domain to Service**:
   ```bash
   gcloud run domain-mappings create \
     --service=financial-nomad-api \
     --domain=api.your-domain.com \
     --region=us-central1
   ```

2. **Configure DNS**:
   Add a CNAME record pointing to `ghs.googlehosted.com`

3. **SSL Certificate**:
   Cloud Run automatically provisions SSL certificates for mapped domains.

## Monitoring and Logging

### Metrics

The API exports Prometheus metrics available at `/api/v1/monitoring/metrics`:

- Request count and duration
- Database operation metrics
- Cache hit/miss rates
- Error rates by endpoint

### Logging

Structured JSON logging is configured for Cloud Logging:

```python
{
  "timestamp": "2024-01-15T10:30:00Z",
  "severity": "INFO",
  "message": "Request processed",
  "request_id": "req_123456789",
  "user_id": "user_987654321",
  "endpoint": "/api/v1/accounts",
  "duration_ms": 45.2
}
```

### Alerts

Recommended Cloud Monitoring alerts:

- **Error Rate > 5%**
- **Response Time > 2s (95th percentile)**
- **Memory Usage > 80%**
- **CPU Usage > 80%**

## Security

### Container Security

- **Non-root user**: Container runs as user 1000
- **Read-only root filesystem**: Where possible
- **Security scanning**: Integrated with Container Analysis
- **Minimal base image**: Uses `python:3.11-slim`

### Network Security

- **VPC Connector**: For private resource access
- **IAM**: Service account with minimal permissions
- **HTTPS Only**: All traffic encrypted in transit

### Secrets Management

Use Google Secret Manager for sensitive data:

```bash
# Store JWT secret
gcloud secrets create jwt-secret-key --data-file=jwt.key

# Grant access to service account
gcloud secrets add-iam-policy-binding jwt-secret-key \
  --member="serviceAccount:financial-nomad-service@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Troubleshooting

### Common Issues

#### 1. Build Failures

**Symptom**: Docker build fails with dependency errors

**Solution**:
```bash
# Clear Docker cache
docker system prune -af

# Rebuild with no cache
docker build --no-cache -f Dockerfile.production .
```

#### 2. Service Unavailable (503)

**Symptom**: Service returns 503 errors

**Debug Steps**:
```bash
# Check service logs
gcloud logs read "resource.type=cloud_run_revision" --limit=50

# Check service status
gcloud run services describe financial-nomad-api --region=us-central1

# Test health endpoint
curl https://your-service-url/api/v1/health
```

#### 3. Authentication Errors

**Symptom**: 401/403 errors

**Debug Steps**:
```bash
# Check service account permissions
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:financial-nomad-service@PROJECT_ID.iam.gserviceaccount.com"

# Test Firestore access
gcloud firestore databases list --project=PROJECT_ID
```

#### 4. Cold Start Issues

**Symptom**: High latency on first request

**Solutions**:
- Set `minInstances: 1` for production
- Enable startup CPU boost
- Optimize application startup time

### Log Analysis

```bash
# View recent logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=financial-nomad-api" --limit=100

# Filter by severity
gcloud logs read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=50

# Real-time log streaming
gcloud logs tail "resource.type=cloud_run_revision" --follow
```

## Rollback Procedures

### Quick Rollback

```bash
# List recent revisions
gcloud run revisions list --service=financial-nomad-api --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic financial-nomad-api \
  --to-revisions=REVISION_NAME=100 \
  --region=us-central1
```

### Staged Rollback

```bash
# Route 50% traffic to previous version
gcloud run services update-traffic financial-nomad-api \
  --to-revisions=NEW_REVISION=50,OLD_REVISION=50 \
  --region=us-central1

# Monitor metrics, then complete rollback
gcloud run services update-traffic financial-nomad-api \
  --to-revisions=OLD_REVISION=100 \
  --region=us-central1
```

## Performance Optimization

### Image Optimization

- Use multi-stage builds
- Minimize layer count
- Use `.dockerignore`
- Enable Docker BuildKit

### Service Optimization

- Set appropriate CPU/memory limits
- Configure concurrency based on workload
- Use regional persistent disks for data
- Enable CPU allocation only during request processing

### Cost Optimization

- Use minimum instances wisely
- Monitor unused resources
- Implement request timeout
- Use appropriate machine types

## CI/CD Integration

The deployment scripts integrate with GitHub Actions:

```yaml
# Example workflow step
- name: Deploy to Cloud Run
  run: |
    echo $GCLOUD_SERVICE_KEY | base64 --decode > gcloud-service-key.json
    gcloud auth activate-service-account --key-file gcloud-service-key.json
    gcloud config set project $GOOGLE_CLOUD_PROJECT
    ./scripts/quick-deploy.sh production
  env:
    GOOGLE_CLOUD_PROJECT: ${{ secrets.GOOGLE_CLOUD_PROJECT }}
    GCLOUD_SERVICE_KEY: ${{ secrets.GCLOUD_SERVICE_KEY }}
```

## Support

For deployment issues:

1. Check the logs first: `gcloud logs read`
2. Verify health endpoints
3. Review service configuration
4. Check IAM permissions
5. Contact platform team if issues persist

---

**Last Updated**: January 2024  
**Version**: 1.0.0