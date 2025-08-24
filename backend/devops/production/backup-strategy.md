# Financial Nomad API - Backup and Disaster Recovery Strategy

## 📋 Overview

This document outlines the backup and disaster recovery strategy for the Financial Nomad API running on Google Cloud Platform. The strategy is designed to ensure data integrity, minimize downtime, and enable quick recovery from various failure scenarios.

## 🎯 Recovery Objectives

- **Recovery Time Objective (RTO)**: 1 hour for critical services
- **Recovery Point Objective (RPO)**: 15 minutes maximum data loss
- **Availability Target**: 99.9% uptime (8.77 hours downtime per year)

## 📊 Data Classification

### Critical Data (Tier 1)
- **User accounts and authentication data**
- **Financial transactions and account balances**
- **Budget configurations and goals**
- **Audit logs and compliance data**

### Important Data (Tier 2)
- **User preferences and settings**
- **Asana integration configurations**
- **Historical reports and analytics**
- **Application logs (recent)**

### Non-Critical Data (Tier 3)
- **Temporary cache data**
- **Old application logs (>30 days)**
- **System metrics (>90 days)**

## 🔧 Backup Components

### 1. Firestore Database Backup

#### Automatic Backups
```bash
# Enable automatic backups (Google Cloud Console or Terraform)
resource "google_firestore_backup_schedule" "daily_backup" {
  project = var.project_id
  database = "(default)"
  
  retention = "2592000s"  # 30 days
  
  daily_recurrence {
    hour = 2  # 2 AM UTC
    minute = 0
  }
}
```

#### Manual Backup Script
```bash
#!/bin/bash
# backup-firestore.sh

PROJECT_ID="your-project-id"
BACKUP_BUCKET="financial-nomad-backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Export Firestore data
gcloud firestore export \
  gs://${BACKUP_BUCKET}/firestore/${TIMESTAMP} \
  --project=${PROJECT_ID} \
  --async

echo "Backup initiated: gs://${BACKUP_BUCKET}/firestore/${TIMESTAMP}"
```

### 2. Application Configuration Backup

#### Secrets Backup
```bash
#!/bin/bash
# backup-secrets.sh

PROJECT_ID="your-project-id"
BACKUP_DIR="./backups/secrets/$(date +%Y%m%d)"

mkdir -p "$BACKUP_DIR"

# Export secret metadata (not the actual secret values)
gcloud secrets list \
  --project="$PROJECT_ID" \
  --format="table(name,created,updated)" \
  > "$BACKUP_DIR/secrets-list.txt"

# Document secret configurations
cat > "$BACKUP_DIR/secrets-config.yaml" << EOF
secrets:
  - name: jwt-secret
    description: JWT signing key
    rotation_schedule: quarterly
    
  - name: google-client-secret
    description: Google OAuth client secret
    rotation_schedule: annually
    
  - name: asana-client-secret
    description: Asana API client secret
    rotation_schedule: annually
EOF
```

### 3. Infrastructure as Code Backup

All infrastructure configurations are stored in version control:
- **Terraform configurations** → Git repository
- **Cloud Build configurations** → Git repository
- **Kubernetes manifests** (if applicable) → Git repository
- **Environment configurations** → Secure repository

### 4. Application Code Backup

- **Source code** → Git repository with multiple remotes
- **Dependencies** → Locked versions in requirements files
- **Container images** → Google Container Registry with retention policy

## 🚨 Disaster Recovery Procedures

### Scenario 1: Service Outage (RTO: 15 minutes)

1. **Detection**
   - Monitoring alerts trigger
   - Health checks fail
   - User reports

2. **Assessment**
   ```bash
   # Check service status
   gcloud run services describe financial-nomad-api --region=us-central1
   
   # Check logs
   gcloud logs read "resource.type=cloud_run_revision" --limit=100
   ```

3. **Recovery Actions**
   ```bash
   # Redeploy service
   gcloud run deploy financial-nomad-api \
     --image=gcr.io/$PROJECT_ID/financial-nomad-api:latest \
     --region=us-central1
   
   # Scale up if needed
   gcloud run services update financial-nomad-api \
     --max-instances=20 \
     --region=us-central1
   ```

### Scenario 2: Data Corruption (RTO: 1 hour)

1. **Immediate Actions**
   ```bash
   # Stop write operations
   gcloud run services update financial-nomad-api \
     --set-env-vars="MAINTENANCE_MODE=true" \
     --region=us-central1
   ```

2. **Data Recovery**
   ```bash
   # List available backups
   gcloud firestore operations list --filter="type:EXPORT_DOCUMENTS"
   
   # Import from backup
   gcloud firestore import gs://financial-nomad-backups/firestore/20240115-020000
   ```

3. **Validation**
   ```bash
   # Run data integrity checks
   ./scripts/validate-data-integrity.sh
   
   # Test critical endpoints
   ./scripts/validate-deployment.sh
   ```

### Scenario 3: Regional Outage (RTO: 2 hours)

1. **Multi-Region Setup** (Future Enhancement)
   - Deploy to secondary region
   - Configure global load balancer
   - Implement database replication

2. **Current Workaround**
   ```bash
   # Deploy to different region
   gcloud run deploy financial-nomad-api \
     --image=gcr.io/$PROJECT_ID/financial-nomad-api:latest \
     --region=us-east1
   
   # Update DNS to point to new region
   # (Manual process - requires DNS provider access)
   ```

### Scenario 4: Complete Account Compromise (RTO: 4 hours)

