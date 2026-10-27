"""Duplicate enrolment management, cross-college notifications, and flag resolution.

Spec: Section 9.3, 10 & TASKS.md T16:
- Cross-college rules query by apaar_id and year using the index.
- Marking a student withdrawn or transferred at one college resolves the flag at both.
- Notify both colleges.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Notification, Student, ValidationFlag
from app.validation.codes import DUP_ACTIVE_OTHER_COLLEGE, DUP_SAME_COURSE_OTHER_COLLEGE


def query_duplicates_by_apaar_and_year(
    db: Session,
    apaar_ids: list[str],
    academic_year: str,
    exclude_institution_id: int | None = None,
) -> list[Student]:
    """Query active student records using the (apaar_id, academic_year) index.

    Per TASKS.md T16:
    Cross-college rules query by apaar_id and year using the index.
    """
    if not apaar_ids:
        return []

    stmt = (
        select(Student)
        .options(joinedload(Student.institution), joinedload(Student.course))
        .where(
            Student.apaar_id.in_(apaar_ids),
            Student.academic_year == academic_year,
            Student.status.not_in(["withdrawn", "transferred"]),
        )
    )
    if exclude_institution_id is not None:
        stmt = stmt.where(Student.institution_id != exclude_institution_id)

    return list(db.scalars(stmt).all())


def notify_duplicate_enrolment(
    db: Session,
    student: Student,
    conflicting_student: Student,
    rule_code: str,
) -> tuple[Notification, Notification]:
    """Create cross-college duplicate notifications for both affected institutions."""
    inst_a = student.institution
    inst_b = conflicting_student.institution

    inst_a_name = inst_a.name if inst_a else "Institution A"
    inst_a_code = inst_a.aicte_id if inst_a else "AICTE-A"
    inst_b_name = inst_b.name if inst_b else "Institution B"
    inst_b_code = inst_b.aicte_id if inst_b else "AICTE-B"

    # Notification for Institution A
    notif_a = Notification(
        institution_id=student.institution_id,
        type="DUPLICATE_ENROLMENT_DETECTED",
        payload_json={
            "rule_code": rule_code,
            "apaar_id": student.apaar_id,
            "student_name": student.name,
            "academic_year": student.academic_year,
            "other_institution_id": conflicting_student.institution_id,
            "other_institution_name": inst_b_name,
            "other_institution_aicte_id": inst_b_code,
            "message": (
                f"Duplicate enrolment detected: student with APAAR ID {student.apaar_id} "
                f"is also active at {inst_b_name} ({inst_b_code}) for academic year "
                f"{student.academic_year}."
            ),
        },
    )

    # Notification for Institution B
    notif_b = Notification(
        institution_id=conflicting_student.institution_id,
        type="DUPLICATE_ENROLMENT_DETECTED",
        payload_json={
            "rule_code": rule_code,
            "apaar_id": student.apaar_id,
            "student_name": conflicting_student.name,
            "academic_year": student.academic_year,
            "other_institution_id": student.institution_id,
            "other_institution_name": inst_a_name,
            "other_institution_aicte_id": inst_a_code,
            "message": (
                f"Duplicate enrolment detected: student with APAAR ID {student.apaar_id} "
                f"is also active at {inst_a_name} ({inst_a_code}) for academic year "
                f"{student.academic_year}."
            ),
        },
    )

    db.add(notif_a)
    db.add(notif_b)
    db.flush()

    return notif_a, notif_b


def resolve_duplicate_flags_on_status_change(
    db: Session,
    student: Student,
    new_status: str | None = None,
) -> list[ValidationFlag]:
    """Resolve duplicate flags across both colleges when a student is marked
    withdrawn or transferred.

    Per SPEC.md Section 9.3 & TASKS.md T16:
    Marking a student withdrawn or transferred at one college resolves the flag at both.
    Notify both colleges.
    """
    if new_status is not None:
        student.status = new_status

    status_lower = (student.status or "").lower()
    if status_lower not in ("withdrawn", "transferred"):
        return []

    resolved_flags: list[ValidationFlag] = []

    # 1. Resolve duplicate flags on the student being withdrawn/transferred
    own_flags = db.scalars(
        select(ValidationFlag).where(
            ValidationFlag.student_id == student.id,
            ValidationFlag.rule_code.in_([DUP_ACTIVE_OTHER_COLLEGE, DUP_SAME_COURSE_OTHER_COLLEGE]),
            ValidationFlag.status == "open",
        )
    ).all()

    for fl in own_flags:
        fl.status = "resolved"
        resolved_flags.append(fl)

    # 2. Find conflicting students at other institutions with same APAAR ID & academic year
    other_students = db.scalars(
        select(Student)
        .options(joinedload(Student.institution))
        .where(
            Student.apaar_id == student.apaar_id,
            Student.academic_year == student.academic_year,
            Student.institution_id != student.institution_id,
        )
    ).all()

    inst_a = student.institution
    inst_a_name = inst_a.name if inst_a else "Withdrawing Institution"
    inst_a_code = inst_a.aicte_id if inst_a else "AICTE-ID"

    for other_s in other_students:
        # Check if other_s still has any remaining active duplicate records elsewhere
        remaining_active = db.scalars(
            select(Student).where(
                Student.apaar_id == student.apaar_id,
                Student.academic_year == student.academic_year,
                Student.institution_id != other_s.institution_id,
                Student.id != student.id,
                Student.status.not_in(["withdrawn", "transferred"]),
            )
        ).all()

        if not remaining_active:
            # No other active duplicate exists; resolve flags on other_s
            other_flags = db.scalars(
                select(ValidationFlag).where(
                    ValidationFlag.student_id == other_s.id,
                    ValidationFlag.rule_code.in_(
                        [DUP_ACTIVE_OTHER_COLLEGE, DUP_SAME_COURSE_OTHER_COLLEGE]
                    ),
                    ValidationFlag.status == "open",
                )
            ).all()

            for ofl in other_flags:
                ofl.status = "resolved"
                resolved_flags.append(ofl)

            # 3. Create resolution notifications for both institutions
            other_inst = other_s.institution
            other_inst_name = other_inst.name if other_inst else "Enrolled Institution"

            notif_own = Notification(
                institution_id=student.institution_id,
                type="DUPLICATE_ENROLMENT_RESOLVED",
                payload_json={
                    "apaar_id": student.apaar_id,
                    "academic_year": student.academic_year,
                    "resolution_action": status_lower,
                    "other_institution_id": other_s.institution_id,
                    "other_institution_name": other_inst_name,
                    "message": (
                        f"Duplicate enrolment flag for APAAR ID {student.apaar_id} "
                        f"resolved as student was marked {status_lower}."
                    ),
                },
            )
            notif_other = Notification(
                institution_id=other_s.institution_id,
                type="DUPLICATE_ENROLMENT_RESOLVED",
                payload_json={
                    "apaar_id": student.apaar_id,
                    "academic_year": student.academic_year,
                    "resolution_action": status_lower,
                    "resolved_by_institution_id": student.institution_id,
                    "resolved_by_institution_name": inst_a_name,
                    "resolved_by_institution_aicte_id": inst_a_code,
                    "message": (
                        f"Duplicate enrolment flag for APAAR ID {student.apaar_id} "
                        f"has been resolved because student was marked {status_lower} "
                        f"at {inst_a_name} ({inst_a_code})."
                    ),
                },
            )
            db.add(notif_own)
            db.add(notif_other)

    db.flush()
    return resolved_flags
