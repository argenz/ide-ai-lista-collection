"""Idealista API client with retry logic and rate limiting."""

from typing import Dict, List, Optional, Any
import time

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import structlog

from src.api.auth import get_token_manager
from src.config import settings
from src.db.connection import db
from src.db.operations import insert_api_request

logger = structlog.get_logger()


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class ServerError(Exception):
    """Raised when API server returns 5xx error."""
    pass


class IdealistaClient:
    """
    Client for Idealista API with automatic retries and rate limiting.

    Features:
    - OAuth2 authentication with token management
    - Automatic retries on rate limits and server errors
    - Rate limiting (1 request/second)
    - Pagination support
    """

    BASE_URL = "https://api.idealista.com/3.5"
    RATE_LIMIT_DELAY = 1.0  # seconds between requests

    def __init__(self, job_id: Optional[str] = None):
        """
        Initialize Idealista API client.

        Args:
            job_id: Optional job ID for correlating API requests with job runs
        """
        self.token_manager = get_token_manager(job_id=job_id)
        self.last_request_time: Optional[float] = None
        self.country = settings.api.target_country
        self.job_id = job_id
        logger.info("Idealista API client initialized", country=self.country, job_id=job_id)

    def _rate_limit(self):
        """Enforce rate limiting (1 request/second)."""
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.RATE_LIMIT_DELAY:
                sleep_time = self.RATE_LIMIT_DELAY - elapsed
                logger.debug("Rate limiting", sleep_seconds=sleep_time)
                time.sleep(sleep_time)

        self.last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((RateLimitError, ServerError)),
        before_sleep=before_sleep_log(logger, "warning"),
        reraise=True
    )
    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to Idealista API with retries.

        Args:
            endpoint: API endpoint (e.g., "/search")
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            RateLimitError: If rate limited (429)
            ServerError: If server error (5xx)
            requests.HTTPError: For other HTTP errors
        """
        self._rate_limit()

        url = f"{self.BASE_URL}/{self.country}{endpoint}"
        token = self.token_manager.get_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        logger.info(
            "api_request",
            endpoint=endpoint,
            params={k: v for k, v in params.items() if k not in ["apikey", "secret"]}
        )

        # Track request start time
        start_time = time.time()

        response = requests.post(
            url,
            headers=headers,
            data=params,
            timeout=30
        )

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Handle rate limiting
        if response.status_code == 429:
            logger.warning("API rate limit exceeded", status_code=429)
            raise RateLimitError("Rate limit exceeded")

        # Handle server errors
        if response.status_code >= 500:
            logger.error("API server error", status_code=response.status_code)
            raise ServerError(f"Server error: {response.status_code}")

        # Handle authentication errors (don't retry)
        if response.status_code == 401:
            logger.error("API authentication failed", status_code=401)
            self.token_manager.invalidate()  # Force token refresh
            response.raise_for_status()

        # Raise for other HTTP errors
        response.raise_for_status()

        data = response.json()
        logger.info(
            "api_response_received",
            total_results=data.get("total"),
            items_count=len(data.get("elementList", []))
        )

        # Track API request in database
        try:
            session = db.get_session()
            try:
                insert_api_request(
                    session=session,
                    request_type="search",
                    endpoint=endpoint,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_params=params,
                    error_message=None,
                    job_id=self.job_id
                )
                session.commit()
            except Exception as e:
                logger.warning("Failed to track API request", error=str(e))
                session.rollback()
            finally:
                session.close()
        except Exception as e:
            logger.warning("Failed to get database session for tracking", error=str(e))

        return data

    def search(
        self,
        operation: str = "sale",
        property_type: str = "homes",
        location_id: str = None,
        since_date: str = None,
        max_items: int = 50,
        num_page: int = 1,
        order: str = "publicationDate",
        sort: str = "desc"
    ) -> Dict[str, Any]:
        """
        Search for properties using Idealista API.

        Args:
            operation: Type of operation (sale, rent)
            property_type: Type of property (homes, offices, etc.)
            location_id: Location identifier
            since_date: Filter by publication date ("Y" for last 2 days)
            max_items: Maximum items per page (max 50)
            num_page: Page number (1-indexed)
            order: Sort field
            sort: Sort direction (asc, desc)

        Returns:
            API response dictionary with keys:
            - total: Total number of results
            - elementList: List of property dictionaries
            - totalPages: Total number of pages
        """
        if location_id is None:
            location_id = settings.api.target_location_id

        params = {
            "operation": operation,
            "propertyType": property_type,
            "locationId": location_id,
            "maxItems": max_items,
            "numPage": num_page,
            "order": order,
            "sort": sort
        }

        # Add optional parameters
        if since_date:
            params["sinceDate"] = since_date

        return self._make_request("/search", params)

    def search_all_pages(
        self,
        operation: str = "sale",
        property_type: str = "homes",
        location_id: str = None,
        since_date: str = None,
        max_items: int = 50,
        order: str = "publicationDate",
        sort: str = "desc",
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for properties and automatically paginate through all results.

        Args:
            Same as search(), plus:
            max_pages: Maximum number of pages to fetch (None for all)

        Returns:
            List of all property dictionaries from all pages

        Yields:
            Tuples of (page_num, page_data) for each page
        """
        current_page = 1
        all_properties = []

        logger.info(
            "starting_paginated_search",
            operation=operation,
            location_id=location_id or settings.api.target_location_id,
            since_date=since_date
        )

        while True:
            # Check if we've reached max_pages limit
            if max_pages and current_page > max_pages:
                logger.info("Max pages limit reached", max_pages=max_pages)
                break

            # Fetch current page
            response = self.search(
                operation=operation,
                property_type=property_type,
                location_id=location_id,
                since_date=since_date,
                max_items=max_items,
                num_page=current_page,
                order=order,
                sort=sort
            )

            properties = response.get("elementList", [])
            total_pages = response.get("totalPages", 1)

            if not properties:
                logger.info("No more results", page=current_page)
                break

            # Yield page data for processing
            yield (current_page, response)

            all_properties.extend(properties)

            logger.info(
                "page_fetched",
                page=current_page,
                total_pages=total_pages,
                items=len(properties),
                cumulative_items=len(all_properties)
            )

            # Check if this was the last page
            if current_page >= total_pages:
                break

            current_page += 1

        logger.info(
            "paginated_search_complete",
            total_pages=current_page,
            total_properties=len(all_properties)
        )


# Standalone test
if __name__ == "__main__":
    import structlog
    structlog.configure(
        processors=[
            structlog.processors.JSONRenderer()
        ]
    )

    client = IdealistaClient()

    # Test single page search
    print("Testing API connection with single page search...")
    response = client.search(since_date="Y", max_items=10)
    print(f"Total results: {response.get('total')}")
    print(f"Items returned: {len(response.get('elementList', []))}")

    if response.get('elementList'):
        first_property = response['elementList'][0]
        print(f"First property: {first_property.get('propertyCode')} - €{first_property.get('price')}")
