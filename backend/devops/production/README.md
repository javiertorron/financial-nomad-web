# Financial Nomad API - Production Deployment Guide

This directory contains all the necessary files and scripts for deploying the Financial Nomad API to Google Cloud Run in a production environment.

## 📁 Directory Structure

```
devops/production/
├── README.md                    # This guide
├── Dockerfile.production        # Production-optimized Docker image
├── cloudbuild.yaml             # Google Cloud Build configuration
├── deploy.sh                   # Main deployment script
├── setup-monitoring.sh         # Monitoring and alerting setup
├── monitoring.yaml             # Monitoring configuration definitions
└── terraform/                  # Infrastructure as Code
    ├── main.tf                 # Main Terraform configuration
    └── terraform.tfvars.example # Example variables file
```

## 🚀 Quick Start

### Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Docker** installed (for local testing)
4. **Terraform** installed (optional, for infrastructure setup)

### Option 1: Automated Deployment (Recommended)

1. **Set your project ID**:
   ```bash
   export PROJECT_ID="your-gcp-project-id"
   ```

2. **Run the deployment script**:
   ```bash
   ./devops/production/deploy.sh
   ```

3. **Set up monitoring** (optional but recommended):
   ```bash
   export API_DOMAIN="your-service-url.run.app"  # From deployment output
   export NOTIFICATION_EMAIL="your-email@domain.com"
   ./devops/production/setup-monitoring.sh
   ```

### Option 2: Infrastructure as Code (Terraform)

1. **Initialize Terraform**:
   ```bash
   cd devops/production/terraform
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   terraform init
   ```

2. **Plan and apply infrastructure**:
   ```bash
   terraform plan
   terraform apply
   ```

3. **Deploy the application**:
   ```bash
   cd ../../..  # Back to backend root
   ./devops/production/deploy.sh
   ```

## 🔧 Configuration

### Environment Variables

The deployment uses the following environment variables:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `PROJECT_ID` | Google Cloud Project ID | Yes | - |
| `REGION` | Deployment region | No | us-central1 |
| `API_DOMAIN` | Your API domain (for monitoring) | No | - |
| `NOTIFICATION_EMAIL` | Alert email address | No | - |

### Secrets Management

The application requires these secrets in Google Secret Manager:

- `jwt-secret`: JWT signing key
- `google-client-secret`: Google OAuth client secret
- `asana-client-secret`: Asana API client secret

**Update secrets after deployment**:
```bash
# Generate a secure JWT secret
openssl rand -hex 32 | gcloud secrets versions add jwt-secret --data-file=-

# Add your Google OAuth secret
echo "your-google-client-secret" | gcloud secrets versions add google-client-secret --data-file=-

# Add your Asana client secret
echo "your-asana-client-secret" | gcloud secrets versions add asana-client-secret --data-file=-
```

## 🏗️ Architecture

### Google Cloud Services Used

- **Cloud Run**: Serverless container hosting
- **Cloud Build**: CI/CD pipeline
- **Container Registry**: Docker image storage
- **Secret Manager**: Secure configuration storage
- **Firestore**: NoSQL database
- **Cloud Monitoring**: Observability and alerting
- **Cloud Logging**: Centralized logging

### Resource Limits (Free Tier Optimized)

- **Memory**: 512Mi (within free tier)
- **CPU**: 1 vCPU (within free tier)
- **Concurrency**: 80 requests per instance
- **Max Instances**: 10 (can be reduced for cost control)
- **Min Instances**: 0 (saves costs when not in use)

## 📊 Monitoring and Alerting

### Automated Monitoring Setup

The `setup-monitoring.sh` script creates:

- **Uptime checks**: Health endpoint monitoring
- **Alert policies**: Error rate, response time, service availability
- **Log-based metrics**: Custom application metrics
- **Notification channels**: Email alerts

### Manual Dashboard Creation

