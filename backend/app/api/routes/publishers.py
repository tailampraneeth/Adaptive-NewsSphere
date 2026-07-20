from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from app.database.connection import get_db
from app.database.models.publisher import Publisher

router = APIRouter(prefix="/api/v1/publishers", tags=["Publishers"])


class PublisherItem(BaseModel):
    id: str
    name: str
    base_url: str
    rss_url: str
    credibility_score: float
    source_type: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[PublisherItem])
async def list_publishers(db: AsyncSession = Depends(get_db)):
    """Lists all registered RSS publishers on the Heimdall platform."""
    res = await db.execute(select(Publisher).order_by(Publisher.name.asc()))
    publishers = res.scalars().all()
    return publishers
