"""Pydantic schemas for seat declarations and course summaries."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ValidationFlagSummary(BaseModel):
    """Validation flag or notice summary for live feedback."""

    rule_code: str
    level: str  # error | exception | warning | info
    message: str
    fix_hint: str | None = None
    field: str | None = None


class SeatDeclarationSaveRequest(BaseModel):
    """Payload to save or autosave a course seat declaration."""

    academic_year: str = Field(default="2026-27", description="Academic year")
    regular_admitted: int = Field(default=0, description="Declared regular admissions")
    supernumerary_admitted: int = Field(default=0, description="Declared supernumerary admissions")
    nri_count: int = Field(default=0, description="Declared NRI admissions")
    oci_count: int = Field(default=0, description="Declared OCI admissions")
    fn_count: int = Field(default=0, description="Declared Foreign National admissions")
    status: Literal["draft", "declared"] = Field(
        default="draft", description="Declaration draft or final status"
    )


class SeatDeclarationBatchItem(BaseModel):
    """Single course declaration item within a batch save request."""

    course_id: int
    regular_admitted: int = 0
    supernumerary_admitted: int = 0
    nri_count: int = 0
    oci_count: int = 0
    fn_count: int = 0
    status: Literal["draft", "declared"] = "draft"


class SeatDeclarationBatchSaveRequest(BaseModel):
    """Payload to save or autosave multiple course declarations in one request."""

    academic_year: str = Field(default="2026-27", description="Academic year")
    declarations: list[SeatDeclarationBatchItem] = Field(default_factory=list)


class SeatDeclarationResponse(BaseModel):
    """Persisted seat declaration record representation."""

    id: int
    course_id: int
    academic_year: str
    regular_admitted: int
    supernumerary_admitted: int
    nri_count: int
    oci_count: int
    fn_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseSummaryResponse(BaseModel):
    """Comprehensive course summary combining AICTE intake, declarations, and enrolment counts."""

    course_id: int
    course_name: str
    branch: str
    level: str
    duration_years: int
    academic_year: str
    approved_intake: int
    supernumerary_seats_allowed: int
    regular_admitted: int
    supernumerary_admitted: int
    nri_count: int
    oci_count: int
    fn_count: int
    total_declared: int
    calculated_enrolment: int
    calculated_regular: int
    calculated_supernumerary: int
    status: str
    status_badge: Literal["within_limit", "over_by_n"]
    overshoot: int
    supernumerary_overshoot: int
    flags: list[ValidationFlagSummary] = []
    updated_at: datetime | None = None


class InstitutionSeatDeclarationResponse(BaseModel):
    """Aggregate institutional seat declarations and course summaries for an academic year."""

    institution_id: int
    academic_year: str
    total_approved_intake: int
    total_supernumerary_allowed: int
    total_declared_regular: int
    total_declared_supernumerary: int
    total_declared: int
    total_enrolled: int
    courses: list[CourseSummaryResponse]


# Student Record Schemas (Spec 8.2, 9.4, TASKS.md T20)


class StudentValidationFlag(BaseModel):
    """Validation flag associated with a student record."""

    id: int | None = None
    rule_code: str
    level: str  # error | exception | warning | info
    field: str | None = None
    message: str
    fix_hint: str | None = None
    audience: str = "both"
    requires_justification: bool = False
    status: str = "open"  # open | justified | resolved | dismissed

    model_config = ConfigDict(from_attributes=True)


class StudentCreateRequest(BaseModel):
    """Payload to create a single student record draft."""

    apaar_id: str = Field(default="", description="12-digit APAAR ID")
    name: str = Field(default="", description="Student full name")
    dob: str = Field(default="", description="Date of birth YYYY-MM-DD")
    gender: str = Field(default="Male", description="Gender (Male, Female, Other)")
    course_id: int = Field(description="Approved course ID")
    academic_year: str = Field(default="2026-27", description="Academic year")
    enrolment_no: str = Field(default="", description="College student enrolment number")
    admission_date: str = Field(default="", description="Admission date YYYY-MM-DD")
    admission_mode: str = Field(
        default="State counselling",
        description="Admission mode (JEE Main, State, Management, etc.)",
    )
    seat_type: str = Field(default="Regular", description="Seat type (Regular or Supernumerary)")
    reservation_category: str = Field(
        default="General", description="Reservation category (General, OBC, SC, ST, EWS)"
    )
    nri: str = Field(default="No", description="NRI status (Yes or No)")
    oci: str = Field(default="No", description="OCI status (Yes or No)")
    foreign_national: str = Field(default="No", description="Foreign national status (Yes or No)")
    country: str | None = Field(default=None, description="Country for foreign nationals")
    status: str = Field(default="draft", description="Initial student status")


class StudentUpdateRequest(BaseModel):
    """Payload to update an existing student draft record."""

    apaar_id: str | None = None
    name: str | None = None
    dob: str | None = None
    gender: str | None = None
    course_id: int | None = None
    academic_year: str | None = None
    enrolment_no: str | None = None
    admission_date: str | None = None
    admission_mode: str | None = None
    seat_type: str | None = None
    reservation_category: str | None = None
    nri: str | None = None
    oci: str | None = None
    foreign_national: str | None = None
    country: str | None = None
    status: str | None = None


class StudentResponse(BaseModel):
    """Detailed student record representation with decrypted DOB and active flags."""

    id: int
    institution_id: int
    course_id: int | None = None
    course_name: str = ""
    branch: str = ""
    academic_year: str
    apaar_id: str
    name: str
    dob: str
    gender: str
    enrolment_no: str
    admission_date: str
    admission_mode: str
    seat_type: str
    reservation_category: str
    nri: str
    oci: str
    foreign_national: str
    country: str | None = None
    status: str
    is_locked: bool
    submission_id: int | None = None
    source: str
    flags: list[StudentValidationFlag] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentSaveResultResponse(BaseModel):
    """Response returned upon 'Check and save' single student entry."""

    student: StudentResponse
    flags: list[StudentValidationFlag]
    is_valid: bool
    errors_count: int
    exceptions_count: int
    warnings_count: int
    infos_count: int


class StudentListStats(BaseModel):
    """Aggregate statistics for filtered student directory."""

    total: int = 0
    valid: int = 0
    flagged: int = 0
    draft: int = 0
    submitted: int = 0
    error_flags_count: int = 0
    exception_flags_count: int = 0
    warning_flags_count: int = 0


class StudentListResponse(BaseModel):
    """Paginated collection of student records with filtering metadata and counts."""

    items: list[StudentResponse]
    total: int
    page: int
    limit: int
    total_pages: int
    stats: StudentListStats


# Bulk Upload Schemas (Spec 8.2, 9.4, 13 & TASKS.md T21)


class UploadSummary(BaseModel):
    """Aggregate summary statistics for a batch upload."""

    total_rows: int = 0
    valid_rows: int = 0
    flagged_rows: int = 0
    error_count: int = 0
    exception_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0


class UploadRowResult(BaseModel):
    """Evaluation result for an individual uploaded student row."""

    row_number: int
    student_id: int | None = None
    apaar_id: str
    name: str
    dob: str
    gender: str
    course: str
    branch: str
    admission_year: str
    enrolment_no: str
    admission_date: str
    admission_mode: str
    seat_type: str
    reservation_category: str
    nri: str
    oci: str
    foreign_national: str
    country: str | None = None
    status: str
    flags: list[StudentValidationFlag] = []


class UploadResultResponse(BaseModel):
    """Full evaluation result response for a bulk student upload."""

    upload_id: int
    filename: str
    row_count: int
    summary: UploadSummary
    rows: list[UploadRowResult]


class UploadHistoryItem(BaseModel):
    """Record representation for past batch upload history."""

    id: int
    institution_id: int
    filename: str
    row_count: int
    status: str
    summary_json: dict | None = None
    uploaded_by: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UploadHistoryResponse(BaseModel):
    """Paginated collection of upload history items."""

    items: list[UploadHistoryItem]
    total: int
