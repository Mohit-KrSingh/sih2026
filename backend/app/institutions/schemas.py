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


# Activation Schemas (Spec 11, TASKS.md T08)


class ActivationInitiateRequest(BaseModel):
    """Payload to initiate college account activation claim."""

    aicte_id: str = Field(..., min_length=3, max_length=50)


class ActivationInitiateResponse(BaseModel):
    """Response containing masked on-file contact details where OTP was dispatched."""

    aicte_id: str
    institution_name: str
    masked_email: str
    masked_phone: str
    status: str
    message: str


class ActivationOtpVerifyRequest(BaseModel):
    """Payload to verify OTP sent to official contact on file."""

    aicte_id: str = Field(..., min_length=3, max_length=50)
    otp_code: str = Field(..., min_length=4, max_length=8)


class ActivationOtpVerifyResponse(BaseModel):
    """Response returned upon successful OTP verification with short-lived session token."""

    verified: bool
    activation_token: str
    aicte_id: str
    institution_name: str
    head_name: str
    message: str


class ActivationSubmitRequest(BaseModel):
    """Payload to submit signatory verification and authorization claim."""

    activation_token: str
    signatory_name: str = Field(..., min_length=2, max_length=255)
    signatory_ref: str = Field(..., min_length=2, max_length=255)
    letter_content_b64: str | None = None
    letter_filename: str | None = "authorisation_letter.pdf"


class ActivationRequestResponse(BaseModel):
    """Activation claim details for institution and AICTE queues."""

    id: int
    institution_id: int
    institution_aicte_id: str
    institution_name: str
    signatory_name: str
    signatory_ref: str
    letter_ref: str
    status: str  # pending | approved | rejected
    decided_by: int | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivationApproveRequest(BaseModel):
    """Optional payload for AICTE officer to approve activation."""

    admin_email: str | None = None
    notes: str | None = None


class ActivationRejectRequest(BaseModel):
    """Payload for AICTE officer to reject activation."""

    reason: str = Field(..., min_length=3, max_length=1000)


class ActivationDecisionResponse(BaseModel):
    """Response returned when an AICTE officer decides on an activation claim."""

    request_id: int
    institution_id: int
    status: str  # approved | rejected
    institution_account_status: str
    admin_user_id: int | None = None
    admin_email: str | None = None
    initial_password: str | None = None
    mfa_enabled: bool = True
    mfa_secret: str | None = None
    mfa_uri: str | None = None
    message: str


class ActivationStatusResponse(BaseModel):
    """Public activation status summary for an institution."""

    aicte_id: str
    institution_name: str
    account_status: str
    approval_status: str
    has_pending_request: bool
    latest_request_status: str | None = None
    latest_request_id: int | None = None


# Staff Management Schemas (Spec 5, 6, 11, TASKS.md T09)


class StaffCreateRequest(BaseModel):
    """Payload for college_admin to create staff accounts with limited roles."""

    email: str = Field(..., min_length=3, max_length=255, description="Staff user email address")
    password: str = Field(
        ...,
        min_length=8,
        description="Initial account password (min 8 characters)",
    )
    role: str = Field(
        default="college_staff",
        description="Role assignment: college_staff, college_viewer, or college_admin",
    )


class StaffUpdateRequest(BaseModel):
    """Payload to update staff account role, active status, or password."""

    role: str | None = Field(default=None, description="Updated role")
    is_active: bool | None = Field(default=None, description="Active status toggle")
    password: str | None = Field(default=None, min_length=8, description="New password")


class StaffResponse(BaseModel):
    """Staff account representation."""

    id: int
    email: str
    role: str
    institution_id: int
    is_active: bool
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StaffListResponse(BaseModel):
    """Paginated list of staff members for an institution."""

    total: int
    items: list[StaffResponse]


class ContactChangeRequestCreate(BaseModel):
    """Payload to request changes to AICTE-owned official institution contacts or head."""

    official_email: str | None = Field(
        default=None,
        min_length=3,
        max_length=255,
        description="Proposed new official email",
    )
    official_phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=50,
        description="Proposed new official phone",
    )
    head_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="Proposed new head of institution",
    )
    address: str | None = Field(
        default=None,
        min_length=5,
        description="Proposed new official address",
    )
    reason: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Justification/reason for contact change",
    )
