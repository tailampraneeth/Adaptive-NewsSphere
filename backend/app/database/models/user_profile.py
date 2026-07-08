"""
UserProfile model — Milestone 4: Recommendation Engine.

Stores recommendation metadata for each user in PostgreSQL.

Architecture Decision:
  The raw 384-dimensional preference embedding lives ONLY in Qdrant
  ("user_preferences" collection). This table stores only the pointer
  (preference_vector_id) and lightweight metadata — following the exact
  same pattern used for Story centroid vectors since Milestone 2.

  Data flow:
    Interaction → PreferenceEngineService → Qdrant (vector)
                                          → Redis  (hot cache: vector ID)
                                          → PostgreSQL (this table: metadata only)
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base


class UserProfile(Base):
    """
    Persistent profile metadata for a user's recommendation state.

    Qdrant holds the preference vector itself. This model holds:
      - The Qdrant point ID to retrieve it
      - Mute lists for negative feedback
      - Interaction count mirror for cold-start detection
    """

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Qdrant point ID — used to fetch the 384-dim preference vector.
    # NULL means the user has never interacted (cold-start).
    preference_vector_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True
    )

    # Mirror of User.interaction_count — kept in sync by PreferenceEngineService.
    # Stored here so analytics queries don't need a join to the users table.
    interaction_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False
    )

    # Categories the user has explicitly muted via negative feedback.
    # Schema: ["Sports", "Entertainment"]
    muted_categories: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        nullable=True
    )

    # Publisher IDs the user has explicitly muted via negative feedback.
    # Schema: ["reuters", "fox-news"]
    muted_publishers: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        nullable=True
    )

    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # ── Profile Drift & Rebuild Metadata (Refinement Pass) ────────────────────
    profile_age_days: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False
    )
    last_profile_decay: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    last_profile_rebuild: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    last_profile_update: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="profile")
