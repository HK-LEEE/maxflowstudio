"""
Health check endpoints
"""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.core.database import get_db

router = APIRouter()
settings = get_settings()


@router.get("/")
async def health_check() -> Dict[str, str]:
    """Basic health check."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """Readiness check including database connectivity."""
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ready" if db_status == "connected" else "not ready",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }