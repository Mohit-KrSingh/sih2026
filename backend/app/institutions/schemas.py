"""Pydantic schemas for institutions, courses, intake, and corrections."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CourseIntakeResponse(BaseModel):
    """Approved intake schema for a course in an academic year."""

    id: int
    course_id: int
    academic_year: str
    approved_intake: int
    supernumerary_seats_allowed: int
    source: str
    set_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseIntakeHistoryResponse(BaseModel):
    """Historical intake modification audit record."""

    id: int
    course_id: int
    academic_year: str
    approved_intake: int
    supernumerary_seats_allowed: int
    source: str
    set_by: str | None
    change_reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseResponse(BaseModel):
    """Course representation with intake information."""

    id: int
    institution_id: int
    name: str
    level: str
    branch: str
    duration_years: int
    supernumerary_allowed: bool
    intakes: list[CourseIntakeResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseCreateRequest(BaseModel):
    """Payload to create an approved course (AICTE officer only)."""

    name: str = Field(..., min_length=2, max_length=255)
    level: str = Field(..., pattern="^(UG|PG|Diploma|PGDM)$")
    branch: str = Field(..., min_length=2, max_length=255)
    duration_years: int = Field(default=4, ge=1, le=6)
    supernumerary_allowed: bool = False
    academic_year: str = Field(default="2026-27", pattern=r"^\d{4}-\d{2}$")
    approved_intake: int = Field(default=60, ge=0)
    supernumerary_seats_allowed: int = Field(default=0, ge=0)


class CourseUpdateRequest(BaseModel):
    """Payload to update an approved course's attributes (AICTE officer only)."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    level: str | None = Field(default=None, pattern="^(UG|PG|Diploma|PGDM)$")
    branch: str | None = Field(default=None, min_length=2, max_length=255)
    duration_years: int | None = Field(default=None, ge=1, le=6)
    supernumerary_allowed: bool | None = None


class CourseIntakeUpdateRequest(BaseModel):
    """Payload to create or update approved intake quota (AICTE officer only)."""

    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    approved_intake: int = Field(..., ge=0)
    supernumerary_seats_allowed: int = Field(default=0, ge=0)
    change_reason: str | None = Field(default=None, max_length=1000)


class InstitutionResponse(BaseModel):
    """Approved educational institution details."""

    id: int
    aicte_id: str
    name: str
    state: str
    district: str
    address: str
    official_email: str
    official_phone: str
    head_name: str
    affiliating_university: str
    approval_status: str
    approval_valid_to: date | None
    account_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstitutionListResponse(BaseModel):
    """Paginated list of educational institutions."""

    total: int
    items: list[InstitutionResponse]


class InstitutionUpdateRequest(BaseModel):
    """Payload for AICTE officer to update AICTE-owned institution attributes."""

    official_email: str | None = None
    official_phone: str | None = None
    head_name: str | None = None
    address: str | None = None
    affiliating_university: str | None = None
    approval_status: str | None = Field(
        default=None, pattern="^(active|suspended|withdrawn|expired)$"
    )
    approval_valid_to: date | None = None


class ApprovalStatusUpdateRequest(BaseModel):
    """Payload to adjust institution approval status (AICTE officer only)."""

    approval_status: str = Field(..., pattern="^(active|suspended|withdrawn|expired)$")
    approval_valid_to: date | None = None
    reason: str | None = Field(default=None, max_length=1000)


class CorrectionRequestCreate(BaseModel):
    """Payload for a college to raise a correction request for AICTE-owned data."""

    kind: str = Field(..., min_length=2, max_length=100)
    payload_json: dict[str, Any] = Field(...)


class CorrectionRequestResponse(BaseModel):
    """Correction request status and resolution record."""

    id: int
    institution_id: int
    kind: str
    payload_json: dict[str, Any]
    status: str
    resolved_by: int | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CorrectionRequestResolve(BaseModel):
    """Payload for AICTE officer to approve or reject a correction request."""

    status: str = Field(..., pattern="^(approved|rejected)$")
    decision_note: str | None = Field(default=None, max_length=1000)
    apply_changes: bool = True


class MasterSyncRequest(BaseModel):
    """Payload to trigger master sync from external mock registry."""

    aicte_id: str | None = None
    academic_year: str = Field(default="2026-27", pattern=r"^\d{4}-\d{2}$")


class MasterSyncResponse(BaseModel):
    """Result summary of master sync."""

    status: str
    synced_institutions: int
    synced_courses: int
    synced_intakes: int
    details: list[str]


class UploadCreateRequest(BaseModel):
    """Payload to initiate a student CSV/Excel batch upload."""

    filename: str = Field(..., min_length=3, max_length=255)
    row_count: int = Field(default=0, ge=0)


class UploadResponse(BaseModel):
    """Upload session model representation."""

    id: int
    institution_id: int
    filename: str
    row_count: int
    status: str
    summary_json: dict[str, Any] | None
    uploaded_by: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
