"""Pydantic schemas for analytics, duplicate listings, anomaly scores, and SSE event feeds.

Spec: Section 10, 12 & TASKS.md T24, T27, T28.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DuplicateInstitutionDetail(BaseModel):
    """Enrolment detail of a duplicate student record at one institution."""

    institution_id: int
    institution_name: str
    aicte_id: str
    course_id: int | None = None
    course_name: str | None = None
    branch: str | None = None
    student_id: int
    student_name: str
    enrolment_no: str
    student_status: str
    submission_id: int | None = None
    receipt_no: str | None = None
    is_locked: bool = False
    flag_id: int | None = None
    flag_status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DuplicateRecordResponse(BaseModel):
    """A cross-college duplicate enrolment case keyed by APAAR ID and academic year."""

    apaar_id: str
    academic_year: str
    rule_code: str = Field(
        ...,
        description="DUP_SAME_COURSE_OTHER_COLLEGE or DUP_ACTIVE_OTHER_COLLEGE",
    )
    level: str = Field(..., description="exception or warning")
    status: str = Field("open", description="open or resolved")
    institutions_count: int
    institutions: list[DuplicateInstitutionDetail]
    detected_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DuplicateListResponse(BaseModel):
    """Paginated or complete list of cross-college duplicate records for AICTE monitoring."""

    total_duplicates: int
    academic_year: str | None = None
    items: list[DuplicateRecordResponse]


class AnomalyScoreItem(BaseModel):
    """Multi-dimensional IsolationForest anomaly score and features for a college-course."""

    id: int
    institution_id: int
    institution_name: str | None = None
    aicte_id: str | None = None
    course_id: int
    course_name: str | None = None
    academic_year: str
    score: float
    flagged: bool
    features: dict[str, Any]
    summary: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AnomalyScoreListResponse(BaseModel):
    """List response for AICTE anomaly detection monitoring."""

    total: int
    flagged_count: int
    academic_year: str | None = None
    items: list[AnomalyScoreItem]


class SSEEventPayload(BaseModel):
    """Format of events broadcast through Server-Sent Events."""

    id: str
    event: str
    data: dict[str, Any]
    timestamp: str
