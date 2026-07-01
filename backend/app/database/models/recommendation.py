import uuid
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models.base import Base

class UserRecommendationLog(Base):
    """Tracks recommended stories served to users for feedback loops and metrics."""
    __tablename__ = "user_recommendation_logs"

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

    score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False
    )  # Recommendation score calculated by ranker
    recommendation_reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )  # e.g., "Recommended because you read tech"

    clicked: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
