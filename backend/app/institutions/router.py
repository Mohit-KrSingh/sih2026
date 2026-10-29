"""FastAPI Router for institutions, courses, intake, and corrections."""

from datetime import UTC, datetime
from typing import Annotated, Any

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
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_roles,
    verify_institution_access,
)
from app.auth.rate_limiter import RateLimiter
from app.auth.schemas import Role
from app.config import get_settings
from app.db import get_db, get_redis
from app.institutions import service
from app.institutions.schemas import (
    ActivationApproveRequest,
    ActivationDecisionResponse,
    ActivationInitiateRequest,
    ActivationInitiateResponse,
    ActivationOtpVerifyRequest,
    ActivationOtpVerifyResponse,
    ActivationRejectRequest,
    ActivationRequestResponse,
    ActivationStatusResponse,
    ActivationSubmitRequest,
    ApprovalStatusUpdateRequest,
    ContactChangeRequestCreate,
    CorrectionRequestCreate,
    CorrectionRequestResolve,
    CorrectionRequestResponse,
    CourseCreateRequest,
    CourseIntakeHistoryResponse,
    CourseIntakeResponse,
    CourseIntakeUpdateRequest,
    CourseResponse,
    CourseUpdateRequest,
    InstitutionListResponse,
    InstitutionResponse,
    InstitutionUpdateRequest,
    MasterSyncRequest,
    MasterSyncResponse,
    StaffCreateRequest,
    StaffListResponse,
    StaffResponse,
    StaffUpdateRequest,
    UploadCreateRequest,
    UploadResponse,
)
from app.integrations.factory import get_storage
from app.models import User

router = APIRouter(prefix="/institutions", tags=["institutions"])
settings = get_settings()

# Role requirements
aicte_officer_guard = Depends(require_roles(Role.AICTE_ADMIN.value, Role.AICTE_OFFICER.value))
college_admin_guard = Depends(require_roles(Role.COLLEGE_ADMIN.value))
college_staff_guard = Depends(require_roles(Role.COLLEGE_ADMIN.value, Role.COLLEGE_STAFF.value))

# Rate limiter for OTP operations
activation_otp_limiter = RateLimiter(
    times=settings.RATE_LIMIT_OTP_PER_MINUTE,
    seconds=60,
    label="activation_otp",
)


# College Activation Endpoints (Spec 11, TASKS.md T08)


