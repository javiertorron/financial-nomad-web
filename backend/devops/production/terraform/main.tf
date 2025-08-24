# Terraform configuration for Financial Nomad API infrastructure
# Deploys to Google Cloud Platform using free tier resources

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Variables
variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The Google Cloud region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The Google Cloud zone"
  type        = string
  default     = "us-central1-a"
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
  default     = "financial-nomad-api"
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "containerregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com"
  ])
  
  service = each.key
  project = var.project_id
  
  disable_dependent_services = true
  disable_on_destroy        = false
}

# Create Firestore database
resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  
  depends_on = [google_project_service.apis]
}

# Service Account for Cloud Run
resource "google_service_account" "api_service_account" {
  account_id   = "financial-nomad-api"
  display_name = "Financial Nomad API Service Account"
  description  = "Service account for Financial Nomad API on Cloud Run"
  project      = var.project_id
  
  depends_on = [google_project_service.apis]
}

# IAM bindings for the service account
resource "google_project_iam_member" "api_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.api_service_account.email}"
}

resource "google_project_iam_member" "api_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api_service_account.email}"
}

# Secrets for application configuration
resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "jwt-secret"
  project   = var.project_id
  
  replication {
    automatic = true
  }
  
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "google_client_secret" {
  secret_id = "google-client-secret"
  project   = var.project_id
  
  replication {
    automatic = true
  }
  
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "asana_client_secret" {
  secret_id = "asana-client-secret"
  project   = var.project_id
  
  replication {
    automatic = true
  }
  
  depends_on = [google_project_service.apis]
}

# Create initial secret versions with placeholder values
resource "google_secret_manager_secret_version" "jwt_secret_version" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = "CHANGE_ME_JWT_SECRET_${random_id.jwt_suffix.hex}"
}

resource "google_secret_manager_secret_version" "google_client_secret_version" {
  secret      = google_secret_manager_secret.google_client_secret.id
  secret_data = "CHANGE_ME_GOOGLE_SECRET_${random_id.google_suffix.hex}"
}

resource "google_secret_manager_secret_version" "asana_client_secret_version" {
  secret      = google_secret_manager_secret.asana_client_secret.id
  secret_data = "CHANGE_ME_ASANA_SECRET_${random_id.asana_suffix.hex}"
}

# Random IDs for unique placeholder values
resource "random_id" "jwt_suffix" {
  byte_length = 8
}

resource "random_id" "google_suffix" {
  byte_length = 8
}

resource "random_id" "asana_suffix" {
  byte_length = 8
}

# Cloud Build trigger (optional - can be created manually)
resource "google_cloudbuild_trigger" "api_deploy_trigger" {
  project     = var.project_id
  name        = "financial-nomad-api-deploy"
  description = "Trigger for Financial Nomad API deployment"
  
  github {
    owner = "your-github-username"  # Replace with actual GitHub username
    name  = "financial-nomad"       # Replace with actual repository name
    
    push {
      branch = "^main$"
    }
  }
  
  filename = "backend/devops/production/cloudbuild.yaml"
  
  substitutions = {
    _REGION = var.region
  }
  
  depends_on = [google_project_service.apis]
}

# Outputs
output "project_id" {
  description = "The Google Cloud Project ID"
  value       = var.project_id
}

output "region" {
  description = "The Google Cloud region"
  value       = var.region
}

output "service_account_email" {
  description = "The service account email for the API"
  value       = google_service_account.api_service_account.email
}

output "firestore_database" {
  description = "The Firestore database name"
  value       = google_firestore_database.database.name
}

output "secrets" {
  description = "Created secrets that need to be updated with actual values"
  value = {
    jwt_secret            = google_secret_manager_secret.jwt_secret.name
    google_client_secret  = google_secret_manager_secret.google_client_secret.name
    asana_client_secret   = google_secret_manager_secret.asana_client_secret.name
  }
}

output "next_steps" {
  description = "Instructions for completing the setup"
  value = <<-EOT
    Infrastructure created successfully! Next steps:
    
    1. Update secrets with actual values:
       - gcloud secrets versions add jwt-secret --data-file=path/to/jwt-secret
       - gcloud secrets versions add google-client-secret --data-file=path/to/google-secret
       - gcloud secrets versions add asana-client-secret --data-file=path/to/asana-secret
    
    2. Deploy the application:
       - Run: ./devops/production/deploy.sh
       
    3. Configure custom domain (optional):
       - Set up Cloud Run domain mapping
       
    4. Set up monitoring and alerting:
       - Configure Cloud Monitoring alerts
       - Set up log-based metrics
  EOT
}