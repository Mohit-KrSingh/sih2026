"""API routes for student records, uploads, and seat declarations."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_db,
    require_college_staff,
    verify_institution_access,
)
from app.models import User
from app.students import seat_declarations as seat_service
from app.students.schemas import (
    CourseSummaryResponse,
    InstitutionSeatDeclarationResponse,
    SeatDeclarationBatchSaveRequest,
    SeatDeclarationSaveRequest,
)

router = APIRouter(tags=["Seat Declarations & Student Management"])

college_staff_guard = require_college_staff


# =========================================================================
# Seat Declarations & Course Summary Endpoints (Spec 8.1, 13, TASKS.md T19)
# =========================================================================


@router.get(
    "/institutions/{institution_id}/seat-declarations",
    response_model=InstitutionSeatDeclarationResponse,
    summary="Get all course summaries and seat declarations for an institution",
)
def get_institution_seat_declarations(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    db: Annotated[Session, Depends(get_db)],
    academic_year: str = Query(default="2026-27", description="Academic year"),
) -> InstitutionSeatDeclarationResponse:
    """Retrieve course summary table and seat declarations for an institution.

    Spec 8.1 & 13:
    - Lists approved courses with read-only approved intake and supernumerary allowed.
    - Shows calculated active student enrolments from student records.
    - Returns declared seat counts and live validation status badges.
    """
    return seat_service.get_institution_seat_declarations(
        db=db,
        institution_id=institution_id,
        academic_year=academic_year,
    )


@router.get(
    "/institutions/{institution_id}/courses/{course_id}/seat-declaration",
    response_model=CourseSummaryResponse,
    summary="Get course summary and seat declaration for a single course",
)
def get_course_seat_declaration(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    course_id: int,
    db: Annotated[Session, Depends(get_db)],
    academic_year: str = Query(default="2026-27", description="Academic year"),
) -> CourseSummaryResponse:
    """Retrieve seat declaration and live validation status for a single course."""
    return seat_service.get_course_summary(
        db=db,
        institution_id=institution_id,
        course_id=course_id,
        academic_year=academic_year,
    )


@router.put(
    "/institutions/{institution_id}/courses/{course_id}/seat-declaration",
    response_model=CourseSummaryResponse,
    summary="Save or autosave a course seat declaration as draft (College Staff only)",
)
def save_course_seat_declaration(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    course_id: int,
    payload: SeatDeclarationSaveRequest,
    request: Request,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> CourseSummaryResponse:
    """Save or autosave a course seat declaration.

    Spec 8.1 & 13, TASKS.md T19:
    - Autosaves as a draft; invalid values show errors immediately but are still saved.
    - Enforces IDOR protection and institution approval status checks.
    - Emits audit log entry for changes.
    """
    client_ip = request.client.host if request.client else None
    return seat_service.save_course_seat_declaration(
        db=db,
        institution_id=institution_id,
        course_id=course_id,
        payload=payload,
        user=current_user,
        client_ip=client_ip,
    )


@router.put(
    "/institutions/{institution_id}/seat-declarations",
    response_model=InstitutionSeatDeclarationResponse,
    summary="Batch save or autosave seat declarations for multiple courses (College Staff only)",
)
def batch_save_seat_declarations(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    payload: SeatDeclarationBatchSaveRequest,
    request: Request,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> InstitutionSeatDeclarationResponse:
    """Batch save or autosave declarations across multiple approved courses."""
    client_ip = request.client.host if request.client else None
    return seat_service.batch_save_seat_declarations(
        db=db,
        institution_id=institution_id,
        payload=payload,
        user=current_user,
        client_ip=client_ip,
    )
