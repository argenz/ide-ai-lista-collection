# Cloud Monitoring Dashboard for ideAIlista Collector
resource "google_monitoring_dashboard" "ideailista_dashboard" {
  dashboard_json = jsonencode({
    displayName = "ideAIlista Data Collector Dashboard"
    mosaicLayout = {
      columns = 12
      tiles = [
        # Cloud Run Job Executions
        {
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run Job Executions (Last 7 Days)"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_job\" resource.labels.job_name=\"daily-new-listings\""
                      aggregation = {
                        alignmentPeriod  = "86400s"
                        perSeriesAligner = "ALIGN_SUM"
                        crossSeriesReducer = "REDUCE_COUNT"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Executions"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud Run Job Duration
        {
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run Job Duration (Last 7 Days)"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_job\" resource.labels.job_name=\"daily-new-listings\" metric.type=\"run.googleapis.com/job/completed_execution_count\""
                      aggregation = {
                        alignmentPeriod  = "86400s"
                        perSeriesAligner = "ALIGN_DELTA"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Duration (seconds)"
                scale = "LINEAR"
              }
            }
          }
        },
        # GCS Bucket Object Count
        {
          width  = 6
          height = 4
          widget = {
            title = "GCS Bucket Object Count"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"gcs_bucket\" resource.labels.bucket_name=\"${google_storage_bucket.data_bucket.name}\" metric.type=\"storage.googleapis.com/storage/object_count\""
                      aggregation = {
                        alignmentPeriod  = "3600s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Objects"
                scale = "LINEAR"
              }
            }
          }
        },
        # GCS Bucket Size
        {
          width  = 6
          height = 4
          widget = {
            title = "GCS Bucket Total Size"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"gcs_bucket\" resource.labels.bucket_name=\"${google_storage_bucket.data_bucket.name}\" metric.type=\"storage.googleapis.com/storage/total_bytes\""
                      aggregation = {
                        alignmentPeriod  = "3600s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Bytes"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud SQL Disk Usage
        {
          width  = 6
          height = 4
          widget = {
            title = "Cloud SQL Disk Utilization"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloudsql_database\" resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.idealista_db.name}\" metric.type=\"cloudsql.googleapis.com/database/disk/utilization\""
                      aggregation = {
                        alignmentPeriod  = "3600s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Utilization (0-1)"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud SQL Connection Count
        {
          width  = 6
          height = 4
          widget = {
            title = "Cloud SQL Active Connections"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloudsql_database\" resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.idealista_db.name}\" metric.type=\"cloudsql.googleapis.com/database/postgresql/num_backends\""
                      aggregation = {
                        alignmentPeriod  = "3600s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Connections"
                scale = "LINEAR"
              }
            }
          }
        },
        # API Request Count (Custom Metric)
        {
          width  = 6
          height = 4
          widget = {
            title = "Idealista API Request Count (Last 30 Days)"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"global\" metric.type=\"custom.googleapis.com/idealista/api_requests_total\""
                  aggregation = {
                    alignmentPeriod  = "2592000s"
                    perSeriesAligner = "ALIGN_SUM"
                  }
                }
              }
              sparkChartView = {
                sparkChartType = "SPARK_BAR"
              }
            }
          }
        },
        # API Quota Usage (Custom Metric)
        {
          width  = 6
          height = 4
          widget = {
            title = "API Quota Usage (Monthly)"
            scorecard = {
              gaugeView = {
                lowerBound = 0
                upperBound = 100
              }
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"global\" metric.type=\"custom.googleapis.com/idealista/api_quota_usage\""
                  aggregation = {
                    alignmentPeriod  = "2592000s"
                    perSeriesAligner = "ALIGN_MAX"
                  }
                }
              }
              thresholds = [
                {
                  value = 80
                  color = "YELLOW"
                },
                {
                  value = 95
                  color = "RED"
                }
              ]
            }
          }
        },
        # API Success Rate
        {
          width  = 6
          height = 4
          widget = {
            title = "API Success Rate (Last 7 Days)"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"global\" metric.type=\"custom.googleapis.com/idealista/api_success_rate\""
                      aggregation = {
                        alignmentPeriod  = "86400s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Success Rate (%)"
                scale = "LINEAR"
              }
            }
          }
        },
        # Listings Collected (Custom Metric)
        {
          width  = 6
          height = 4
          widget = {
            title = "New Listings Collected (Last 7 Days)"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"global\" metric.type=\"custom.googleapis.com/idealista/listings_collected\""
                      aggregation = {
                        alignmentPeriod  = "86400s"
                        perSeriesAligner = "ALIGN_SUM"
                        crossSeriesReducer = "REDUCE_SUM"
                        groupByFields      = ["metric.label.listing_type"]
                      }
                    }
                  }
                  plotType = "STACKED_BAR"
                }
              ]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Listings"
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

# Alert Policy for High API Usage
resource "google_monitoring_alert_policy" "api_quota_alert" {
  display_name = "ideAIlista API Quota Alert"
  combiner     = "OR"

  conditions {
    display_name = "API Quota Above 80%"

    condition_threshold {
      filter          = "resource.type=\"global\" AND metric.type=\"custom.googleapis.com/idealista/api_quota_usage\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 80

      aggregations {
        alignment_period   = "3600s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  notification_channels = []

  alert_strategy {
    auto_close = "86400s"
  }

  documentation {
    content   = "API quota usage has exceeded 80% (80 out of 100 requests per month). Review usage patterns and consider optimizing collection frequency."
    mime_type = "text/markdown"
  }

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
      filter          = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.idealista_db.name}\" AND metric.type=\"cloudsql.googleapis.com/database/disk/utilization\""
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
    google_sql_database_instance.idealista_db
  ]
}
