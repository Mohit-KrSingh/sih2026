"""Pydantic schemas for analytics, duplicate listings, anomaly scores, and SSE event feeds."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Duplicate Enrolment Schemas (T24)


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


# Anomaly Score Schemas (T27)


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


# Server-Sent Events (SSE) Schemas


class SSEEventPayload(BaseModel):
    """Format of events broadcast through Server-Sent Events."""

    id: str
    event: str
    data: dict[str, Any]
    timestamp: str


# Overview Metrics Schemas (T28)


class SubmissionProgressOverview(BaseModel):
    """High-level summary of college annual submissions."""

    total: int
    submitted: int
    pending: int
    not_started: int
    submitted_percentage: float


class OverviewMetricsResponse(BaseModel):
    """Comprehensive high-level oversight metrics for the AICTE dashboard."""

    academic_year: str
    total_colleges: int
    active_colleges: int
    total_students: int
    approved_intake_total: int
    supernumerary_intake_total: int
    actual_enrolment_total: int
    total_courses: int
    exceptions_count: int
    errors_count: int
    warnings_count: int
    duplicates_count: int
    anomalies_count: int
    over_intake_colleges_count: int
    submission_progress: SubmissionProgressOverview
    status_breakdown: dict[str, int]


# State and Course Breakdown Schemas (T28)


class StateMetricsItem(BaseModel):
    """Enrolment, intake, and compliance metrics aggregated per state."""

    state: str
    colleges_count: int
    active_colleges_count: int
    approved_intake: int
    regular_admitted: int
    supernumerary_admitted: int
    total_enrolled: int
    utilization_rate: float
    over_intake_colleges: int
    exceptions_count: int
    duplicates_count: int
    submissions_submitted: int
    submissions_pending: int
    submissions_not_started: int


class StateMetricsListResponse(BaseModel):
    """Response containing state-level aggregations."""

    academic_year: str
    total_states: int
    items: list[StateMetricsItem]


class CourseMetricsItem(BaseModel):
    """Enrolment, quotas, and violations aggregated by course discipline."""

    course_name: str
    level: str
    branch: str
    institutions_count: int
    approved_intake: int
    supernumerary_allowed: int
    regular_admitted: int
    supernumerary_admitted: int
    total_enrolled: int
    utilization_rate: float
    over_intake_count: int
    exceptions_count: int


class CourseMetricsListResponse(BaseModel):
    """Response containing course discipline aggregations."""

    academic_year: str
    total_courses: int
    items: list[CourseMetricsItem]


# Submission Progress Tracking Schemas (T28)


class InstitutionSubmissionProgressItem(BaseModel):
    """Detailed submission status and metrics for an individual institution."""

    institution_id: int
    aicte_id: str
    institution_name: str
    state: str
    district: str
    approval_status: str
    account_status: str
    submission_status: str
    submitted_at: datetime | None = None
    receipt_no: str | None = None
    total_students: int
    approved_intake: int
    error_count: int
    exception_count: int
    warning_count: int


class SubmissionProgressResponse(BaseModel):
    """Detailed institutional submission progress across the platform."""

    academic_year: str
    total_institutions: int
    submitted: int
    pending: int
    not_started: int
    submitted_percentage: float
    status_breakdown: dict[str, int]
    items: list[InstitutionSubmissionProgressItem]


# Compliance Monitoring and Red List Schemas (T28)


class ComplianceViolationItem(BaseModel):
    """Detailed record of an institution exceeding approved intake or supernumerary quota."""

    institution_id: int
    aicte_id: str
    institution_name: str
    state: str
    district: str
    approval_status: str
    course_id: int
    course_name: str
    level: str
    branch: str
    academic_year: str
    approved_intake: int
    regular_admitted: int
    overshoot_amount: int
    supernumerary_allowed: int
    supernumerary_admitted: int
    supernumerary_overshoot: int
    red_list: bool
    submission_status: str
    receipt_no: str | None = None
    flag_id: int | None = None
    flag_status: str | None = None
    has_justification: bool


class ComplianceListResponse(BaseModel):
    """Compliance oversight list featuring over-intake colleges and red-list institutions."""

    academic_year: str
    total_violations: int
    red_list_colleges_count: int
    total_overshoot_seats: int
    items: list[ComplianceViolationItem]


# Drilldown Schemas (State -> College -> Course -> Flagged Students) (T28)


class DrilldownStateSummary(BaseModel):
    """State node in hierarchical drilldown."""

    state: str
    colleges_count: int
    approved_intake: int
    actual_enrolment: int
    exceptions_count: int
    over_intake_colleges: int


class DrilldownCollegeSummary(BaseModel):
    """College node in hierarchical drilldown."""

    institution_id: int
    aicte_id: str
    institution_name: str
    district: str
    approval_status: str
    submission_status: str
    courses_count: int
    approved_intake: int
    actual_enrolment: int
    overshoot_amount: int
    error_count: int
    exception_count: int
    warning_count: int


class DrilldownCourseSummary(BaseModel):
    """Course node in hierarchical drilldown."""

    course_id: int
    course_name: str
    level: str
    branch: str
    approved_intake: int
    supernumerary_allowed: int
    regular_admitted: int
    supernumerary_admitted: int
    total_enrolled: int
    overshoot_amount: int
    status_badge: str
    flagged_students_count: int
    error_count: int
    exception_count: int
    warning_count: int


class DrilldownStudentFlagItem(BaseModel):
    """Validation flag attached to a flagged student in drilldown."""

    id: int
    rule_code: str
    level: str
    field: str | None = None
    message: str
    fix_hint: str | None = None
    status: str
    requires_justification: bool


class DrilldownStudentItem(BaseModel):
    """Student leaf node in hierarchical drilldown."""

    student_id: int
    apaar_id: str
    name: str
    enrolment_no: str
    gender: str
    admission_mode: str
    seat_type: str
    status: str
    flags: list[DrilldownStudentFlagItem]


class DrilldownResponse(BaseModel):
    """Multi-tiered drilldown response spanning State, College, Course, and Students."""

    level: str = Field(..., description="national | state | college | course")
    academic_year: str
    selected_state: str | None = None
    selected_institution: dict[str, Any] | None = None
    selected_course: dict[str, Any] | None = None
    states: list[DrilldownStateSummary] | None = None
    colleges: list[DrilldownCollegeSummary] | None = None
    courses: list[DrilldownCourseSummary] | None = None
    students: list[DrilldownStudentItem] | None = None


# Action Tools Schemas (T28)


class SendNoticeRequest(BaseModel):
    """Payload to dispatch an official AICTE notice to an institution."""

    institution_id: int
    subject: str = Field(..., min_length=3, max_length=255)
    message: str = Field(..., min_length=5)
    urgency: str = Field("normal", description="normal or urgent")


class NoticeResponse(BaseModel):
    """Response returned upon dispatching an institutional compliance notice."""

    id: int
    institution_id: int
    type: str
    payload: dict[str, Any]
    created_at: datetime


class ResolveFlagRequest(BaseModel):
    """Payload for AICTE officer to resolve or dismiss a validation flag."""

    flag_id: int
    note: str = Field(..., min_length=3)
    action: str = Field("resolve", description="resolve or dismiss")


class ResolveFlagResponse(BaseModel):
    """Response returned upon marking a validation flag resolved or dismissed."""

    flag_id: int
    rule_code: str
    status: str
    resolution_note: str
    updated_at: datetime
