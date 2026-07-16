import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ArticleSourceItem(BaseModel):
    id: uuid.UUID
    title: str
    publish_date: Optional[datetime]
    source_url: Optional[str]
    author: Optional[str]
    publisher_name: str
    credibility_score: float

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

    class Config:
        from_attributes = True


class StoryDetailResponse(BaseModel):
    id: uuid.UUID
    title: str
    summary: Optional[str]
    summary_quick: Optional[str]
    summary_beginner: Optional[str]
    summary_professional: Optional[str]
    importance_score: float
    trending_score: float
    credibility_score: Optional[float]
    verification_score: Optional[float]
    has_conflicts: bool
    publisher_diversity: int
    article_count: int
    last_updated_at: Optional[datetime]
    
    # Nested lists
    articles: List[ArticleSourceItem] = []
    timelines: List[TimelineMilestoneItem] = []
    related_stories: List[RelatedStoryItem] = []
    
    # Verification JSONs
    evidence: Optional[List[Dict[str, Any]]] = None
    verification_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
