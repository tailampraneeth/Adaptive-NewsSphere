import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ArticleSourceItem(BaseModel):
    id: uuid.UUID
    title: str
    publish_date: Optional[datetime]
    source_url: Optional[str]
    canonical_url: Optional[str] = None
    author: Optional[str] = None
    publisher_name: str
    credibility_score: float
    body_text: Optional[str] = None

    class Config:
        from_attributes = True


class TimelineMilestoneItem(BaseModel):
    id: uuid.UUID
    event_timestamp: datetime
    headline: str
    description: str
    importance_weight: float
    event_type: str

    class Config:
        from_attributes = True


class RelatedStoryItem(BaseModel):
    id: uuid.UUID
    title: str
    importance_score: float
    trending_score: float
    predicted_category: str
    last_updated_at: datetime
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class StoryDetailResponse(BaseModel):
    id: uuid.UUID
    title: str
    summary: Optional[str]
    ai_summary: Optional[str] = None
    ai_summary_at: Optional[datetime] = None
    importance_score: float
    trending_score: float
    credibility_score: Optional[float] = None
    verification_score: Optional[float] = None
    has_conflicts: bool
    publisher_diversity: int
    article_count: int
    last_updated_at: Optional[datetime]
    region_tags: Optional[List[str]] = None
    
    articles: List[ArticleSourceItem] = []
    timelines: List[TimelineMilestoneItem] = []
    related_stories: List[RelatedStoryItem] = []
    
    evidence: Optional[List[Dict[str, Any]]] = None
    verification_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
