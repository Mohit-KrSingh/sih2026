"""Pydantic schemas for validation flags, justifications, and submission verification."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JustificationCreateRequest(BaseModel):
    """Payload to submit a written justification for an exception or warning flag."""

    text: str = Field(
        ...,
        min_length=5,
        max_length=4000,
        description="Detailed plain-English justification for the compliance exception",
    )
    document_ref: str | None = Field(
        default=None,
        max_length=255,
        description="Optional storage reference for an uploaded supporting document",
    )


class JustificationResponse(BaseModel):
    """Written justification record and supporting document metadata."""

    id: int
    flag_id: int
    text: str
    document_ref: str | None = None
    document_url: str | None = None
    by_user: int | None = None
    author_name: str | None = None
    author_role: str | None = None
    at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlagTargetStudent(BaseModel):
    """Minimal student metadata associated with a validation flag."""

    id: int
    apaar_id: str
    name: str
    enrolment_no: str
    academic_year: str
    course_name: str | None = None
    branch: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FlagTargetCourse(BaseModel):
    """Course metadata associated with a course-level validation flag."""

    id: int
    name: str
    branch: str
    level: str

    model_config = ConfigDict(from_attributes=True)


class ValidationFlagDetailResponse(BaseModel):
    """Complete validation flag detail with contextual student/course target and justifications."""

    id: int
    student_id: int | None = None
    course_id: int | None = None
    submission_id: int | None = None
    rule_code: str
    level: str  # error | exception | warning | info
    field: str | None = None
    message: str
    fix_hint: str | None = None
    audience: str = "both"  # college | aicte | both
    requires_justification: bool = False
    status: str = "open"  # open | justified | resolved | dismissed
    student: FlagTargetStudent | None = None
    course: FlagTargetCourse | None = None
    justifications: list[JustificationResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValidationFlagsSummary(BaseModel):
    """Statistical summary of institutional validation flags and final submission gate readiness."""

    total_flags: int = 0
    open_count: int = 0
    justified_count: int = 0
    resolved_count: int = 0
    error_count: int = 0
    exception_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    blocking_count: int = 0
    can_submit: bool = False


class InstitutionFlagsListResponse(BaseModel):
    """Response containing filtered institutional flags list and statistical summary."""

    institution_id: int
    academic_year: str | None = None
    summary: ValidationFlagsSummary
    items: list[ValidationFlagDetailResponse]


class BlockerDetail(BaseModel):
    """Actionable blocker preventing final data submission with deep links."""

    flag_id: int | None = None
    rule_code: str
    level: str  # error | exception | warning
    message: str
    fix_hint: str | None = None
    field: str | None = None
    student_id: int | None = None
    student_name: str | None = None
    apaar_id: str | None = None
    enrolment_no: str | None = None
    course_id: int | None = None
    course_name: str | None = None
    target_link: str
    reason: str


class SubmissionGateResponse(BaseModel):
    """Complete submission gate evaluation status for an institution and academic year."""

    institution_id: int
    institution_name: str
    aicte_id: str
    academic_year: str
    current_status: str  # draft | submitted | submitted_with_exceptions | under_review | etc.
    is_locked: bool
    can_submit: bool
    target_status: str | None = None  # submitted | submitted_with_exceptions
    gate_reason: str
    blockers: list[BlockerDetail] = []
    total_students: int = 0
    total_courses: int = 0
    open_errors_count: int = 0
    unjustified_exceptions_count: int = 0
    unjustified_warnings_count: int = 0
    justified_exceptions_count: int = 0
    justified_warnings_count: int = 0
    seat_mismatch_detected: bool = False
    submission_id: int | None = None
    receipt_no: str | None = None
    submitted_at: datetime | None = None
    submitted_by_name: str | None = None
    declaration_ref: str | None = None


class SubmissionOtpRequest(BaseModel):
    """Payload to request a submission declaration verification OTP."""

    academic_year: str = Field(default="2026-27", max_length=20)


class SubmissionOtpResponse(BaseModel):
    """Response indicating OTP dispatch for declaration confirmation."""

    status: str
    recipient: str
    channel: str
    purpose: str
    expires_in: int
    message: str


class SubmissionSubmitRequest(BaseModel):
    """Payload to confirm declaration with OTP and lock data for final submission."""

    academic_year: str = Field(default="2026-27", max_length=20)
    confirmed_declaration: bool = Field(
        ...,
        description="Affirmation that student data is authentic, verified, and complete",
    )
    declaration_text: str = Field(
        default="I confirm this data is correct and complete as authorized by the head.",
        min_length=10,
        max_length=500,
    )
    otp_code: str = Field(
        ...,
        min_length=4,
        max_length=8,
        description="6-digit verification code received via registered contact",
    )


class SubmissionReceiptResponse(BaseModel):
    """Official submission receipt details upon successful locking and submission."""

    institution_id: int
    institution_name: str
    aicte_id: str
    academic_year: str
    submission_id: int
    receipt_no: str
    status: str  # submitted | submitted_with_exceptions
    submitted_at: datetime
    submitted_by_email: str
    submitted_by_name: str | None = None
    declaration_text: str
    total_students: int
    regular_students: int
    supernumerary_students: int
    courses_count: int
    justified_exceptions_count: int
    is_locked: bool = True
