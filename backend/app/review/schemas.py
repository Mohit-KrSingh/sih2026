"""Pydantic v2 schemas for AICTE Review Queue and College Clarification Queries."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReviewDecisionRequest(BaseModel):
    """Payload submitted by an AICTE officer to record a review decision."""

    decision: Literal["accept", "query", "escalate"] = Field(
        description="Review action: accept (approve), query (ask college), escalate (refer)"
    )
    note: str = Field(
        min_length=3,
        max_length=2000,
        description="Official note detailing the decision rationale or clarification inquiry",
    )


class ReviewJustificationDetail(BaseModel):
    """Attached justification and document reference for a validation flag."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    flag_id: int
    text: str
    document_ref: str | None = None
    document_filename: str | None = None
    by_user_id: int | None = None
    by_user_email: str | None = None
    at: str


class ReviewFlagDetail(BaseModel):
    """Validation flag details associated with an exception in the review queue."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    rule_code: str
    level: str
    field: str | None = None
    row_ref: str | None = None
    message: str
    fix_hint: str | None = None
    status: str
    student_id: int | None = None
    student_name: str | None = None
    student_apaar: str | None = None
    course_id: int | None = None
    course_name: str | None = None
    branch: str | None = None
    justifications: list[ReviewJustificationDetail] = []


class QueryItemResponse(BaseModel):
    """Clarification query thread between AICTE officers and institution staff."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    review_item_id: int | None = None
    submission_id: int
    message: str
    response: str | None = None
    state: str  # pending | answered | closed
    created_by: int | None = None
    created_by_email: str | None = None
    responded_by: int | None = None
    responded_by_email: str | None = None
    created_at: str
    responded_at: str | None = None


class ReviewItemSummary(BaseModel):
    """Summary record for displaying a submission review item in the AICTE queue."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    institution_id: int
    institution_name: str
    aicte_id: str
    state: str
    academic_year: str
    receipt_no: str | None = None
    status: str  # pending | under_review | accepted | query_raised | escalated
    decision: str | None = None
    decision_note: str | None = None
    decided_at: str | None = None
    assigned_to: int | None = None
    assigned_to_email: str | None = None
    flag_ids: list[int] = []
    rule_codes: list[str] = []
    flag_count: int = 0
    pending_queries_count: int = 0
    created_at: str
    updated_at: str


class ReviewItemListResponse(BaseModel):
    """List response for AICTE review items with statistical counts."""

    total: int
    pending_count: int
    under_review_count: int
    queries_raised_count: int
    escalated_count: int
    accepted_count: int
    items: list[ReviewItemSummary]


class ReviewItemDetailResponse(BaseModel):
    """Detailed review item context including flags, student rows, documents, and query history."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    submission_id: int
    institution_id: int
    institution_name: str
    aicte_id: str
    state: str
    district: str | None = None
    academic_year: str
    submission_status: str
    receipt_no: str | None = None
    submitted_at: str | None = None
    status: str
    decision: str | None = None
    decision_note: str | None = None
    decided_at: str | None = None
    assigned_to: int | None = None
    assigned_to_email: str | None = None
    flags: list[ReviewFlagDetail] = []
    queries: list[QueryItemResponse] = []
    created_at: str
    updated_at: str


class CollegeQueryResponse(BaseModel):
    """Query record presented to a college for response and clarification."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    review_item_id: int | None = None
    submission_id: int
    institution_id: int
    institution_name: str
    academic_year: str
    receipt_no: str | None = None
    message: str
    response: str | None = None
    state: str  # pending | answered | closed
    created_at: str
    responded_at: str | None = None
    officer_name: str | None = None
    flags: list[ReviewFlagDetail] = []


class CollegeQueryListResponse(BaseModel):
    """List response for college clarification queries."""

    total: int
    pending_count: int
    items: list[CollegeQueryResponse]


class CollegeQueryRespondRequest(BaseModel):
    """Payload submitted by a college to answer an AICTE officer's clarification query."""

    response: str = Field(
        min_length=5,
        max_length=3000,
        description="College's detailed answer, explanation, or reference resolving the inquiry",
    )
    document_ref: str | None = Field(
        default=None,
        description="Optional pre-uploaded document reference identifier",
    )
