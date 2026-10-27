"""FastAPI router for AICTE analytics, cross-college duplicate monitoring, and live SSE streaming.

Spec: Section 10, 12 & TASKS.md T24, T28:
- Real-time SSE event stream for live dashboard updates.
- Centralized duplicate enrolments query across all colleges.
- Historical event inspection for AICTE officers and admins.
"""

from __future__ import annotations

from typing import Annotated

import redis
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.analytics import sse
from app.analytics.schemas import DuplicateListResponse, SSEEventPayload
from app.auth.dependencies import require_aicte_user
from app.db import get_db, get_redis
from app.models import User
from app.students import duplicate_service

router = APIRouter(prefix="/analytics", tags=["AICTE Analytics & Monitoring"])


@router.get(
    "/duplicates",
    response_model=DuplicateListResponse,
    summary="List cross-college duplicate enrolments across all institutions (AICTE only)",
)
def get_duplicate_enrolments(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str | None, Query(description="Filter by academic year")] = None,
    rule_code: Annotated[
        str | None,
        Query(description="Filter by DUP_ACTIVE_OTHER_COLLEGE or DUP_SAME_COURSE_OTHER_COLLEGE"),
    ] = None,
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter by open or resolved")
    ] = None,
) -> DuplicateListResponse:
    """Retrieve all student records enrolled across two or more colleges.

    Grouped by APAAR ID so two colleges submitting the same APAAR ID
    produce exactly one duplicate case record for AICTE.
    """
    records = duplicate_service.get_duplicate_records(
        db=db,
        academic_year=academic_year,
        rule_code=rule_code,
        status_filter=status_filter,
    )
    return DuplicateListResponse(
        total_duplicates=len(records),
        academic_year=academic_year,
        items=records,
    )


@router.get(
    "/stream",
    summary="Live Server-Sent Events (SSE) stream for AICTE dashboards (AICTE only)",
)
async def stream_live_events(
    request: Request,
    current_user: Annotated[User, require_aicte_user],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> StreamingResponse:
    """Server-Sent Events endpoint streaming real-time submission, flag, and duplicate events.

    Updates AICTE dashboards live without requiring manual page refresh.
    """
    return StreamingResponse(
        sse.sse_event_generator(request=request, redis_client=redis_client),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/events",
    response_model=list[SSEEventPayload],
    summary="Get recent system events from memory buffer (AICTE only)",
)
def get_recent_system_events(
    current_user: Annotated[User, require_aicte_user],
    limit: Annotated[int, Query(ge=1, le=200, description="Max events to return")] = 50,
    event_type: Annotated[str | None, Query(description="Filter by event name")] = None,
) -> list[SSEEventPayload]:
    """Retrieve recent SSE events recorded in the system buffer."""
    raw_events = sse.get_recent_events(limit=limit, event_type=event_type)
    return [
        SSEEventPayload(
            id=e["id"],
            event=e["event"],
            data=e["data"],
            timestamp=e["timestamp"],
        )
        for e in raw_events
    ]