1. **Immediate Security Actions**
   - Rotate all secrets immediately
   - Review audit logs
   - Block suspicious access

2. **Recovery Process**
   ```bash
   # Create new project
   gcloud projects create financial-nomad-recovery
   
   # Deploy from scratch using IaC
   cd terraform/
   terraform workspace new recovery
   terraform apply -var="project_id=financial-nomad-recovery"
   
   # Restore data from backups
   gcloud firestore import gs://financial-nomad-backups/firestore/latest
   ```

## 📅 Backup Schedule

| Backup Type | Frequency | Retention | Storage Location |
|-------------|-----------|-----------|------------------|
| Firestore Full | Daily 2:00 AM UTC | 30 days | Google Cloud Storage |
| Firestore Incremental | Every 6 hours | 7 days | Google Cloud Storage |
| Application Logs | Continuous | 30 days | Google Cloud Logging |
| Configuration | On change | Forever | Git Repository |
| Container Images | On deployment | 10 versions | Google Container Registry |
| Secrets Metadata | Weekly | 90 days | Secure Storage |

## 🧪 Testing and Validation

### Monthly DR Tests

```bash
#!/bin/bash
# dr-test.sh

# Test 1: Service Recovery
echo "Testing service recovery..."
gcloud run services update financial-nomad-api \
  --set-env-vars="SIMULATE_FAILURE=true" \
  --region=us-central1

sleep 60

gcloud run deploy financial-nomad-api \
  --image=gcr.io/$PROJECT_ID/financial-nomad-api:latest \
  --region=us-central1

# Test 2: Data Recovery (to test environment)
echo "Testing data recovery..."
gcloud firestore export gs://test-backups/firestore/$(date +%Y%m%d)

# Test 3: Monitoring Alerts
echo "Testing monitoring alerts..."
curl -X POST "https://api.financial-nomad.com/test/trigger-alert"

echo "DR test completed. Review results and update procedures as needed."
```

### Quarterly Full Recovery Test

1. **Create isolated test environment**
2. **Deploy application from scratch**
3. **Restore data from production backup**
4. **Validate all functionality**
5. **Document lessons learned**

## 📊 Monitoring and Alerting

### Critical Alerts
- **Backup failure**: Immediate notification
- **High error rate**: 5% over 5 minutes
- **Service unavailable**: 2 consecutive failed health checks
- **Data corruption detected**: Immediate notification

### Backup Monitoring
```bash
# Monitor backup success
gcloud logging read 'resource.type="firestore_database" AND jsonPayload.operation_type="EXPORT_DOCUMENTS"' --limit=10

# Check backup storage usage
gsutil du -s gs://financial-nomad-backups/
```

## 💰 Cost Optimization

### Storage Costs
- Use **Standard** storage for recent backups (30 days)
- Move to **Nearline** for medium-term (30-90 days)
- Archive to **Coldline** for long-term (>90 days)

### Automation Script
```bash
#!/bin/bash
# optimize-backup-costs.sh

BUCKET="financial-nomad-backups"

# Move backups older than 30 days to Nearline
gsutil -m lifecycle set lifecycle-nearline.json gs://$BUCKET/

# Move backups older than 90 days to Coldline  
gsutil -m lifecycle set lifecycle-coldline.json gs://$BUCKET/
```

## 🔐 Security Considerations

### Backup Encryption
- All backups encrypted at rest (Google-managed keys)
- Consider customer-managed encryption keys (CMEK) for sensitive data

### Access Control
```yaml
# backup-access-policy.yaml
bindings:
  - members:
    - user:admin@financial-nomad.com
    - serviceAccount:backup-service@project.iam.gserviceaccount.com
    role: roles/storage.objectAdmin
    condition:
      title: "Backup Access Only"
      expression: 'resource.name.startsWith("projects/_/buckets/financial-nomad-backups")'
```

### Audit Logging
```bash
# Enable audit logs for backup operations
gcloud logging sinks create backup-audit-sink \
  bigquery.googleapis.com/projects/$PROJECT_ID/datasets/audit_logs \
  --log-filter='resource.type="gcs_bucket" AND resource.labels.bucket_name="financial-nomad-backups"'
```

## 📋 Checklists

### Daily Backup Verification
- [ ] Check backup completion status
- [ ] Verify backup file integrity
- [ ] Monitor storage usage
- [ ] Review any error logs

### Weekly DR Review
- [ ] Test restore procedures (sample data)
- [ ] Review and update documentation
- [ ] Verify contact information for emergency response
- [ ] Check monitoring alert functionality

### Monthly Full Review
- [ ] Conduct full DR exercise
- [ ] Update RTO/RPO targets based on business needs
- [ ] Review and optimize costs
- [ ] Update emergency contact list
- [ ] Review and rotate secrets if needed

## 📞 Emergency Contacts

| Role | Primary Contact | Secondary Contact | 24/7 Available |
|------|----------------|-------------------|-----------------|
| System Administrator | admin@financial-nomad.com | backup-admin@financial-nomad.com | Yes |
| Database Administrator | dba@financial-nomad.com | - | No |
| Security Team | security@financial-nomad.com | - | Yes |
| Business Continuity | bc@financial-nomad.com | - | Yes |

## 📚 Additional Resources

- [Google Cloud Backup and Recovery Best Practices](https://cloud.google.com/architecture/backup-and-recovery-overview)
- [Firestore Backup Documentation](https://cloud.google.com/firestore/docs/manage-data)
- [Cloud Run Disaster Recovery](https://cloud.google.com/run/docs/deploying)

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-15  
**Next Review**: 2024-04-15