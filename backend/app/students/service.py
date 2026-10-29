"""Student management service: CRUD operations, validation execution, and directory search."""

from __future__ import annotations

import math
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.audit import service as audit_service
from app.auth.security import decrypt_dob, encrypt_dob
from app.institutions.service import check_institution_can_upload
from app.models import Course, Institution, Student, User, ValidationFlag
from app.students.duplicate_service import resolve_duplicate_flags_on_status_change
from app.students.schemas import (
    StudentCreateRequest,
    StudentListResponse,
    StudentListStats,
    StudentResponse,
    StudentSaveResultResponse,
    StudentUpdateRequest,
    StudentValidationFlag,
)
from app.validation.flags import ValidationAudience, ValidationLevel


def _parse_iso_date(date_str: str | None, default_date: date | None = None) -> date:
    """Safely parse an ISO date string (YYYY-MM-DD), with fallback."""
    if not date_str:
        return default_date or date.today()
    try:
        return date.fromisoformat(date_str.strip())
    except Exception:
        return default_date or date.today()


def build_student_response(student: Student) -> StudentResponse:
    """Map ORM Student model to typed StudentResponse with decrypted DOB and active flags."""
    dob_str: str = ""
    if student.dob_encrypted:
        try:
            decrypted = decrypt_dob(student.dob_encrypted)
            dob_str = (
                decrypted.isoformat()
                if hasattr(decrypted, "isoformat")
                else str(decrypted)
            )
        except Exception:
            dob_str = student.dob_encrypted

    adm_date_str = (
        student.admission_date.isoformat()
        if hasattr(student.admission_date, "isoformat")
        else str(student.admission_date)
    )

    course_name = student.course.name if student.course else ""
    branch_name = student.course.branch if student.course else ""

    # Include active (non-resolved) validation flags for this student
    active_flags: list[StudentValidationFlag] = []
    if student.flags:
        for fl in student.flags:
            if fl.status != "resolved":
                active_flags.append(
                    StudentValidationFlag(
                        id=fl.id,
                        rule_code=fl.rule_code,
                        level=fl.level,
                        field=fl.field,
                        message=fl.message,
                        fix_hint=fl.fix_hint,
                        audience=fl.audience,
                        requires_justification=fl.requires_justification,
                        status=fl.status,
                    )
                )

    return StudentResponse(
        id=student.id,
        institution_id=student.institution_id,
        course_id=student.course_id,
        course_name=course_name,
        branch=branch_name,
        academic_year=student.academic_year,
        apaar_id=student.apaar_id,
        name=student.name,
        dob=dob_str,
        gender=student.gender,
        enrolment_no=student.enrolment_no,
        admission_date=adm_date_str,
        admission_mode=student.admission_mode,
        seat_type=student.seat_type,
        reservation_category=student.reservation_category,
        nri=student.nri,
        oci=student.oci,
        foreign_national=student.foreign_national,
        country=student.fn_country,
        status=student.status,
        is_locked=student.is_locked,
        submission_id=student.submission_id,
        source=student.source,
        flags=active_flags,
        created_at=student.created_at,
        updated_at=student.updated_at,
    )


