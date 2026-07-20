from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import String, Numeric, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base


class PublisherSourceType(str, Enum):
    NEWSWIRE = "NEWSWIRE"
    PRIMARY_SOURCE = "PRIMARY_SOURCE"
    LOCAL_NEWS = "LOCAL_NEWS"
    INTERNATIONAL = "INTERNATIONAL"
    GOVERNMENT = "GOVERNMENT"
    RESEARCH = "RESEARCH"
    TECH_MEDIA = "TECH_MEDIA"
    FINANCIAL = "FINANCIAL"


class Publisher(Base):
    __tablename__ = "publishers"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True
    )  # e.g., 'bbc', 'reuters'
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    base_url: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    rss_url: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    credibility_score: Mapped[float] = mapped_column(
        Numeric(3, 2),
        default=1.00
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        default=PublisherSourceType.LOCAL_NEWS.value,
        server_default=PublisherSourceType.LOCAL_NEWS.value
    )

    # Feed quality & health monitoring fields
    successful_fetches: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=0,
        nullable=True
    )
    failed_fetches: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=0,
        nullable=True
    )
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    articles = relationship("Article", back_populates="publisher", cascade="all, delete-orphan")
