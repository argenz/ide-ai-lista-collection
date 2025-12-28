# Secret for Idealista API Key
resource "google_secret_manager_secret" "api_key" {
  secret_id = "idealista-api-key"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    application = "ideailista-collector"
    managed_by  = "terraform"
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "api_key" {
  secret      = google_secret_manager_secret.api_key.id
  secret_data = var.idealista_api_key
}

# Secret for Idealista API Secret
resource "google_secret_manager_secret" "api_secret" {
  secret_id = "idealista-api-secret"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    application = "ideailista-collector"
    managed_by  = "terraform"
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "api_secret" {
  secret      = google_secret_manager_secret.api_secret.id
  secret_data = var.idealista_api_secret
}

# Secret for Database URL
resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    application = "ideailista-collector"
    managed_by  = "terraform"
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret = google_secret_manager_secret.database_url.id
  # Connection string for Cloud SQL via private IP
  secret_data = "postgresql://appuser:${var.db_password}@${google_sql_database_instance.ideailista_db.private_ip_address}:5432/ideailista-db"

  depends_on = [google_sql_database_instance.ideailista_db]
}
