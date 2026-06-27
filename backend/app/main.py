import logging
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger
from app.database.connection import get_db

app = FastAPI(
    title="Adaptive NewsSphere API",
    description="AI-Powered Personalized News Intelligence Platform Backend",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Welcome endpoint for Adaptive NewsSphere API."""
    return {
        "status": "online",
        "message": "Welcome to the Adaptive NewsSphere News Intelligence Platform API.",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint verifying relational database connectivity."""
    try:
        # Run simple query to verify connection
        result = await db.execute(text("SELECT 1;"))
        result.scalar()
        return {
            "status": "healthy",
            "database": "connected",
            "services": {
                "postgres": "healthy"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )
