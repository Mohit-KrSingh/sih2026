"""Seat declaration business logic, course summary, live validation, and autosave."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import service as audit_service
from app.institutions.service import check_institution_can_upload
from app.models import Course, CourseIntake, Institution, SeatDeclaration, Student, User
from app.students.schemas import (
    CourseSummaryResponse,
    InstitutionSeatDeclarationResponse,
    SeatDeclarationBatchSaveRequest,
    SeatDeclarationSaveRequest,
    ValidationFlagSummary,
)


def _get_active_enrolment_counts(
    db: Session,
    institution_id: int,
    course_id: int,
    academic_year: str,
) -> tuple[int, int, int]:
    """Calculate active regular, supernumerary, and total student counts for a course."""
    regular_count = (
        db.scalar(
            select(func.count(Student.id)).where(
                Student.institution_id == institution_id,
                Student.course_id == course_id,
                Student.academic_year == academic_year,
                Student.seat_type == "Regular",
                Student.status.notin_(["withdrawn", "transferred"]),
            )
        )
        or 0
    )

    supernumerary_count = (
        db.scalar(
            select(func.count(Student.id)).where(
                Student.institution_id == institution_id,
                Student.course_id == course_id,
                Student.academic_year == academic_year,
                Student.seat_type == "Supernumerary",
                Student.status.notin_(["withdrawn", "transferred"]),
            )
        )
        or 0
    )

    total_count = regular_count + supernumerary_count
    return regular_count, supernumerary_count, total_count


def _build_course_summary(
    db: Session,
    institution_id: int,
    course: Course,
    academic_year: str,
    decl: SeatDeclaration | None = None,
) -> CourseSummaryResponse:
    """Build a CourseSummaryResponse including AICTE quota, declarations, counts, and live flags."""
    # 1. Fetch AICTE approved intake for this academic year
    intake = db.scalar(
        select(CourseIntake).where(
            CourseIntake.course_id == course.id,
            CourseIntake.academic_year == academic_year,
        )
    )
    approved_intake = intake.approved_intake if intake else 0
    supernumerary_allowed = intake.supernumerary_seats_allowed if intake else 0

    # 2. Fetch existing SeatDeclaration if not passed
    if decl is None:
        decl = db.scalar(
            select(SeatDeclaration).where(
                SeatDeclaration.course_id == course.id,
                SeatDeclaration.academic_year == academic_year,
            )
        )

    reg_admitted = decl.regular_admitted if decl else 0
    sup_admitted = decl.supernumerary_admitted if decl else 0
    nri_count = decl.nri_count if decl else 0
    oci_count = decl.oci_count if decl else 0
    fn_count = decl.fn_count if decl else 0
    decl_status = decl.status if decl else "draft"
    updated_at = decl.updated_at if decl else None

    # 3. Calculate actual active student counts
    calc_regular, calc_super, calc_total = _get_active_enrolment_counts(
        db, institution_id, course.id, academic_year
    )

    # 4. Quota and overshoot calculation
    overshoot = max(0, reg_admitted - approved_intake)
    super_overshoot = max(0, sup_admitted - supernumerary_allowed)
    status_badge = "over_by_n" if overshoot > 0 else "within_limit"

    # 5. Live validation flags (live checks on input)
    flags: list[ValidationFlagSummary] = []

    # Check for negative values
    if any(v < 0 for v in [reg_admitted, sup_admitted, nri_count, oci_count, fn_count]):
        flags.append(
            ValidationFlagSummary(
                rule_code="SEAT_DECLARATION_INVALID",
                level="error",
                message="Seat declaration counts cannot be negative numbers.",
                fix_hint="Enter zero or positive integers for all seat counts.",
                field="regular_admitted",
            )
        )

    # Check category sum vs total declared
    total_declared = reg_admitted + sup_admitted
    category_total = nri_count + oci_count + fn_count
    if category_total > total_declared and total_declared >= 0:
        flags.append(
            ValidationFlagSummary(
                rule_code="SEAT_DECLARATION_INVALID",
                level="error",
                message=(
                    f"Total category admissions (NRI={nri_count} + OCI={oci_count} + "
                    f"Foreign National={fn_count} = {category_total}) "
                    f"exceed total declared seats ({total_declared})."
                ),
                fix_hint=(
                    "Ensure sum of NRI, OCI, and Foreign National counts does not "
                    "exceed total admitted seats."
                ),
                field="nri_count",
            )
        )

    # Check regular quota overshoot (INTAKE_EXCEEDED)
    if overshoot > 0:
        flags.append(
            ValidationFlagSummary(
                rule_code="INTAKE_EXCEEDED",
                level="exception",
                message=(
                    f"Regular admitted students ({reg_admitted}) exceed approved intake "
                    f"({approved_intake}) by {overshoot}."
                ),
                fix_hint=(
                    "Reduce admitted regular student count or submit a justification "
                    "for over-intake admissions."
                ),
                field="regular_admitted",
            )
        )

    # Check supernumerary overshoot (SUPERNUMERARY_EXCEEDED)
    if super_overshoot > 0:
        flags.append(
            ValidationFlagSummary(
                rule_code="SUPERNUMERARY_EXCEEDED",
                level="exception",
                message=(
                    f"Supernumerary admitted students ({sup_admitted}) exceed allowed "
                    f"supernumerary quota ({supernumerary_allowed}) by {super_overshoot}."
                ),
                fix_hint="Reduce admitted supernumerary student count or submit justification.",
                field="supernumerary_admitted",
            )
        )

    # Check declaration mismatch against active students (SEAT_DECLARATION_MISMATCH)
    if calc_total > 0:
        if reg_admitted != calc_regular or sup_admitted != calc_super:
            flags.append(
                ValidationFlagSummary(
                    rule_code="SEAT_DECLARATION_MISMATCH",
                    level="error",
                    message=(
                        f"Declared seats ({reg_admitted} regular, {sup_admitted} supernumerary) "
                        f"differ from uploaded enrolled records "
                        f"({calc_regular} regular, {calc_super} supernumerary)."
                    ),
                    fix_hint=(
                        "Align declared counts with your uploaded student records "
                        "or adjust student data."
                    ),
                    field="regular_admitted",
                )
            )

    return CourseSummaryResponse(
        course_id=course.id,
        course_name=course.name,
        branch=course.branch,
        level=course.level,
        duration_years=course.duration_years,
        academic_year=academic_year,
        approved_intake=approved_intake,
        supernumerary_seats_allowed=supernumerary_allowed,
        regular_admitted=reg_admitted,
        supernumerary_admitted=sup_admitted,
        nri_count=nri_count,
        oci_count=oci_count,
        fn_count=fn_count,
        total_declared=total_declared,
        calculated_enrolment=calc_total,
        calculated_regular=calc_regular,
        calculated_supernumerary=calc_super,
        status=decl_status,
        status_badge=status_badge,
        overshoot=overshoot,
        supernumerary_overshoot=super_overshoot,
        flags=flags,
        updated_at=updated_at,
    )


def get_course_summary(
    db: Session,
    institution_id: int,
    course_id: int,
    academic_year: str,
) -> CourseSummaryResponse:
    """Fetch summary for a single course including AICTE intake and seat declarations."""
    course = db.get(Course, course_id)
    if not course or course.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course {course_id} not found for institution {institution_id}",
        )
    return _build_course_summary(db, institution_id, course, academic_year)


def get_institution_seat_declarations(
    db: Session,
    institution_id: int,
    academic_year: str,
) -> InstitutionSeatDeclarationResponse:
    """Retrieve all approved courses and seat declarations for an institution."""
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution {institution_id} not found",
        )

    courses = (
        db.scalars(
            select(Course)
            .where(Course.institution_id == institution_id)
            .order_by(Course.level, Course.name, Course.branch)
        ).all()
    )

    summaries: list[CourseSummaryResponse] = []
    total_approved = 0
    total_super_allowed = 0
    total_decl_reg = 0
    total_decl_super = 0
    total_decl = 0
    total_enrolled = 0

    for c in courses:
        summary = _build_course_summary(db, institution_id, c, academic_year)
        summaries.append(summary)
        total_approved += summary.approved_intake
        total_super_allowed += summary.supernumerary_seats_allowed
        total_decl_reg += summary.regular_admitted
        total_decl_super += summary.supernumerary_admitted
        total_decl += summary.total_declared
        total_enrolled += summary.calculated_enrolment

    return InstitutionSeatDeclarationResponse(
        institution_id=institution_id,
        academic_year=academic_year,
        total_approved_intake=total_approved,
        total_supernumerary_allowed=total_super_allowed,
        total_declared_regular=total_decl_reg,
        total_declared_supernumerary=total_decl_super,
        total_declared=total_decl,
        total_enrolled=total_enrolled,
        courses=summaries,
    )


def save_course_seat_declaration(
    db: Session,
    institution_id: int,
    course_id: int,
    payload: SeatDeclarationSaveRequest,
    user: User,
    client_ip: str | None = None,
) -> CourseSummaryResponse:
    """Save or autosave a course seat declaration as a draft.

    Spec 8.1 & 13:
    - Autosaves as a draft; invalid values show errors immediately but are still saved.
    - If institution approval is suspended, withdrawn or expired: blocked with 403.
    """
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution {institution_id} not found",
        )
    check_institution_can_upload(institution)

    course = db.get(Course, course_id)
    if not course or course.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course {course_id} not found for institution {institution_id}",
        )

    decl = db.scalar(
        select(SeatDeclaration).where(
            SeatDeclaration.course_id == course_id,
            SeatDeclaration.academic_year == payload.academic_year,
        )
    )

    before_json: dict[str, Any] | None = None
    is_new = False

    if decl is None:
        is_new = True
        decl = SeatDeclaration(
            course_id=course_id,
            academic_year=payload.academic_year,
            regular_admitted=payload.regular_admitted,
            supernumerary_admitted=payload.supernumerary_admitted,
            nri_count=payload.nri_count,
            oci_count=payload.oci_count,
            fn_count=payload.fn_count,
            status=payload.status,
        )
        db.add(decl)
    else:
        before_json = {
            "regular_admitted": decl.regular_admitted,
            "supernumerary_admitted": decl.supernumerary_admitted,
            "nri_count": decl.nri_count,
            "oci_count": decl.oci_count,
            "fn_count": decl.fn_count,
            "status": decl.status,
        }
        decl.regular_admitted = payload.regular_admitted
        decl.supernumerary_admitted = payload.supernumerary_admitted
        decl.nri_count = payload.nri_count
        decl.oci_count = payload.oci_count
        decl.fn_count = payload.fn_count
        decl.status = payload.status

    db.flush()

    after_json = {
        "regular_admitted": decl.regular_admitted,
        "supernumerary_admitted": decl.supernumerary_admitted,
        "nri_count": decl.nri_count,
        "oci_count": decl.oci_count,
        "fn_count": decl.fn_count,
        "status": decl.status,
    }

    audit_service.record(
        db=db,
        action="seat_declaration.create" if is_new else "seat_declaration.update",
        actor_id=user.id,
        actor_role=user.role,
        entity="seat_declarations",
        entity_id=str(decl.id),
        before_json=before_json,
        after_json=after_json,
        ip=client_ip,
    )

    db.commit()
    db.refresh(decl)

    return _build_course_summary(db, institution_id, course, payload.academic_year, decl=decl)


def batch_save_seat_declarations(
    db: Session,
    institution_id: int,
    payload: SeatDeclarationBatchSaveRequest,
    user: User,
    client_ip: str | None = None,
) -> InstitutionSeatDeclarationResponse:
    """Save or autosave declarations for multiple courses in a batch."""
    institution = db.get(Institution, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution {institution_id} not found",
        )
    check_institution_can_upload(institution)

    for item in payload.declarations:
        course = db.get(Course, item.course_id)
        if not course or course.institution_id != institution_id:
            continue

        decl = db.scalar(
            select(SeatDeclaration).where(
                SeatDeclaration.course_id == item.course_id,
                SeatDeclaration.academic_year == payload.academic_year,
            )
        )

        before_json: dict[str, Any] | None = None
        is_new = False

        if decl is None:
            is_new = True
            decl = SeatDeclaration(
                course_id=item.course_id,
                academic_year=payload.academic_year,
                regular_admitted=item.regular_admitted,
                supernumerary_admitted=item.supernumerary_admitted,
                nri_count=item.nri_count,
                oci_count=item.oci_count,
                fn_count=item.fn_count,
                status=item.status,
            )
            db.add(decl)
        else:
            before_json = {
                "regular_admitted": decl.regular_admitted,
                "supernumerary_admitted": decl.supernumerary_admitted,
                "nri_count": decl.nri_count,
                "oci_count": decl.oci_count,
                "fn_count": decl.fn_count,
                "status": decl.status,
            }
            decl.regular_admitted = item.regular_admitted
            decl.supernumerary_admitted = item.supernumerary_admitted
            decl.nri_count = item.nri_count
            decl.oci_count = item.oci_count
            decl.fn_count = item.fn_count
            decl.status = item.status

        db.flush()

        after_json = {
            "regular_admitted": decl.regular_admitted,
            "supernumerary_admitted": decl.supernumerary_admitted,
            "nri_count": decl.nri_count,
            "oci_count": decl.oci_count,
            "fn_count": decl.fn_count,
            "status": decl.status,
        }

        audit_service.record(
            db=db,
            action="seat_declaration.create" if is_new else "seat_declaration.update",
            actor_id=user.id,
            actor_role=user.role,
            entity="seat_declarations",
            entity_id=str(decl.id),
            before_json=before_json,
            after_json=after_json,
            ip=client_ip,
        )

    db.commit()
    return get_institution_seat_declarations(db, institution_id, payload.academic_year)
