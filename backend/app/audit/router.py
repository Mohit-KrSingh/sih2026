"""Audit log API endpoints: search, query filtering, and cryptographic chain verification."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.schemas import (
    AuditChainVerificationResponse,
    AuditLogListResponse,
    AuditLogResponse,
)
from app.audit.service import verify_chain
from app.auth.dependencies import require_aicte_role
from app.db import get_db
from app.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/verify-chain",
    response_model=AuditChainVerificationResponse,
    summary="Cryptographically verify audit chain integrity",
)
def verify_audit_chain(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, require_aicte_role],
) -> AuditChainVerificationResponse:
    """Recompute the complete SHA-256 hash chain and report first broken row if tampered."""
    result = verify_chain(db)
    return AuditChainVerificationResponse(**result)


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="Search audit logs with filters",
)
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, require_aicte_role],
    action: str | None = Query(None, description="Filter by event action name"),
    actor_id: str | None = Query(None, description="Filter by actor ID"),
    actor_role: str | None = Query(None, description="Filter by actor role"),
    entity: str | None = Query(None, description="Filter by entity domain name"),
    entity_id: str | None = Query(None, description="Filter by entity identifier"),
    from_date: datetime | None = Query(None, description="Filter events on or after timestamp"),
    to_date: datetime | None = Query(None, description="Filter events on or before timestamp"),
    limit: int = Query(50, ge=1, le=500, description="Max items per page"),
    offset: int = Query(0, ge=0, description="Items offset position"),
) -> AuditLogListResponse:
    """Retrieve audit log entries matching filters, ordered with newest events first."""
    query = select(AuditLog)

    if action:
        query = query.where(AuditLog.action == action)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if actor_role:
        query = query.where(AuditLog.actor_role == actor_role)
    if entity:
        query = query.where(AuditLog.entity == entity)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    if from_date:
        query = query.where(AuditLog.ts >= from_date)
    if to_date:
        query = query.where(AuditLog.ts <= to_date)

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    items = db.scalars(query.order_by(AuditLog.id.desc()).offset(offset).limit(limit)).all()

    return AuditLogListResponse(
        total=total,
        items=[AuditLogResponse.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
    )