def list_students(
    db: Session,
    institution_id: int,
    academic_year: str | None = None,
    course_id: int | None = None,
    status_filter: str | None = None,
    level_filter: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> StudentListResponse:
    """Retrieve filtered, paginated student records directory for an institution."""
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20

    base_query = (
        select(Student)
        .options(
            joinedload(Student.course),
            selectinload(Student.flags),
        )
        .where(Student.institution_id == institution_id)
    )

    if academic_year:
        base_query = base_query.where(Student.academic_year == academic_year)
    if course_id is not None:
        base_query = base_query.where(Student.course_id == course_id)
    if status_filter and status_filter.lower() != "all":
        base_query = base_query.where(Student.status == status_filter.lower())

    if search:
        search_term = f"%{search.strip()}%"
        base_query = base_query.where(
            or_(
                Student.apaar_id.ilike(search_term),
                Student.name.ilike(search_term),
                Student.enrolment_no.ilike(search_term),
            )
        )

    # Flag level filtering
    if level_filter and level_filter.lower() != "all":
        target_lvl = level_filter.lower()
        if target_lvl == "clean":
            # Subquery: students with no active flags
            flag_subquery = (
                select(ValidationFlag.student_id)
                .where(
                    ValidationFlag.student_id.is_not(None),
                    ValidationFlag.status != "resolved",
                )
            )
            base_query = base_query.where(Student.id.not_in(flag_subquery))
        else:
            # Students having at least one active flag of this level
            flag_subquery = (
                select(ValidationFlag.student_id)
                .where(
                    ValidationFlag.student_id.is_not(None),
                    ValidationFlag.level == target_lvl,
                    ValidationFlag.status != "resolved",
                )
            )
            base_query = base_query.where(Student.id.in_(flag_subquery))

    # Compute total matching records
    count_stmt = select(func.count()).select_from(base_query.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0

    # Pagination
    offset = (page - 1) * limit
    paged_stmt = (
        base_query.order_by(Student.updated_at.desc(), Student.id.desc())
        .offset(offset)
        .limit(limit)
    )
    records = db.scalars(paged_stmt).unique().all()
    items = [build_student_response(s) for s in records]

    # Compute overall institution stats for the selected year
    stats_query = select(Student.status, func.count(Student.id)).where(
        Student.institution_id == institution_id
    )
    if academic_year:
        stats_query = stats_query.where(Student.academic_year == academic_year)
    stats_query = stats_query.group_by(Student.status)
    status_counts = dict(db.execute(stats_query).all())

    # Count flags by level across this institution's students
    flag_counts_stmt = (
        select(ValidationFlag.level, func.count(distinct(ValidationFlag.student_id)))
        .join(Student, Student.id == ValidationFlag.student_id)
        .where(
            Student.institution_id == institution_id,
            ValidationFlag.status != "resolved",
        )
    )
    if academic_year:
        flag_counts_stmt = flag_counts_stmt.where(Student.academic_year == academic_year)
    flag_counts_stmt = flag_counts_stmt.group_by(ValidationFlag.level)
    level_counts = dict(db.execute(flag_counts_stmt).all())

    total_inst_students = sum(status_counts.values())
    stats = StudentListStats(
        total=total_inst_students,
        valid=status_counts.get("valid", 0),
        flagged=status_counts.get("flagged", 0),
        draft=status_counts.get("draft", 0),
        submitted=status_counts.get("submitted", 0),
        error_flags_count=level_counts.get("error", 0),
        exception_flags_count=level_counts.get("exception", 0),
        warning_flags_count=level_counts.get("warning", 0),
    )

    total_pages = math.ceil(total / limit) if total > 0 else 1

    return StudentListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        stats=stats,
    )


def get_student(db: Session, institution_id: int, student_id: int) -> StudentResponse:
    """Retrieve a single student record with decrypted data and active flags."""
    stmt = (
        select(Student)
        .options(
            joinedload(Student.course),
            selectinload(Student.flags),
        )
        .where(
            Student.id == student_id,
            Student.institution_id == institution_id,
        )
    )
    student = db.scalar(stmt)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student record #{student_id} not found in this institution",
        )

    return build_student_response(student)


