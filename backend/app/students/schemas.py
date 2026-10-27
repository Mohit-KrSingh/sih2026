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
