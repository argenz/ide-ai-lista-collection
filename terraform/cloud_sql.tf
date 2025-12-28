# Cloud SQL PostgreSQL instance
resource "google_sql_database_instance" "ideailista_db" {
  name             = "ideailista-collector-db"
  database_version = "POSTGRES_15"
  region           = var.region
  project          = var.project_id

  settings {
    tier              = var.db_instance_tier
    availability_type = "ZONAL"
    disk_size         = var.db_disk_size
    disk_type         = "PD_SSD"
    disk_autoresize   = true

    # Automated backups
    backup_configuration {
      enabled    = true
      start_time = "02:00"
      location   = var.region

      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    # IP configuration - private IP only for security
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
      require_ssl     = false # Set to true in production

      # No authorized networks needed with private IP
    }

    # Insights configuration for monitoring
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }

    # Maintenance window
    maintenance_window {
      day          = 7 # Sunday
      hour         = 3 # 3 AM UTC
      update_track = "stable"
    }
  }

  # Prevent accidental deletion
  deletion_protection = true

  depends_on = [
    google_project_service.required_apis,
    google_service_networking_connection.private_vpc_connection
  ]
}

# Create database
resource "google_sql_database" "database" {
  name     = "ideailista-db"
  instance = google_sql_database_instance.ideailista_db.name
  project  = var.project_id
}

# Create database user
resource "google_sql_user" "appuser" {
  name     = "appuser"
  instance = google_sql_database_instance.ideailista_db.name
  password = var.db_password
  project  = var.project_id
}
