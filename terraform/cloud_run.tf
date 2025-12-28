# Cloud Run Job for daily new listings collection
resource "google_cloud_run_v2_job" "daily_new_listings" {
  name     = "daily-new-listings"
  location = var.region
  project  = var.project_id

  template {
    template {
      service_account = google_service_account.cloud_run_sa.email

      timeout = "${var.daily_job_timeout}s"

      max_retries = 3

      containers {
        image = var.docker_image

        # Environment variables
        env {
          name  = "JOB_TYPE"
          value = "daily_new_listings"
        }

        env {
          name  = "TARGET_LOCATION_ID"
          value = var.target_location_id
        }

        env {
          name  = "TARGET_COUNTRY"
          value = var.target_country
        }

        env {
          name  = "GCS_BUCKET_NAME"
          value = google_storage_bucket.data_bucket.name
        }

        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }

        env {
          name  = "LOG_LEVEL"
          value = "INFO"
        }

        # Secrets from Secret Manager
        env {
          name = "IDEALISTA_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.api_key.secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "IDEALISTA_API_SECRET"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.api_secret.secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = "latest"
            }
          }
        }

        # Resource limits
        resources {
          limits = {
            cpu    = var.daily_job_cpu
            memory = var.daily_job_memory
          }
        }
      }

      # VPC Access for Cloud SQL connection
      vpc_access {
        connector = google_vpc_access_connector.connector.id
        egress    = "PRIVATE_RANGES_ONLY"
      }
    }
  }

  labels = {
    application = "ideailista-collector"
    job_type    = "daily-new-listings"
    managed_by  = "terraform"
  }

  depends_on = [
    google_project_service.required_apis,
    google_service_account.cloud_run_sa,
    google_vpc_access_connector.connector,
    google_secret_manager_secret_version.api_key,
    google_secret_manager_secret_version.api_secret,
    google_secret_manager_secret_version.database_url
  ]
}
