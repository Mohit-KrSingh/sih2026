"""FastAPI Router for institutions, courses, intake, and corrections.

SPEC.md Section 6 & TASKS.md T07:
- Colleges never edit AICTE-owned data (intake, courses, approval status, contacts).
- AICTE officers can change intake, courses, and approval status with full history and audit.
- Mock AICTE master sync endpoint.
- Correction requests: college creates, AICTE resolves.
- Suspended/withdrawn/expired approval blocks uploads (403 Forbidden).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_roles,
    verify_institution_access,
)
from app.auth.schemas import Role
from app.db import get_db
from app.institutions import service
from app.institutions.schemas import (
    ApprovalStatusUpdateRequest,
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
    UploadCreateRequest,
    UploadResponse,
)
from app.models import User

router = APIRouter(prefix="/institutions", tags=["institutions"])

# Role requirements
aicte_officer_guard = Depends(require_roles(Role.AICTE_ADMIN.value, Role.AICTE_OFFICER.value))
college_staff_guard = Depends(
    require_roles(Role.COLLEGE_ADMIN.value, Role.COLLEGE_STAFF.value)
)


# =========================================================================
# AICTE Master Sync & Global Correction Queue (Static Paths First)
# =========================================================================


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


# =========================================================================
# Institution Listing and Detail
# =========================================================================


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
        return InstitutionListResponse(
            total=1, items=[InstitutionResponse.model_validate(inst)]
        )

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


# =========================================================================
# Course Endpoints
# =========================================================================


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


# =========================================================================
# Intake & Intake History Endpoints
# =========================================================================


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


# =========================================================================
# Correction Requests (Colleges create, view own)
# =========================================================================


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
                f"Correction request {request_id} does not "
                f"belong to institution {institution_id}"
            ),
        )
    return CorrectionRequestResponse.model_validate(req)


# =========================================================================
# Upload Gate (Enforcing Suspended Approval Blocks Uploads)
# =========================================================================


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
