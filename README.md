# IdeAilista Data Collection System

A data collection system that gathers residential property listings from the Idealista API to train ideAIlista. The system runs on Google Cloud Platform, collecting daily new listings and performing weekly full scans to track price changes and property lifecycle.

**Target:** Madrid, Spain

## Features

- Daily collection of new property listings
- Price change tracking with historical data
- Listing lifecycle tracking (active/inactive/republished)

## Architecture

- **Language:** Python 3.11
- **Database:** PostgreSQL 15
- **Cloud Platform:** Google Cloud Platform
  - Cloud Run Jobs (scheduled execution)
  - Cloud SQL (managed PostgreSQL)
  - Cloud Storage (raw data backup)
  - Secret Manager (credentials)
  - Cloud Scheduler (cron triggers)

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Google Cloud Platform account (for production deployment)
- Idealista API credentials.
- Terraform 1.5.0+ (for infrastructure deployment)
- gcloud CLI (for GCP operations)

## Project Structure

```
idealista-collector/
├── src/
│   ├── api/
│   │   ├── auth.py           # OAuth2 token management
│   │   └── client.py         # Idealista API client
│   ├── collectors/
│   │   └── new_listings.py   # Daily job logic
│   ├── db/
│   │   ├── connection.py     # Database connection
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── operations.py     # CRUD operations
│   │   └── schema.sql        # Database schema
│   ├── storage/
│   │   └── gcs.py            # GCS operations 
│   ├── config.py             # Configuration management
│   └── main.py               # Main entrypoint
├── terraform/                # Infrastructure as Code
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Database Schema

### `listings` Table
Tracks property lifecycle and activity status.

| Column | Type | Description |
|--------|------|-------------|
| `property_code` | VARCHAR(20) | Idealista property ID (PK) |
| `first_seen_at` | TIMESTAMP | First capture timestamp |
| `last_seen_at` | TIMESTAMP | Most recent appearance |
| `is_active` | BOOLEAN | Currently listed |
| `republished` | BOOLEAN | Reappeared after deactivation |

### `listing_details` Table
Stores property data and price history.

| Column | Type | Description |
|--------|------|-------------|
| `property_code` | VARCHAR(20) | Foreign key to listings |
| `price` | INTEGER | Current price (€) |
| `previous_prices` | JSONB | Historical prices |
| `all_fields_json` | JSONB | Complete API response |

## Local Development Setup

### Quick Start

1. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your Idealista API credentials
   ```

2. **Start PostgreSQL:**
   ```bash
   docker-compose up -d postgres
   ```

3. **Run the collector:**
   ```bash
   docker-compose up app
   ```

4. **Verify data:**
   ```bash
   docker-compose exec postgres psql -U postgres -d ideailista-db -c "SELECT COUNT(*) FROM listings;"
   ```

## Testing API Client Standalone

```bash
# Test API connectivity without running full job
python src/api/client.py
```

## GCP Deployment

### Prerequisites

1. Enable required GCP APIs:

```bash
gcloud services enable \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  vpcaccess.googleapis.com \
  compute.googleapis.com
```

2. Set up Terraform variables:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Review planned changes
terraform plan

# Apply infrastructure
terraform apply
```

### Deploy Application

#### Option 1: Automatic Deployment via GitHub Actions 

Push to `main` branch triggers automatic deployment. Setup required secrets in GitHub:

1. Go to **Settings → Secrets and variables → Actions**
2. Add the following secrets:
   - `GCP_PROJECT_ID`: Your Google Cloud project ID
   - `GCP_SA_KEY`: Service account JSON key with permissions:
     - Cloud Run Admin
     - Storage Admin
     - Service Account User

#### Option 2: Manual Deployment to Cloud Run

```bash
# Set your project ID
export PROJECT_ID=your-gcp-project-id

# Authenticate with Google Cloud
gcloud auth login
gcloud config set project $PROJECT_ID
gcloud auth configure-docker

# Build for Cloud Run (linux/amd64 required)
docker build --platform=linux/amd64 -t gcr.io/$PROJECT_ID/idealista-collector:latest .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/idealista-collector:latest

# Update the Cloud Run job with new image
gcloud run jobs update daily-new-listings \
  --image=gcr.io/$PROJECT_ID/idealista-collector:latest \
  --region=europe-west1

# Trigger the job manually (optional)
gcloud run jobs execute daily-new-listings --region=europe-west1
```

## Monitoring

### View GCP Logs

```bash
# Cloud Run job logs
gcloud run jobs logs daily-new-listings --region=europe-west1

# Follow logs in real-time
gcloud run jobs logs daily-new-listings --region=europe-west1 --follow
```

### Database Queries

```bash
# Get statistics
SELECT
  COUNT(*) as total_listings,
  COUNT(*) FILTER (WHERE is_active = true) as active,
  COUNT(*) FILTER (WHERE is_active = false) as inactive,
  COUNT(*) FILTER (WHERE republished = true) as republished
FROM listings;

# Recent price changes
SELECT
  l.property_code,
  ld.price as current_price,
  ld.previous_prices
FROM listings l
JOIN listing_details ld USING (property_code)
WHERE ld.previous_prices IS NOT NULL
ORDER BY l.last_seen_at DESC
LIMIT 10;
```

## Configuration

All configuration is managed through environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `IDEALISTA_API_KEY` | Idealista API key | Yes |
| `IDEALISTA_API_SECRET` | Idealista API secret | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `TARGET_LOCATION_ID` | Madrid location ID | No (default: 0-EU-ES-28) |
| `JOB_TYPE` | Job to run | No (default: daily_new_listings) |

## Cost Estimates

Monthly costs for GCP deployment:

| Resource | Cost |
|----------|------|
| Cloud SQL (db-f1-micro) | $7-10 |
| Cloud Storage (5-10GB) | $0.10-0.20 |
| Cloud Run Jobs | $1-2 |
| **Total** | **~$10-15/month** |

