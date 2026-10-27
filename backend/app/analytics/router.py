"""FastAPI router for AICTE analytics, duplicate monitoring, anomalies, and SSE.

Spec: Section 10, 12 & TASKS.md T24, T27, T28:
- Real-time SSE event stream for live dashboard updates.
- Centralized duplicate enrolments query across all colleges.
- IsolationForest anomaly detection scores and multi-dimensional deviation monitoring.
- Historical event inspection for AICTE officers and admins.
"""

from __future__ import annotations

from typing import Annotated

import redis
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.analytics import anomaly_service, sse
from app.analytics.schemas import (
    AnomalyScoreItem,
    AnomalyScoreListResponse,
    DuplicateListResponse,
    SSEEventPayload,
)
from app.auth.dependencies import require_aicte_user
from app.db import get_db, get_redis
from app.models import AnomalyScore, User
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
    "/anomalies",
    response_model=AnomalyScoreListResponse,
    summary="List machine learning and statistical anomaly scores across institutions (AICTE only)",
)
def get_anomaly_scores(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str | None, Query(description="Filter by academic year")] = None,
    flagged_only: Annotated[bool, Query(description="Filter only flagged anomalies")] = False,
    institution_id: Annotated[int | None, Query(description="Filter by institution ID")] = None,
    scan_now: Annotated[bool, Query(description="Trigger fresh IsolationForest scan")] = False,
) -> AnomalyScoreListResponse:
    """Retrieve IsolationForest anomaly scores and 6-dimensional features for AICTE monitoring.

    Optionally runs fresh on-demand scan when scan_now=True.
    """
    if scan_now:
        year_to_scan = academic_year or "2026-27"
        anomaly_service.evaluate_and_store_anomalies(db=db, academic_year=year_to_scan)

    stmt = select(AnomalyScore).options(
        joinedload(AnomalyScore.institution),
        joinedload(AnomalyScore.course),
    )
    if academic_year:
        stmt = stmt.where(AnomalyScore.academic_year == academic_year)
    if flagged_only:
        stmt = stmt.where(AnomalyScore.flagged.is_(True))
    if institution_id:
        stmt = stmt.where(AnomalyScore.institution_id == institution_id)

    # Order by most anomalous (lowest decision score) first
    stmt = stmt.order_by(AnomalyScore.score.asc())
    records = list(db.scalars(stmt).all())

    items: list[AnomalyScoreItem] = []
    flagged_cnt = 0
    for r in records:
        if r.flagged:
            flagged_cnt += 1
        summary_val = None
        if r.features_json and isinstance(r.features_json, dict):
            summary_val = r.features_json.get("summary")
        items.append(
            AnomalyScoreItem(
                id=r.id,
                institution_id=r.institution_id,
                institution_name=r.institution.name if r.institution else None,
                aicte_id=r.institution.aicte_id if r.institution else None,
                course_id=r.course_id,
                course_name=r.course.name if r.course else None,
                academic_year=r.academic_year,
                score=r.score,
                flagged=r.flagged,
                features=r.features_json or {},
                summary=summary_val,
                created_at=r.created_at,
            )
        )

    return AnomalyScoreListResponse(
        total=len(items),
        flagged_count=flagged_cnt,
        academic_year=academic_year,
        items=items,
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
