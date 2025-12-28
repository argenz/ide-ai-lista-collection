# Cloud Scheduler job to trigger daily new listings collection
resource "google_cloud_scheduler_job" "daily_trigger" {
  name             = "daily-new-listings-trigger"
  description      = "Triggers daily new listings collection at 2 AM UTC"
  schedule         = var.daily_job_schedule
  time_zone        = "UTC"
  attempt_deadline = "${var.daily_job_timeout}s"
  region           = var.region
  project          = var.project_id

  retry_config {
    retry_count          = 3
    max_retry_duration   = "600s"
    min_backoff_duration = "5s"
    max_backoff_duration = "60s"
    max_doublings        = 3
  }

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.daily_new_listings.name}:run"

    oauth_token {
      service_account_email = google_service_account.cloud_scheduler_sa.email
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_cloud_run_v2_job.daily_new_listings,
    google_service_account.cloud_scheduler_sa,
    google_project_iam_member.scheduler_invoker
  ]
}
