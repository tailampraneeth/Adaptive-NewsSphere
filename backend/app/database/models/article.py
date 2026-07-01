"""
Article SQLAlchemy model.

An Article represents a single news piece ingested from an RSS feed.
Each article is deduped (content_hash, article_hash), NLP-enriched
(keywords, named_entities, topics), semantically embedded (qdrant_point_id),
and then clustered into a Story.

New in M2 Final Review:
- `predicted_category`: auto-assigned category from CategoryClassifierService
- `category_confidence`: classifier confidence score (0.0–1.0)
- `duplicate_type`: classification of the duplicate relationship if applicable
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, func, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base


class Article(Base):
    """
    Represents a single ingested news article.

    Deduplication strategy:
      1. source_url unique constraint (same URL = exact same article)
      2. article_hash (SHA-256 of title + cleaned body) — catches republished content
      3. content_hash (SHA-256 of cleaned body) — catches re-titled copies

    NLP enrichment (populated by enrich_articles.py):
      - keywords: KeyBERT top-5 keyphrases
      - named_entities: spaCy PERSON / ORG / GPE entities
      - topics: frequency-based noun-chunk topics

    Category classification (populated by classify_categories.py):
      - category: original category from RSS feed (if provided)
      - predicted_category: auto-assigned via CategoryClassifierService
      - category_confidence: classifier confidence (0.0–1.0)
    """

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
    # Auto-assigned category from CategoryClassifierService (embedding + keyword fallback)
    predicted_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    # Classifier confidence score (0.0 = keyword fallback, 1.0 = high embedding confidence)
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

    # Classification of duplicate relationship (populated by ClusteringService)
    # Values: EXACT_DUPLICATE, SEMANTIC_DUPLICATE, UPDATED_ARTICLE, CORRECTED_ARTICLE
    duplicate_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )

    # Quality score tracking for ranking and recommendations
    quality_score: Mapped[float] = mapped_column(
        Float,
        default=1.00,
        nullable=False,
        server_default='1.00'
    )

    # ── NLP & Qdrant Fields ──────────────────────────────────────────────────
    subtitle: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    reading_time: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    word_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    character_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    qdrant_point_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True
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
    interactions = relationship("UserInteraction", back_populates="article", cascade="all, delete-orphan")
    duplicates_as_original = relationship(
        "ArticleDuplicate",
        foreign_keys="ArticleDuplicate.original_article_id",
        back_populates="original_article",
        cascade="all, delete-orphan"
    )
    duplicates_as_duplicate = relationship(
        "ArticleDuplicate",
        foreign_keys="ArticleDuplicate.duplicate_article_id",
        back_populates="duplicate_article",
        cascade="all, delete-orphan"
    )