@router.post(
    "/activation/initiate",
    response_model=ActivationInitiateResponse,
    dependencies=[Depends(activation_otp_limiter)],
    summary="Initiate college activation claim by AICTE ID",
)
def initiate_college_activation(
    payload: ActivationInitiateRequest,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> ActivationInitiateResponse:
    """Claim institution by AICTE ID. OTP is sent ONLY to on-file contacts."""
    return service.initiate_activation(
        db=db,
        redis_client=redis_client,
        aicte_id=payload.aicte_id,
    )


@router.post(
    "/activation/verify-otp",
    response_model=ActivationOtpVerifyResponse,
    dependencies=[Depends(activation_otp_limiter)],
    summary="Verify OTP sent to on-file contact",
)
def verify_college_activation_otp(
    payload: ActivationOtpVerifyRequest,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> ActivationOtpVerifyResponse:
    """Verify one-time verification code and issue activation token."""
    return service.verify_activation_otp(
        db=db,
        redis_client=redis_client,
        aicte_id=payload.aicte_id,
        otp_code=payload.otp_code,
    )


@router.post(
    "/activation/submit",
    response_model=ActivationRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit activation claim with signatory info and encoded letter",
)
def submit_college_activation_json(
    payload: ActivationSubmitRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> ActivationRequestResponse:
    """Submit activation claim to AICTE queue (JSON payload)."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    req = service.submit_activation_claim(
        db=db,
        payload=payload,
        ip=client_ip,
    )
    return ActivationRequestResponse(
        id=req.id,
        institution_id=req.institution_id,
        institution_aicte_id=req.institution.aicte_id,
        institution_name=req.institution.name,
        signatory_name=req.signatory_name,
        signatory_ref=req.signatory_ref,
        letter_ref=req.letter_ref,
        status=req.status,
        decided_by=req.decided_by,
        decided_at=req.decided_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


@router.post(
    "/activation/submit-form",
    response_model=ActivationRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit activation claim with multipart letter file upload",
)
async def submit_college_activation_multipart(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    activation_token: Annotated[str, Form(...)],
    signatory_name: Annotated[str, Form(...)],
    signatory_ref: Annotated[str, Form(...)],
    letter_file: Annotated[UploadFile, File(...)],
) -> ActivationRequestResponse:
    """Submit activation claim to AICTE queue (Multipart form-data)."""
    file_bytes = await letter_file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded authorization letter is empty",
        )
    client_ip = request.client.host if request.client else "127.0.0.1"
    payload = ActivationSubmitRequest(
        activation_token=activation_token,
        signatory_name=signatory_name,
        signatory_ref=signatory_ref,
    )
    req = service.submit_activation_claim(
        db=db,
        payload=payload,
        file_bytes=file_bytes,
        filename=letter_file.filename,
        content_type=letter_file.content_type,
        ip=client_ip,
    )
    return ActivationRequestResponse(
        id=req.id,
        institution_id=req.institution_id,
        institution_aicte_id=req.institution.aicte_id,
        institution_name=req.institution.name,
        signatory_name=req.signatory_name,
        signatory_ref=req.signatory_ref,
        letter_ref=req.letter_ref,
        status=req.status,
        decided_by=req.decided_by,
        decided_at=req.decided_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


@router.get(
    "/activation/status/{aicte_id}",
    response_model=ActivationStatusResponse,
    summary="Public status check for an institution activation",
)
def get_activation_status_by_id(
    aicte_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> ActivationStatusResponse:
    """Check current activation status of an institution by AICTE ID."""
    return service.get_activation_status(db=db, aicte_id=aicte_id)


# AICTE Officer Endpoints for Activation Queue


@router.get(
    "/activation/requests",
    response_model=list[ActivationRequestResponse],
    summary="List activation requests (AICTE Officer only)",
)
def list_activation_requests_queue(
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ActivationRequestResponse]:
    """Review queue of pending, approved, and rejected activation claims."""
    _, requests = service.list_activation_requests(
        db=db,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    return [
        ActivationRequestResponse(
            id=r.id,
            institution_id=r.institution_id,
            institution_aicte_id=r.institution.aicte_id,
            institution_name=r.institution.name,
            signatory_name=r.signatory_name,
            signatory_ref=r.signatory_ref,
            letter_ref=r.letter_ref,
            status=r.status,
            decided_by=r.decided_by,
            decided_at=r.decided_at,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in requests
    ]


@router.get(
    "/activation/requests/{request_id}",
    response_model=ActivationRequestResponse,
    summary="Get single activation request details (AICTE Officer only)",
)
def get_activation_request_details(
    request_id: int,
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
) -> ActivationRequestResponse:
    """View details of a specific activation request."""
    req = service.get_activation_request(db=db, request_id=request_id)
    return ActivationRequestResponse(
        id=req.id,
        institution_id=req.institution_id,
        institution_aicte_id=req.institution.aicte_id,
        institution_name=req.institution.name,
        signatory_name=req.signatory_name,
        signatory_ref=req.signatory_ref,
        letter_ref=req.letter_ref,
        status=req.status,
        decided_by=req.decided_by,
        decided_at=req.decided_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


@router.get(
    "/activation/requests/{request_id}/letter",
    summary="Download authorization letter (AICTE Officer only)",
)
def download_authorization_letter(
    request_id: int,
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Retrieve and stream the uploaded authorization letter document."""
    req = service.get_activation_request(db=db, request_id=request_id)
    storage = get_storage()
    try:
        content = storage.get(req.letter_ref)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authorization letter file not found in storage",
        )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{req.institution.aicte_id}_auth.pdf"'},
    )


@router.post(
    "/activation/requests/{request_id}/approve",
    response_model=ActivationDecisionResponse,
    summary="Approve college activation claim (AICTE Officer only)",
)
def approve_activation(
    request_id: int,
    payload: ActivationApproveRequest,
    request: Request,
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
) -> ActivationDecisionResponse:
    """Approve an activation claim, activate college account, and create admin with MFA."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    return service.approve_activation_request(
        db=db,
        request_id=request_id,
        current_user=current_user,
        admin_email=payload.admin_email,
        notes=payload.notes,
        ip=client_ip,
    )


@router.post(
    "/activation/requests/{request_id}/reject",
    response_model=ActivationDecisionResponse,
    summary="Reject college activation claim (AICTE Officer only)",
)
def reject_activation(
    request_id: int,
    payload: ActivationRejectRequest,
    request: Request,
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
) -> ActivationDecisionResponse:
    """Reject an activation claim with stated justification."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    return service.reject_activation_request(
        db=db,
        request_id=request_id,
        current_user=current_user,
        reason=payload.reason,
        ip=client_ip,
    )


