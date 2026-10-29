"""Core reporting engine for the 7 official AICTE reports."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import case, distinct, func, select
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import check_institution_access
from app.models import (
    AnomalyScore,
    Course,
    CourseIntake,
    Institution,
    SeatDeclaration,
    Student,
    Submission,
    User,
    ValidationFlag,
)
from app.reports.exporters import export_to_csv, export_to_pdf, export_to_xlsx
from app.reports.schemas import (
    ReportData,
    ReportFormat,
    ReportSummaryBox,
    ReportType,
)

logger = logging.getLogger(__name__)


def mask_apaar(apaar_id: str | None) -> str:
    """Mask 12-digit APAAR ID preserving only last 4 digits for privacy."""
    if not apaar_id:
        return "N/A"
    cleaned = apaar_id.replace("-", "").strip()
    if len(cleaned) == 12:
        return f"XXXX-XXXX-{cleaned[-4:]}"
    return f"XXXX-{cleaned[-4:]}" if len(cleaned) >= 4 else "XXXX"


# 1. Enrolment by State and Course


def generate_enrolment_by_state_course(
    db: Session,
    academic_year: str = "2026-27",
    state: str | None = None,
    course: str | None = None,
) -> ReportData:
    """Report 1: Aggregated enrolment, intake, and fill rate by State and Course."""
    # Query aggregated stats grouped by State, Course Name, Level
    stmt = (
        select(
            Institution.state.label("state"),
            Course.name.label("course_name"),
            Course.level.label("course_level"),
            func.count(distinct(Institution.id)).label("colleges_count"),
            func.coalesce(func.sum(CourseIntake.approved_intake), 0).label("approved_intake"),
            func.coalesce(func.sum(CourseIntake.supernumerary_seats_allowed), 0).label(
                "supernumerary_allowed"
            ),
        )
        .join(Institution, Course.institution_id == Institution.id)
        .join(CourseIntake, CourseIntake.course_id == Course.id)
        .where(
            CourseIntake.academic_year == academic_year,
            Institution.approval_status == "active",
        )
    )

    if state:
        stmt = stmt.where(Institution.state == state)
    if course:
        stmt = stmt.where(Course.name.ilike(f"%{course}%"))

    stmt = stmt.group_by(Institution.state, Course.name, Course.level).order_by(
        Institution.state, Course.name
    )
    rows_data = list(db.execute(stmt).all())

    # Query student counts grouped by State, Course Name, Level
    stu_stmt = (
        select(
            Institution.state.label("state"),
            Course.name.label("course_name"),
            Course.level.label("course_level"),
            func.coalesce(
                func.sum(case((Student.seat_type == "Regular", 1), else_=0)), 0
            ).label("regular_admitted"),
            func.coalesce(
                func.sum(case((Student.seat_type == "Supernumerary", 1), else_=0)), 0
            ).label("supernumerary_admitted"),
            func.count(Student.id).label("total_admitted"),
        )
        .join(Institution, Student.institution_id == Institution.id)
        .join(Course, Student.course_id == Course.id)
        .where(
            Student.academic_year == academic_year,
            Student.status.not_in(["withdrawn", "transferred"]),
            Institution.approval_status == "active",
        )
    )

    if state:
        stu_stmt = stu_stmt.where(Institution.state == state)
    if course:
        stu_stmt = stu_stmt.where(Course.name.ilike(f"%{course}%"))

    stu_stmt = stu_stmt.group_by(Institution.state, Course.name, Course.level)
    stu_dict = {
        (r.state, r.course_name, r.course_level): (
            r.regular_admitted,
            r.supernumerary_admitted,
            r.total_admitted,
        )
        for r in db.execute(stu_stmt).all()
    }

    # Format table rows and calculate running totals
    table_rows: list[list[Any]] = []
    tot_colleges_set: set[str] = set()
    tot_approved_intake = 0
    tot_supernumerary_allowed = 0
    tot_regular_admitted = 0
    tot_supernumerary_admitted = 0
    tot_enrolled = 0

    for r in rows_data:
        key = (r.state, r.course_name, r.course_level)
        reg_adm, super_adm, total_adm = stu_dict.get(key, (0, 0, 0))

        appr_intake = int(r.approved_intake)
        fill_rate = round((total_adm / appr_intake) * 100, 1) if appr_intake > 0 else 0.0

        table_rows.append(
            [
                r.state,
                r.course_name,
                r.course_level,
                int(r.colleges_count),
                appr_intake,
                int(r.supernumerary_allowed),
                int(reg_adm),
                int(super_adm),
                int(total_adm),
                fill_rate,
            ]
        )

        tot_colleges_set.add(f"{r.state}_{r.course_name}")
        tot_approved_intake += appr_intake
        tot_supernumerary_allowed += int(r.supernumerary_allowed)
        tot_regular_admitted += int(reg_adm)
        tot_supernumerary_admitted += int(super_adm)
        tot_enrolled += int(total_adm)

    # Distinct institution count matching query filters
    distinct_inst_count = (
        db.scalar(
            select(func.count(distinct(Institution.id)))
            .join(Course, Course.institution_id == Institution.id)
            .join(CourseIntake, CourseIntake.course_id == Course.id)
            .where(
                CourseIntake.academic_year == academic_year,
                Institution.approval_status == "active",
                Institution.state == state if state else True,
                Course.name.ilike(f"%{course}%") if course else True,
            )
        )
        or 0
    )

    overall_fill_rate = (
        round((tot_enrolled / tot_approved_intake) * 100, 1) if tot_approved_intake > 0 else 0.0
    )

    totals_row = [
        "National Total" if not state else f"Total ({state})",
        "-",
        "-",
        int(distinct_inst_count),
        tot_approved_intake,
        tot_supernumerary_allowed,
        tot_regular_admitted,
        tot_supernumerary_admitted,
        tot_enrolled,
        overall_fill_rate,
    ]

    summary_boxes = [
        ReportSummaryBox(
            label="Approved Intake",
            value=tot_approved_intake,
            detail="Sanctioned quota",
        ),
        ReportSummaryBox(
            label="Total Enrolled",
            value=tot_enrolled,
            detail="Active students",
        ),
        ReportSummaryBox(
            label="Regular Admissions",
            value=tot_regular_admitted,
            detail="Standard seats",
        ),
        ReportSummaryBox(
            label="Supernumerary",
            value=tot_supernumerary_admitted,
            detail="TFW / J&K / KM seats",
        ),
        ReportSummaryBox(
            label="Overall Fill Rate",
            value=f"{overall_fill_rate}%",
            detail="Capacity utilization",
        ),
    ]

    return ReportData(
        report_type=ReportType.ENROLMENT_BY_STATE_COURSE,
        title="Enrolment by State and Course Report",
        subtitle=(
            "National intake, admissions, and capacity fill rate broken down by state and course"
        ),
        academic_year=academic_year,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        filters_applied={"state": state, "course": course, "academic_year": academic_year},
        summary_boxes=summary_boxes,
        columns=[
            "State",
            "Course Discipline",
            "Level",
            "Institutions Offering",
            "Approved Intake",
            "Supernumerary Quota",
            "Regular Admitted",
            "Supernumerary Admitted",
            "Total Admitted",
            "Fill Rate (%)",
        ],
        rows=table_rows,
        totals_row=totals_row,
        notes=[
            "Admissions exclude withdrawn and transferred students.",
            "Counts match central APAAR registry records.",
        ],
    )


# 2. Seat Utilisation (Admitted vs Intake)


def generate_seat_utilisation(
    db: Session,
    academic_year: str = "2026-27",
    state: str | None = None,
    course: str | None = None,
) -> ReportData:
    """Report 2: Institutional course-level seat utilisation and intake compliance."""
    stmt = (
        select(
            Institution.aicte_id,
            Institution.name.label("institution_name"),
            Institution.state,
            Course.name.label("course_name"),
            Course.level.label("course_level"),
            Course.id.label("course_id"),
            CourseIntake.approved_intake,
            CourseIntake.supernumerary_seats_allowed,
        )
        .join(Institution, Course.institution_id == Institution.id)
        .join(CourseIntake, CourseIntake.course_id == Course.id)
        .where(
            CourseIntake.academic_year == academic_year,
            Institution.approval_status == "active",
        )
    )

    if state:
        stmt = stmt.where(Institution.state == state)
    if course:
        stmt = stmt.where(Course.name.ilike(f"%{course}%"))

    stmt = stmt.order_by(Institution.state, Institution.name, Course.name)
    course_list = list(db.execute(stmt).all())

    # Get student counts per course
    course_ids = [c.course_id for c in course_list]
    stu_dict: dict[int, tuple[int, int, int]] = {}
    if course_ids:
        stu_stmt = (
            select(
                Student.course_id,
                func.coalesce(
                    func.sum(case((Student.seat_type == "Regular", 1), else_=0)), 0
                ).label("regular_admitted"),
                func.coalesce(
                    func.sum(case((Student.seat_type == "Supernumerary", 1), else_=0)), 0
                ).label("supernumerary_admitted"),
                func.count(Student.id).label("total_admitted"),
            )
            .where(
                Student.course_id.in_(course_ids),
                Student.academic_year == academic_year,
                Student.status.not_in(["withdrawn", "transferred"]),
            )
            .group_by(Student.course_id)
        )
        stu_dict = {
            r.course_id: (
                int(r.regular_admitted),
                int(r.supernumerary_admitted),
                int(r.total_admitted),
            )
            for r in db.execute(stu_stmt).all()
        }

    table_rows: list[list[Any]] = []
    tot_intake = 0
    tot_super_allowed = 0
    tot_regular = 0
    tot_super = 0
    tot_admitted = 0
    over_intake_courses_count = 0
    total_overshoot = 0

    for c in course_list:
        reg_adm, super_adm, total_adm = stu_dict.get(c.course_id, (0, 0, 0))
        appr_intake = int(c.approved_intake)

        util_rate = round((total_adm / appr_intake) * 100, 1) if appr_intake > 0 else 0.0

        overshoot = max(0, reg_adm - appr_intake)
        if overshoot > 0:
            status_text = f"OVER INTAKE (+{overshoot})"
            over_intake_courses_count += 1
            total_overshoot += overshoot
        elif reg_adm == appr_intake:
            status_text = "Full (100%)"
        else:
            status_text = f"Available ({appr_intake - reg_adm})"

        table_rows.append(
            [
                c.aicte_id,
                c.institution_name,
                c.state,
                c.course_name,
                c.course_level,
                appr_intake,
                int(c.supernumerary_seats_allowed),
                reg_adm,
                super_adm,
                total_adm,
                util_rate,
                status_text,
            ]
        )

        tot_intake += appr_intake
        tot_super_allowed += int(c.supernumerary_seats_allowed)
        tot_regular += reg_adm
        tot_super += super_adm
        tot_admitted += total_adm

    overall_util = round((tot_admitted / tot_intake) * 100, 1) if tot_intake > 0 else 0.0

    totals_row = [
        "National Total" if not state else f"Total ({state})",
        f"{len(course_list)} Courses",
        "-",
        "-",
        "-",
        tot_intake,
        tot_super_allowed,
        tot_regular,
        tot_super,
        tot_admitted,
        overall_util,
        f"{over_intake_courses_count} Over-Intake Courses (+{total_overshoot})",
    ]

    summary_boxes = [
        ReportSummaryBox(
            label="Total Approved Intake",
            value=tot_intake,
            detail="Sanctioned quota",
        ),
        ReportSummaryBox(
            label="Total Admitted",
            value=tot_admitted,
            detail="Enrolled students",
        ),
        ReportSummaryBox(
            label="Capacity Utilisation",
            value=f"{overall_util}%",
            detail="Admitted vs Intake",
        ),
        ReportSummaryBox(
            label="Over-Intake Courses",
            value=over_intake_courses_count,
            detail=f"+{total_overshoot} over-quota admissions",
        ),
    ]

    return ReportData(
        report_type=ReportType.SEAT_UTILISATION,
        title="Seat Utilisation and Intake Compliance Report",
        subtitle=(
            "Detailed institutional course-level seat utilisation, quota limits, "
            "and over-intake tracking"
        ),
        academic_year=academic_year,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        filters_applied={"state": state, "course": course, "academic_year": academic_year},
        summary_boxes=summary_boxes,
        columns=[
            "AICTE ID",
            "Institution Name",
            "State",
            "Course Name",
            "Level",
            "Approved Intake",
            "Supernum Quota",
            "Regular Admitted",
            "Supernum Admitted",
            "Total Admitted",
            "Utilisation (%)",
            "Quota Status",
        ],
        rows=table_rows,
        totals_row=totals_row,
        notes=[
            "Over-intake status flags regular admissions exceeding AICTE approved intake.",
            "Supernumerary admissions are verified against statutory allowances (e.g. TFW, PMSSS).",
        ],
    )


# 3. Colleges with Exceptions


def generate_colleges_with_exceptions(
    db: Session,
    academic_year: str = "2026-27",
    state: str | None = None,
    course: str | None = None,
) -> ReportData:
    """Report 3: Register of institutions with validation exceptions and justifications."""
    stmt = (
        select(ValidationFlag)
        .options(
            joinedload(ValidationFlag.course).joinedload(Course.institution),
            joinedload(ValidationFlag.student).joinedload(Student.institution),
            joinedload(ValidationFlag.submission).joinedload(Submission.institution),
            joinedload(ValidationFlag.justifications),
        )
        .where(
            ValidationFlag.level == "exception",
            ValidationFlag.status.in_(["open", "justified"]),
        )
    )

    all_flags = list(db.scalars(stmt).unique().all())

    # Filter and construct rows
    table_rows: list[list[Any]] = []
    affected_colleges: set[str] = set()
    justified_count = 0
    open_count = 0

    for flag in all_flags:
        # Determine institution, course, academic_year
        inst = None
        c_name = "-"
        flag_year = None

        if flag.student:
            inst = flag.student.institution
            flag_year = flag.student.academic_year
            if flag.student.course:
                c_name = flag.student.course.name
        elif flag.course:
            inst = flag.course.institution
            c_name = flag.course.name
            # If course intake exists for this year
            if flag.course.intakes:
                flag_year = flag.course.intakes[0].academic_year
        elif flag.submission:
            inst = flag.submission.institution
            flag_year = flag.submission.academic_year

        if not inst:
            continue

        if flag_year and flag_year != academic_year:
            continue

        if state and inst.state != state:
            continue

        if course and (c_name == "-" or course.lower() not in c_name.lower()):
            continue

        # Justification details
        just_text = "-"
        just_doc = "-"
        if flag.justifications:
            latest_just = flag.justifications[-1]
            just_text = latest_just.text
            just_doc = latest_just.document_ref or "-"

        if flag.status == "justified":
            justified_count += 1
        else:
            open_count += 1

        affected_colleges.add(inst.aicte_id)

        table_rows.append(
            [
                inst.aicte_id,
                inst.name,
                inst.state,
                c_name,
                flag.rule_code,
                flag.level.upper(),
                flag.message,
                flag.status.title(),
                just_text,
                just_doc,
            ]
        )

    totals_row = [
        "Total Exceptions",
        f"{len(affected_colleges)} Institutions Affected",
        "-",
        "-",
        f"{len(table_rows)} Total Flags",
        "EXCEPTION",
        "-",
        f"{justified_count} Justified / {open_count} Open",
        "-",
        "-",
    ]

    summary_boxes = [
        ReportSummaryBox(
            label="Total Exceptions",
            value=len(table_rows),
            detail="Requiring review/justification",
        ),
        ReportSummaryBox(
            label="Colleges Affected",
            value=len(affected_colleges),
            detail="Distinct institutions",
        ),
        ReportSummaryBox(
            label="Justified",
            value=justified_count,
            detail="With written rationale",
        ),
        ReportSummaryBox(
            label="Pending Justification",
            value=open_count,
            detail="Awaiting college response",
        ),
    ]

    return ReportData(
        report_type=ReportType.COLLEGES_WITH_EXCEPTIONS,
        title="Colleges with Exceptions Report",
        subtitle=(
            "Institutions with recorded validation exceptions, justifications, and evidence"
        ),
        academic_year=academic_year,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        filters_applied={"state": state, "course": course, "academic_year": academic_year},
        summary_boxes=summary_boxes,
        columns=[
            "AICTE ID",
            "Institution Name",
            "State",
            "Course Name",
            "Rule Code",
            "Level",
            "Exception Message",
            "Status",
            "College Justification",
            "Evidence Document",
        ],
        rows=table_rows,
        totals_row=totals_row,
        notes=[
            "Exceptions allow conditional submission when backed by official justification.",
            "Errors cannot be justified and must be corrected before submission.",
        ],
    )


# 4. Duplicate Enrolments


def generate_duplicate_enrolments(
    db: Session,
    academic_year: str = "2026-27",
    state: str | None = None,
) -> ReportData:
    """Report 4: Cross-college duplicate student enrolments across AICTE institutions."""
    from app.students import duplicate_service

    dup_records = duplicate_service.get_duplicate_records(db=db, academic_year=academic_year)

    # Pre-fetch institution states
    inst_ids: set[int] = set()
    for dup in dup_records:
        for inst in dup.institutions:
            inst_ids.add(inst.institution_id)

    inst_state_map: dict[int, str] = {}
    if inst_ids:
        inst_rows = db.execute(
            select(Institution.id, Institution.state).where(Institution.id.in_(inst_ids))
        ).all()
        inst_state_map = {row.id: (row.state or "-") for row in inst_rows}

    table_rows: list[list[Any]] = []
    affected_colleges: set[str] = set()
    active_count = 0
    resolved_count = 0

    for dup in dup_records:
        inst_a = dup.institutions[0] if len(dup.institutions) > 0 else None
        inst_b = dup.institutions[1] if len(dup.institutions) > 1 else None

        state_a = inst_state_map.get(inst_a.institution_id, "-") if inst_a else "-"
        state_b = inst_state_map.get(inst_b.institution_id, "-") if inst_b else "-"

        if state:
            state_match = (state_a == state) or (state_b == state)
            if not state_match:
                continue

        if inst_a:
            affected_colleges.add(inst_a.aicte_id)
        if inst_b:
            affected_colleges.add(inst_b.aicte_id)

        stu_name = inst_a.student_name if inst_a else (inst_b.student_name if inst_b else "N/A")

        if getattr(dup, "status", "open") == "open":
            active_count += 1
            res_str = "Active Duplicate"
        else:
            resolved_count += 1
            res_str = "Resolved (Withdrawn/Transferred)"

        table_rows.append(
            [
                mask_apaar(dup.apaar_id),
                stu_name,
                dup.academic_year,
                inst_a.aicte_id if inst_a else "-",
                inst_a.institution_name if inst_a else "-",
                state_a,
                inst_a.course_name if inst_a else "-",
                inst_b.aicte_id if inst_b else "-",
                inst_b.institution_name if inst_b else "-",
                state_b,
                inst_b.course_name if inst_b else "-",
                res_str,
            ]
        )

    totals_row = [
        "Total Cases",
        f"{len(table_rows)} Students",
        academic_year,
        f"{len(affected_colleges)} Colleges",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        f"{active_count} Active / {resolved_count} Resolved",
    ]

    summary_boxes = [
        ReportSummaryBox(
            label="Duplicate Cases",
            value=len(table_rows),
            detail="Cross-college dual admissions",
        ),
        ReportSummaryBox(
            label="Institutions Affected",
            value=len(affected_colleges),
            detail="Colleges involved",
        ),
        ReportSummaryBox(
            label="Active Multi-Enrolments",
            value=active_count,
            detail="Violates single-regular rule",
        ),
        ReportSummaryBox(
            label="Resolved / Cleared",
            value=resolved_count,
            detail="Marked withdrawn/transferred",
        ),
    ]

    return ReportData(
        report_type=ReportType.DUPLICATE_ENROLMENTS,
        title="Cross-College Duplicate Enrolments Report",
        subtitle="Students enrolled at two or more AICTE institutions in the same academic year",
        academic_year=academic_year,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        filters_applied={"state": state, "academic_year": academic_year},
        summary_boxes=summary_boxes,
        columns=[
            "Masked APAAR ID",
            "Student Name",
            "Academic Year",
            "College A (ID)",
            "College A (Name)",
            "College A (State)",
            "College A (Course)",
            "College B (ID)",
            "College B (Name)",
            "College B (State)",
            "College B (Course)",
            "Resolution Status",
        ],
        rows=table_rows,
        totals_row=totals_row,
        notes=[
            "APAAR IDs are masked to protect student privacy in accordance with DPDP principles.",
            "Resolution of a duplicate at one college automatically clears the flag at both.",
        ],
    )


# 5. Year-over-Year Trends


def generate_year_over_year_trends(
    db: Session,
    state: str | None = None,
    course: str | None = None,
    base_year: str = "2025-26",
    target_year: str = "2026-27",
) -> ReportData:
    """Report 5: Comparative admissions, intake, and growth trends between academic years."""
    # Base Year stats
    stmt_base = (
        select(
            Institution.state.label("state"),
            Course.name.label("course_name"),
            Course.level.label("course_level"),
            func.coalesce(func.sum(CourseIntake.approved_intake), 0).label("approved_intake"),
        )
        .join(Institution, Course.institution_id == Institution.id)
        .join(CourseIntake, CourseIntake.course_id == Course.id)
        .where(
            CourseIntake.academic_year == base_year,
            Institution.approval_status == "active",
        )
    )
    if state:
        stmt_base = stmt_base.where(Institution.state == state)
    if course:
        stmt_base = stmt_base.where(Course.name.ilike(f"%{course}%"))
    stmt_base = stmt_base.group_by(Institution.state, Course.name, Course.level)

    base_intake_map = {
        (r.state, r.course_name, r.course_level): int(r.approved_intake)
        for r in db.execute(stmt_base).all()
    }

    # Base Year students
    stu_base = (
        select(
            Institution.state.label("state"),
            Course.name.label("course_name"),
            Course.level.label("course_level"),
            func.count(Student.id).label("total_admitted"),
        )
        .join(Institution, Student.institution_id == Institution.id)
        .join(Course, Student.course_id == Course.id)
        .where(
            Student.academic_year == base_year,
            Student.status.not_in(["withdrawn", "transferred"]),
            Institution.approval_status == "active",
        )
    )
    if state:
        stu_base = stu_base.where(Institution.state == state)
    if course:
        stu_base = stu_base.where(Course.name.ilike(f"%{course}%"))
    stu_base = stu_base.group_by(Institution.state, Course.name, Course.level)

    base_stu_map = {
        (r.state, r.course_name, r.course_level): int(r.total_admitted)
        for r in db.execute(stu_base).all()
    }

    # Target Year stats
    stmt_target = (
        select(
            Institution.state.label("state"),
            Course.name.label("course_name"),
            Course.level.label("course_level"),
            func.coalesce(func.sum(CourseIntake.approved_intake), 0).label("approved_intake"),
        )
        .join(Institution, Course.institution_id == Institution.id)
        .join(CourseIntake, CourseIntake.course_id == Course.id)
        .where(
            CourseIntake.academic_year == target_year,
            Institution.approval_status == "active",
        )
    )
    if state:
        stmt_target = stmt_target.where(Institution.state == state)
    if course:
        stmt_target = stmt_target.where(Course.name.ilike(f"%{course}%"))
    stmt_target = stmt_target.group_by(Institution.state, Course.name, Course.level)

    target_intake_map = {
        (r.state, r.course_name, r.course_level): int(r.approved_intake)
        for r in db.execute(stmt_target).all()
    }

    # Target Year students
    stu_target = (
        select(
            Institution.state.label("state"),
            Course.name.label("course_name"),
            Course.level.label("course_level"),
            func.count(Student.id).label("total_admitted"),
        )
        .join(Institution, Student.institution_id == Institution.id)
        .join(Course, Student.course_id == Course.id)
        .where(
            Student.academic_year == target_year,
            Student.status.not_in(["withdrawn", "transferred"]),
            Institution.approval_status == "active",
        )
    )
    if state:
        stu_target = stu_target.where(Institution.state == state)
    if course:
        stu_target = stu_target.where(Course.name.ilike(f"%{course}%"))
    stu_target = stu_target.group_by(Institution.state, Course.name, Course.level)

    target_stu_map = {
        (r.state, r.course_name, r.course_level): int(r.total_admitted)
        for r in db.execute(stu_target).all()
    }

    all_keys = sorted(
        set(base_intake_map.keys())
        | set(base_stu_map.keys())
        | set(target_intake_map.keys())
        | set(target_stu_map.keys())
    )

    table_rows: list[list[Any]] = []
    tot_base_intake = 0
    tot_base_admitted = 0
    tot_target_intake = 0
    tot_target_admitted = 0

    for key in all_keys:
        st, c_name, c_level = key
        b_intake = base_intake_map.get(key, 0)
        b_adm = base_stu_map.get(key, 0)
        b_fill = round((b_adm / b_intake) * 100, 1) if b_intake > 0 else 0.0

        t_intake = target_intake_map.get(key, 0)
        t_adm = target_stu_map.get(key, 0)
        t_fill = round((t_adm / t_intake) * 100, 1) if t_intake > 0 else 0.0

        net_diff = t_adm - b_adm
        growth_pct = round((net_diff / b_adm) * 100, 1) if b_adm > 0 else 0.0

        table_rows.append(
            [
                st,
                c_name,
                c_level,
                b_intake,
                b_adm,
                b_fill,
                t_intake,
                t_adm,
                t_fill,
                net_diff,
                growth_pct,
            ]
        )

        tot_base_intake += b_intake
        tot_base_admitted += b_adm
        tot_target_intake += t_intake
        tot_target_admitted += t_adm

    overall_base_fill = (
        round((tot_base_admitted / tot_base_intake) * 100, 1) if tot_base_intake > 0 else 0.0
    )
    overall_target_fill = (
        round((tot_target_admitted / tot_target_intake) * 100, 1) if tot_target_intake > 0 else 0.0
    )
    overall_net = tot_target_admitted - tot_base_admitted
    overall_growth = (
        round((overall_net / tot_base_admitted) * 100, 1) if tot_base_admitted > 0 else 0.0
    )

    totals_row = [
        "National Total" if not state else f"Total ({state})",
        f"{len(table_rows)} Courses",
        "-",
        tot_base_intake,
        tot_base_admitted,
        overall_base_fill,
        tot_target_intake,
        tot_target_admitted,
        overall_target_fill,
        overall_net,
        overall_growth,
    ]

    summary_boxes = [
        ReportSummaryBox(
            label=f"{base_year} Admitted",
            value=tot_base_admitted,
            detail="Prior year baseline",
        ),
        ReportSummaryBox(
            label=f"{target_year} Admitted",
            value=tot_target_admitted,
            detail="Current year admissions",
        ),
        ReportSummaryBox(
            label="Net Admitted Change",
            value=f"{overall_net:+d}",
            detail="Year-over-year difference",
        ),
        ReportSummaryBox(
            label="YoY Growth Rate",
            value=f"{overall_growth:+0.1f}%",
            detail="Growth percentage",
        ),
    ]

    return ReportData(
        report_type=ReportType.YEAR_OVER_YEAR_TRENDS,
        title="Year-over-Year (YoY) Admission Trends Report",
        subtitle=(
            f"Comparative growth, approved intake, and fill rate ({base_year} vs {target_year})"
        ),
        academic_year=f"{base_year} vs {target_year}",
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        filters_applied={
            "state": state,
            "course": course,
            "base_year": base_year,
            "target_year": target_year,
        },
        summary_boxes=summary_boxes,
        columns=[
            "State",
            "Course Name",
            "Level",
            f"{base_year} Intake",
            f"{base_year} Admitted",
            f"{base_year} Fill %",
            f"{target_year} Intake",
            f"{target_year} Admitted",
            f"{target_year} Fill %",
            "Net Change",
            "YoY Growth (%)",
        ],
        rows=table_rows,
        totals_row=totals_row,
        notes=[
            f"{base_year} accepted history represents verified central repository baseline.",
            "YoY growth is evaluated by anomaly detection models to flag anomalous intake spikes.",
        ],
    )


# 6. Accreditation Snapshot for One College


def generate_accreditation_snapshot(
    db: Session,
    institution_id: int,
    academic_year: str = "2026-27",
) -> ReportData:
    """Report 6: Comprehensive institutional accreditation and compliance snapshot."""
    inst = db.get(Institution, institution_id)
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution with ID {institution_id} not found",
        )

    # 1. Submission status
    sub = db.scalar(
        select(Submission).where(
            Submission.institution_id == institution_id,
            Submission.academic_year == academic_year,
        )
    )
    sub_status = sub.status.replace("_", " ").title() if sub else "Not Started"
    receipt_no = sub.receipt_no if (sub and sub.receipt_no) else "Unsubmitted / Draft"

    # 2. Courses, Intakes, and Declarations
    courses_stmt = (
        select(Course, CourseIntake)
        .outerjoin(
            CourseIntake,
            (CourseIntake.course_id == Course.id) & (CourseIntake.academic_year == academic_year),
        )
        .where(Course.institution_id == institution_id)
        .order_by(Course.level, Course.name)
    )
    course_rows = list(db.execute(courses_stmt).all())

    # Seat declarations
    decl_stmt = select(SeatDeclaration).where(
        SeatDeclaration.course_id.in_([c.Course.id for c in course_rows]),
        SeatDeclaration.academic_year == academic_year,
    )
    decl_map = {d.course_id: d for d in db.scalars(decl_stmt).all()}

    # Student counts per course
    stu_stmt = (
        select(
            Student.course_id,
            func.coalesce(
                func.sum(case((Student.seat_type == "Regular", 1), else_=0)), 0
            ).label("regular_admitted"),
            func.coalesce(
                func.sum(case((Student.seat_type == "Supernumerary", 1), else_=0)), 0
            ).label("supernumerary_admitted"),
            func.coalesce(
                func.sum(case((Student.nri == "Yes", 1), else_=0)), 0
            ).label("nri_count"),
            func.count(Student.id).label("total_admitted"),
        )
        .where(
            Student.institution_id == institution_id,
            Student.academic_year == academic_year,
            Student.status.not_in(["withdrawn", "transferred"]),
        )
        .group_by(Student.course_id)
    )
    stu_map = {
        r.course_id: (
            int(r.regular_admitted),
            int(r.supernumerary_admitted),
            int(r.nri_count),
            int(r.total_admitted),
        )
        for r in db.execute(stu_stmt).all()
    }

    table_rows: list[list[Any]] = []
    tot_intake = 0
    tot_declared = 0
    tot_regular = 0
    tot_super = 0
    tot_nri = 0
    tot_enrolled = 0
    over_intake_count = 0

    for c, intake in course_rows:
        appr_intake = intake.approved_intake if intake else 0
        decl = decl_map.get(c.id)
        decl_seats = (
            (decl.regular_admitted + decl.supernumerary_admitted) if decl else appr_intake
        )

        reg_adm, super_adm, nri_c, total_adm = stu_map.get(c.id, (0, 0, 0, 0))
        util = round((total_adm / appr_intake) * 100, 1) if appr_intake > 0 else 0.0

        if reg_adm > appr_intake:
            comp_status = f"NON-COMPLIANT (+{reg_adm - appr_intake})"
            over_intake_count += (reg_adm - appr_intake)
        else:
            comp_status = "Compliant"

        table_rows.append(
            [
                c.name,
                c.level,
                c.branch,
                appr_intake,
                decl_seats,
                reg_adm,
                super_adm,
                nri_c,
                total_adm,
                util,
                comp_status,
            ]
        )

        tot_intake += appr_intake
        tot_declared += decl_seats
        tot_regular += reg_adm
        tot_super += super_adm
        tot_nri += nri_c
        tot_enrolled += total_adm

    overall_util = round((tot_enrolled / tot_intake) * 100, 1) if tot_intake > 0 else 0.0

    compliance_summary = (
        f"Compliant (Overshoot: {over_intake_count})"
        if over_intake_count == 0
        else f"NON-COMPLIANT (+{over_intake_count})"
    )

    totals_row = [
        "Institutional Total",
        f"{len(course_rows)} Courses",
        "-",
        tot_intake,
        tot_declared,
        tot_regular,
        tot_super,
        tot_nri,
        tot_enrolled,
        overall_util,
        compliance_summary,
    ]

    # Validation Flags summary
    flag_count_stmt = (
        select(
            ValidationFlag.level,
            func.count(ValidationFlag.id),
        )
        .join(Student, ValidationFlag.student_id == Student.id)
        .where(
            Student.institution_id == institution_id,
            Student.academic_year == academic_year,
            ValidationFlag.status.in_(["open", "justified"]),
        )
        .group_by(ValidationFlag.level)
    )
    flag_counts = dict(db.execute(flag_count_stmt).all())
    err_c = flag_counts.get("error", 0)
    exc_c = flag_counts.get("exception", 0)
    warn_c = flag_counts.get("warning", 0)

    # Anomaly status
    anom = db.scalar(
        select(AnomalyScore).where(
            AnomalyScore.institution_id == institution_id,
            AnomalyScore.academic_year == academic_year,
        )
    )
    anom_str = "Flagged (High Risk)" if (anom and anom.flagged) else "Normal (Low Risk)"

    summary_boxes = [
        ReportSummaryBox(
            label="Sanctioned Intake",
            value=tot_intake,
            detail=f"{len(course_rows)} Approved Programmes",
        ),
        ReportSummaryBox(
            label="Total Enrolled",
            value=tot_enrolled,
            detail=f"Capacity Utilisation: {overall_util}%",
        ),
        ReportSummaryBox(
            label="Submission Status",
            value=sub_status,
            detail=f"Receipt: {receipt_no[:20]}",
        ),
        ReportSummaryBox(
            label="Flagged Issues",
            value=f"{err_c} Errors / {exc_c} Exceptions",
            detail=f"{warn_c} Warnings Logged",
        ),
        ReportSummaryBox(
            label="AICTE Anomaly Risk",
            value=anom_str,
            detail=f"Approval: {inst.approval_status.upper()}",
        ),
    ]

    return ReportData(
        report_type=ReportType.ACCREDITATION_SNAPSHOT,
        title=f"Accreditation Compliance Snapshot - {inst.name}",
        subtitle=(
            f"AICTE ID: {inst.aicte_id} | State: {inst.state} | "
            f"Affiliating University: {inst.affiliating_university} | "
            f"Status: {inst.approval_status.upper()}"
        ),
        academic_year=academic_year,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        filters_applied={"institution_id": institution_id, "academic_year": academic_year},
        summary_boxes=summary_boxes,
        columns=[
            "Course Name",
            "Level",
            "Branch",
            "Approved Intake",
            "Declared Seats",
            "Regular Admitted",
            "Supernum Admitted",
            "NRI / FN",
            "Total Enrolled",
            "Utilisation (%)",
            "Quota Compliance",
        ],
        rows=table_rows,
        totals_row=totals_row,
        notes=[
            f"Official Contact: {inst.official_email} | Head of Institution: {inst.head_name}",
            "Certified under the AICTE Approval Process Handbook (APH) and EduTrace Platform.",
        ],
    )


# 7. College's Own Submission Report


def generate_college_submission_report(
    db: Session,
    institution_id: int,
    academic_year: str = "2026-27",
    course_id: int | None = None,
) -> ReportData:
    """Report 7: Formal submission register and student roster for a single college."""
    inst = db.get(Institution, institution_id)
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution with ID {institution_id} not found",
        )

    sub = db.scalar(
        select(Submission)
        .options(joinedload(Submission.submitter))
        .where(
            Submission.institution_id == institution_id,
            Submission.academic_year == academic_year,
        )
    )

    sub_status = sub.status.replace("_", " ").title() if sub else "Draft / Unsubmitted"
    receipt_no = sub.receipt_no if (sub and sub.receipt_no) else "PENDING_FINAL_SUBMISSION"
    submitter_str = (
        f"{sub.submitter.email} at {sub.submitted_at.strftime('%Y-%m-%d %H:%M')}"
        if (sub and sub.submitter and sub.submitted_at)
        else "In Preparation"
    )

    # Query students
    stu_stmt = (
        select(Student)
        .options(joinedload(Student.course))
        .where(
            Student.institution_id == institution_id,
            Student.academic_year == academic_year,
        )
    )
    if course_id:
        stu_stmt = stu_stmt.where(Student.course_id == course_id)

    stu_stmt = stu_stmt.order_by(Student.course_id, Student.enrolment_no)
    students = list(db.scalars(stu_stmt).unique().all())

    table_rows: list[list[Any]] = []
    regular_count = 0
    supernum_count = 0
    male_count = 0
    female_count = 0
    flagged_count = 0

    for idx, s in enumerate(students, start=1):
        if s.seat_type == "Regular":
            regular_count += 1
        elif s.seat_type == "Supernumerary":
            supernum_count += 1

        g_upper = (s.gender or "").upper()
        if g_upper.startswith("M"):
            male_count += 1
        elif g_upper.startswith("F"):
            female_count += 1

        if s.status == "flagged":
            flagged_count += 1

        c_name = s.course.name if s.course else "Unassigned / General"
        adm_date_str = s.admission_date.strftime("%Y-%m-%d") if s.admission_date else "-"

        table_rows.append(
            [
                idx,
                mask_apaar(s.apaar_id),
                s.name,
                s.enrolment_no,
                c_name,
                adm_date_str,
                s.admission_mode,
                s.seat_type,
                s.reservation_category,
                s.gender,
                s.status.title(),
            ]
        )

    totals_row = [
        "Roster Total",
        f"{len(students)} Students",
        "-",
        "-",
        "-",
        "-",
        f"Reg: {regular_count} / Super: {supernum_count}",
        "-",
        f"M: {male_count} / F: {female_count}",
        "-",
        f"{flagged_count} Flagged" if flagged_count > 0 else "All Clean",
    ]

    summary_boxes = [
        ReportSummaryBox(
            label="Total Students",
            value=len(students),
            detail="Registered in roster",
        ),
        ReportSummaryBox(
            label="Regular Admissions",
            value=regular_count,
            detail="Standard sanctioned quota",
        ),
        ReportSummaryBox(
            label="Supernumerary Seats",
            value=supernum_count,
            detail="TFW / J&K / KM / GOI",
        ),
        ReportSummaryBox(
            label="Official Receipt",
            value=receipt_no[:20],
            detail=f"Status: {sub_status}",
        ),
        ReportSummaryBox(
            label="Submitted By",
            value=submitter_str,
            detail="Statutory declaration verified",
        ),
    ]

    return ReportData(
        report_type=ReportType.COLLEGE_SUBMISSION,
        title=f"Institutional Student Submission Report - {inst.name}",
        subtitle=(
            f"AICTE ID: {inst.aicte_id} | State: {inst.state} | "
            f"Receipt No: {receipt_no} | Status: {sub_status.upper()}"
        ),
        academic_year=academic_year,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        filters_applied={
            "institution_id": institution_id,
            "academic_year": academic_year,
            "course_id": course_id,
        },
        summary_boxes=summary_boxes,
        columns=[
            "S.No",
            "Masked APAAR ID",
            "Student Name",
            "Enrolment No",
            "Course Name",
            "Admission Date",
            "Mode",
            "Seat Type",
            "Category",
            "Gender",
            "Status",
        ],
        rows=table_rows,
        totals_row=totals_row,
        notes=[
            f"Institution Official Email: {inst.official_email} | Address: {inst.address}",
            "APAAR IDs are displayed in masked format to preserve data privacy under DPDP rules.",
            "This report is an official regulatory record submitted to the Central Repository.",
        ],
    )


# Dispatcher / File Generation


def generate_report(
    db: Session,
    report_type: ReportType,
    output_format: ReportFormat,
    current_user: User,
    academic_year: str = "2026-27",
    state: str | None = None,
    course: str | None = None,
    institution_id: int | None = None,
    course_id: int | None = None,
    base_year: str = "2025-26",
    target_year: str = "2026-27",
) -> tuple[bytes, str, str]:
    """Execute query, assemble ReportData, and export to specified format.

    Returns:
        tuple[bytes, str, str]: (content_bytes, media_type, filename)
    """
    # 1. Dispatch query logic based on report_type
    if report_type == ReportType.ENROLMENT_BY_STATE_COURSE:
        report_data = generate_enrolment_by_state_course(
            db=db, academic_year=academic_year, state=state, course=course
        )
        base_name = f"enrolment_by_state_course_{academic_year}"

    elif report_type == ReportType.SEAT_UTILISATION:
        report_data = generate_seat_utilisation(
            db=db, academic_year=academic_year, state=state, course=course
        )
        base_name = f"seat_utilisation_{academic_year}"

    elif report_type == ReportType.COLLEGES_WITH_EXCEPTIONS:
        report_data = generate_colleges_with_exceptions(
            db=db, academic_year=academic_year, state=state, course=course
        )
        base_name = f"colleges_with_exceptions_{academic_year}"

    elif report_type == ReportType.DUPLICATE_ENROLMENTS:
        report_data = generate_duplicate_enrolments(
            db=db, academic_year=academic_year, state=state
        )
        base_name = f"duplicate_enrolments_{academic_year}"

    elif report_type == ReportType.YEAR_OVER_YEAR_TRENDS:
        report_data = generate_year_over_year_trends(
            db=db,
            state=state,
            course=course,
            base_year=base_year,
            target_year=target_year,
        )
        base_name = f"yoy_trends_{base_year}_to_{target_year}"

    elif report_type == ReportType.ACCREDITATION_SNAPSHOT:
        target_inst_id = institution_id or current_user.institution_id
        if not target_inst_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="institution_id is required for accreditation snapshot",
            )
        # IDOR protection
        check_institution_access(target_inst_id, current_user)
        report_data = generate_accreditation_snapshot(
            db=db, institution_id=target_inst_id, academic_year=academic_year
        )
        base_name = f"accreditation_snapshot_inst_{target_inst_id}_{academic_year}"

    elif report_type == ReportType.COLLEGE_SUBMISSION:
        target_inst_id = institution_id or current_user.institution_id
        if not target_inst_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="institution_id is required for college submission report",
            )
        # IDOR protection
        check_institution_access(target_inst_id, current_user)
        report_data = generate_college_submission_report(
            db=db,
            institution_id=target_inst_id,
            academic_year=academic_year,
            course_id=course_id,
        )
        base_name = f"submission_report_inst_{target_inst_id}_{academic_year}"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported report type: {report_type}",
        )

    # 2. Export to requested format
    if output_format == ReportFormat.CSV:
        content = export_to_csv(report_data)
        media_type = "text/csv; charset=utf-8"
        filename = f"{base_name}.csv"

    elif output_format == ReportFormat.XLSX:
        content = export_to_xlsx(report_data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{base_name}.xlsx"

    elif output_format == ReportFormat.PDF:
        content = export_to_pdf(report_data)
        media_type = "application/pdf"
        filename = f"{base_name}.pdf"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {output_format}",
        )

    return content, media_type, filename
