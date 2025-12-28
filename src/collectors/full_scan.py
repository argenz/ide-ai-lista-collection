"""Weekly full scan collector job."""

from datetime import datetime, date
from typing import Dict, Any
import os

import structlog

from src.api.client import IdealistaClient
from src.db.connection import db
from src.db.operations import upsert_listing, mark_as_inactive, get_statistics
from src.config import settings

logger = structlog.get_logger()

# Import GCS client if available
_gcs_client = None
try:
    from src.storage.gcs import get_gcs_client
    if os.getenv("GCS_BUCKET_NAME"):
        try:
            _gcs_client = get_gcs_client()
            logger.info("gcs_storage_enabled", bucket=os.getenv("GCS_BUCKET_NAME"))
        except Exception as e:
            # Fall back to local storage if GCS auth fails (e.g., running locally without credentials)
            logger.info("local_storage_enabled", reason=f"GCS authentication failed: {str(e)}")
    else:
        logger.info("local_storage_enabled", reason="GCS_BUCKET_NAME not set")
except ImportError:
    logger.info("local_storage_enabled", reason="google-cloud-storage not installed")


def save_raw_response(date_str: str, page_num: int, data: Dict[str, Any]):
    """
    Save raw API response (GCS in cloud, local file in dev).

    Args:
        date_str: Date string (YYYY-MM-DD)
        page_num: Page number
        data: API response data
    """
    from src.collectors.new_listings import save_raw_response as _save
    _save(date_str, page_num, data, job_type="full_scan")


def save_metadata(date_str: str, metadata: Dict[str, Any]):
    """
    Save job metadata (GCS in cloud, local file in dev).

    Args:
        date_str: Date string (YYYY-MM-DD)
        metadata: Metadata dictionary
    """
    from src.collectors.new_listings import save_metadata as _save_meta
    _save_meta(date_str, metadata, job_type="full_scan")


def process_listing(session, property_data: Dict[str, Any]) -> str:
    """
    Process a single listing from API response.

    Uses the same logic as daily job:
    - New listing → insert both tables
    - Price change → update previous_prices JSONB
    - Republished → set is_active=True, republished=True
    - Active (no change) → update last_seen_at

    Args:
        session: Database session
        property_data: Property data from API

    Returns:
        Action taken: 'new', 'price_change', 'republished', or 'active'
    """
    property_code = property_data.get("propertyCode")
    price = property_data.get("price")

    if not property_code or not price:
        logger.warning("Invalid property data", data=property_data)
        return "skipped"

    # TODO: Remove publication_date parameter - API doesn't provide this value
    # Kept as None for now to maintain compatibility with database schema
    publication_date = None

    # Upsert listing
    action, listing, details = upsert_listing(
        session=session,
        property_code=property_code,
        price=price,
        all_fields=property_data,
        publication_date=publication_date
    )

    return action


def process_page(session, page_num: int, page_data: Dict[str, Any]) -> Dict[str, int]:
    """
    Process a single page of API results.

    Args:
        session: Database session
        page_num: Page number
        page_data: API response for this page

    Returns:
        Dictionary with counts of actions taken
    """
    properties = page_data.get("elementList", [])

    stats = {
        "new": 0,
        "price_change": 0,
        "republished": 0,
        "active": 0,
        "skipped": 0
    }

    for prop in properties:
        action = process_listing(session, prop)
        stats[action] = stats.get(action, 0) + 1

    logger.info(
        "page_processed",
        page=page_num,
        total_properties=len(properties),
        stats=stats
    )

    return stats


def run_weekly_scan():
    """
    Run the weekly full scan job.

    Scans all active listings to:
    - Track price changes
    - Detect republished listings
    - Mark sold or withdrawn properties as inactive

    Key differences from daily job:
    - No sinceDate filter (scans all active listings)
    - Orders by price ascending
    - Records scan_start_timestamp
    - Deactivates listings not seen in this scan
    """
    # Record scan start time BEFORE fetching any data
    # This ensures we don't accidentally deactivate listings we're about to process
    scan_start_timestamp = datetime.utcnow()
    job_id = f"weekly-{scan_start_timestamp.strftime('%Y%m%d-%H%M%S')}"
    date_str = scan_start_timestamp.strftime('%Y-%m-%d')

    logger.info(
        "weekly_scan_started",
        job_id=job_id,
        scan_start=scan_start_timestamp.isoformat()
    )

    # Initialize API client with job_id for request tracking
    client = IdealistaClient(job_id=job_id)

    # Database health check
    if not db.health_check():
        logger.error("Database health check failed, aborting job")
        raise RuntimeError("Database unavailable")

    # Get database session
    session = db.get_session()

    try:
        # Aggregate statistics
        total_stats = {
            "new": 0,
            "price_change": 0,
            "republished": 0,
            "active": 0,
            "skipped": 0
        }

        total_pages = 0
        total_properties = 0

        # Fetch all pages WITHOUT sinceDate (full scan)
        # Order by price ascending for consistent pagination
        logger.info("Starting full pagination of all active listings")

        for page_num, page_data in client.search_all_pages(
            operation="sale",
            property_type="homes",
            since_date=None,  # No date filter - scan ALL listings
            max_items=50,
            order="price",  # Order by price for consistent results
            sort="asc"  # Ascending order
        ):
            # Save raw response (GCS in cloud, local in dev)
            save_raw_response(date_str, page_num, page_data)

            # Process page and update database
            page_stats = process_page(session, page_num, page_data)

            # Update totals
            for key, value in page_stats.items():
                total_stats[key] = total_stats.get(key, 0) + value

            total_pages += 1
            total_properties += len(page_data.get("elementList", []))

            # Commit after each page to avoid losing work on errors
            session.commit()
            logger.info("page_committed", page=page_num)

        logger.info(
            "pagination_complete",
            total_pages=total_pages,
            total_properties=total_properties
        )

        # CRITICAL: Mark listings as inactive if they weren't seen in this scan
        # Any listing with last_seen_at < scan_start_timestamp is no longer active
        deactivated_count = mark_as_inactive(session, scan_start_timestamp)
        session.commit()

        logger.info(
            "deactivation_complete",
            deactivated_count=deactivated_count
        )

        # Get final database statistics
        db_stats = get_statistics(session)

        # Job completion
        end_time = datetime.utcnow()
        duration_seconds = (end_time - scan_start_timestamp).total_seconds()

        metadata = {
            "job_id": job_id,
            "job_type": "weekly_full_scan",
            "scan_start_timestamp": scan_start_timestamp.isoformat(),
            "start_time": scan_start_timestamp.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration_seconds,
            "total_pages": total_pages,
            "total_properties": total_properties,
            "actions": total_stats,
            "deactivated_count": deactivated_count,
            "database_stats": db_stats
        }

        save_metadata(date_str, metadata)

        logger.info(
            "weekly_scan_completed",
            job_id=job_id,
            duration_seconds=duration_seconds,
            total_pages=total_pages,
            total_properties=total_properties,
            actions=total_stats,
            deactivated_count=deactivated_count,
            database_stats=db_stats
        )

    except Exception as e:
        logger.error("weekly_scan_failed", job_id=job_id, error=str(e), exc_info=True)
        session.rollback()
        raise

    finally:
        session.close()
        logger.info("database_session_closed")


if __name__ == "__main__":
    # Configure structured logging for standalone execution
    import structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ]
    )

    run_weekly_scan()
