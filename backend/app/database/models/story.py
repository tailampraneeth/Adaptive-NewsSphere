import uuid
from datetime import datetime
from sqlalchemy import Text, Numeric, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base

class Story(Base):
    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4
    )
    centroid_vector_id: Mapped[uuid.UUID] = mapped_column(
        unique=True, 
        nullable=False, 
        index=True
    )  # References Qdrant cluster centroid vector ID
    
    summary_quick: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )
    summary_beginner: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )
    summary_professional: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )
    
    confidence_score: Mapped[float] = mapped_column(
        Numeric(3, 2), 
        default=0.50
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
    articles = relationship("Article", back_populates="story")
    timelines = relationship("StoryTimeline", back_populates="story", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="story", cascade="all, delete-orphan")
