import uuid
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database.connection import get_db
from app.database.models.user import User
from app.database.models.bookmark import Bookmark
from app.database.models.story import Story
from app.database.models.article import Article
from app.api.schemas.bookmarks import BookmarkItem
from app.api.dependencies import get_current_user
from app.api.routes.feed import get_story_image_url

router = APIRouter(prefix="/api/v1/bookmarks", tags=["Bookmarks"])


@router.get("", response_model=List[BookmarkItem])
async def list_bookmarks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists all story bookmarks saved by the current authenticated user."""
    stmt = (
        select(Bookmark)
        .options(selectinload(Bookmark.story).selectinload(Story.articles))
        .where(Bookmark.user_id == current_user.id)
        .order_by(Bookmark.bookmarked_at.desc())
    )
    res = await db.execute(stmt)
    bookmarks = res.scalars().all()

    results = []
    for b in bookmarks:
        if b.story:
            results.append(
                BookmarkItem(
                    story_id=b.story_id,
                    title=b.story.title or "Untitled News Update",
                    predicted_category=b.story.predicted_category or "World",
                    bookmarked_at=b.bookmarked_at,
                    image_url=get_story_image_url(b.story)
                )
            )
    return results


@router.post("/{story_id}", status_code=status.HTTP_201_CREATED)
async def add_bookmark(
    story_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Adds a story to the user's bookmarks. Returns 409 conflict if already bookmarked."""
    story_check = await db.execute(select(Story).where(Story.id == story_id))
    story = story_check.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    bookmark_check = await db.execute(
        select(Bookmark).where(Bookmark.user_id == current_user.id, Bookmark.story_id == story_id)
    )
    if bookmark_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Story is already bookmarked."
        )

    bookmark = Bookmark(user_id=current_user.id, story_id=story_id, bookmarked_at=datetime.now(timezone.utc))
    db.add(bookmark)
    await db.commit()
    return {"status": "success"}


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark(
    story_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Removes a story from the user's bookmarks."""
    bookmark_stmt = select(Bookmark).where(
        Bookmark.user_id == current_user.id, Bookmark.story_id == story_id
    )
    bookmark_res = await db.execute(bookmark_stmt)
    bookmark = bookmark_res.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")

    await db.delete(bookmark)
    await db.commit()
    return
