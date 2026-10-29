"""FastAPI routes for validation flags, justifications, and document downloads."""

from typing import Annotated

import redis
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    require_college_admin,
    require_college_staff,
    require_college_user,
    verify_institution_access,
)
from app.db import get_db, get_redis
from app.models import User
from app.submissions import service
from app.submissions.schemas import (
    InstitutionFlagsListResponse,
    JustificationResponse,
    SubmissionGateResponse,
    SubmissionOtpRequest,
    SubmissionOtpResponse,
    SubmissionReceiptResponse,
    SubmissionSubmitRequest,
    ValidationFlagDetailResponse,
)

router = APIRouter(prefix="/institutions/{institution_id}", tags=["Flags & Justifications"])


@router.get(
    "/flags",
    response_model=InstitutionFlagsListResponse,
    summary="List validation flags with justification details and submit gate summary",
)
def get_institution_flags(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[User, require_college_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str | None, Query(description="Filter by academic year")] = None,
    level: Annotated[str | None, Query(description="Filter level")] = None,
    status_filter: Annotated[str | None, Query(alias="status", description="Filter status")] = None,
    rule_code: Annotated[str | None, Query(description="Filter by rule code")] = None,
    course_id: Annotated[int | None, Query(description="Filter by course ID")] = None,
    student_id: Annotated[int | None, Query(description="Filter by student ID")] = None,
    requires_justification: Annotated[
        bool | None, Query(description="Filter by justification requirement")
    ] = None,
    search: Annotated[str | None, Query(description="Search text")] = None,
) -> InstitutionFlagsListResponse:
    """Retrieve all validation flags for an institution with statistical summary and gate status."""
    return service.list_institution_flags(
        db=db,
        institution_id=institution_id,
        academic_year=academic_year,
        level=level,
        flag_status=status_filter,
        rule_code=rule_code,
        course_id=course_id,
        student_id=student_id,
        requires_justification=requires_justification,
        search=search,
    )


@router.get(
    "/flags/{flag_id}",
    response_model=ValidationFlagDetailResponse,
    summary="Get single validation flag detail and attached justifications",
)
def get_flag_detail(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    flag_id: int,
    current_user: Annotated[User, require_college_user],
    db: Annotated[Session, Depends(get_db)],
) -> ValidationFlagDetailResponse:
    """Retrieve single validation flag record with student/course target and justification."""
    flag = service.get_flag_or_404(db=db, flag_id=flag_id, institution_id=institution_id)
    return service.map_flag_to_response(flag, institution_id)


@router.post(
    "/flags/{flag_id}/justifications",
    response_model=JustificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit written justification and optional supporting document for a flag",
)
async def create_flag_justification(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    flag_id: int,
    request: Request,
    current_user: Annotated[User, require_college_staff],
    db: Annotated[Session, Depends(get_db)],
    text: Annotated[str | None, Form()] = None,
    document: Annotated[UploadFile | None, File()] = None,
) -> JustificationResponse:
    """Write an official justification and attach an evidence document for an exception or warning.

    Rejects error-level flags (SPEC.md Section 9.1: error flags must be fixed in data).
    Uploads supporting document via Storage interface.
    Transitions flag status to 'justified'.
    Appends audit log entry.
    """
    final_text: str | None = text
    doc_ref: str | None = None

    # Handle application/json payloads as fallback for API/scripted clients
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            final_text = body.get("text")
            doc_ref = body.get("document_ref")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            ) from None

    if not final_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Justification text is required",
        )

    return await service.create_flag_justification(
        db=db,
        institution_id=institution_id,
        flag_id=flag_id,
        user=current_user,
        text=final_text,
        document_file=document,
        document_ref=doc_ref,
    )


@router.get(
    "/justifications/{justification_id}/document",
    summary="Download attached supporting document for a justification",
)
def download_justification_document(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    justification_id: int,
    current_user: Annotated[User, require_college_user],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Stream justification supporting document from Storage interface."""
    content, filename, media_type = service.get_justification_document_file(
        db=db,
        institution_id=institution_id,
        justification_id=justification_id,
        user=current_user,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.delete(
    "/justifications/{justification_id}",
    summary="Remove a justification before final submission",
)
def delete_justification(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    justification_id: int,
    current_user: Annotated[User, require_college_staff],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str | int]:
    """Remove a justification. If no justifications remain on the flag, reverts flag to open."""
    return service.delete_flag_justification(
        db=db,
        institution_id=institution_id,
        justification_id=justification_id,
        user=current_user,
    )


# Submission Lifecycle and Submit Gate Endpoints (SPEC.md Section 10 & TASKS.md T23)


@router.get(
    "/submissions/gate",
    response_model=SubmissionGateResponse,
    summary="Evaluate final submit gate readiness, blockers, and locking status",
)
def get_submission_gate(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[User, require_college_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
) -> SubmissionGateResponse:
    """Evaluate whether institution data satisfies all gate criteria for submission."""
    return service.check_submission_gate(
        db=db,
        institution_id=institution_id,
        academic_year=academic_year,
    )


@router.post(
    "/submissions/declaration-otp",
    response_model=SubmissionOtpResponse,
    summary="Request a verification OTP for final submission declaration",
)
def request_submission_declaration_otp(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    payload: SubmissionOtpRequest,
    current_user: Annotated[User, require_college_admin],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> SubmissionOtpResponse:
    """Send a mock verification OTP for submission declaration to the admin's email."""
    return service.send_declaration_otp(
        db=db,
        redis_client=redis_client,
        institution_id=institution_id,
        academic_year=payload.academic_year,
        user=current_user,
    )


@router.post(
    "/submissions/submit",
    response_model=SubmissionReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm declaration with OTP and lock data for final submission (college_admin only)",
)
def submit_institution_data(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    payload: SubmissionSubmitRequest,
    request: Request,
    current_user: Annotated[User, require_college_admin],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> SubmissionReceiptResponse:
    """Submit and lock annual student data into AICTE Central Repository with receipt."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    return service.submit_annual_data(
        db=db,
        redis_client=redis_client,
        institution_id=institution_id,
        user=current_user,
        payload=payload,
        client_ip=client_ip,
    )


@router.get(
    "/submissions/receipt",
    response_model=SubmissionReceiptResponse,
    summary="Get official submission receipt and locked record counts",
)
def get_submission_receipt(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[User, require_college_user],
    db: Annotated[Session, Depends(get_db)],
    academic_year: Annotated[str, Query(description="Academic year")] = "2026-27",
) -> SubmissionReceiptResponse:
    """Retrieve official submission receipt details for an already submitted academic year."""
    return service.get_submission_receipt(
        db=db,
        institution_id=institution_id,
        academic_year=academic_year,
    )
