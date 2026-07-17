import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Integer, String, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base


class ReadingHistory(Base):
    __tablename__ = "reading_history"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True
    )
    read_pct: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    dwell_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    # read | finish | bookmark | share | hide | skip
    interaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="reading_history")
    story = relationship("Story", back_populates="reading_history")

    __table_args__ = (
        UniqueConstraint("user_id", "story_id", name="uq_user_story_reading_history"),
    )
