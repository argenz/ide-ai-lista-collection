"""SQLAlchemy ORM models for database tables."""

from datetime import datetime, date
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Listing(Base):
    """
    Tracks property lifecycle and activity status.

    This table maintains the lifecycle information for each property,
    including when it was first seen, last seen, and whether it's currently active.
    """

    __tablename__ = "listings"

    property_code = Column(String(20), primary_key=True, index=True)
    first_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    publication_date = Column(Date, nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    sold_or_withdrawn_at = Column(Date, nullable=True)
    republished = Column(Boolean, nullable=False, default=False)
    republished_at = Column(DateTime, nullable=True)

    # Relationship to listing details
    details = relationship(
        "ListingDetails",
        back_populates="listing",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Relationship to images
    images = relationship(
        "ListingImage",
        back_populates="listing",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Listing(property_code='{self.property_code}', is_active={self.is_active})>"


class ListingDetails(Base):
    """
    Stores current property data and price change history.

    This table contains the detailed information about each property,
    including the current price, price history, and the complete API response.
    """

    __tablename__ = "listing_details"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    property_code = Column(
        String(20),
        ForeignKey("listings.property_code", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    price = Column(Integer, nullable=False, index=True)
    previous_prices = Column(JSONB, nullable=True)
    all_fields_json = Column(JSONB, nullable=False)

    # Relationship to listing
    listing = relationship("Listing", back_populates="details")

    def __repr__(self):
        return f"<ListingDetails(property_code='{self.property_code}', price={self.price})>"


class ListingImage(Base):
    """
    Stores compressed images tagged by room type.

    Each property can have multiple images, one per tag (kitchen, bedroom, etc.).
    Images are compressed and stored in GCS.
    """

    __tablename__ = "listing_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    property_code = Column(
        String(20),
        ForeignKey("listings.property_code", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    image_tag = Column(String(50), nullable=False)
    source_url = Column(Text, nullable=False)
    local_path = Column(Text, nullable=True)
    downloaded_at = Column(DateTime, nullable=True)
    file_hash = Column(String(64), nullable=True)

    # Relationship to listing
    listing = relationship("Listing", back_populates="images")

    # Unique constraint on property_code + image_tag is defined in schema.sql

    def __repr__(self):
        return f"<ListingImage(property_code='{self.property_code}', tag='{self.image_tag}')>"


class ApiRequest(Base):
    """
    Tracks all Idealista API requests for quota monitoring and analytics.

    Records every API call including OAuth token requests and search queries.
    Used for monitoring API usage against quota limits and analyzing performance.
    """

    __tablename__ = "api_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    request_type = Column(String(50), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False)
    status_code = Column(Integer, nullable=True, index=True)
    duration_ms = Column(Integer, nullable=True)
    request_params = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    job_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<ApiRequest(type='{self.request_type}', status={self.status_code}, created_at='{self.created_at}')>"
