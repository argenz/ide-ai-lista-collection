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

# Cloud Scheduler job to trigger weekly full scan
resource "google_cloud_scheduler_job" "weekly_trigger" {
  name             = "weekly-full-scan-trigger"
  description      = "Triggers weekly full scan at 3 AM UTC on Sundays"
  schedule         = var.weekly_job_schedule
  time_zone        = "UTC"
  # Cloud Scheduler attempt_deadline max is 1800s (30 minutes)
  # This is just for the HTTP trigger, not the job execution time
  attempt_deadline = "1800s"
  region           = var.region
  project          = var.project_id

  retry_config {
    retry_count          = 3
    max_retry_duration   = "3600s"
    min_backoff_duration = "5s"
    max_backoff_duration = "60s"
    max_doublings        = 3
  }

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.weekly_full_scan.name}:run"

    oauth_token {
      service_account_email = google_service_account.cloud_scheduler_sa.email
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_cloud_run_v2_job.weekly_full_scan,
    google_service_account.cloud_scheduler_sa,
    google_project_iam_member.scheduler_invoker
  ]
}
