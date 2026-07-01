"""
Adaptive NewsSphere — FastAPI application entry point.

Registers all domain routers and provides base health/status endpoints.

API structure:
  GET  /            — Welcome message and version info
  GET  /health      — Postgres connectivity health check
  GET  /api/v1/metrics       — Pipeline performance statistics
  POST /api/v1/metrics/reset — Reset metrics (dev/testing only)
"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.logging import logger
from app.database.connection import get_db
from app.api.routes.metrics import router as metrics_router

app = FastAPI(
    title="Adaptive NewsSphere API",
    description="AI-Powered Personalized News Intelligence Platform Backend",
    version="2.0.0",
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(metrics_router)


# ── Base Endpoints ────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> dict:
    """Welcome endpoint for Adaptive NewsSphere API."""
    return {
        "status": "online",
        "message": "Welcome to the Adaptive NewsSphere News Intelligence Platform API.",
        "version": "2.0.0",
        "docs": "/docs",
        "metrics": "/api/v1/metrics",
    }


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Health check endpoint verifying relational database connectivity."""
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
