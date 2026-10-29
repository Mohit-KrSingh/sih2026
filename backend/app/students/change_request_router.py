"""API routes for post-lock student change requests."""

import io
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_aicte_user,
    require_college_staff,
    require_college_user,
    verify_institution_access,
)
from app.auth.schemas import UserResponse
from app.db import get_db
from app.integrations.factory import get_storage
from app.models import ChangeRequest
from app.students.change_request_schemas import (
    ChangeRequestDecision,
    ChangeRequestListResponse,
    ChangeRequestResponse,
)
from app.students.change_request_service import (
    create_change_request,
    decide_change_request,
    get_change_request_detail,
    list_change_requests,
)

# Router for college institution routes
college_router = APIRouter(
    prefix="/institutions/{institution_id}/change-requests",
    tags=["College Change Requests"],
)

# Router for AICTE review queue routes
aicte_router = APIRouter(
    prefix="/change-requests",
    tags=["AICTE Change Requests"],
)


# College Endpoints


@college_router.post(
    "",
    response_model=ChangeRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a post-lock change request with reason and evidence",
)
async def submit_student_change_request(
    request: Request,
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[UserResponse, require_college_staff],
    db: Annotated[Session, Depends(get_db)],
    student_id: Annotated[int | None, Form()] = None,
    field: Annotated[str | None, Form()] = None,
    field_name: Annotated[str | None, Form()] = None,
    new_value: Annotated[str | None, Form()] = None,
    reason: Annotated[str | None, Form()] = None,
    document: Annotated[UploadFile | None, File()] = None,
    evidence: Annotated[UploadFile | None, File()] = None,
) -> ChangeRequestResponse:
    """Submit a formal change request for a locked student record.

    Accepts multipart/form-data with evidence document or JSON payload fallback.
    """
    final_student_id = student_id
    final_field = field or field_name
    final_new_value = new_value
    final_reason = reason
    final_doc = document or evidence
    doc_ref: str | None = None

    # Support JSON fallback
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            final_student_id = body.get("student_id")
            final_field = body.get("field") or body.get("field_name")
            final_new_value = body.get("new_value")
            final_reason = body.get("reason")
            doc_ref = body.get("document_ref")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            ) from None

    if not final_student_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="student_id is required",
        )
    if not final_field:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="field is required",
        )
    if final_new_value is None or str(final_new_value).strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_value is required",
        )
    if not final_reason or len(str(final_reason).strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason must be at least 5 characters long",
        )

    return await create_change_request(
        db=db,
        institution_id=institution_id,
        student_id=int(final_student_id),
        field=str(final_field),
        new_value=str(final_new_value),
        reason=str(final_reason),
        user=current_user,
        document_file=final_doc,
        document_ref=doc_ref,
    )


@college_router.get(
    "",
    response_model=ChangeRequestListResponse,
    summary="List change requests for an institution",
)
def list_institution_change_requests(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[UserResponse, require_college_user],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    academic_year: Annotated[str | None, Query()] = None,
    student_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ChangeRequestListResponse:
    """List change requests belonging to this institution."""
    return list_change_requests(
        db=db,
        institution_id=institution_id,
        status_filter=status_filter,
        academic_year=academic_year,
        student_id=student_id,
        limit=limit,
        offset=offset,
    )


@college_router.get(
    "/{request_id}",
    response_model=ChangeRequestResponse,
    summary="Get single change request detail for an institution",
)
def get_institution_change_request(
    request_id: int,
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[UserResponse, require_college_user],
    db: Annotated[Session, Depends(get_db)],
) -> ChangeRequestResponse:
    """Get change request detail, enforcing institution scoping."""
    return get_change_request_detail(
        db=db,
        request_id=request_id,
        institution_id=institution_id,
    )


@college_router.get(
    "/{request_id}/evidence",
    summary="Download evidence document attached to change request",
)
def download_institution_change_request_evidence(
    request_id: int,
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[UserResponse, require_college_user],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """Download the attached evidence document for this institution's change request."""
    cr = db.get(ChangeRequest, request_id)
    if not cr or not cr.student or cr.student.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found",
        )
    if not cr.document_ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evidence document attached to this change request",
        )

    storage = get_storage()
    try:
        file_bytes = storage.get(cr.document_ref)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence file not found in storage",
        ) from None

    content_type = "application/pdf"
    if cr.document_ref.lower().endswith(".png"):
        content_type = "image/png"
    elif cr.document_ref.lower().endswith((".jpg", ".jpeg")):
        content_type = "image/jpeg"

    filename = cr.document_ref.split("/")[-1]
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# AICTE Review Queue Endpoints


@aicte_router.get(
    "",
    response_model=ChangeRequestListResponse,
    summary="Global change requests queue for AICTE officers",
)
def list_all_change_requests_for_aicte(
    current_user: Annotated[UserResponse, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    institution_id: Annotated[int | None, Query()] = None,
    academic_year: Annotated[str | None, Query()] = None,
    student_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ChangeRequestListResponse:
    """List change requests across all institutions for AICTE review."""
    return list_change_requests(
        db=db,
        institution_id=institution_id,
        status_filter=status_filter,
        academic_year=academic_year,
        student_id=student_id,
        limit=limit,
        offset=offset,
    )


@aicte_router.get(
    "/{request_id}",
    response_model=ChangeRequestResponse,
    summary="Get change request detail for AICTE review",
)
def get_aicte_change_request_detail(
    request_id: int,
    current_user: Annotated[UserResponse, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
) -> ChangeRequestResponse:
    """Retrieve detailed change request data across any institution for AICTE review."""
    return get_change_request_detail(db=db, request_id=request_id)


@aicte_router.get(
    "/{request_id}/evidence",
    summary="Download evidence document for AICTE review",
)
def download_aicte_change_request_evidence(
    request_id: int,
    current_user: Annotated[UserResponse, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """Download attached evidence document for AICTE review."""
    cr = db.get(ChangeRequest, request_id)
    if not cr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found",
        )
    if not cr.document_ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evidence document attached to this change request",
        )

    storage = get_storage()
    try:
        file_bytes = storage.get(cr.document_ref)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence file not found in storage",
        ) from None

    content_type = "application/pdf"
    if cr.document_ref.lower().endswith(".png"):
        content_type = "image/png"
    elif cr.document_ref.lower().endswith((".jpg", ".jpeg")):
        content_type = "image/jpeg"

    filename = cr.document_ref.split("/")[-1]
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@aicte_router.post(
    "/{request_id}/decision",
    response_model=ChangeRequestResponse,
    summary="Approve or reject a student change request",
)
def decide_student_change_request(
    request_id: int,
    payload: ChangeRequestDecision,
    current_user: Annotated[UserResponse, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
) -> ChangeRequestResponse:
    """Approve or reject a change request.

    If approved:
    - Changes are applied to the student record.
    - If status is changed to withdrawn or transferred, duplicate flags are resolved.
    - Audit log records before and after state.
    """
    return decide_change_request(
        db=db,
        request_id=request_id,
        decision=payload.decision,
        decision_note=payload.decision_note,
        officer=current_user,
    )
