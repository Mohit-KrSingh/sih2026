"""Pydantic schemas for post-lock student change requests."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChangeRequestCreate(BaseModel):
    """Payload to create a post-lock change request for a student."""

    student_id: int = Field(..., description="ID of the locked student record")
    field: str = Field(..., description="Field to modify (e.g., status, name, dob, etc.)")
    new_value: str = Field(..., description="Requested new value")
    reason: str = Field(..., min_length=5, description="Official justification for the change")
    document_ref: str | None = Field(
        None, description="Optional pre-uploaded storage document reference"
    )


class ChangeRequestDecision(BaseModel):
    """Decision payload for an AICTE officer."""

    decision: str = Field(..., pattern="^(approve|reject)$", description="'approve' or 'reject'")
    decision_note: str | None = Field(
        None, description="Optional explanation or directive from AICTE reviewer"
    )


class ChangeRequestStudentInfo(BaseModel):
    """Minimal student details for change request context."""

    id: int
    apaar_id: str
    name: str
    course_id: int | None = None
    course_name: str | None = None
    academic_year: str
    status: str
    is_locked: bool


class ChangeRequestInstitutionInfo(BaseModel):
    """Minimal institution details for change request context."""

    id: int
    aicte_id: str
    name: str
    state: str


class ChangeRequestResponse(BaseModel):
    """Comprehensive change request representation."""

    id: int
    student_id: int
    student: ChangeRequestStudentInfo | None = None
    institution_id: int
    institution: ChangeRequestInstitutionInfo | None = None
    field: str
    old_value: str | None = None
    new_value: str
    reason: str
    status: str  # pending | approved | rejected
    decided_by: int | None = None
    decided_by_email: str | None = None
    decided_at: datetime | None = None
    document_ref: str | None = None
    decision_note: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChangeRequestListResponse(BaseModel):
    """Paginated list of change requests."""

    items: list[ChangeRequestResponse]
    total: int
    limit: int
    offset: int
