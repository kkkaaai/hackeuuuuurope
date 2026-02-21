"""SSE endpoint for real-time push notifications."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger("agentflow.sse")
router = APIRouter(prefix="/api", tags=["sse"])

MAX_SSE_SUBSCRIBERS = 200


class NotificationBus:
    """Pub/sub bus for pushing notifications to SSE subscribers."""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]] | None:
        """Subscribe to notifications. Returns None if at capacity."""
        async with self._lock:
            if len(self._subscribers) >= MAX_SSE_SUBSCRIBERS:
                return None
            queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
            self._subscribers.append(queue)
            return queue

    async def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    async def publish(self, notification: dict[str, Any]) -> None:
        """Push a notification to all subscribers."""
        async with self._lock:
            subscribers = list(self._subscribers)

        dead: list[asyncio.Queue[dict[str, Any]]] = []
        for queue in subscribers:
            try:
                queue.put_nowait(notification)
            except asyncio.QueueFull:
                dead.append(queue)

        if dead:
            async with self._lock:
                for q in dead:
                    if q in self._subscribers:
                        self._subscribers.remove(q)


notification_bus = NotificationBus()


@router.get("/notifications/stream")
async def notification_stream(request: Request) -> StreamingResponse:
    """SSE endpoint — streams notifications in real-time."""

    async def event_generator():
        queue = await notification_bus.subscribe()
        if queue is None:
            yield "data: {\"error\": \"Too many connections\"}\n\n"
            return
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    notification = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(notification)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive comment to prevent connection timeout
                    yield ": keepalive\n\n"
        finally:
            await notification_bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
