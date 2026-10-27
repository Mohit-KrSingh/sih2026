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
from app.students import service as student_service
from app.students.schemas import (
    CourseSummaryResponse,
    InstitutionSeatDeclarationResponse,
    SeatDeclarationBatchSaveRequest,
    SeatDeclarationSaveRequest,
    StudentCreateRequest,
    StudentListResponse,
    StudentResponse,
    StudentSaveResultResponse,
    StudentUpdateRequest,
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


# =========================================================================
# Single Student Entry & Directory Endpoints (Spec 8.2, 9.4, TASKS.md T20)
# =========================================================================


@router.get(
    "/institutions/{institution_id}/students",
    response_model=StudentListResponse,
    summary="List student records with status, flag level, and search filters",
)
def list_students(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    db: Annotated[Session, Depends(get_db)],
    academic_year: str | None = Query(
        default="2026-27", description="Filter by academic year"
    ),
    course_id: int | None = Query(
        default=None, description="Filter by course ID"
    ),
    status: str | None = Query(
        default=None, description="Filter by status (draft, valid, flagged, etc.)"
    ),
    level: str | None = Query(
        default=None, description="Filter by flag level (error, exception, warning, info, clean)"
    ),
    search: str | None = Query(
        default=None, description="Search by name, APAAR ID, or enrolment number"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> StudentListResponse:
    """Retrieve filtered and paginated list of student records for an institution."""
    return student_service.list_students(
        db=db,
        institution_id=institution_id,
        academic_year=academic_year,
        course_id=course_id,
        status_filter=status,
        level_filter=level,
        search=search,
        page=page,
        limit=limit,
    )


@router.get(
    "/institutions/{institution_id}/students/{student_id}",
    response_model=StudentResponse,
    summary="Get details of a single student record",
)
def get_student(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    student_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> StudentResponse:
    """Retrieve full details of a student record including decrypted data and active flags."""
    return student_service.get_student(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
    )


@router.post(
    "/institutions/{institution_id}/students",
    response_model=StudentSaveResultResponse,
    status_code=201,
    summary="Create student draft record and execute validation ('Check and save')",
)
def create_student(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    payload: StudentCreateRequest,
    request: Request,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> StudentSaveResultResponse:
    """Create a single student record as draft and run validation engine immediately.

    Spec 8.2 & 9.4:
    - Never discard data: saved as draft either way.
    - Runs cheap checks, APAAR lookups, and duplicate checks immediately.
    - Persists validation flags with row reference.
    - Country field persisted only when foreign_national is Yes.
    """
    client_ip = request.client.host if request.client else None
    return student_service.create_student(
        db=db,
        institution_id=institution_id,
        payload=payload,
        user=current_user,
        client_ip=client_ip,
    )


@router.put(
    "/institutions/{institution_id}/students/{student_id}",
    response_model=StudentSaveResultResponse,
    summary="Update an existing student draft record and re-validate ('Check and save')",
)
def update_student(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    student_id: int,
    payload: StudentUpdateRequest,
    request: Request,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> StudentSaveResultResponse:
    """Update student draft fields and re-run validation engine.

    Spec 8.2, 9.4, 10:
    - Locked records cannot be edited directly (403 Forbidden).
    - Preserves existing justifications on still-applicable flags.
    - Emits hash-chained audit log entry.
    """
    client_ip = request.client.host if request.client else None
    return student_service.update_student(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
        payload=payload,
        user=current_user,
        client_ip=client_ip,
    )


@router.delete(
    "/institutions/{institution_id}/students/{student_id}",
    summary="Delete a student draft record",
)
def delete_student(
    institution_id: Annotated[int, Depends(verify_institution_access)],
    student_id: int,
    request: Request,
    current_user: Annotated[User, college_staff_guard],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Delete a student draft record.

    Spec 8.2, 10:
    - Locked records cannot be deleted (403 Forbidden).
    - Resolves cross-college duplicate flags if applicable.
    - Emits hash-chained audit log entry.
    """
    client_ip = request.client.host if request.client else None
    return student_service.delete_student(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
        user=current_user,
        client_ip=client_ip,
    )

