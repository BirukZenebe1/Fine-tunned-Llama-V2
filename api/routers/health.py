"""Health and readiness check endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.dependencies import get_redis
from storage.redis_client import RedisClient

router = APIRouter()


@router.get("/health")
async def health():
    """Liveness probe — returns 200 if the process is alive."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(redis: RedisClient = Depends(get_redis)):
    """Readiness probe — checks Redis connectivity."""
    redis_ok = redis.ping()
    if not redis_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "redis": "unreachable"},
        )
    return {
        "status": "ready",
        "redis": "connected",
        "circuit_breaker": redis.circuit_state,
    }
