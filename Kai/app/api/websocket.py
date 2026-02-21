"""WebSocket endpoint for real-time pipeline execution updates."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("agentflow.websocket")
router = APIRouter(tags=["websocket"])


MAX_WS_CONNECTIONS = 200


class ConnectionManager:
    """Manages WebSocket connections grouped by run_id."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._total = 0

    async def connect(self, run_id: str, ws: WebSocket) -> bool:
        """Accept a new connection. Returns False if at capacity."""
        if self._total >= MAX_WS_CONNECTIONS:
            await ws.close(code=1013, reason="Too many connections")
            return False
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(run_id, []).append(ws)
            self._total += 1
        logger.debug("WS connected for run %s (total: %d)", run_id, len(self._connections[run_id]))

    async def disconnect(self, run_id: str, ws: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(run_id, [])
            if ws in conns:
                conns.remove(ws)
                self._total -= 1
            if not conns:
                self._connections.pop(run_id, None)

    async def broadcast(self, run_id: str, data: dict[str, Any]) -> None:
        """Send a JSON message to all connections subscribed to a run_id."""
        async with self._lock:
            conns = list(self._connections.get(run_id, []))

        message = json.dumps(data)
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        if dead:
            async with self._lock:
                for ws in dead:
                    conns = self._connections.get(run_id, [])
                    if ws in conns:
                        conns.remove(ws)


connection_manager = ConnectionManager()


@router.websocket("/ws/execution/{run_id}")
async def execution_websocket(websocket: WebSocket, run_id: str) -> None:
    """WebSocket endpoint for subscribing to execution updates."""
    connected = await connection_manager.connect(run_id, websocket)
    if not connected:
        return
    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong keepalive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect(run_id, websocket)
