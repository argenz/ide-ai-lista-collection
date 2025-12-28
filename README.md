# Idealista Data Collection System

A data collection system that gathers residential property listings from the Idealista API to train a price prediction ML model. The system runs on Google Cloud Platform, collecting daily new listings and performing weekly full scans to track price changes and property lifecycle.

**Target:** Madrid, Spain (`locationId: 0-EU-ES-28`)

## Features

- Daily collection of new property listings
- Price change tracking with historical data
- Property lifecycle management (active/inactive/republished)
- Raw data backup to Google Cloud Storage
- Structured logging for monitoring
- Retry logic and rate limiting for API calls
- Local development environment with Docker

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

```bash
# Build Docker image
docker build -t gcr.io/YOUR_PROJECT_ID/idealista-collector:latest .

# Authenticate with Google Container Registry
gcloud auth configure-docker

# Push image
docker push gcr.io/YOUR_PROJECT_ID/idealista-collector:latest

# The Cloud Scheduler will automatically trigger the job on schedule
# Or trigger manually:
gcloud run jobs execute daily-new-listings --region=europe-west1
```

## Monitoring

### View Logs

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
| `GCS_BUCKET_NAME` | GCS bucket for raw data | Yes (cloud) |
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

## Troubleshooting

### Database Connection Issues

```bash
# Check database is running
docker-compose ps postgres

# Restart database
docker-compose restart postgres

# View database logs
docker-compose logs postgres
```

### API Authentication Errors

- Verify credentials in `.env` file
- Ensure credentials are not expired

### Rate Limiting

The client implements automatic retry with exponential backoff. If you encounter persistent rate limiting:
- Reduce collection frequency
- Request higher API quota from Idealista

## Development

### Running Tests

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Code Style

```bash
# Format code
black src/

# Lint code
pylint src/
```

