"""
Adaptive NewsSphere — FastAPI application entry point.

Registers all domain routers and provides base health/status endpoints.

API structure:
  GET  /                              — Welcome message and version info
  GET  /health                        — Postgres + Redis + Qdrant health check
  GET  /api/v1/metrics                — Pipeline performance statistics
  POST /api/v1/metrics/reset          — Reset metrics (dev/testing only)
  GET  /api/v1/feed/{user_id}         — Personalized ranked news feed
  POST /api/v1/feed/interact          — Record user interaction
  GET  /api/v1/feed/{user_id}/profile/health — Profile diagnostics
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.logging import logger
from app.database.connection import get_db
from app.api.routes.metrics import router as metrics_router
from app.api.routes.feed import router as feed_router
from app.api.routes.chat import router as chat_router
from app.api.routes.auth import router as auth_router
from app.api.routes.stories import router as stories_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Startup: hydrates Redis preference cache from PostgreSQL so that
    returning users get sub-millisecond preference vector lookups
    from the first request after a server restart.
    If DEMO_MODE is enabled and database is unseeded, auto-seeds mock data.
    """
    logger.info("Starting Adaptive NewsSphere API v3.0.0...")
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        from app.database.connection import AsyncSessionLocal
        from app.services.vector_store import VectorStoreService
        from app.services.preference_engine import PreferenceEngineService
        from sqlalchemy.future import select
        from sqlalchemy import func
        from app.database.models.story import Story

        # Auto-seed if DEMO_MODE is True and database is empty/under-seeded
        if settings.DEMO_MODE:
            should_seed = False
            async with AsyncSessionLocal() as db:
                stmt = select(func.count()).select_from(Story)
                res = await db.execute(stmt)
                count = res.scalar() or 0
                if count < 50:
                    should_seed = True

            if should_seed:
                logger.info("DEMO_MODE is True and database is unseeded. Running auto-seeding...")
                from scripts.seed_demo_data import seed_demo_mode_data
                await seed_demo_mode_data()
                logger.info("Auto-seeding of demo dataset completed successfully.")

        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
        vector_store = VectorStoreService()

        async with AsyncSessionLocal() as db:
            engine = PreferenceEngineService(
                db_session=db,
                vector_store=vector_store,
                redis_client=redis_client,
            )
            count = await engine.hydrate_redis_from_postgres()
            logger.info(f"Redis hydrated with {count} user preference vector IDs.")

        await redis_client.aclose()
    except Exception as e:
        logger.warning(f"Lifespan initialization error: {e}")

    yield

    logger.info("Adaptive NewsSphere API shutting down.")


app = FastAPI(
    title="Adaptive NewsSphere API",
    description="AI-Powered Personalized News Intelligence Platform Backend",
    version="4.0.0",
    lifespan=lifespan,
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(metrics_router)
app.include_router(feed_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(stories_router)


# ── Base Endpoints ────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> dict:
    """Welcome endpoint for Adaptive NewsSphere API."""
    return {
        "status": "online",
        "message": "Welcome to the Adaptive NewsSphere News Intelligence Platform API.",
        "version": "4.0.0",
        "docs": "/docs",
        "endpoints": {
            "metrics": "/api/v1/metrics",
            "feed": "/api/v1/feed/{user_id}",
            "interact": "/api/v1/feed/interact",
            "profile_health": "/api/v1/feed/{user_id}/profile/health",
            "chat": "/api/v1/chat/sessions",
            "chat_health": "/api/v1/chat/health",
            "auth_signup": "/api/v1/auth/signup",
            "auth_login": "/api/v1/auth/login"
        },
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
            "services": {
                "postgres": "healthy",
            },
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}",
        )
