"""
Story and StoryRelation SQLAlchemy models.

`Story` represents a clustered group of semantically related articles covering
the same real-world event. The centroid_vector_id links to the Qdrant "stories"
collection, which stores the running-average centroid embedding for the cluster.

New in M2 Final Review:
- `title`: centroid-nearest article headline (deterministic representative title)
- `importance_score`: weighted composite score (article count, publisher diversity, freshness)
- `trending_score`: time-decay score for home-feed ranking
- `formation_evidence`: structured JSON explaining why articles belong together (XAI)
- Reserved fields for Milestone 3: verification_score, credibility_score,
  first_reported_at, last_updated_at
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Text, Numeric, DateTime, func, String, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base


class StoryRelationType(str, Enum):
    RELATED = "RELATED"
    FOLLOW_UP = "FOLLOW_UP"
    CAUSES = "CAUSES"
    MERGED_FROM = "MERGED_FROM"
    SPLIT_FROM = "SPLIT_FROM"
    CONTRADICTS = "CONTRADICTS"


class StoryRelation(Base):
    """Junction table for self-referencing story relationships (e.g., 'follow-up', 'related')."""

    __tablename__ = "story_relations"

    parent_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        primary_key=True
    )
    child_story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        primary_key=True
    )
    relation_type: Mapped[str] = mapped_column(
        String(50),
        default=StoryRelationType.RELATED.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class Story(Base):
    """
    A Story is the central aggregation unit — a cluster of semantically related
    articles covering the same real-world event.

    Lifecycle:
      ACTIVE  → story is alive and accepting new articles
      MERGED  → story was folded into another story
      ARCHIVED → story is too old or became inactive
    """

    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    centroid_vector_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        unique=True,
        nullable=True,
        index=True
    )  # References Qdrant cluster centroid vector ID (string to support string UUIDs)

    # Representative headline — title of the article closest to centroid embedding
    title: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True
    )

    # Generic story summary (deterministic representation from longest article)
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Adaptive summaries for different user expertise levels (populated in Milestone 3+)
    summary_quick: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    summary_beginner: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    summary_professional: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Story lifecycle state
    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE"  # ACTIVE, MERGED, ARCHIVED
    )

    # Semantic clustering quality (mean similarity of member articles to centroid)
    confidence_score: Mapped[float] = mapped_column(
        Numeric(3, 2),
        default=1.00
    )
    article_count: Mapped[int] = mapped_column(
        Integer,
        default=1
    )

    # ── Scoring Signals ─────────────────────────────────────────────────────────
    # Composite importance signal for recommendation ranking (0.0–1.0)
    importance_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )
    # Recency + growth-rate trending signal for home feed ranking (0.0–1.0)
    trending_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )

    # ── Explainable AI Evidence & RAG Context ──────────────────────────────────
    # Structured metadata explaining why articles were clustered together
    # Schema: { shared_keywords, shared_entities, shared_topics,
    #           avg_similarity_score, min_similarity_score,
    #           article_count, publisher_count }
    formation_evidence: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )

    # Exposes a structured context object for future Retrieval-Augmented Generation (RAG)
    # Schema: { representative_article: { id, title, body_text, publisher },
    #           summary, keywords: [], named_entities: {}, topics: [] }
    rag_context: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )

    # List of structured evidence mappings for multi-source verification
    evidence: Mapped[Optional[list[dict]]] = mapped_column(
        JSON,
        nullable=True
    )

    # Structured metadata explaining the fact-check verification score
    # Schema: { agreement_score, publisher_diversity, trusted_publishers,
    #           supporting_articles, conflicting_articles, semantic_confidence }
    verification_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )

    # Flag denoting if numeric/factual conflict exists between source articles
    has_conflicts: Mapped[bool] = mapped_column(
        default=False,
        server_default="false"
    )

    # Centroid-nearest representative article link
    representative_article_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL", use_alter=True, name="fk_stories_representative_article"),
        nullable=True
    )

    # Cached count of unique publishers contributing to this story cluster
    publisher_diversity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        server_default='1'
    )

    # ── Milestone 3 Reserved Fields ───────────────────────────────────────────
    # These fields are intentionally left NULL. They will be populated in Milestone 3
    # when story verification, credibility analysis, and timeline generation are implemented.

    # Aggregate fact-check score (0.0–1.0) — reserved for Milestone 3
    verification_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=None
    )
    # Weighted mean of member publishers' credibility scores — reserved for Milestone 3
    credibility_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=None
    )
    # Earliest article publish timestamp within the cluster — reserved for Milestone 3
    first_reported_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    # Most recent article publish timestamp within the cluster — reserved for Milestone 3
    last_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True
    )

    # Relationships
    articles = relationship("Article", back_populates="story", foreign_keys="[Article.story_id]")
    representative_article = relationship("Article", foreign_keys="[Story.representative_article_id]")
    timelines = relationship("StoryTimeline", back_populates="story", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="story", cascade="all, delete-orphan")

    # Future-proof self-referencing relationship mapping
    related_stories = relationship(
        "Story",
        secondary="story_relations",
        primaryjoin="Story.id==StoryRelation.parent_story_id",
        secondaryjoin="Story.id==StoryRelation.child_story_id",
        backref="parent_stories"
    )
