import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BookmarkItem(BaseModel):
    story_id: uuid.UUID
    title: str
    predicted_category: str
    bookmarked_at: datetime
    image_url: Optional[str] = None


class BookmarkCreate(BaseModel):
    story_id: uuid.UUID
