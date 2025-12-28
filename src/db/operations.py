"""Database CRUD operations for listings."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_
import structlog

from src.db.models import Listing, ListingDetails, ApiRequest

logger = structlog.get_logger()


def get_listing(session: Session, property_code: str) -> Optional[Listing]:
    """
    Retrieve a listing by property code.

    Args:
        session: Database session
        property_code: Idealista property ID

    Returns:
        Listing object if found, None otherwise
    """
    return session.query(Listing).filter(Listing.property_code == property_code).first()


def get_listing_with_details(session: Session, property_code: str) -> Optional[tuple]:
    """
    Retrieve a listing with its details.

    Args:
        session: Database session
        property_code: Idealista property ID

    Returns:
        Tuple of (Listing, ListingDetails) if found, None otherwise
    """
    result = (
        session.query(Listing, ListingDetails)
        .join(ListingDetails, Listing.property_code == ListingDetails.property_code)
        .filter(Listing.property_code == property_code)
        .first()
    )
    return result


def upsert_listing(
    session: Session,
    property_code: str,
    price: int,
    all_fields: Dict[str, Any],
    publication_date: Optional[date] = None
) -> tuple:
    """
    Insert a new listing or update an existing one.

    This implements the core business logic from the design document:
    - New listing: Insert into both tables
    - Price change: Update previous_prices JSONB
    - Republished: Set is_active=True, republished=True
    - Active (no change): Update last_seen_at

    Args:
        session: Database session
        property_code: Idealista property ID
        price: Current price in euros
        all_fields: Complete API response JSON
        publication_date: Estimated publication date

    Returns:
        Tuple of (action, listing, details) where action is one of:
        'new', 'price_change', 'republished', 'active'
    """
    now = datetime.utcnow()
    existing_listing = get_listing(session, property_code)

    if existing_listing is None:
        # New listing - insert into both tables
        listing = Listing(
            property_code=property_code,
            first_seen_at=now,
            last_seen_at=now,
            publication_date=publication_date,
            is_active=True,
            republished=False
        )
        session.add(listing)

        details = ListingDetails(
            property_code=property_code,
            price=price,
            previous_prices=None,
            all_fields_json=all_fields
        )
        session.add(details)

        logger.info(
            "new_listing_inserted",
            property_code=property_code,
            price=price
        )
        return ("new", listing, details)

    # Listing exists - get details
    existing_details = session.query(ListingDetails).filter(
        ListingDetails.property_code == property_code
    ).first()

    # Check if price changed
    if existing_details and existing_details.price != price:
        # Price change - update previous_prices JSONB
        previous_prices = existing_details.previous_prices or {}
        previous_prices[str(date.today())] = existing_details.price

        existing_details.price = price
        existing_details.previous_prices = previous_prices
        existing_details.all_fields_json = all_fields

        existing_listing.last_seen_at = now

        logger.info(
            "price_change_detected",
            property_code=property_code,
            old_price=existing_details.price,
            new_price=price
        )
        return ("price_change", existing_listing, existing_details)

    # Check if republished (was inactive, now active again)
    if not existing_listing.is_active:
        existing_listing.is_active = True
        existing_listing.sold_or_withdrawn_at = None
        existing_listing.republished = True
        existing_listing.republished_at = now
        existing_listing.last_seen_at = now

        # Update details in case anything changed
        if existing_details:
            existing_details.all_fields_json = all_fields

        logger.info(
            "listing_republished",
            property_code=property_code
        )
        return ("republished", existing_listing, existing_details)

    # Active listing with no changes - just update last_seen_at
    existing_listing.last_seen_at = now

    # Update details to keep all_fields_json fresh
    if existing_details:
        existing_details.all_fields_json = all_fields

    return ("active", existing_listing, existing_details)


def mark_as_inactive(session: Session, scan_start_timestamp: datetime) -> int:
    """
    Mark listings as inactive if they weren't seen in the most recent scan.

    This is used by the weekly full scan job to detect sold or withdrawn properties.

    Args:
        session: Database session
        scan_start_timestamp: When the scan started

    Returns:
        Number of listings marked as inactive
    """
    count = (
        session.query(Listing)
        .filter(
            and_(
                Listing.is_active == True,
                Listing.last_seen_at < scan_start_timestamp
            )
        )
        .update(
            {
                "is_active": False,
                "sold_or_withdrawn_at": date.today()
            },
            synchronize_session=False
        )
    )

    logger.info(
        "listings_marked_inactive",
        count=count,
        scan_start=scan_start_timestamp.isoformat()
    )
    return count


def get_active_listings(session: Session, limit: int = 1000) -> List[Listing]:
    """
    Get active listings.

    Args:
        session: Database session
        limit: Maximum number of listings to return

    Returns:
        List of active Listing objects
    """
    return (
        session.query(Listing)
        .filter(Listing.is_active == True)
        .limit(limit)
        .all()
    )


def get_listings_needing_images(session: Session, limit: int = 200) -> List[tuple]:
    """
    Get active listings that don't have images yet.

    Used by the image scraper job (Phase 5.2).

    Args:
        session: Database session
        limit: Maximum number of listings to return

    Returns:
        List of tuples (property_code, url)
    """
    from src.db.models import ListingImage

    results = (
        session.query(
            Listing.property_code,
            ListingDetails.all_fields_json["url"].astext
        )
        .join(ListingDetails, Listing.property_code == ListingDetails.property_code)
        .outerjoin(ListingImage, Listing.property_code == ListingImage.property_code)
        .filter(
            and_(
                Listing.is_active == True,
                ListingImage.id == None  # No images exist
            )
        )
        .limit(limit)
        .all()
    )

    return results


def get_statistics(session: Session) -> Dict[str, int]:
    """
    Get database statistics for monitoring.

    Returns:
        Dictionary with counts of various listing states
    """
    total = session.query(Listing).count()
    active = session.query(Listing).filter(Listing.is_active == True).count()
    inactive = session.query(Listing).filter(Listing.is_active == False).count()
    republished = session.query(Listing).filter(Listing.republished == True).count()

    return {
        "total_listings": total,
        "active_listings": active,
        "inactive_listings": inactive,
        "republished_listings": republished
    }


# API Request Tracking Functions

def insert_api_request(
    session: Session,
    request_type: str,
    endpoint: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[int] = None,
    request_params: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    job_id: Optional[str] = None
) -> ApiRequest:
    """
    Insert a new API request record for tracking.

    Args:
        session: Database session
        request_type: Type of request ('oauth_token', 'search', etc.)
        endpoint: API endpoint called
        status_code: HTTP status code returned
        duration_ms: Request duration in milliseconds
        request_params: Request parameters as dictionary
        error_message: Error message if request failed
        job_id: Associated job ID for correlation

    Returns:
        Created ApiRequest object
    """
    api_request = ApiRequest(
        request_type=request_type,
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=duration_ms,
        request_params=request_params,
        error_message=error_message,
        job_id=job_id
    )
    session.add(api_request)

    logger.debug(
        "api_request_tracked",
        request_type=request_type,
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=duration_ms
    )

    return api_request


def get_api_usage_stats(
    session: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Get API usage statistics for monitoring and quota tracking.

    Args:
        session: Database session
        start_date: Start date for filtering (inclusive)
        end_date: End date for filtering (inclusive)

    Returns:
        Dictionary with API usage statistics
    """
    from sqlalchemy import func, extract

    # Base query
    query = session.query(ApiRequest)

    # Apply date filters if provided
    if start_date:
        query = query.filter(func.date(ApiRequest.created_at) >= start_date)
    if end_date:
        query = query.filter(func.date(ApiRequest.created_at) <= end_date)

    # Total requests
    total_requests = query.count()

    # Requests by type
    requests_by_type = (
        query.with_entities(
            ApiRequest.request_type,
            func.count(ApiRequest.id).label('count')
        )
        .group_by(ApiRequest.request_type)
        .all()
    )

    # Success rate (2xx status codes)
    successful = query.filter(
        and_(
            ApiRequest.status_code >= 200,
            ApiRequest.status_code < 300
        )
    ).count()

    # Failed requests (4xx, 5xx)
    failed = query.filter(
        ApiRequest.status_code >= 400
    ).count()

    # Average response time
    avg_duration = (
        query.with_entities(func.avg(ApiRequest.duration_ms))
        .filter(ApiRequest.duration_ms.isnot(None))
        .scalar()
    )

    # Monthly quota calculation (excluding OAuth requests)
    # Assuming 2000 requests/month quota
    search_requests = query.filter(
        ApiRequest.request_type != 'oauth_token'
    ).count()

    quota_limit = 2000
    quota_remaining = quota_limit - search_requests

    return {
        "total_requests": total_requests,
        "search_requests": search_requests,
        "requests_by_type": dict(requests_by_type),
        "successful_requests": successful,
        "failed_requests": failed,
        "success_rate": round(successful / total_requests * 100, 2) if total_requests > 0 else 0,
        "avg_duration_ms": round(avg_duration, 2) if avg_duration else None,
        "monthly_quota_limit": quota_limit,
        "monthly_quota_used": search_requests,
        "monthly_quota_remaining": quota_remaining,
        "quota_usage_percent": round(search_requests / quota_limit * 100, 2) if quota_limit > 0 else 0
    }
