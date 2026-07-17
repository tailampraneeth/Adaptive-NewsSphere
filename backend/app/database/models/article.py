"""
Article SQLAlchemy model for Heimdall Consumer Edition.

An Article represents a single news piece ingested from an RSS feed.
Compared to the enterprise version:
  - Removed: qdrant_point_id, duplicate_type, quality_score, word_count, character_count
  - Added: canonical_url, region
  - Removed relationships: interactions, duplicates_as_original, duplicates_as_duplicate
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, func, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    story_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("stories.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    publisher_id: Mapped[str] = mapped_column(
        ForeignKey("publishers.id"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    body_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    author: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    source_url: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        index=True
    )
    # Resolved, validated canonical URL without redirects
    canonical_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        index=True
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # ── Ingestion Metadata Fields ─────────────────────────────────────────────
    language: Mapped[str] = mapped_column(
        String(10),
        default="en"
    )
    # Original category from RSS feed (often missing)
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    # Auto-assigned category from CategoryClassifierService (keyword-only)
    predicted_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    # Classifier confidence score (0.0 = keyword fallback)
    category_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True
    )
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True
    )  # JSONB array representation on PostgreSQL
    region: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # ── Hash Values for Deduplication ────────────────────────────────────────
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True
    )  # SHA-256 of cleaned body content
    article_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False
    )  # SHA-256 of title + cleaned body content

    # ── NLP & Metadata ────────────────────────────────────────────────────────
    subtitle: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    # Estimated reading time in minutes, computed once at ingestion
    reading_time: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    keywords: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True
    )
    named_entities: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )
    topics: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True
    )

    fetch_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    story = relationship("Story", back_populates="articles", foreign_keys="[Article.story_id]")
    publisher = relationship("Publisher", back_populates="articles")
