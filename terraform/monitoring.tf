# Cloud Monitoring Dashboard for ideAIlista Collector
# Simplified dashboard with GCP-provided metrics only
resource "google_monitoring_dashboard" "ideailista_dashboard" {
  dashboard_json = jsonencode({
    displayName = "ideAIlista Data Collector Dashboard"
    mosaicLayout = {
      columns = 12
      tiles = [
        # Cloud Run Job Executions
        {
          xPos   = 0
          yPos   = 0
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run Job Executions"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_job\" AND resource.labels.job_name=\"daily-new-listings\" AND metric.type=\"run.googleapis.com/job/completed_execution_count\""
                      aggregation = {
                        alignmentPeriod    = "86400s"
                        perSeriesAligner   = "ALIGN_SUM"
                        crossSeriesReducer = "REDUCE_SUM"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              yAxis = {
                label = "Executions"
                scale = "LINEAR"
              }
            }
          }
        },
        # GCS Bucket Object Count
        {
          xPos   = 6
          yPos   = 0
          width  = 6
          height = 4
          widget = {
            title = "GCS Bucket Object Count"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"gcs_bucket\" AND resource.labels.bucket_name=\"${google_storage_bucket.data_bucket.name}\" AND metric.type=\"storage.googleapis.com/storage/object_count\""
                      aggregation = {
                        alignmentPeriod  = "3600s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              yAxis = {
                label = "Objects"
                scale = "LINEAR"
              }
            }
          }
        },
        # GCS Bucket Size
        {
          xPos   = 0
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "GCS Bucket Total Size"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"gcs_bucket\" AND resource.labels.bucket_name=\"${google_storage_bucket.data_bucket.name}\" AND metric.type=\"storage.googleapis.com/storage/total_bytes\""
                      aggregation = {
                        alignmentPeriod  = "3600s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              yAxis = {
                label = "Bytes"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud SQL Disk Usage
        {
          xPos   = 6
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Cloud SQL Disk Utilization"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.ideailista_db.name}\" AND metric.type=\"cloudsql.googleapis.com/database/disk/utilization\""
                      aggregation = {
                        alignmentPeriod  = "3600s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              yAxis = {
                label = "Utilization (0-1)"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud SQL Connection Count
        {
          xPos   = 0
          yPos   = 8
          width  = 6
          height = 4
          widget = {
            title = "Cloud SQL Active Connections"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.ideailista_db.name}\" AND metric.type=\"cloudsql.googleapis.com/database/postgresql/num_backends\""
                      aggregation = {
                        alignmentPeriod  = "3600s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              yAxis = {
                label = "Connections"
                scale = "LINEAR"
              }
            }
          }
        }
      ]
    }
  })

  project = var.project_id

  depends_on = [
    google_project_service.required_apis
  ]
}

# Alert Policy for Cloud Run Job Failures
resource "google_monitoring_alert_policy" "job_failure_alert" {
  display_name = "Cloud Run Job Failure Alert"
  combiner     = "OR"

  conditions {
    display_name = "Job Execution Failed"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_job\" AND resource.labels.job_name=\"daily-new-listings\" AND metric.type=\"run.googleapis.com/job/completed_execution_count\" AND metric.labels.result=\"failed\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_DELTA"
      }
    }
  }

  notification_channels = []

  alert_strategy {
    auto_close = "86400s"
  }

  documentation {
    content   = "Cloud Run job execution has failed. Check logs for error details and investigate the root cause."
    mime_type = "text/markdown"
  }

  project = var.project_id

  depends_on = [
    google_project_service.required_apis,
    google_cloud_run_v2_job.daily_new_listings
  ]
}

# Alert Policy for Cloud SQL Disk Usage
resource "google_monitoring_alert_policy" "cloud_sql_disk_alert" {
  display_name = "Cloud SQL Disk Usage Alert"
  combiner     = "OR"

  conditions {
    display_name = "Disk Utilization Above 80%"

    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.ideailista_db.name}\" AND metric.type=\"cloudsql.googleapis.com/database/disk/utilization\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8

      aggregations {
        alignment_period   = "3600s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = []

  alert_strategy {
    auto_close = "86400s"
  }

  documentation {
    content   = "Cloud SQL disk utilization has exceeded 80%. Consider increasing disk size or implementing data archival strategies."
    mime_type = "text/markdown"
  }

  project = var.project_id

  depends_on = [
    google_project_service.required_apis,
    google_sql_database_instance.ideailista_db
  ]
}
