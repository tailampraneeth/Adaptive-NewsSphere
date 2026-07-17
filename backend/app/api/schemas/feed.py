import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FeedItem(BaseModel):
    story_id: uuid.UUID
    title: str
    summary: str
    predicted_category: str
    importance_score: float
    trending_score: float
    last_updated_at: datetime
    publisher_diversity: int
    article_count: int
    has_conflicts: bool
    explanation: str
    score: float
    verification_label: str
    verification_color: str
    verification_icon: str
    image_url: Optional[str] = None


class FeedResponse(BaseModel):
    results: List[FeedItem]
    next_cursor: Optional[str] = None


class InteractionPayload(BaseModel):
    story_id: uuid.UUID
    interaction_type: str = Field(..., description="read | finish | bookmark | share | hide | skip")
    read_pct: int = Field(default=0, ge=0, le=100)
    dwell_seconds: int = Field(default=0, ge=0)
