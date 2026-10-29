"""Duplicate enrolment management, cross-college notifications, and flag resolution."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.analytics.schemas import DuplicateInstitutionDetail, DuplicateRecordResponse
from app.integrations.factory import get_otp_sender
from app.models import Course, Notification, Student, Submission, ValidationFlag

DUP_ACTIVE_OTHER_COLLEGE = "DUP_ACTIVE_OTHER_COLLEGE"
DUP_SAME_COURSE_OTHER_COLLEGE = "DUP_SAME_COURSE_OTHER_COLLEGE"


def are_courses_equivalent(c1: Course | None, c2: Course | None) -> bool:
    """Check if two course records represent the same academic course/programme."""
    if c1 is None or c2 is None:
        return False
    if c1.id == c2.id:
        return True

    n1 = (c1.name or "").strip().lower().replace("&", "and")
    n2 = (c2.name or "").strip().lower().replace("&", "and")
    b1 = (c1.branch or "").strip().lower()
    b2 = (c2.branch or "").strip().lower()

    if n1 and n2 and n1 == n2:
        if b1 and b2:
            return b1 == b2
        return True
    return False


def query_duplicates_by_apaar_and_year(
    db: Session,
    apaar_ids: list[str],
    academic_year: str,
    exclude_institution_id: int | None = None,
) -> list[Student]:
    """Query active student records using the (apaar_id, academic_year) index.

    Per TASKS.md T16 & T24:
    Cross-college rules query by apaar_id and year using the index.
    """
    if not apaar_ids:
        return []

    stmt = (
        select(Student)
        .options(
            joinedload(Student.institution),
            joinedload(Student.course),
            joinedload(Student.submission),
        )
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

    inst_a_name = inst_a.name if inst_a else f"Institution #{student.institution_id}"
    inst_a_code = inst_a.aicte_id if inst_a else "AICTE-A"
    inst_b_name = inst_b.name if inst_b else f"Institution #{conflicting_student.institution_id}"
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

    # Also dispatch mock system notifications into dev_outbox
    try:
        otp_sender = get_otp_sender(db)
        if inst_a and inst_a.official_email:
            otp_sender.send_notification(
                channel="email",
                recipient=inst_a.official_email,
                body=notif_a.payload_json["message"],
            )
        if inst_b and inst_b.official_email:
            otp_sender.send_notification(
                channel="email",
                recipient=inst_b.official_email,
                body=notif_b.payload_json["message"],
            )
    except Exception:
        pass

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


def get_duplicate_records(
    db: Session,
    academic_year: str | None = None,
    rule_code: str | None = None,
    status_filter: str | None = None,
) -> list[DuplicateRecordResponse]:
    """Retrieve all cross-college duplicate student records for AICTE monitoring.

    Groups active enrolments by APAAR ID and academic year across multiple institutions.
    SPEC.md Section 12 & TASKS.md T24, T28:
    - Lists students at two or more colleges, with both colleges and resolution status.
    - Two colleges submitting the same APAAR ID produce exactly ONE duplicate record.
    """
    # 1. Identify distinct (apaar_id, academic_year) pairs enrolled in > 1 institution
    stmt = (
        select(Student.apaar_id, Student.academic_year)
        .where(
            Student.apaar_id.is_not(None),
            Student.status.not_in(["withdrawn", "transferred"]),
        )
    )
    if academic_year:
        stmt = stmt.where(Student.academic_year == academic_year)

    stmt = (
        stmt.group_by(Student.apaar_id, Student.academic_year)
        .having(func.count(func.distinct(Student.institution_id)) > 1)
    )
    active_dup_pairs = db.execute(stmt).all()

    # Also identify historical duplicate pairs via flags if status_filter is 'resolved' or None
    flag_dup_pairs: list[Any] = []
    if status_filter in ("resolved", None):
        flag_stmt = (
            select(Student.apaar_id, Student.academic_year)
            .join(ValidationFlag, ValidationFlag.student_id == Student.id)
            .where(
                ValidationFlag.rule_code.in_(
                    [DUP_ACTIVE_OTHER_COLLEGE, DUP_SAME_COURSE_OTHER_COLLEGE]
                ),
                Student.apaar_id.is_not(None),
            )
        )
        if academic_year:
            flag_stmt = flag_stmt.where(Student.academic_year == academic_year)
        flag_stmt = flag_stmt.group_by(Student.apaar_id, Student.academic_year)
        flag_dup_pairs = db.execute(flag_stmt).all()

    # Combine unique (apaar_id, academic_year) keys
    all_keys = list(dict.fromkeys(list(active_dup_pairs) + list(flag_dup_pairs)))
    results: list[DuplicateRecordResponse] = []

    for row_key in all_keys:
        apaar_val = str(row_key[0])
        year_val = str(row_key[1])

        # Fetch all student records for this APAAR ID & year
        students_query = (
            select(Student)
            .options(
                joinedload(Student.institution),
                joinedload(Student.course),
                joinedload(Student.submission),
            )
            .where(
                Student.apaar_id == apaar_val,
                Student.academic_year == year_val,
            )
            .order_by(Student.institution_id, Student.id)
        )
        students = list(db.scalars(students_query).all())
        if not students:
            continue

        # Fetch all validation flags on these students
        s_ids = [s.id for s in students]
        flags = list(
            db.scalars(
                select(ValidationFlag).where(
                    ValidationFlag.student_id.in_(s_ids),
                    ValidationFlag.rule_code.in_(
                        [DUP_ACTIVE_OTHER_COLLEGE, DUP_SAME_COURSE_OTHER_COLLEGE]
                    ),
                )
            ).all()
        )
        flags_by_student: dict[int, ValidationFlag] = {
            f.student_id: f for f in flags if f.student_id is not None
        }

        # Check if any pair represents the exact same course
        has_same_course = False
        for i in range(len(students)):
            for j in range(i + 1, len(students)):
                if are_courses_equivalent(students[i].course, students[j].course):
                    has_same_course = True
                    break
            if has_same_course:
                break

        assigned_rule = (
            DUP_SAME_COURSE_OTHER_COLLEGE if has_same_course else DUP_ACTIVE_OTHER_COLLEGE
        )
        assigned_level = "exception" if has_same_course else "warning"

        if rule_code and assigned_rule != rule_code:
            continue

        # Check active enrolment count
        active_students = [
            s for s in students if (s.status or "").lower() not in ("withdrawn", "transferred")
        ]
        active_institutions = {s.institution_id for s in active_students}

        if len(active_institutions) > 1:
            overall_status = "open"
        else:
            overall_status = "resolved"

        if status_filter and overall_status != status_filter:
            continue

        # Assemble institution details
        inst_details: list[DuplicateInstitutionDetail] = []
        detected_at: datetime | None = None

        for st in students:
            fl = flags_by_student.get(st.id)
            if fl and fl.created_at:
                if detected_at is None or fl.created_at < detected_at:
                    detected_at = fl.created_at

            rec_no = st.submission.receipt_no if st.submission else None
            sub_id = st.submission_id or (st.submission.id if st.submission else None)
            if not rec_no:
                sub_rec = (
                    db.get(Submission, sub_id)
                    if sub_id
                    else db.scalar(
                        select(Submission).where(
                            Submission.institution_id == st.institution_id,
                            Submission.academic_year == year_val,
                        )
                    )
                )
                if sub_rec:
                    rec_no = sub_rec.receipt_no
                    sub_id = sub_rec.id

            inst_name = (
                st.institution.name
                if st.institution
                else f"Institution #{st.institution_id}"
            )
            inst_aicte = st.institution.aicte_id if st.institution else "N/A"
            c_name = st.course.name if st.course else None
            branch = st.course.branch if st.course else None

            inst_details.append(
                DuplicateInstitutionDetail(
                    institution_id=st.institution_id,
                    institution_name=inst_name,
                    aicte_id=inst_aicte,
                    course_id=st.course_id,
                    course_name=c_name,
                    branch=branch,
                    student_id=st.id,
                    student_name=st.name,
                    enrolment_no=st.enrolment_no,
                    student_status=st.status,
                    submission_id=sub_id,
                    receipt_no=rec_no,
                    is_locked=st.is_locked,
                    flag_id=fl.id if fl else None,
                    flag_status=fl.status if fl else None,
                )
            )

        # Use earliest student creation timestamp if no flags
        if detected_at is None and students:
            earliest = min((s.created_at for s in students if s.created_at), default=None)
            detected_at = earliest or datetime.now(UTC)

        results.append(
            DuplicateRecordResponse(
                apaar_id=apaar_val,
                academic_year=year_val,
                rule_code=assigned_rule,
                level=assigned_level,
                status=overall_status,
                institutions_count=len({d.institution_id for d in inst_details}),
                institutions=inst_details,
                detected_at=detected_at,
            )
        )

    return results