def create_student(
    db: Session,
    institution_id: int,
    payload: StudentCreateRequest,
    user: User,
    client_ip: str | None = None,
) -> StudentSaveResultResponse:
    """Create a new student draft record and execute validation engine ('Check and save').

    Spec 8.2 & 9.4:
    - Never discard data: saves as draft either way.
    - Runs cheap checks, APAAR lookups, and duplicate rules immediately.
    - Country field persisted only when foreign_national is Yes.
    - Encrypts date of birth with Fernet.
    - Records state change in hash-chained audit log.
    """
    # 1. Enforce active institution approval check
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution #{institution_id} not found",
        )
    check_institution_can_upload(institution)

    # 2. Verify course belongs to institution
    course = db.scalar(
        select(Course).where(
            Course.id == payload.course_id,
            Course.institution_id == institution_id,
        )
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course #{payload.course_id} is not an approved course of this institution",
        )

    # 3. Check duplicate (institution, course, year, apaar_id)
    if payload.apaar_id:
        existing = db.scalar(
            select(Student).where(
                Student.institution_id == institution_id,
                Student.course_id == payload.course_id,
                Student.academic_year == payload.academic_year,
                Student.apaar_id == payload.apaar_id.strip(),
            )
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Student with APAAR ID {payload.apaar_id} is already enrolled in "
                    f"'{course.name}' for {payload.academic_year}. Please edit the existing record."
                ),
            )

    # 4. Prepare values
    clean_apaar = payload.apaar_id.strip()
    clean_name = payload.name.strip()
    clean_enrolment = payload.enrolment_no.strip()
    clean_dob = payload.dob.strip()
    parsed_adm_date = _parse_iso_date(payload.admission_date)

    # Country appears and is stored only for foreign nationals
    is_foreign = (payload.foreign_national or "").strip().lower() == "yes"
    fn_country = payload.country.strip() if (is_foreign and payload.country) else None

    # Encrypt DOB with Fernet
    encrypted_dob = encrypt_dob(clean_dob if clean_dob else "2000-01-01")

    # 5. Instantiate Student ORM model
    student = Student(
        institution_id=institution_id,
        course_id=payload.course_id,
        academic_year=payload.academic_year,
        apaar_id=clean_apaar,
        name=clean_name,
        dob_encrypted=encrypted_dob,
        gender=payload.gender.strip(),
        enrolment_no=clean_enrolment,
        admission_date=parsed_adm_date,
        admission_mode=payload.admission_mode.strip(),
        seat_type=payload.seat_type.strip(),
        reservation_category=payload.reservation_category.strip(),
        nri="Yes" if (payload.nri or "").strip().lower() == "yes" else "No",
        oci="Yes" if (payload.oci or "").strip().lower() == "yes" else "No",
        foreign_national="Yes" if is_foreign else "No",
        fn_country=fn_country,
        status="draft",
        is_locked=False,
        source="form",
    )
    student.course = course
    db.add(student)
    db.flush()  # assign student.id

    # 6. Run validation engine and persist flags
    from app.validation.service import validate_rows

    val_result = validate_rows(
        rows=[student],
        institution_id=institution_id,
        academic_year=student.academic_year,
        course_id=student.course_id,
        db_session=db,
        persist=True,
        keep_justifications=True,
    )

    # Determine status: if student-facing flags exist -> flagged, else valid (or draft)
    active_flags = [
        f for f in val_result
        if f.level in (ValidationLevel.ERROR, ValidationLevel.EXCEPTION, ValidationLevel.WARNING)
        and f.audience != ValidationAudience.AICTE.value
    ]
    if active_flags:
        student.status = "flagged"
    else:
        student.status = "valid"

    audit_service.record(
        db=db,
        actor_id=user.id,
        actor_role=user.role,
        action="student.create",
        entity="student",
        entity_id=student.id,
        before_json=None,
        after_json={
            "id": student.id,
            "apaar_id": student.apaar_id,
            "name": student.name,
            "course_id": student.course_id,
            "academic_year": student.academic_year,
            "enrolment_no": student.enrolment_no,
            "status": student.status,
        },
        ip=client_ip,
    )

    db.commit()

    # Re-fetch with fresh relations
    student_resp = get_student(db, institution_id, student.id)
    return StudentSaveResultResponse(
        student=student_resp,
        flags=student_resp.flags,
        is_valid=val_result.is_valid,
        errors_count=len(val_result.errors),
        exceptions_count=len(val_result.exceptions),
        warnings_count=len(val_result.warnings),
        infos_count=len(val_result.infos),
    )


