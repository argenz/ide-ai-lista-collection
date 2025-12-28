terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Optional: Use GCS backend for state management
  # Uncomment and configure after creating a state bucket
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "idealista-collector"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required Google Cloud APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "sqladmin.googleapis.com",           # Cloud SQL
    "storage.googleapis.com",            # Cloud Storage
    "secretmanager.googleapis.com",      # Secret Manager
    "run.googleapis.com",                # Cloud Run
    "cloudscheduler.googleapis.com",     # Cloud Scheduler
    "vpcaccess.googleapis.com",          # VPC Access
    "compute.googleapis.com",            # Compute (for VPC)
    "servicenetworking.googleapis.com",  # Service Networking (for Cloud SQL)
    "cloudresourcemanager.googleapis.com" # Resource Manager
  ])

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}
