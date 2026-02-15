"""REST API endpoints for querying metrics, alerts, and leaderboards."""

import time

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_ts_reader, get_cache
from storage.time_series import TimeSeriesReader
from storage.cache import MetricsCache

router = APIRouter(prefix="/api/v1")


@router.get("/metrics/iot/latest")
async def get_iot_latest(cache: MetricsCache = Depends(get_cache)):
    """Latest reading for every IoT device."""
    return cache.get_iot_latest()


@router.get("/metrics/iot/history")
async def get_iot_history(
    key: str = Query(..., description="Time-series key, e.g. iot:temperature:sensor-001"),
    start: float = Query(default=None, description="Start timestamp (ms)"),
    end: float = Query(default=None, description="End timestamp (ms)"),
    max_points: int = Query(default=200, le=1000),
    reader: TimeSeriesReader = Depends(get_ts_reader),
):
    """Historical IoT data for a specific sensor key."""
    now_ms = time.time() * 1000
    start = start or (now_ms - 3_600_000)  # Default: last hour
    end = end or now_ms
    return reader.get_range(key, start, end, max_points)


@router.get("/metrics/activity/latest")
async def get_activity_latest(cache: MetricsCache = Depends(get_cache)):
    """Latest activity event counts by type."""
    return cache.get_activity_latest()


@router.get("/metrics/activity/leaderboard")
async def get_leaderboard(
    top_n: int = Query(default=10, le=50),
    cache: MetricsCache = Depends(get_cache),
):
    """Top pages by purchase value."""
    return cache.get_leaderboard(top_n)


@router.get("/alerts")
async def get_alerts(
    limit: int = Query(default=50, le=100),
    cache: MetricsCache = Depends(get_cache),
):
    """Recent anomaly alerts."""
    return cache.get_alerts(limit)