# AICTE Master Sync & Global Correction Queue (Static Paths First)


@router.post(
    "/sync",
    response_model=MasterSyncResponse,
    summary="Sync from external AICTE Master Registry (AICTE Officer only)",
)
def sync_aicte_master(
    payload: MasterSyncRequest,
    request: Request,
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
) -> MasterSyncResponse:
    """Sync institutions, courses, and intake from the external master registry."""
    client_ip = request.client.host if request.client else None
    return service.sync_master_data(
        db=db,
        aicte_id=payload.aicte_id,
        academic_year=payload.academic_year,
        officer=current_user,
        ip=client_ip,
    )


@router.get(
    "/correction-requests",
    response_model=list[CorrectionRequestResponse],
    summary="List all correction requests (AICTE Officer only)",
)
def list_all_correction_requests(
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
    status: str | None = Query(default=None),
    institution_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[CorrectionRequestResponse]:
    """Review queue of correction requests across all colleges for AICTE officers."""
    _, requests = service.list_correction_requests(
        db=db,
        institution_id=institution_id,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    return [CorrectionRequestResponse.model_validate(r) for r in requests]


@router.patch(
    "/correction-requests/{request_id}/resolve",
    response_model=CorrectionRequestResponse,
    summary="Approve or reject a correction request (AICTE Officer only)",
)
def resolve_correction_request(
    request_id: int,
    payload: CorrectionRequestResolve,
    request: Request,
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
) -> CorrectionRequestResponse:
    """Resolve a correction request and conditionally apply changes to AICTE-owned data."""
    client_ip = request.client.host if request.client else None
    req = service.resolve_correction_request(
        db=db,
        request_id=request_id,
        payload=payload,
        officer=current_user,
        ip=client_ip,
    )
    return CorrectionRequestResponse.model_validate(req)


# Institution Listing and Detail


@router.get(
    "",
    response_model=InstitutionListResponse,
    summary="List institutions (scoped to college for college users, global for AICTE)",
)
def list_institutions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    state: str | None = Query(default=None),
    approval_status: str | None = Query(default=None),
    account_status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> InstitutionListResponse:
    """List institutions. College users only see their own institution."""
    if current_user.role in Role.college_roles():
        if current_user.institution_id is None:
            return InstitutionListResponse(total=0, items=[])
        inst = service.get_institution(db, current_user.institution_id)
        return InstitutionListResponse(total=1, items=[InstitutionResponse.model_validate(inst)])

    # AICTE roles see all institutions
    total, items = service.list_institutions(
        db=db,
        state=state,
        approval_status=approval_status,
        account_status=account_status,
        search=search,
        limit=limit,
        offset=offset,
    )
    return InstitutionListResponse(
        total=total,
        items=[InstitutionResponse.model_validate(i) for i in items],
    )


@router.get(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Get institution details",
)
def get_institution(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    db: Annotated[Session, Depends(get_db)],
) -> InstitutionResponse:
    """Get single institution details. Enforces institution scoping for colleges."""
    inst = service.get_institution(db, institution_id)
    return InstitutionResponse.model_validate(inst)


@router.patch(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Update official institution information (AICTE Officer only)",
)
def update_institution(
    institution_id: int,
    payload: InstitutionUpdateRequest,
    request: Request,
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
) -> InstitutionResponse:
    """Update AICTE-owned official institution fields (email, phone, head, address)."""
    client_ip = request.client.host if request.client else None
    inst = service.update_institution_info(
        db=db,
        institution_id=institution_id,
        payload=payload,
        officer=current_user,
        ip=client_ip,
    )
    return InstitutionResponse.model_validate(inst)


@router.patch(
    "/{institution_id}/approval-status",
    response_model=InstitutionResponse,
    summary="Update institution approval status (AICTE Officer only)",
)
def update_institution_approval_status(
    institution_id: int,
    payload: ApprovalStatusUpdateRequest,
    request: Request,
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
) -> InstitutionResponse:
    """Update approval status (active, suspended, withdrawn, expired)."""
    client_ip = request.client.host if request.client else None
    inst = service.update_approval_status(
        db=db,
        institution_id=institution_id,
        payload=payload,
        officer=current_user,
        ip=client_ip,
    )
    return InstitutionResponse.model_validate(inst)


# Course Endpoints


@router.get(
    "/{institution_id}/courses",
    response_model=list[CourseResponse],
    summary="List approved courses for an institution",
)
def list_courses(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CourseResponse]:
    """List approved courses for an institution with their current intake quotas."""
    courses = service.list_courses(db, institution_id)
    return [CourseResponse.model_validate(c) for c in courses]


@router.post(
    "/{institution_id}/courses",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an approved course (AICTE Officer only)",
)
def create_course(
    institution_id: int,
    payload: CourseCreateRequest,
    request: Request,
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
) -> CourseResponse:
    """Approve a new course and initial intake quota (AICTE Officer only)."""
    client_ip = request.client.host if request.client else None
    course = service.create_course(
        db=db,
        institution_id=institution_id,
        payload=payload,
        officer=current_user,
        ip=client_ip,
    )
    return CourseResponse.model_validate(course)


@router.get(
    "/{institution_id}/courses/{course_id}",
    response_model=CourseResponse,
    summary="Get course details",
)
def get_course(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    course_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> CourseResponse:
    """Fetch single course details for an institution."""
    course = service.get_course(db, course_id, institution_id=institution_id)
    return CourseResponse.model_validate(course)


@router.put(
    "/{institution_id}/courses/{course_id}",
    response_model=CourseResponse,
    summary="Update approved course attributes (AICTE Officer only)",
)
def update_course(
    institution_id: int,
    course_id: int,
    payload: CourseUpdateRequest,
    request: Request,
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
) -> CourseResponse:
    """Update approved course metadata (AICTE Officer only)."""
    client_ip = request.client.host if request.client else None
    # Verify course belongs to institution
    service.get_course(db, course_id, institution_id=institution_id)
    course = service.update_course(
        db=db,
        course_id=course_id,
        payload=payload,
        officer=current_user,
        ip=client_ip,
    )
    return CourseResponse.model_validate(course)


# Intake & Intake History Endpoints


@router.get(
    "/{institution_id}/courses/{course_id}/intake",
    response_model=list[CourseIntakeResponse],
    summary="Get approved intake quotas for a course",
)
def get_course_intakes(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    course_id: int,
    db: Annotated[Session, Depends(get_db)],
    academic_year: str | None = Query(default=None),
) -> list[CourseIntakeResponse]:
    """Retrieve approved intake quotas by academic year (read-only for colleges)."""
    service.get_course(db, course_id, institution_id=institution_id)
    intakes = service.get_course_intakes(db, course_id, academic_year=academic_year)
    return [CourseIntakeResponse.model_validate(i) for i in intakes]


@router.put(
    "/{institution_id}/courses/{course_id}/intake",
    response_model=CourseIntakeResponse,
    summary="Update approved intake quota with full history (AICTE Officer only)",
)
def update_course_intake(
    institution_id: int,
    course_id: int,
    payload: CourseIntakeUpdateRequest,
    request: Request,
    current_user: Annotated[User, aicte_officer_guard],
    db: Annotated[Session, Depends(get_db)],
) -> CourseIntakeResponse:
    """Update approved intake and supernumerary quotas. Appends full history and audit row."""
    client_ip = request.client.host if request.client else None
    service.get_course(db, course_id, institution_id=institution_id)
    intake = service.update_course_intake(
        db=db,
        course_id=course_id,
        payload=payload,
        officer=current_user,
        ip=client_ip,
    )
    return CourseIntakeResponse.model_validate(intake)


@router.get(
    "/{institution_id}/courses/{course_id}/intake/history",
    response_model=list[CourseIntakeHistoryResponse],
    summary="Get intake change history for a course",
)
def get_intake_history(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    course_id: int,
    db: Annotated[Session, Depends(get_db)],
    academic_year: str | None = Query(default=None),
) -> list[CourseIntakeHistoryResponse]:
    """View full audit history of all intake quota adjustments made by AICTE officers."""
    service.get_course(db, course_id, institution_id=institution_id)
    history = service.get_intake_history(db, course_id, academic_year=academic_year)
    return [CourseIntakeHistoryResponse.model_validate(h) for h in history]


# Correction Requests (Colleges create, view own)


@router.post(
    "/{institution_id}/correction-requests",
    response_model=CorrectionRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Raise a correction request for AICTE-owned data (College only)",
)
def create_correction_request(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    payload: CorrectionRequestCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CorrectionRequestResponse:
    """College files a formal correction request for AICTE-owned data."""
    client_ip = request.client.host if request.client else None
    req = service.create_correction_request(
        db=db,
        institution_id=institution_id,
        payload=payload,
        user=current_user,
        ip=client_ip,
    )
    return CorrectionRequestResponse.model_validate(req)


@router.get(
    "/{institution_id}/correction-requests",
    response_model=list[CorrectionRequestResponse],
    summary="List correction requests for an institution",
)
def list_institution_correction_requests(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    db: Annotated[Session, Depends(get_db)],
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[CorrectionRequestResponse]:
    """List correction requests filed by this institution."""
    _, requests = service.list_correction_requests(
        db=db,
        institution_id=institution_id,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    return [CorrectionRequestResponse.model_validate(r) for r in requests]


@router.get(
    "/{institution_id}/correction-requests/{request_id}",
    response_model=CorrectionRequestResponse,
    summary="Get single correction request detail",
)
def get_correction_request_detail(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    request_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> CorrectionRequestResponse:
    """Get status and details of a single correction request."""
    req = service.get_correction_request(db, request_id)
    if req.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Correction request {request_id} does not belong to institution {institution_id}"
            ),
        )
    return CorrectionRequestResponse.model_validate(req)


# Upload Gate (Enforcing Suspended Approval Blocks Uploads)


@router.post(
    "/{institution_id}/uploads",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate student data upload (Blocked if institution approval is not active)",
)
def create_upload_session(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    payload: UploadCreateRequest,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> UploadResponse:
    """Initiate an upload session. Rejects with HTTP 403 if institution approval is suspended."""
    upload = service.create_upload_session(
        db=db,
        institution_id=institution_id,
        payload=payload,
        user=current_user,
    )
    return UploadResponse.model_validate(upload)


# Staff Management Endpoints (Spec 5, 6, 11, TASKS.md T09)


@router.post(
    "/{institution_id}/staff",
    response_model=StaffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create staff account with role under institution (College Admin only)",
)
def create_institution_staff(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    payload: StaffCreateRequest,
    request: Request,
    current_user: Annotated[User, college_admin_guard],
    db: Annotated[Session, Depends(get_db)],
) -> StaffResponse:
    """College admin provisions a staff user account with limited roles.

    Role limits (Spec 5 & 11):
    - Only college_admin can manage staff.
    - Staff members cannot manage staff (403 Forbidden).
    """
    client_ip = request.client.host if request.client else None
    staff_user = service.create_staff(
        db=db,
        institution_id=institution_id,
        payload=payload,
        current_user=current_user,
        ip=client_ip,
    )
    return StaffResponse.model_validate(staff_user)


@router.get(
    "/{institution_id}/staff",
    response_model=StaffListResponse,
    summary="List staff accounts under institution (College Admin only)",
)
def list_institution_staff(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[User, college_admin_guard],
    db: Annotated[Session, Depends(get_db)],
    role: str | None = Query(default=None, description="Filter by role"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> StaffListResponse:
    """List staff accounts under this college. College staff cannot view or manage staff."""
    total, staff_members = service.list_staff(
        db=db,
        institution_id=institution_id,
        role=role,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return StaffListResponse(
        total=total,
        items=[StaffResponse.model_validate(u) for u in staff_members],
    )


@router.get(
    "/{institution_id}/staff/{user_id}",
    response_model=StaffResponse,
    summary="Get single staff account details (College Admin only)",
)
def get_institution_staff(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    user_id: int,
    current_user: Annotated[User, college_admin_guard],
    db: Annotated[Session, Depends(get_db)],
) -> StaffResponse:
    """Retrieve details of a single staff member."""
    user = service.get_staff(db=db, institution_id=institution_id, user_id=user_id)
    return StaffResponse.model_validate(user)


@router.patch(
    "/{institution_id}/staff/{user_id}",
    response_model=StaffResponse,
    summary="Update staff role, status, or password (College Admin only)",
)
def update_institution_staff(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    user_id: int,
    payload: StaffUpdateRequest,
    request: Request,
    current_user: Annotated[User, college_admin_guard],
    db: Annotated[Session, Depends(get_db)],
) -> StaffResponse:
    """Update staff account attributes. College staff cannot manage staff."""
    client_ip = request.client.host if request.client else None
    updated_user = service.update_staff(
        db=db,
        institution_id=institution_id,
        user_id=user_id,
        payload=payload,
        current_user=current_user,
        ip=client_ip,
    )
    return StaffResponse.model_validate(updated_user)


@router.delete(
    "/{institution_id}/staff/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate staff account (College Admin only)",
)
def delete_institution_staff(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    user_id: int,
    request: Request,
    current_user: Annotated[User, college_admin_guard],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Deactivate a staff account."""
    client_ip = request.client.host if request.client else None
    service.delete_staff(
        db=db,
        institution_id=institution_id,
        user_id=user_id,
        current_user=current_user,
        ip=client_ip,
    )
    return {"status": "success", "message": f"Staff user {user_id} deactivated"}


# Contact or Head Change Requests (Spec 6, 11)


@router.post(
    "/{institution_id}/contact-change-requests",
    response_model=CorrectionRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request contact or head change to AICTE (College Admin only)",
)
def request_contact_change(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    payload: ContactChangeRequestCreate,
    request: Request,
    current_user: Annotated[User, college_admin_guard],
    db: Annotated[Session, Depends(get_db)],
) -> CorrectionRequestResponse:
    """Raise a contact or head change request to AICTE.

    Spec 6 & 11:
    - Colleges never edit AICTE-owned official contacts directly (403 Forbidden).
    - Requests go to AICTE review queue for official approval.
    """
    client_ip = request.client.host if request.client else None
    req = service.create_contact_change_request(
        db=db,
        institution_id=institution_id,
        payload=payload,
        current_user=current_user,
        ip=client_ip,
    )
    return CorrectionRequestResponse.model_validate(req)


# Final Submit Gate (Spec 5, 10, TASKS.md T09)


@router.post(
    "/{institution_id}/submit",
    status_code=status.HTTP_200_OK,
    summary="Final submit gate check for student data (College Admin only)",
)
def submit_student_data_gate(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[User, college_admin_guard],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Submit gate enforcement (Spec 5 & 10):

    - Only college_admin can submit data.
    - College staff and viewers are strictly rejected with HTTP 403 Forbidden.
    """
    return {
        "status": "authorized",
        "institution_id": institution_id,
        "role": current_user.role,
        "submitted_by": current_user.email,
        "message": "Authorized: college_admin has submit permission",
    }


# Institutional Notifications (Spec 7, TASKS.md T16, T24)


@router.get(
    "/{institution_id}/notifications",
    summary="Get system notifications for this institution",
)
def get_institution_notifications(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[
        User,
        Depends(
            require_roles(
                Role.COLLEGE_ADMIN.value,
                Role.COLLEGE_STAFF.value,
                Role.COLLEGE_VIEWER.value,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, Any]]:
    """Retrieve all notifications sent to this institution."""
    from app.models import Notification

    stmt = (
        select(Notification)
        .where(Notification.institution_id == institution_id)
        .order_by(Notification.id.desc())
        .limit(limit)
    )
    items = db.scalars(stmt).all()
    return [
        {
            "id": n.id,
            "institution_id": n.institution_id,
            "type": n.type,
            "payload": n.payload_json,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in items
    ]


@router.patch(
    "/{institution_id}/notifications/{notification_id}/read",
    summary="Mark a specific notification as read",
)
def mark_institution_notification_read(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    notification_id: int,
    current_user: Annotated[
        User,
        Depends(
            require_roles(
                Role.COLLEGE_ADMIN.value,
                Role.COLLEGE_STAFF.value,
                Role.COLLEGE_VIEWER.value,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Mark a notification as read by this institution."""
    from app.models import Notification

    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.institution_id == institution_id,
    )
    notif = db.scalars(stmt).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if not notif.read_at:
        notif.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notif)

    return {
        "status": "success",
        "id": notif.id,
        "read_at": notif.read_at.isoformat() if notif.read_at else None,
    }


@router.post(
    "/{institution_id}/notifications/mark-all-read",
    summary="Mark all notifications as read for this institution",
)
def mark_all_institution_notifications_read(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    current_user: Annotated[
        User,
        Depends(
            require_roles(
                Role.COLLEGE_ADMIN.value,
                Role.COLLEGE_STAFF.value,
                Role.COLLEGE_VIEWER.value,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Mark all unread notifications as read."""
    from app.models import Notification

    stmt = (
        update(Notification)
        .where(
            Notification.institution_id == institution_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    res = db.execute(stmt)
    db.commit()
    return {"status": "success", "marked_read_count": res.rowcount}
