from datetime import datetime
import uuid
from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base

class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id: Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True, 
        autoincrement=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    interaction_type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # e.g., 'click', 'bookmark', 'share', 'dwell'
    dwell_seconds: Mapped[int] = mapped_column(
        Integer, 
        default=0
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        index=True
    )

    # Relationships
    user = relationship("User", back_populates="interactions")
    article = relationship("Article", back_populates="interactions")
