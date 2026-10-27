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
