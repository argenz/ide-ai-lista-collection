"""Daily new listings collector job."""

from datetime import datetime, date
from typing import Dict, Any, Optional
import json
import os

import structlog

from src.api.client import IdealistaClient
from src.db.connection import db
from src.db.operations import upsert_listing, get_statistics
from src.config import settings

logger = structlog.get_logger()

# Import GCS client if available
_gcs_client = None
try:
    from src.storage.gcs import get_gcs_client
    if os.getenv("GCS_BUCKET_NAME"):
        _gcs_client = get_gcs_client()
        logger.info("gcs_storage_enabled", bucket=os.getenv("GCS_BUCKET_NAME"))
    else:
        logger.info("local_storage_enabled", reason="GCS_BUCKET_NAME not set")
except ImportError:
    logger.info("local_storage_enabled", reason="google-cloud-storage not installed")


def save_raw_response_local(date_str: str, page_num: int, data: Dict[str, Any]):
    """
    Save raw API response to local file (for local development).

    In production, this will be replaced with GCS upload.

    Args:
        date_str: Date string (YYYY-MM-DD)
        page_num: Page number
        data: API response data
    """
    output_dir = f"raw_responses/{date_str}"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{output_dir}/new_listings_p{page_num}.json"

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

    logger.info("raw_response_saved", filename=filename)


def save_metadata_local(date_str: str, metadata: Dict[str, Any]):
    """
    Save job metadata to local file.

    Args:
        date_str: Date string (YYYY-MM-DD)
        metadata: Metadata dictionary
    """
    output_dir = f"raw_responses/{date_str}"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{output_dir}/_meta.json"

    with open(filename, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.info("metadata_saved", filename=filename)


def save_raw_response(date_str: str, page_num: int, data: Dict[str, Any], job_type: str = "new_listings"):
    """
    Save raw API response (GCS in cloud, local file in dev).

    Args:
        date_str: Date string (YYYY-MM-DD)
        page_num: Page number
        data: API response data
        job_type: Type of collection job
    """
    collection_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    if _gcs_client:
        # Use GCS in production
        _gcs_client.upload_raw_response(collection_date, page_num, data, job_type)
    else:
        # Use local storage in development
        save_raw_response_local(date_str, page_num, data)


def save_metadata(date_str: str, metadata: Dict[str, Any], job_type: str = "new_listings"):
    """
    Save job metadata (GCS in cloud, local file in dev).

    Args:
        date_str: Date string (YYYY-MM-DD)
        metadata: Metadata dictionary
        job_type: Type of collection job
    """
    collection_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    if _gcs_client:
        # Use GCS in production
        _gcs_client.upload_metadata(collection_date, metadata, job_type)
    else:
        # Use local storage in development
        save_metadata_local(date_str, metadata)


def process_listing(session, property_data: Dict[str, Any]) -> str:
    """
    Process a single listing from API response.

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

    # Attempt to infer publication date (not provided in most cases)
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


def run_daily_job():
    """
    Run the daily new listings collection job.

    Fetches listings published in the last 2 days and stores them in the database.
    """
    start_time = datetime.utcnow()
    job_id = f"daily-{start_time.strftime('%Y%m%d-%H%M%S')}"
    date_str = start_time.strftime('%Y-%m-%d')

    logger.info("daily_job_started", job_id=job_id, start_time=start_time.isoformat())

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

        # Fetch all pages with sinceDate=Y (last 2 days)
        for page_num, page_data in client.search_all_pages(
            operation="sale",
            property_type="homes",
            since_date="Y",  # Last 2 days
            max_items=50,
            order="publicationDate",
            sort="desc"
        ):
            # Save raw response (GCS in cloud, local in dev)
            save_raw_response(date_str, page_num, page_data, "new_listings")

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

        # Get database statistics
        db_stats = get_statistics(session)

        # Job completion
        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()

        metadata = {
            "job_id": job_id,
            "job_type": "daily_new_listings",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration_seconds,
            "total_pages": total_pages,
            "total_properties": total_properties,
            "actions": total_stats,
            "database_stats": db_stats
        }

        save_metadata(date_str, metadata, "new_listings")

        logger.info(
            "daily_job_completed",
            job_id=job_id,
            duration_seconds=duration_seconds,
            total_pages=total_pages,
            total_properties=total_properties,
            actions=total_stats,
            database_stats=db_stats
        )

    except Exception as e:
        logger.error("daily_job_failed", job_id=job_id, error=str(e), exc_info=True)
        session.rollback()
        raise

    finally:
        session.close()
        logger.info("database_session_closed")


if __name__ == "__main__":
    # Configure structured logging for standalone execution
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ]
    )

    run_daily_job()
