-- Idealista Data Collection Database Schema
-- PostgreSQL 15+

-- NOTE: For local development reset, manually run:
--   DROP TABLE IF EXISTS api_requests CASCADE;
--   DROP TABLE IF EXISTS listing_images CASCADE;
--   DROP TABLE IF EXISTS listing_details CASCADE;
--   DROP TABLE IF EXISTS listings CASCADE;

-- Table: listings
-- Tracks property lifecycle and activity status
CREATE TABLE IF NOT EXISTS listings (
    property_code VARCHAR(20) PRIMARY KEY,
    first_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    -- TODO: Remove publication_date - API doesn't provide this value, first_seen_at serves this purpose
    publication_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sold_or_withdrawn_at DATE,
    republished BOOLEAN NOT NULL DEFAULT FALSE,
    republished_at TIMESTAMP
);

-- Table: listing_details
-- Stores property data and price history
CREATE TABLE IF NOT EXISTS listing_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_code VARCHAR(20) NOT NULL UNIQUE REFERENCES listings(property_code) ON DELETE CASCADE,
    price INTEGER NOT NULL,
    previous_prices JSONB,
    all_fields_json JSONB NOT NULL
);

-- Table: listing_images (for future use in Phase 5.2)
-- Stores one image per tag per listing
CREATE TABLE IF NOT EXISTS listing_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_code VARCHAR(20) NOT NULL REFERENCES listings(property_code) ON DELETE CASCADE,
    image_tag VARCHAR(50) NOT NULL,
    source_url TEXT NOT NULL,
    local_path TEXT,
    downloaded_at TIMESTAMP,
    file_hash VARCHAR(64),
    UNIQUE (property_code, image_tag)
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_listings_is_active ON listings(is_active);
CREATE INDEX IF NOT EXISTS idx_listings_last_seen_at ON listings(last_seen_at);
-- TODO: Remove this index when publication_date field is removed
CREATE INDEX IF NOT EXISTS idx_listings_publication_date ON listings(publication_date);
CREATE INDEX IF NOT EXISTS idx_listing_details_price ON listing_details(price);
CREATE INDEX IF NOT EXISTS idx_listing_images_property_code ON listing_images(property_code);

-- Comments for documentation
COMMENT ON TABLE listings IS 'Tracks property lifecycle and activity status';
COMMENT ON TABLE listing_details IS 'Stores current property data and price change history';
COMMENT ON TABLE listing_images IS 'Stores compressed images tagged by room type';

COMMENT ON COLUMN listings.property_code IS 'Idealista property ID (unique identifier)';
COMMENT ON COLUMN listings.first_seen_at IS 'Timestamp when property was first discovered';
COMMENT ON COLUMN listings.last_seen_at IS 'Timestamp of most recent appearance in API results';
COMMENT ON COLUMN listings.is_active IS 'True if property appeared in most recent scan';
COMMENT ON COLUMN listings.republished IS 'True if property reappeared after being inactive';

COMMENT ON COLUMN listing_details.previous_prices IS 'JSON object mapping dates to historical prices';
COMMENT ON COLUMN listing_details.all_fields_json IS 'Complete API response for this property';

-- Table: api_requests
-- Tracks all Idealista API requests for quota monitoring and analytics
CREATE TABLE IF NOT EXISTS api_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_type VARCHAR(50) NOT NULL,  -- 'oauth_token', 'search', etc.
    endpoint VARCHAR(255) NOT NULL,
    status_code INTEGER,
    duration_ms INTEGER,
    request_params JSONB,
    error_message TEXT,
    job_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indices for api_requests
CREATE INDEX IF NOT EXISTS idx_api_requests_created_at ON api_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_api_requests_type ON api_requests(request_type);
CREATE INDEX IF NOT EXISTS idx_api_requests_job_id ON api_requests(job_id);
CREATE INDEX IF NOT EXISTS idx_api_requests_status ON api_requests(status_code);

-- Comments for api_requests
COMMENT ON TABLE api_requests IS 'Tracks all Idealista API requests for quota monitoring';
COMMENT ON COLUMN api_requests.request_type IS 'Type of request (oauth_token, search, etc.)';
COMMENT ON COLUMN api_requests.endpoint IS 'API endpoint called';
COMMENT ON COLUMN api_requests.status_code IS 'HTTP status code returned';
COMMENT ON COLUMN api_requests.duration_ms IS 'Request duration in milliseconds';
COMMENT ON COLUMN api_requests.request_params IS 'Request parameters as JSON';
COMMENT ON COLUMN api_requests.job_id IS 'Associated job ID for correlation';
