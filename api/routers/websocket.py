"""WebSocket endpoint for real-time dashboard updates."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.ws_manager import WebSocketManager

router = APIRouter()


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Real-time WebSocket endpoint.

    Clients connect and optionally send filter preferences:
        {"type": "subscribe", "channels": ["iot", "activity", "alerts"]}

    Data is pushed by the PubSubListener via the WebSocketManager.
    """
    manager: WebSocketManager = websocket.app.state.ws_manager
    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                if data.get("type") == "subscribe" and "channels" in data:
                    manager.update_filters(websocket, data["channels"])
                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
