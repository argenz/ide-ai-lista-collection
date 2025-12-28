"""
Google Cloud Storage operations for raw API responses and metadata.
"""
import json
import os
from datetime import date, datetime
from typing import Any, Dict, Optional

import structlog
from google.cloud import storage

logger = structlog.get_logger(__name__)


class GCSStorageClient:
    """Client for managing raw API responses and metadata in GCS."""

    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize GCS client.

        Args:
            bucket_name: GCS bucket name (defaults to GCS_BUCKET_NAME env var)
        """
        self.bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET_NAME must be set")

        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)

        logger.info("gcs_client_initialized", bucket_name=self.bucket_name)

    def upload_raw_response(
        self, collection_date: date, page_num: int, data: Dict[str, Any], job_type: str = "new_listings"
    ) -> str:
        """
        Upload raw API response to GCS.

        Path structure: raw_responses/YYYY-MM-DD/job_type_pN.json

        Args:
            collection_date: Date of collection
            page_num: Page number (1-indexed)
            data: Raw API response data
            job_type: Type of collection job (new_listings, full_scan, etc.)

        Returns:
            GCS blob path
        """
        date_str = collection_date.strftime("%Y-%m-%d")
        blob_path = f"raw_responses/{date_str}/{job_type}_p{page_num}.json"

        try:
            blob = self.bucket.blob(blob_path)
            content = json.dumps(data, ensure_ascii=False, indent=2)
            blob.upload_from_string(content, content_type="application/json")

            logger.info(
                "raw_response_uploaded",
                blob_path=blob_path,
                page_num=page_num,
                total_listings=data.get("total", 0),
                size_bytes=len(content),
            )

            return blob_path

        except Exception as e:
            logger.error(
                "raw_response_upload_failed", blob_path=blob_path, error=str(e), exc_info=True
            )
            raise

    def download_raw_response(
        self, collection_date: date, page_num: int, job_type: str = "new_listings"
    ) -> Optional[Dict[str, Any]]:
        """
        Download raw API response from GCS.

        Args:
            collection_date: Date of collection
            page_num: Page number (1-indexed)
            job_type: Type of collection job

        Returns:
            Raw API response data or None if not found
        """
        date_str = collection_date.strftime("%Y-%m-%d")
        blob_path = f"raw_responses/{date_str}/{job_type}_p{page_num}.json"

        try:
            blob = self.bucket.blob(blob_path)

            if not blob.exists():
                logger.warning("raw_response_not_found", blob_path=blob_path)
                return None

            content = blob.download_as_string()
            data = json.loads(content)

            logger.info("raw_response_downloaded", blob_path=blob_path, size_bytes=len(content))

            return data

        except Exception as e:
            logger.error(
                "raw_response_download_failed", blob_path=blob_path, error=str(e), exc_info=True
            )
            raise

    def upload_metadata(
        self, collection_date: date, metadata: Dict[str, Any], job_type: str = "new_listings"
    ) -> str:
        """
        Upload job metadata to GCS.

        Path structure: raw_responses/YYYY-MM-DD/job_type_meta.json

        Metadata should include:
        - total_listings: Total number of listings processed
        - total_pages: Number of API pages fetched
        - execution_time: Job execution time in seconds
        - timestamp: ISO timestamp of job completion
        - job_id: Unique job identifier
        - new_count: Number of new listings
        - updated_count: Number of updated listings
        - error_count: Number of errors encountered

        Args:
            collection_date: Date of collection
            metadata: Job execution metadata
            job_type: Type of collection job

        Returns:
            GCS blob path
        """
        date_str = collection_date.strftime("%Y-%m-%d")
        blob_path = f"raw_responses/{date_str}/{job_type}_meta.json"

        try:
            # Add timestamp if not present
            if "timestamp" not in metadata:
                metadata["timestamp"] = datetime.utcnow().isoformat()

            blob = self.bucket.blob(blob_path)
            content = json.dumps(metadata, ensure_ascii=False, indent=2)
            blob.upload_from_string(content, content_type="application/json")

            logger.info(
                "metadata_uploaded",
                blob_path=blob_path,
                total_listings=metadata.get("total_listings", 0),
                execution_time=metadata.get("execution_time", 0),
            )

            return blob_path

        except Exception as e:
            logger.error("metadata_upload_failed", blob_path=blob_path, error=str(e), exc_info=True)
            raise

    def download_metadata(
        self, collection_date: date, job_type: str = "new_listings"
    ) -> Optional[Dict[str, Any]]:
        """
        Download job metadata from GCS.

        Args:
            collection_date: Date of collection
            job_type: Type of collection job

        Returns:
            Job metadata or None if not found
        """
        date_str = collection_date.strftime("%Y-%m-%d")
        blob_path = f"raw_responses/{date_str}/{job_type}_meta.json"

        try:
            blob = self.bucket.blob(blob_path)

            if not blob.exists():
                logger.warning("metadata_not_found", blob_path=blob_path)
                return None

            content = blob.download_as_string()
            metadata = json.loads(content)

            logger.info("metadata_downloaded", blob_path=blob_path)

            return metadata

        except Exception as e:
            logger.error("metadata_download_failed", blob_path=blob_path, error=str(e), exc_info=True)
            raise

    def list_raw_responses(
        self, collection_date: Optional[date] = None, job_type: Optional[str] = None
    ) -> list[str]:
        """
        List all raw response files in GCS.

        Args:
            collection_date: Optional date filter
            job_type: Optional job type filter

        Returns:
            List of blob paths
        """
        prefix = "raw_responses/"

        if collection_date:
            date_str = collection_date.strftime("%Y-%m-%d")
            prefix = f"raw_responses/{date_str}/"

        try:
            blobs = self.bucket.list_blobs(prefix=prefix)
            blob_paths = []

            for blob in blobs:
                # Skip if job_type filter is set and doesn't match
                if job_type and f"/{job_type}_" not in blob.name:
                    continue

                # Skip metadata files
                if not blob.name.endswith("_meta.json"):
                    blob_paths.append(blob.name)

            logger.info(
                "raw_responses_listed",
                count=len(blob_paths),
                collection_date=collection_date,
                job_type=job_type,
            )

            return blob_paths

        except Exception as e:
            logger.error("list_raw_responses_failed", prefix=prefix, error=str(e), exc_info=True)
            raise

    def delete_old_responses(self, days_to_keep: int = 365) -> int:
        """
        Delete raw responses older than specified days.

        This is a manual cleanup function. Normally lifecycle rules handle this.

        Args:
            days_to_keep: Number of days to retain

        Returns:
            Number of blobs deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        try:
            blobs = self.bucket.list_blobs(prefix="raw_responses/")
            deleted_count = 0

            for blob in blobs:
                if blob.time_created and blob.time_created < cutoff_date:
                    blob.delete()
                    deleted_count += 1

            logger.info("old_responses_deleted", deleted_count=deleted_count, days_to_keep=days_to_keep)

            return deleted_count

        except Exception as e:
            logger.error("delete_old_responses_failed", error=str(e), exc_info=True)
            raise


