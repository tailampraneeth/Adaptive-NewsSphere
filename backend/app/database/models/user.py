import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # ── Milestone 4: Recommendation Engine ───────────────────────────────────
    # Qdrant point ID for this user's preference embedding.
    # The raw 384-dim vector lives in Qdrant; this is the lookup key.
    preference_vector_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True
    )
    # Running total of all interactions — determines cold-start vs warm status.
    interaction_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False
    )
    # Hashed password for authentication. Nullable to prevent breaking seeded dev users.
    hashed_password: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    # Timestamp of the last feed request served to this user.
    last_feed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    interactions = relationship("UserInteraction", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    recommendation_logs = relationship("UserRecommendationLog", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