def update_student(
    db: Session,
    institution_id: int,
    student_id: int,
    payload: StudentUpdateRequest,
    user: User,
    client_ip: str | None = None,
) -> StudentSaveResultResponse:
    """Update an existing student draft record and re-run validation engine.

    Spec 8.2, 9.4, 10:
    - Locked records cannot be edited directly (raises 403 Forbidden).
    - Idempotent re-run updates flags and preserves justifications.
    - Records state change in hash-chained audit log.
    """
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution #{institution_id} not found",
        )
    check_institution_can_upload(institution)

    student = db.scalar(
        select(Student)
        .options(joinedload(Student.course), selectinload(Student.flags))
        .where(
            Student.id == student_id,
            Student.institution_id == institution_id,
        )
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student record #{student_id} not found in this institution",
        )

    # Enforce draft/lock protection
    locked_statuses = ("submitted", "accepted", "verified", "verified_with_exception")
    if student.is_locked or student.status in locked_statuses:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Locked or submitted student records cannot be modified directly. "
                "Please raise a formal change request."
            ),
        )

    before_snapshot = {
        "id": student.id,
        "apaar_id": student.apaar_id,
        "name": student.name,
        "course_id": student.course_id,
        "academic_year": student.academic_year,
        "enrolment_no": student.enrolment_no,
        "status": student.status,
    }

    # Verify target course if updating course_id
    if payload.course_id is not None and payload.course_id != student.course_id:
        target_course = db.scalar(
            select(Course).where(
                Course.id == payload.course_id,
                Course.institution_id == institution_id,
            )
        )
        if not target_course:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Course #{payload.course_id} is not an approved course of this institution",
            )
        student.course_id = payload.course_id

    # Check unique constraint if apaar_id or course_id changed
    target_apaar = (
        payload.apaar_id.strip() if payload.apaar_id is not None else student.apaar_id
    )
    target_year = (
        payload.academic_year.strip()
        if payload.academic_year is not None
        else student.academic_year
    )
    target_course_id = payload.course_id or student.course_id

    is_key_changed = (
        target_apaar != student.apaar_id
        or target_course_id != student.course_id
        or target_year != student.academic_year
    )
    if is_key_changed:
        clash = db.scalar(
            select(Student).where(
                Student.institution_id == institution_id,
                Student.course_id == target_course_id,
                Student.academic_year == target_year,
                Student.apaar_id == target_apaar,
                Student.id != student.id,
            )
        )
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Another student with APAAR ID {target_apaar} already exists "
                    f"in this course for {target_year}."
                ),
            )

    # Apply updates
    if payload.apaar_id is not None:
        student.apaar_id = payload.apaar_id.strip()
    if payload.name is not None:
        student.name = payload.name.strip()
    if payload.dob is not None:
        clean_dob = payload.dob.strip()
        student.dob_encrypted = encrypt_dob(clean_dob if clean_dob else "2000-01-01")
    if payload.gender is not None:
        student.gender = payload.gender.strip()
    if payload.academic_year is not None:
        student.academic_year = payload.academic_year.strip()
    if payload.enrolment_no is not None:
        student.enrolment_no = payload.enrolment_no.strip()
    if payload.admission_date is not None:
        student.admission_date = _parse_iso_date(
            payload.admission_date, default_date=student.admission_date
        )
    if payload.admission_mode is not None:
        student.admission_mode = payload.admission_mode.strip()
    if payload.seat_type is not None:
        student.seat_type = payload.seat_type.strip()
    if payload.reservation_category is not None:
        student.reservation_category = payload.reservation_category.strip()
    if payload.nri is not None:
        student.nri = "Yes" if payload.nri.strip().lower() == "yes" else "No"
    if payload.oci is not None:
        student.oci = "Yes" if payload.oci.strip().lower() == "yes" else "No"
    if payload.foreign_national is not None:
        is_foreign = payload.foreign_national.strip().lower() == "yes"
        student.foreign_national = "Yes" if is_foreign else "No"
        if is_foreign and payload.country is not None:
            student.fn_country = payload.country.strip() if payload.country.strip() else None
        elif not is_foreign:
            student.fn_country = None
    elif payload.country is not None and student.foreign_national == "Yes":
        student.fn_country = payload.country.strip() if payload.country.strip() else None

    # Re-run validation engine
    student.course = student.course or db.get(Course, student.course_id)
    from app.validation.service import validate_rows

    val_result = validate_rows(
        rows=[student],
        institution_id=institution_id,
        academic_year=student.academic_year,
        course_id=student.course_id,
        db_session=db,
        persist=True,
        keep_justifications=True,
    )

    active_flags = [
        f for f in val_result
        if f.level in (ValidationLevel.ERROR, ValidationLevel.EXCEPTION, ValidationLevel.WARNING)
        and f.audience != ValidationAudience.AICTE.value
    ]
    if active_flags:
        student.status = "flagged"
    else:
        student.status = "valid"

    # Audit logging
    audit_service.record(
        db=db,
        actor_id=user.id,
        actor_role=user.role,
        action="student.update",
        entity="student",
        entity_id=student.id,
        before_json=before_snapshot,
        after_json={
            "id": student.id,
            "apaar_id": student.apaar_id,
            "name": student.name,
            "course_id": student.course_id,
            "academic_year": student.academic_year,
            "enrolment_no": student.enrolment_no,
            "status": student.status,
        },
        ip=client_ip,
    )

    db.commit()

    student_resp = get_student(db, institution_id, student.id)
    return StudentSaveResultResponse(
        student=student_resp,
        flags=student_resp.flags,
        is_valid=val_result.is_valid,
        errors_count=len(val_result.errors),
        exceptions_count=len(val_result.exceptions),
        warnings_count=len(val_result.warnings),
        infos_count=len(val_result.infos),
    )


