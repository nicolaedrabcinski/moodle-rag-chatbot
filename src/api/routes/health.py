"""
Health check endpoints.
"""

from typing import Any, Dict

from fastapi import APIRouter, status

from src.core.config import settings
from src.core.config.logging import LoggerAdapter
from src.core.llm import get_llm_client
from src.data_pipeline.storage import get_qdrant_storage
from src.services.cache import get_redis_cache

logger = LoggerAdapter(__name__)

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns service health status.
    """
    health_status = {
        "status": "healthy",
        "version": settings.api_version,
        "services": {},
    }

    # Check LLM server
    try:
        llm_client = get_llm_client()
        llm_healthy = await llm_client.health_check()
        health_status["services"]["llm"] = "healthy" if llm_healthy else "unhealthy"
    except Exception as e:
        logger.error("LLM health check failed", error=str(e))
        health_status["services"]["llm"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check Qdrant
    try:
        storage = get_qdrant_storage()
        info = storage.get_collection_info()
        health_status["services"]["qdrant"] = {
            "status": "healthy",
            "points_count": info.get("points_count", 0),
        }
    except Exception as e:
        logger.error("Qdrant health check failed", error=str(e))
        health_status["services"]["qdrant"] = {"status": "unhealthy"}
        health_status["status"] = "degraded"

    # Check Redis
    try:
        cache = await get_redis_cache()
        if cache.redis:
            await cache.redis.ping()
            health_status["services"]["redis"] = {
                "status": "healthy",
                "hit_rate": cache.get_hit_rate(),
            }
        else:
            health_status["services"]["redis"] = {"status": "disabled"}
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        health_status["services"]["redis"] = {"status": "unhealthy"}
        health_status["status"] = "degraded"

    return health_status


@router.get("/readiness", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, str]:
    """
    Readiness check endpoint.

    Returns whether service is ready to accept requests.
    """
    try:
        # Quick checks without external calls
        return {"status": "ready"}
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {"status": "not_ready", "error": str(e)}


@router.get("/liveness", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check endpoint.

    Returns whether service is alive.
    """
    return {"status": "alive"}
