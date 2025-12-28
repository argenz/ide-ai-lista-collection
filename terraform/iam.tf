# Service Account for Cloud Run jobs
resource "google_service_account" "cloud_run_sa" {
  account_id   = "ideailista-collector-sa"
  display_name = "ideAIlista Collector Service Account"
  description  = "Service account for Cloud Run jobs to access Cloud SQL, GCS, and Secret Manager"
  project      = var.project_id

  depends_on = [google_project_service.required_apis]
}

# IAM: Cloud SQL Client role
resource "google_project_iam_member" "cloud_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# IAM: Storage Object Admin role for GCS
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# IAM: Secret Manager Secret Accessor role
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# IAM: Logs Writer role for Cloud Logging
resource "google_project_iam_member" "logs_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# IAM: Metric Writer role for Cloud Monitoring
resource "google_project_iam_member" "metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Service Account for Cloud Scheduler (to invoke Cloud Run jobs)
resource "google_service_account" "cloud_scheduler_sa" {
  account_id   = "ideailista-scheduler-sa"
  display_name = "ideAIlista Scheduler Service Account"
  description  = "Service account for Cloud Scheduler to trigger Cloud Run jobs"
  project      = var.project_id

  depends_on = [google_project_service.required_apis]
}

# IAM: Cloud Run Invoker role for Scheduler
resource "google_project_iam_member" "scheduler_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.cloud_scheduler_sa.email}"
}
