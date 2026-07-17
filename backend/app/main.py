"""
Heimdall — FastAPI application entry point.

Registers all domain routers, configures CORS, and provides health/welcome endpoints.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.logging import logger
from app.core.config import settings
from app.database.connection import get_db

# Import routers (to be created in Phase 6)
from app.api.routes.auth import router as auth_router
from app.api.routes.feed import router as feed_router
from app.api.routes.stories import router as stories_router
from app.api.routes.bookmarks import router as bookmarks_router
from app.api.routes.search import router as search_router
from app.api.routes.publishers import router as publishers_router
from app.api.routes.internal import router as internal_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting Heimdall API v{settings.APP_VERSION}...")
    
    # Auto-initialize SQLite database schema if using SQLite
    from app.database.connection import engine
    from app.database.models.base import Base
    if "sqlite" in str(engine.url):
        logger.info("SQLite database detected. Initializing schema tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    yield
    logger.info("Heimdall API shutting down.")


app = FastAPI(
    title="Heimdall API",
    description="World News Intelligence - Consumer Edition",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS Configuration
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth_router)
app.include_router(feed_router)
app.include_router(stories_router)
app.include_router(bookmarks_router)
app.include_router(search_router)
app.include_router(publishers_router)
app.include_router(internal_router)


@app.get("/")
async def root() -> dict:
    """Welcome endpoint for Heimdall API."""
    return {
        "status": "online",
        "message": "See the World's Stories Before They Reach Everyone Else.",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Health check endpoint verifying database connectivity."""
    try:
        result = await db.execute(text("SELECT 1;"))
        result.scalar()
        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}",
        )
