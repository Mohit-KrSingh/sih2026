"""Server-Sent Events (SSE) publishing, Redis pub/sub integration, and event streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

import redis
from fastapi import Request

logger = logging.getLogger(__name__)

SSE_REDIS_CHANNEL = "sse:aicte_events"
MAX_RECENT_EVENTS = 200

# Thread-safe in-memory buffer for recent events
_recent_events: deque[dict[str, Any]] = deque(maxlen=MAX_RECENT_EVENTS)

# Active in-process asyncio subscriber queues
_local_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()


def publish_sse_event(
    redis_client: redis.Redis | None,
    event_type: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Publish an SSE event to Redis pub/sub and in-memory subscribers.

    Returns the canonical event payload.
    """
    event_id = str(uuid.uuid4())
    payload = {
        "id": event_id,
        "event": event_type,
        "data": data,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    _recent_events.append(payload)

    for q in list(_local_subscribers):
        try:
            q.put_nowait(payload)
        except Exception:
            _local_subscribers.discard(q)

    if redis_client is not None:
        try:
            redis_client.publish(SSE_REDIS_CHANNEL, json.dumps(payload))
        except Exception as e:
            logger.warning("Failed to publish SSE event to Redis: %s", e)

    return payload


def get_recent_events(
    limit: int = 50,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve recent SSE events from the buffer, optionally filtered by type."""
    events = list(_recent_events)
    if event_type:
        events = [e for e in events if e.get("event") == event_type]
    return events[-limit:]


def clear_recent_events() -> None:
    """Clear in-memory events buffer (used in tests)."""
    _recent_events.clear()


async def sse_event_generator(
    request: Request,
    redis_client: redis.Redis | None = None,
    heartbeat_seconds: float = 15.0,
):
    """Async generator streaming SSE events to connected HTTP clients.

    Emits standard W3C Server-Sent Events format:
        event: <type>
        id: <uuid>
        data: <json>

    Supports disconnect detection and keep-alive ping comments.
    """
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
    _local_subscribers.add(queue)

    # Send initial greeting/handshake event
    greeting = {
        "id": str(uuid.uuid4()),
        "event": "connected",
        "data": {
            "status": "connected",
            "message": "AICTE Real-time Event Stream Connected",
            "connected_at": datetime.now(UTC).isoformat(),
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    greeting_json = json.dumps(greeting["data"])
    yield f"id: {greeting['id']}\nevent: {greeting['event']}\ndata: {greeting_json}\n\n"

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                # Wait for next event or timeout for heartbeat
                event_payload = await asyncio.wait_for(queue.get(), timeout=heartbeat_seconds)
                evt_id = event_payload.get("id", str(uuid.uuid4()))
                evt_name = event_payload.get("event", "message")
                evt_data = json.dumps(event_payload.get("data", {}))
                yield f"id: {evt_id}\nevent: {evt_name}\ndata: {evt_data}\n\n"
            except TimeoutError:
                # Heartbeat keep-alive comment
                yield ": keep-alive\n\n"
    finally:
        _local_subscribers.discard(queue)
