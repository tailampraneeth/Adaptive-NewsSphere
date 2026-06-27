import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base

class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4
    )
    story_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("stories.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    publisher_id: Mapped[str] = mapped_column(
        ForeignKey("publishers.id"), 
        nullable=False
    )
    
    title: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    body_text: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )
    author: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True
    )
    source_url: Mapped[str] = mapped_column(
        String(512), 
        unique=True, 
        nullable=False,
        index=True
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )

    # Ingestion Metadata Fields
    language: Mapped[str] = mapped_column(
        String(10), 
        default="en"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(512), 
        nullable=True
    )
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON, 
        nullable=True
    )  # JSONB array representation on PostgreSQL

    # Hash values for deduplication and version control
    content_hash: Mapped[str] = mapped_column(
        String(64), 
        nullable=False, 
        index=True
    )  # SHA-256 of cleaned body content
    article_hash: Mapped[str] = mapped_column(
        String(64), 
        unique=True, 
        nullable=False
    )  # SHA-256 of title + cleaned body content
    
    fetch_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )

    # Relationships
    story = relationship("Story", back_populates="articles")
    publisher = relationship("Publisher", back_populates="articles")
    interactions = relationship("UserInteraction", back_populates="article", cascade="all, delete-orphan")
