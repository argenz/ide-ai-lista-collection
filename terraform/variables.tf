variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "europe-west1"
}

variable "zone" {
  description = "GCP zone for zonal resources"
  type        = string
  default     = "europe-west1-b"
}

variable "idealista_api_key" {
  description = "Idealista API key"
  type        = string
  sensitive   = true
}

variable "idealista_api_secret" {
  description = "Idealista API secret"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Cloud SQL postgres password"
  type        = string
  sensitive   = true
}

variable "db_instance_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 10
}

variable "bucket_location" {
  description = "GCS bucket location"
  type        = string
  default     = "EU"
}

variable "target_location_id" {
  description = "Idealista location ID for Madrid"
  type        = string
  default     = "0-EU-ES-28"
}

variable "target_country" {
  description = "Target country code"
  type        = string
  default     = "es"
}

variable "docker_image" {
  description = "Docker image for Cloud Run job (e.g., gcr.io/PROJECT_ID/idealista-collector:latest)"
  type        = string
}

variable "daily_job_schedule" {
  description = "Cron schedule for daily job (UTC)"
  type        = string
  default     = "0 2 * * *" # Daily at 2 AM UTC
}

variable "daily_job_timeout" {
  description = "Timeout for daily job in seconds"
  type        = number
  default     = 600 # 10 minutes
}

variable "daily_job_memory" {
  description = "Memory limit for daily job"
  type        = string
  default     = "512Mi"
}

variable "daily_job_cpu" {
  description = "CPU limit for daily job"
  type        = string
  default     = "1"
}

# Weekly Full Scan Job Variables
variable "enable_weekly_job" {
  description = "Enable or disable the weekly full scan job and scheduler"
  type        = bool
  default     = false # Disabled by default to avoid API quota issues
}

variable "weekly_job_schedule" {
  description = "Cron schedule for weekly full scan job (UTC)"
  type        = string
  default     = "0 3 * * 0" # Sunday at 3 AM UTC
}

variable "weekly_job_timeout" {
  description = "Timeout for weekly scan job in seconds"
  type        = number
  default     = 3600 # 60 minutes
}

variable "weekly_job_memory" {
  description = "Memory limit for weekly scan job"
  type        = string
  default     = "1Gi"
}

variable "weekly_job_cpu" {
  description = "CPU limit for weekly scan job"
  type        = string
  default     = "1"
}