# Singleton instance
_gcs_client: Optional[GCSStorageClient] = None


def get_gcs_client() -> GCSStorageClient:
    """
    Get or create GCS client singleton.

    Returns:
        GCSStorageClient instance
    """
    global _gcs_client

    if _gcs_client is None:
        _gcs_client = GCSStorageClient()

    return _gcs_client


# Convenience functions for backward compatibility


def upload_raw_response(
    collection_date: date, page_num: int, data: Dict[str, Any], job_type: str = "new_listings"
) -> str:
    """Upload raw API response to GCS."""
    client = get_gcs_client()
    return client.upload_raw_response(collection_date, page_num, data, job_type)


def download_raw_response(
    collection_date: date, page_num: int, job_type: str = "new_listings"
) -> Optional[Dict[str, Any]]:
    """Download raw API response from GCS."""
    client = get_gcs_client()
    return client.download_raw_response(collection_date, page_num, job_type)


def upload_metadata(
    collection_date: date, metadata: Dict[str, Any], job_type: str = "new_listings"
) -> str:
    """Upload job metadata to GCS."""
    client = get_gcs_client()
    return client.upload_metadata(collection_date, metadata, job_type)


def download_metadata(
    collection_date: date, job_type: str = "new_listings"
) -> Optional[Dict[str, Any]]:
    """Download job metadata from GCS."""
    client = get_gcs_client()
    return client.download_metadata(collection_date, job_type)
