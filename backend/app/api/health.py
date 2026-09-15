import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis

from backend.app.db.session import get_db, get_redis
from backend.app.core.config import settings

logger = logging.getLogger("clipper-x.api.health")

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service health check")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """
    Evaluates backend service health, database connectivity, and Redis runtime cache connectivity.
    """
    db_status = "unknown"
    redis_status = "unknown"
    all_healthy = True

    # Check PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Health check failed for database: {e}")
        db_status = f"error: {str(e)}"
        all_healthy = False

    # Check Redis
    try:
        ping_res = await redis_client.ping()
        redis_status = "connected" if ping_res else "unreachable"
    except Exception as e:
        logger.error(f"Health check failed for Redis: {e}")
        redis_status = f"error: {str(e)}"
        all_healthy = False

    response_payload = {
        "status": "ok" if all_healthy else "degraded",
        "service": "clipper-x-backend",
        "version": settings.VERSION,
        "database": db_status,
        "redis": redis_status,
    }

    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=response_payload)
