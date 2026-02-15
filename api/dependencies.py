"""FastAPI dependency injection."""

from fastapi import Request

from storage.redis_client import RedisClient
from storage.time_series import TimeSeriesReader
from storage.cache import MetricsCache


def get_redis(request: Request) -> RedisClient:
    return request.app.state.redis


def get_ts_reader(request: Request) -> TimeSeriesReader:
    return request.app.state.ts_reader


def get_cache(request: Request) -> MetricsCache:
    return request.app.state.cache
