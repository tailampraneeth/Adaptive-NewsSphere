"""
ArticleDuplicate SQLAlchemy model.

Tracks provenance of duplicate article relationships with typed classification.
Each record explains WHY two articles are considered duplicates and provides
the similarity evidence.

Duplicate types:
  EXACT_DUPLICATE    — same content_hash (identical cleaned body text)
  SEMANTIC_DUPLICATE — cosine similarity > 0.95 in the same story cluster
  UPDATED_ARTICLE    — same source_url, newer version (future: RSS update detection)
  CORRECTED_ARTICLE  — same publisher, similar topic, divergent conclusion (future)
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base


class ArticleDuplicate(Base):
    """
    Provenance record linking two articles in a duplicate relationship.

    This table enables:
      - Audit trails for duplicate detection decisions
      - Downstream explainability ("this article was skipped because...")
      - Future deduplication quality analysis
    """

    __tablename__ = "article_duplicates"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )

    # The original (canonical) article
    original_article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # The duplicate article (the one being classified as a copy)
    duplicate_article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Duplicate classification: EXACT_DUPLICATE | SEMANTIC_DUPLICATE |
    # UPDATED_ARTICLE | CORRECTED_ARTICLE
    duplicate_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    # Cosine similarity score at the time of detection (0.0 for exact duplicates)
    similarity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    original_article = relationship(
        "Article",
        foreign_keys=[original_article_id],
        back_populates="duplicates_as_original"
    )
    duplicate_article = relationship(
        "Article",
        foreign_keys=[duplicate_article_id],
        back_populates="duplicates_as_duplicate"
    )