def delete_student(
    db: Session,
    institution_id: int,
    student_id: int,
    user: User,
    client_ip: str | None = None,
) -> dict[str, Any]:
    """Delete a student draft record.

    Spec 8.2, 9.4, 10:
    - Locked records cannot be deleted (raises 403 Forbidden).
    - Resolves cross-college duplicate flags at other institutions.
    - Emits hash-chained audit log entry.
    """
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution #{institution_id} not found",
        )
    check_institution_can_upload(institution)

    student = db.scalar(
        select(Student).where(
            Student.id == student_id,
            Student.institution_id == institution_id,
        )
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student record #{student_id} not found in this institution",
        )

    locked_statuses = ("submitted", "accepted", "verified", "verified_with_exception")
    if student.is_locked or student.status in locked_statuses:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Locked or submitted student records cannot be deleted. "
                "Please raise a formal change request."
            ),
        )

    before_snapshot = {
        "id": student.id,
        "apaar_id": student.apaar_id,
        "name": student.name,
        "course_id": student.course_id,
        "academic_year": student.academic_year,
        "enrolment_no": student.enrolment_no,
        "status": student.status,
    }

    # Resolve cross-college duplicate flags if this student was duplicated at another institution
    try:
        resolve_duplicate_flags_on_status_change(db, student.id, "deleted")
    except Exception:
        pass

    # Audit log
    audit_service.record(
        db=db,
        actor_id=user.id,
        actor_role=user.role,
        action="student.delete",
        entity="student",
        entity_id=student.id,
        before_json=before_snapshot,
        after_json=None,
        ip=client_ip,
    )

    db.delete(student)
    db.commit()

    return {
        "message": f"Student draft #{student_id} deleted successfully",
        "student_id": student_id,
    }
