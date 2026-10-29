"""FastAPI router for AICTE analytics, duplicate monitoring, anomalies, and SSE."""

from __future__ import annotations

from typing import Annotated

import redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.analytics import analytics_service, anomaly_service, sse
from app.analytics.schemas import (
    AnomalyScoreItem,
    AnomalyScoreListResponse,
    ComplianceListResponse,
    CourseMetricsListResponse,
    DrilldownResponse,
    DuplicateListResponse,
    NoticeResponse,
    OverviewMetricsResponse,
    ResolveFlagRequest,
    ResolveFlagResponse,
    SendNoticeRequest,
    SSEEventPayload,
    StateMetricsListResponse,
    SubmissionProgressResponse,
)
from app.auth.dependencies import require_aicte_user
from app.db import get_db, get_redis
from app.models import AnomalyScore, User
from app.students import duplicate_service

router = APIRouter(prefix="/analytics", tags=["AICTE Analytics & Monitoring"])


# Overview Metrics


@router.get(
    "/overview",
    response_model=OverviewMetricsResponse,
    summary="Get high-level oversight metrics for AICTE dashboard (AICTE only)",
)
def get_overview_metrics(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str, Query(description="Academic year to inspect")] = "2026-27",
) -> OverviewMetricsResponse:
    """Retrieve comprehensive system overview metrics matching direct database counts."""
    return analytics_service.get_overview_metrics(db=db, academic_year=academic_year)


# State and Course Breakdown


@router.get(
    "/by-state",
    response_model=StateMetricsListResponse,
    summary="Get metrics aggregated by state (AICTE only)",
)
def get_metrics_by_state(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
) -> StateMetricsListResponse:
    """Retrieve state-level aggregations of colleges, intake, enrolment, and compliance."""
    return analytics_service.get_by_state(db=db, academic_year=academic_year)


@router.get(
    "/by-course",
    response_model=CourseMetricsListResponse,
    summary="Get metrics aggregated by course discipline (AICTE only)",
)
def get_metrics_by_course(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    level: Annotated[
        str | None,
        Query(description="Filter by level: UG, PG, Diploma, PGDM"),
    ] = None,
) -> CourseMetricsListResponse:
    """Retrieve course discipline aggregations of intake, enrolment, and overshoots."""
    return analytics_service.get_by_course(db=db, academic_year=academic_year, level=level)


# Submission Progress Tracking


@router.get(
    "/submission-progress",
    response_model=SubmissionProgressResponse,
    summary="Get annual submission progress tracking across colleges (AICTE only)",
)
def get_submission_progress(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    state: Annotated[str | None, Query(description="Filter by state")] = None,
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter by submission status")
    ] = None,
) -> SubmissionProgressResponse:
    """Retrieve submission progress tracking across all AICTE-approved colleges."""
    return analytics_service.get_submission_progress(
        db=db,
        academic_year=academic_year,
        state=state,
        status_filter=status_filter,
    )


# Compliance Monitoring and Red List


@router.get(
    "/compliance",
    response_model=ComplianceListResponse,
    summary="List over-intake colleges, quota overshoots, and red-list institutions (AICTE only)",
)
def get_compliance_list(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    state: Annotated[str | None, Query(description="Filter by state")] = None,
    min_overshoot: Annotated[int, Query(ge=0, description="Minimum regular seat overshoot")] = 1,
) -> ComplianceListResponse:
    """Retrieve compliance violations: colleges admitting regular students above approved intake."""
    return analytics_service.get_compliance_list(
        db=db,
        academic_year=academic_year,
        state=state,
        min_overshoot=min_overshoot,
    )


# Hierarchical Drilldown


@router.get(
    "/drilldown",
    response_model=DrilldownResponse,
    summary="Hierarchical drill-down: State -> College -> Course -> Flagged Students (AICTE only)",
)
def get_drilldown(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
    state: Annotated[str | None, Query(description="Selected state")] = None,
    institution_id: Annotated[int | None, Query(description="Selected institution ID")] = None,
    course_id: Annotated[int | None, Query(description="Selected course ID")] = None,
) -> DrilldownResponse:
    """Multi-tiered drilldown into states, institutions, courses, and individual students."""
    try:
        return analytics_service.get_drilldown(
            db=db,
            academic_year=academic_year,
            state=state,
            institution_id=institution_id,
            course_id=course_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# Action Tools


@router.post(
    "/action/notice",
    response_model=NoticeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send an official compliance notice to an institution (AICTE only)",
)
def send_compliance_notice(
    request_data: SendNoticeRequest,
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> NoticeResponse:
    """Dispatch an official compliance notice to an institution with SSE notification."""
    try:
        return analytics_service.send_institution_notice(
            db=db,
            current_user=current_user,
            institution_id=request_data.institution_id,
            subject=request_data.subject,
            message=request_data.message,
            urgency=request_data.urgency,
            redis_client=redis_client,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/action/resolve-flag",
    response_model=ResolveFlagResponse,
    summary="Mark a validation flag as resolved or dismissed (AICTE only)",
)
def resolve_flag_action(
    request_data: ResolveFlagRequest,
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> ResolveFlagResponse:
    """Mark a validation flag resolved or dismissed with hash-chained audit logging."""
    try:
        return analytics_service.resolve_validation_flag(
            db=db,
            current_user=current_user,
            flag_id=request_data.flag_id,
            note=request_data.note,
            action=request_data.action,
            redis_client=redis_client,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# Cross-College Duplicate Enrolments


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
    """Retrieve all student records enrolled across two or more colleges."""
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


# Machine Learning Anomaly Detection Scores


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
    """Retrieve IsolationForest anomaly scores and 6-dimensional features for AICTE monitoring."""
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


# Server-Sent Events (SSE) Live Event Stream


@router.get(
    "/stream",
    summary="Live Server-Sent Events (SSE) stream for AICTE dashboards (AICTE only)",
)
async def stream_live_events(
    request: Request,
    current_user: Annotated[User, require_aicte_user],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> StreamingResponse:
    """Server-Sent Events endpoint streaming real-time submission, flag, and duplicate events."""
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
