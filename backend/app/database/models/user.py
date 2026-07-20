"""
User model for Heimdall Consumer Edition.

Replaces the enterprise User model. Drops:
  - preference_vector_id (Qdrant removed)
  - interaction_count (replaced by reading_history table)
  - relationships to enterprise models (chat_sessions, profile, interactions)

Adds:
  - name, country, state, city (onboarding & region personalization)
  - theme (dark/light/system)
  - preferred_categories, preferred_publishers (positive signals)
  - hidden_categories, hidden_publishers (negative filters)
  - onboarding_complete (gates onboarding redirect)
  - brief_time (daily brief window preference)
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, func, JSON
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
    hashed_password: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    # ── Profile ───────────────────────────────────────────────────────────────
    name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # ── Appearance ────────────────────────────────────────────────────────────
    # dark | light | system
    theme: Mapped[str] = mapped_column(
        String(20),
        default="dark",
        server_default="dark",
        nullable=False
    )

    # ── Personalization Preferences ───────────────────────────────────────────
    # Positive interest filters stored as JSON arrays
    preferred_categories: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    preferred_publishers: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    # Negative filters (mute)
    hidden_categories: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    hidden_publishers: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )

    # ── Onboarding ────────────────────────────────────────────────────────────
    onboarding_complete: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False
    )

    # ── Daily Brief ───────────────────────────────────────────────────────────
    # morning (06-12) | afternoon (12-18) | evening (18-00)
    brief_time: Mapped[str] = mapped_column(
        String(20),
        default="morning",
        server_default="morning",
        nullable=False
    )

    # ── Reset Password ────────────────────────────────────────────────────────
    reset_token_hash: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True
    )
    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    bookmarks = relationship(
        "Bookmark",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    reading_history = relationship(
        "ReadingHistory",
        back_populates="user",
        cascade="all, delete-orphan"
    )
