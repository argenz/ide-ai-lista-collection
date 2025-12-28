output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL connection name for connecting via proxy"
  value       = google_sql_database_instance.ideailista_db.connection_name
}

output "cloud_sql_instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.ideailista_db.name
}

output "cloud_sql_private_ip" {
  description = "Cloud SQL private IP address"
  value       = google_sql_database_instance.ideailista_db.private_ip_address
}

output "gcs_bucket_name" {
  description = "GCS bucket name for raw data"
  value       = google_storage_bucket.data_bucket.name
}

output "gcs_bucket_url" {
  description = "GCS bucket URL"
  value       = google_storage_bucket.data_bucket.url
}

output "service_account_email" {
  description = "Service account email for Cloud Run jobs"
  value       = google_service_account.cloud_run_sa.email
}

output "cloud_run_job_name" {
  description = "Cloud Run job name"
  value       = google_cloud_run_v2_job.daily_new_listings.name
}

output "vpc_connector_name" {
  description = "VPC Access connector name"
  value       = google_vpc_access_connector.connector.name
}

output "database_url" {
  description = "Database connection string (use with Cloud SQL Proxy or private IP)"
  value       = "postgresql://appuser:${var.db_password}@${google_sql_database_instance.ideailista_db.private_ip_address}:5432/ideailista-db"
  sensitive   = true
}

output "next_steps" {
  description = "Next steps after Terraform apply"
  value = <<-EOT

  ========================================
  ideAIlista Collector Infrastructure Created!
  ========================================

  Next steps:

  1. Build and push Docker image:
     docker build -t gcr.io/${var.project_id}/ideailista-collector:latest .
     docker push gcr.io/${var.project_id}/ideailista-collector:latest

  2. Apply database schema using Cloud SQL Proxy:
     cloud-sql-proxy ${google_sql_database_instance.ideailista_db.connection_name} &
     psql "host=127.0.0.1 port=5432 dbname=ideailista-db user=appuser" < src/db/schema.sql

  3. Test the Cloud Run job manually:
     gcloud run jobs execute ${google_cloud_run_v2_job.daily_new_listings.name} --region=${var.region}

  4. View logs:
     gcloud run jobs logs ${google_cloud_run_v2_job.daily_new_listings.name} --region=${var.region}

  5. Monitor in Cloud Console:
     https://console.cloud.google.com/run/jobs/${google_cloud_run_v2_job.daily_new_listings.name}?project=${var.project_id}

  The daily job will run automatically at: ${var.daily_job_schedule} UTC

  EOT
}
