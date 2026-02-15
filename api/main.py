"""FastAPI application factory with lifespan management."""

import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Settings
from storage.redis_client import RedisClient
from storage.time_series import TimeSeriesReader
from storage.cache import MetricsCache
from api.ws_manager import WebSocketManager, PubSubListener
from api.routers import health, metrics, websocket, prometheus


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    settings = Settings()

    # Initialize Redis
    redis_client = RedisClient(settings)
    ts_reader = TimeSeriesReader(redis_client)
    cache = MetricsCache(redis_client)

    # Initialize WebSocket manager
    ws_manager = WebSocketManager(throttle_ms=settings.ws_throttle_ms)

    # Start Pub/Sub listener for real-time updates
    pubsub_listener = PubSubListener(redis_client, ws_manager)
    listener_task = asyncio.create_task(pubsub_listener.run())

    # Store in app state for dependency injection
    app.state.redis = redis_client
    app.state.ts_reader = ts_reader
    app.state.cache = cache
    app.state.ws_manager = ws_manager
    app.state.start_time = time.time()

    yield

    # Cleanup
    listener_task.cancel()
    redis_client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Real-Time Analytics Dashboard API",
        version="1.0.0",
        description="Streaming analytics pipeline with live WebSocket updates",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(websocket.router)
    app.include_router(prometheus.router)

    return app


app = create_app()
