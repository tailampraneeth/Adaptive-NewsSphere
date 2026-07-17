from typing import List, Optional
from pydantic import BaseModel
from app.api.schemas.feed import FeedItem


class SearchResponse(BaseModel):
    results: List[FeedItem]
