"""WebSocket connection manager with throttling and backpressure."""

import asyncio
import json
import time

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from config import configure_logging


class ConnectionState:
    __slots__ = ("websocket", "channels", "last_send_time")

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.channels: set[str] = {"iot", "activity", "alerts", "trends"}
        self.last_send_time: float = 0.0


class WebSocketManager:
    """
    Manages WebSocket connections with:
    - Per-connection message throttling (min interval between sends)
    - Channel-based filtering (clients choose what data to receive)
    - Concurrent broadcast with error handling
    """

    def __init__(self, throttle_ms: int = 100):
        self._connections: dict[WebSocket, ConnectionState] = {}
        self._throttle_interval = throttle_ms / 1000.0
        self.log = configure_logging("ws-manager")

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections[websocket] = ConnectionState(websocket)
        self.log.info("ws_connected", total=len(self._connections))

    def disconnect(self, websocket: WebSocket):
        self._connections.pop(websocket, None)
        self.log.info("ws_disconnected", total=len(self._connections))

    def update_filters(self, websocket: WebSocket, channels: list[str]):
        state = self._connections.get(websocket)
        if state:
            state.channels = set(channels)

    async def broadcast(self, channel: str, data: dict):
        """Send data to all clients subscribed to the given channel."""
        if not self._connections:
            return

        now = time.time()
        message = json.dumps({"channel": channel, "data": data})

        tasks = []
        for ws, state in list(self._connections.items()):
            if channel not in state.channels:
                continue
            if now - state.last_send_time < self._throttle_interval:
                continue
            state.last_send_time = now
            tasks.append(self._safe_send(ws, message))

        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_send(self, ws: WebSocket, message: str):
        try:
            if ws.client_state == WebSocketState.CONNECTED:
                await ws.send_text(message)
        except Exception:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


class PubSubListener:
    """Subscribes to Redis Pub/Sub and broadcasts to WebSocket clients."""

    def __init__(self, redis_client, ws_manager: WebSocketManager):
        self._redis = redis_client
        self._ws_manager = ws_manager
        self.log = configure_logging("pubsub-listener")

    async def run(self):
        """Listen to Redis Pub/Sub and forward to WebSocket manager."""
        while True:
            try:
                client = self._redis.get_client()
                pubsub = client.pubsub()
                pubsub.subscribe("channel:dashboard_updates")
                self.log.info("pubsub_subscribed", channel="channel:dashboard_updates")

                for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    try:
                        data = json.loads(message["data"])
                        # Broadcast to appropriate channels based on data content
                        await self._ws_manager.broadcast("metrics", data)
                    except json.JSONDecodeError:
                        continue
                    # Yield control to event loop
                    await asyncio.sleep(0)

            except Exception as e:
                self.log.error("pubsub_error", error=str(e))
                await asyncio.sleep(2)  # Reconnect backoff
