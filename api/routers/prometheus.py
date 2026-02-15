"""Prometheus-compatible metrics endpoint."""

import time

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/metrics")
async def prometheus_metrics(request: Request):
    """Expose metrics in Prometheus text exposition format."""
    ws_manager = request.app.state.ws_manager
    redis_client = request.app.state.redis

    state_map = {"closed": 0, "open": 1, "half_open": 2}
    cb_value = state_map.get(redis_client.circuit_state, 0)
    uptime = time.time() - request.app.state.start_time

    lines = [
        "# HELP websocket_connections_active Current WebSocket connections",
        "# TYPE websocket_connections_active gauge",
        f"websocket_connections_active {ws_manager.connection_count}",
        "",
        "# HELP redis_circuit_breaker_state Circuit breaker state (0=closed, 1=open, 2=half_open)",
        "# TYPE redis_circuit_breaker_state gauge",
        f"redis_circuit_breaker_state {cb_value}",
        "",
        "# HELP api_uptime_seconds Seconds since API start",
        "# TYPE api_uptime_seconds gauge",
        f"api_uptime_seconds {uptime:.1f}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
