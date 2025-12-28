# GCS bucket for raw data storage
resource "google_storage_bucket" "data_bucket" {
  name     = "ideailista-${var.target_location_id}-${var.project_id}"
  location = var.bucket_location
  project  = var.project_id

  # Uniform bucket-level access for simpler IAM
  uniform_bucket_level_access = true

  # Lifecycle rules to manage storage costs
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age                   = 365 # Delete raw responses after 1 year
      matches_prefix        = ["raw_responses/"]
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age            = 90 # Move to nearline storage after 90 days
      matches_prefix = ["raw_responses/"]
    }
  }

  # Versioning for important data
  versioning {
    enabled = false # Can enable if needed for audit trail
  }

  # Labels for organization
  labels = {
    environment = "production"
    application = "ideailista-collector"
    managed_by  = "terraform"
  }

  depends_on = [google_project_service.required_apis]
}

# Create folder structure (via objects)
resource "google_storage_bucket_object" "raw_responses_folder" {
  name    = "raw_responses/.placeholder"
  content = "This folder stores raw API responses"
  bucket  = google_storage_bucket.data_bucket.name
}

resource "google_storage_bucket_object" "images_folder" {
  name    = "images/.placeholder"
  content = "This folder stores compressed property images"
  bucket  = google_storage_bucket.data_bucket.name
}