1. Visit [Google Cloud Console > Monitoring](https://console.cloud.google.com/monitoring)
2. Create custom dashboards using the metrics:
   - Request rate and volume
   - Error rates by status code
   - Response time percentiles
   - Memory and CPU utilization

## 🔒 Security Considerations

### Network Security
- HTTPS enforced for all traffic
- CORS properly configured
- Trusted host middleware enabled

### Authentication
- OAuth 2.0 with Google
- JWT tokens with secure signing
- Service account with minimal permissions

### Data Protection
- Secrets stored in Secret Manager
- Environment variables for non-sensitive config
- Database access through service accounts

## 🚀 Deployment Process

### Automated CI/CD

The Cloud Build configuration (`cloudbuild.yaml`) handles:

1. **Build**: Creates production Docker image
2. **Test**: Runs validation checks
3. **Deploy**: Updates Cloud Run service
4. **Validate**: Confirms deployment health

### Manual Deployment Steps

If you prefer manual deployment:

1. **Build image**:
   ```bash
   docker build -f devops/production/Dockerfile.production -t financial-nomad-api .
   ```

2. **Tag for GCR**:
   ```bash
   docker tag financial-nomad-api gcr.io/$PROJECT_ID/financial-nomad-api
   ```

3. **Push to registry**:
   ```bash
   docker push gcr.io/$PROJECT_ID/financial-nomad-api
   ```

4. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy financial-nomad-api \
     --image gcr.io/$PROJECT_ID/financial-nomad-api \
     --region us-central1 \
     --platform managed \
     --allow-unauthenticated
   ```

## 🔄 Maintenance and Updates

### Rolling Updates

Cloud Run automatically handles rolling updates with zero downtime:

1. New revision is created
2. Traffic is gradually shifted
3. Old revision is retired

### Database Migrations

For schema changes:
1. Test migrations in development
2. Deploy backward-compatible changes first
3. Update application code
4. Remove deprecated fields later

### Backup Strategy

- **Automatic**: Firestore automatic backups
- **Manual**: Export data via API endpoints
- **Disaster Recovery**: Cross-region replication available

## 📈 Scaling and Performance

### Auto-scaling Configuration

Cloud Run automatically scales based on:
- Request volume
- CPU and memory utilization
- Custom metrics (if configured)

### Performance Optimization

- **Caching**: Multi-level caching implemented
- **Connection pooling**: Database connections optimized
- **Compression**: Gzip enabled for responses
- **CDN**: Consider adding Cloud CDN for static assets

## 🐛 Troubleshooting

### Common Issues

1. **Deployment fails**: Check Cloud Build logs
2. **Service not accessible**: Verify IAM permissions
3. **High latency**: Check database queries and caching
4. **Memory issues**: Monitor usage and adjust limits

### Debugging Commands

```bash
# Check service status
gcloud run services describe financial-nomad-api --region=us-central1

# View logs
gcloud logs read "resource.type=cloud_run_revision" --limit=100

# Test endpoints
curl -f https://your-service-url.run.app/api/v1/health

# Check secrets
gcloud secrets versions list jwt-secret
```

### Log Analysis

Key log patterns to monitor:
- HTTP error status codes (4xx, 5xx)
- Slow queries (>2s response time)
- Authentication failures
- Memory pressure warnings

## 💰 Cost Management

### Free Tier Limits

Google Cloud Run free tier includes:
- 2 million requests per month
- 400,000 GB-seconds of compute
- 200,000 vCPU-seconds

### Cost Optimization Tips

1. **Set max instances**: Prevent runaway costs
2. **Use min instances sparingly**: Only for critical uptime
3. **Monitor metrics**: Track usage patterns
4. **Cleanup unused resources**: Remove old revisions

## 📞 Support and Resources

- **Documentation**: [Cloud Run Documentation](https://cloud.google.com/run/docs)
- **Pricing**: [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- **Support**: [Google Cloud Support](https://cloud.google.com/support)
- **Status**: [Google Cloud Status](https://status.cloud.google.com)

## 📝 Next Steps

After successful deployment:

1. **Configure custom domain** (optional)
2. **Set up CI/CD triggers** for automated deployments
3. **Configure backup schedules**
4. **Review and adjust monitoring thresholds**
5. **Document operational procedures**

---

For questions or issues, please refer to the project documentation or create an issue in the repository.