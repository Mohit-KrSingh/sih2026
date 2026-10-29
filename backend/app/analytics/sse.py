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
PROCESS_ID = str(uuid.uuid4())

# Thread-safe in-memory buffer for recent events
_recent_events: deque[dict[str, Any]] = deque(maxlen=MAX_RECENT_EVENTS)

# Active in-process asyncio subscriber queues
_local_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

_redis_listener_task: asyncio.Task[None] | None = None


async def _listen_redis_pubsub() -> None:
    """Background listener that forwards Redis pub/sub events to local SSE queues."""
    from app.config import get_settings
    import redis.asyncio as aioredis

    settings = get_settings()
    while True:
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(SSE_REDIS_CHANNEL)
            logger.info("SSE Redis PubSub subscriber started on channel %s", SSE_REDIS_CHANNEL)
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    try:
                        raw_data = message.get("data")
                        if isinstance(raw_data, str):
                            payload = json.loads(raw_data)
                            if payload.get("sender_id") != PROCESS_ID:
                                _recent_events.append(payload)
                                for q in list(_local_subscribers):
                                    try:
                                        q.put_nowait(payload)
                                    except Exception:
                                        _local_subscribers.discard(q)
                    except Exception as parse_err:
                        logger.warning("Error parsing Redis SSE payload: %s", parse_err)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("Redis SSE listener reconnecting after error: %s", e)
            await asyncio.sleep(2)


def ensure_redis_subscriber() -> None:
    """Ensure background Redis pub/sub listener is running in the active event loop."""
    global _redis_listener_task
    if _redis_listener_task is None or _redis_listener_task.done():
        try:
            loop = asyncio.get_running_loop()
            _redis_listener_task = loop.create_task(_listen_redis_pubsub())
        except RuntimeError:
            pass


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
        "sender_id": PROCESS_ID,
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
    ensure_redis_subscriber()

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
