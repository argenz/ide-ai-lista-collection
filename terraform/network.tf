# VPC Network for Cloud SQL private IP
resource "google_compute_network" "vpc" {
  name                    = "ideailista-vpc"
  auto_create_subnetworks = true
  project                 = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Reserve IP range for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "ideailista-sql-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
  project       = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Private VPC connection for Cloud SQL
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]

  depends_on = [google_project_service.required_apis]
}

# VPC Access Connector for Cloud Run to access Cloud SQL
resource "google_vpc_access_connector" "connector" {
  name          = "ideailista-vpc-connector"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.8.0.0/28"
  project       = var.project_id

  # Minimum machine type for connector
  machine_type = "e2-micro"

  depends_on = [
    google_project_service.required_apis,
    google_compute_network.vpc
  ]
}
