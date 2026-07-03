import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base

class StoryTimeline(Base):
    __tablename__ = "story_timelines"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    headline: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        default="update",
        server_default="update"
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        server_default="1.0"
    )
    supporting_articles: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1"
    )
    supporting_publishers: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1"
    )

    # Relationships
    story = relationship("Story", back_populates="timelines")
