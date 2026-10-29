"""Analytics service for AICTE real-time monitoring and reporting."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import redis
from sqlalchemy import distinct, func, select, union
from sqlalchemy.orm import Session, joinedload

from app.analytics.schemas import (
    ComplianceListResponse,
    ComplianceViolationItem,
    CourseMetricsItem,
    CourseMetricsListResponse,
    DrilldownCollegeSummary,
    DrilldownCourseSummary,
    DrilldownResponse,
    DrilldownStateSummary,
    DrilldownStudentFlagItem,
    DrilldownStudentItem,
    InstitutionSubmissionProgressItem,
    NoticeResponse,
    OverviewMetricsResponse,
    ResolveFlagResponse,
    StateMetricsItem,
    StateMetricsListResponse,
    SubmissionProgressOverview,
    SubmissionProgressResponse,
)
from app.analytics.sse import publish_sse_event
from app.audit import record as record_audit
from app.models import (
    AnomalyScore,
    Course,
    CourseIntake,
    Institution,
    Notification,
    Student,
    Submission,
    User,
    ValidationFlag,
)
from app.students import duplicate_service

logger = logging.getLogger(__name__)


# Helper: Academic Year Flag Scope


def get_academic_year_flag_ids_stmt(academic_year: str):
    """Generate SQLAlchemy select statement of distinct flag IDs belonging to an academic year."""
    sub_flags = (
        select(ValidationFlag.id)
        .join(Submission, ValidationFlag.submission_id == Submission.id)
        .where(Submission.academic_year == academic_year)
    )

    stu_flags = (
        select(ValidationFlag.id)
        .join(Student, ValidationFlag.student_id == Student.id)
        .where(Student.academic_year == academic_year)
    )

    # 3. Flags linked to courses with intake in this academic year (where no submission/student id)
    crs_flags = (
        select(ValidationFlag.id)
        .join(Course, ValidationFlag.course_id == Course.id)
        .join(CourseIntake, CourseIntake.course_id == Course.id)
        .where(
            CourseIntake.academic_year == academic_year,
            ValidationFlag.submission_id.is_(None),
            ValidationFlag.student_id.is_(None),
        )
    )

    return union(sub_flags, stu_flags, crs_flags)


# Overview Metrics


def get_overview_metrics(
    db: Session,
    academic_year: str = "2026-27",
) -> OverviewMetricsResponse:
    """Compute high-level oversight metrics matching direct database counts."""
    total_colleges = db.scalar(select(func.count(Institution.id))) or 0
    active_colleges = (
        db.scalar(
            select(func.count(Institution.id)).where(
                Institution.approval_status == "active",
                Institution.account_status == "active",
            )
        )
        or 0
    )

    total_students = (
        db.scalar(
            select(func.count(Student.id)).where(
                Student.academic_year == academic_year,
                Student.status.not_in(["withdrawn", "transferred"]),
            )
        )
        or 0
    )

    approved_intake_total = (
        db.scalar(
            select(func.coalesce(func.sum(CourseIntake.approved_intake), 0)).where(
                CourseIntake.academic_year == academic_year
            )
        )
        or 0
    )
    supernumerary_intake_total = (
        db.scalar(
            select(func.coalesce(func.sum(CourseIntake.supernumerary_seats_allowed), 0)).where(
                CourseIntake.academic_year == academic_year
            )
        )
        or 0
    )
    total_courses = db.scalar(select(func.count(Course.id))) or 0

    year_flags_union = get_academic_year_flag_ids_stmt(academic_year)

    exceptions_count = (
        db.scalar(
            select(func.count(ValidationFlag.id)).where(
                ValidationFlag.id.in_(year_flags_union),
                ValidationFlag.level == "exception",
                ValidationFlag.status.in_(["open", "justified"]),
            )
        )
        or 0
    )

    errors_count = (
        db.scalar(
            select(func.count(ValidationFlag.id)).where(
                ValidationFlag.id.in_(year_flags_union),
                ValidationFlag.level == "error",
                ValidationFlag.status == "open",
            )
        )
        or 0
    )

    warnings_count = (
        db.scalar(
            select(func.count(ValidationFlag.id)).where(
                ValidationFlag.id.in_(year_flags_union),
                ValidationFlag.level == "warning",
                ValidationFlag.status.in_(["open", "justified"]),
            )
        )
        or 0
    )

    dup_records = duplicate_service.get_duplicate_records(db=db, academic_year=academic_year)
    duplicates_count = len(dup_records)

    anomalies_count = (
        db.scalar(
            select(func.count(AnomalyScore.id)).where(
                AnomalyScore.academic_year == academic_year,
                AnomalyScore.flagged.is_(True),
            )
        )
        or 0
    )

    # 6. Submission Progress across active institutions
    active_institutions = list(
        db.scalars(
            select(Institution).where(
                Institution.approval_status == "active",
                Institution.account_status == "active",
            )
        ).all()
    )

    active_sub_map: dict[int, Submission] = {}
    subs = list(
        db.scalars(
            select(Submission).where(Submission.academic_year == academic_year)
        ).all()
    )
    for s in subs:
        active_sub_map[s.institution_id] = s

    # Count institutions with draft students
    draft_student_inst_ids = set(
        db.scalars(
            select(Student.institution_id).distinct().where(
                Student.academic_year == academic_year,
                Student.status.not_in(["withdrawn", "transferred"]),
            )
        ).all()
    )

    submitted_cnt = 0
    pending_cnt = 0
    not_started_cnt = 0
    status_breakdown: dict[str, int] = {
        "accepted": 0,
        "under_review": 0,
        "query_raised": 0,
        "escalated": 0,
        "submitted_clean": 0,
        "submitted_with_exceptions": 0,
        "draft": 0,
        "not_started": 0,
    }

    for inst in active_institutions:
        sub = active_sub_map.get(inst.id)
        if sub and sub.status in [
            "submitted",
            "submitted_with_exceptions",
            "under_review",
            "accepted",
            "query_raised",
            "escalated",
        ]:
            submitted_cnt += 1
            if sub.status == "submitted":
                status_breakdown["submitted_clean"] += 1
            elif sub.status == "submitted_with_exceptions":
                status_breakdown["submitted_with_exceptions"] += 1
            elif sub.status in status_breakdown:
                status_breakdown[sub.status] += 1
        elif (sub and sub.status == "draft") or (inst.id in draft_student_inst_ids):
            pending_cnt += 1
            status_breakdown["draft"] += 1
        else:
            not_started_cnt += 1
            status_breakdown["not_started"] += 1

    total_tracked = len(active_institutions)
    sub_pct = round((submitted_cnt / total_tracked * 100), 1) if total_tracked > 0 else 0.0

    # 7. Over-intake colleges count (Red List)
    compliance_res = get_compliance_list(db=db, academic_year=academic_year, min_overshoot=1)
    over_intake_colleges_count = compliance_res.red_list_colleges_count

    return OverviewMetricsResponse(
        academic_year=academic_year,
        total_colleges=total_colleges,
        active_colleges=active_colleges,
        total_students=total_students,
        approved_intake_total=approved_intake_total,
        supernumerary_intake_total=supernumerary_intake_total,
        actual_enrolment_total=total_students,
        total_courses=total_courses,
        exceptions_count=exceptions_count,
        errors_count=errors_count,
        warnings_count=warnings_count,
        duplicates_count=duplicates_count,
        anomalies_count=anomalies_count,
        over_intake_colleges_count=over_intake_colleges_count,
        submission_progress=SubmissionProgressOverview(
            total=total_tracked,
            submitted=submitted_cnt,
            pending=pending_cnt,
            not_started=not_started_cnt,
            submitted_percentage=sub_pct,
        ),
        status_breakdown=status_breakdown,
    )


# State Breakdown


def get_by_state(
    db: Session,
    academic_year: str = "2026-27",
) -> StateMetricsListResponse:
    """Compute state-level aggregation of colleges, intake, students, and compliance."""
    # Query distinct states
    states = list(
        db.scalars(
            select(Institution.state).distinct().order_by(Institution.state.asc())
        ).all()
    )

    items: list[StateMetricsItem] = []

    # Pre-load all institutions and their courses/intakes for the year
    institutions = list(
        db.scalars(
            select(Institution).options(
                joinedload(Institution.courses).joinedload(Course.intakes)
            )
        ).unique().all()
    )

    # Map institutions by state
    state_insts: dict[str, list[Institution]] = {}
    for inst in institutions:
        state_insts.setdefault(inst.state, []).append(inst)

    # Active duplicate APAAR student IDs by state
    dup_records = duplicate_service.get_duplicate_records(db=db, academic_year=academic_year)
    state_dup_counts: dict[str, int] = {}
    for dup in dup_records:
        seen_states: set[str] = set()
        for inst_detail in dup.institutions:
            inst_obj = next((i for i in institutions if i.id == inst_detail.institution_id), None)
            if inst_obj and inst_obj.state not in seen_states:
                seen_states.add(inst_obj.state)
                state_dup_counts[inst_obj.state] = state_dup_counts.get(inst_obj.state, 0) + 1

    # Pre-query student counts grouped by institution and seat_type
    student_counts_query = (
        select(
            Student.institution_id,
            Student.seat_type,
            func.count(Student.id).label("cnt"),
        )
        .where(
            Student.academic_year == academic_year,
            Student.status.not_in(["withdrawn", "transferred"]),
        )
        .group_by(Student.institution_id, Student.seat_type)
    )
    student_rows = list(db.execute(student_counts_query).all())
    inst_regular: dict[int, int] = {}
    inst_supernum: dict[int, int] = {}
    for inst_id, seat_type, cnt in student_rows:
        if seat_type == "Regular":
            inst_regular[inst_id] = inst_regular.get(inst_id, 0) + cnt
        else:
            inst_supernum[inst_id] = inst_supernum.get(inst_id, 0) + cnt

    # Course-level regular student counts for over-intake detection
    course_reg_query = (
        select(
            Student.course_id,
            func.count(Student.id).label("cnt"),
        )
        .where(
            Student.academic_year == academic_year,
            Student.status.not_in(["withdrawn", "transferred"]),
            Student.seat_type == "Regular",
            Student.course_id.is_not(None),
        )
        .group_by(Student.course_id)
    )
    course_reg_map = {
        cid: cnt for cid, cnt in db.execute(course_reg_query).all() if cid is not None
    }

    # Pre-query submissions for the year
    subs = list(
        db.scalars(
            select(Submission).where(Submission.academic_year == academic_year)
        ).all()
    )
    sub_map = {s.institution_id: s for s in subs}

    # Pre-query exception flags grouped by institution
    exc_flags_query = (
        select(
            Student.institution_id,
            func.count(distinct(ValidationFlag.id)).label("cnt"),
        )
        .join(ValidationFlag, ValidationFlag.student_id == Student.id)
        .where(
            Student.academic_year == academic_year,
            ValidationFlag.level == "exception",
            ValidationFlag.status.in_(["open", "justified"]),
        )
        .group_by(Student.institution_id)
    )
    exc_flag_rows = list(db.execute(exc_flags_query).all())
    inst_exc_flags = {inst_id: cnt for inst_id, cnt in exc_flag_rows}

    # Course-level exception flags
    crs_exc_flags_query = (
        select(
            Course.institution_id,
            func.count(distinct(ValidationFlag.id)).label("cnt"),
        )
        .join(ValidationFlag, ValidationFlag.course_id == Course.id)
        .join(CourseIntake, CourseIntake.course_id == Course.id)
        .where(
            CourseIntake.academic_year == academic_year,
            ValidationFlag.student_id.is_(None),
            ValidationFlag.level == "exception",
            ValidationFlag.status.in_(["open", "justified"]),
        )
        .group_by(Course.institution_id)
    )
    crs_exc_rows = list(db.execute(crs_exc_flags_query).all())
    for inst_id, cnt in crs_exc_rows:
        inst_exc_flags[inst_id] = inst_exc_flags.get(inst_id, 0) + cnt

    for state in states:
        inst_list = state_insts.get(state, [])
        colleges_count = len(inst_list)
        active_colleges_count = sum(
            1 for i in inst_list if i.approval_status == "active" and i.account_status == "active"
        )

        approved_intake = 0
        regular_admitted = 0
        supernumerary_admitted = 0
        over_intake_colleges = 0
        exceptions_count = 0
        submitted_cnt = 0
        pending_cnt = 0
        not_started_cnt = 0

        for inst in inst_list:
            # Intake
            inst_approved = 0
            for c in inst.courses:
                for ci in c.intakes:
                    if ci.academic_year == academic_year:
                        inst_approved += ci.approved_intake
            approved_intake += inst_approved

            # Admitted
            reg = inst_regular.get(inst.id, 0)
            sup = inst_supernum.get(inst.id, 0)
            regular_admitted += reg
            supernumerary_admitted += sup

            # Over intake check: college is over intake if any course exceeds approved intake
            inst_is_over = False
            for c in inst.courses:
                for ci in c.intakes:
                    if ci.academic_year == academic_year and ci.approved_intake > 0:
                        c_reg = course_reg_map.get(c.id, 0)
                        if c_reg > ci.approved_intake:
                            inst_is_over = True
                            break
                if inst_is_over:
                    break
            if inst_is_over:
                over_intake_colleges += 1

            # Exceptions
            exceptions_count += inst_exc_flags.get(inst.id, 0)

            # Submissions
            sub = sub_map.get(inst.id)
            if sub and sub.status in [
                "submitted",
                "submitted_with_exceptions",
                "under_review",
                "accepted",
                "query_raised",
                "escalated",
            ]:
                submitted_cnt += 1
            elif (sub and sub.status == "draft") or ((reg + sup) > 0):
                pending_cnt += 1
            else:
                not_started_cnt += 1

        total_enrolled = regular_admitted + supernumerary_admitted
        utilization = (
            round((total_enrolled / approved_intake * 100), 1) if approved_intake > 0 else 0.0
        )

        items.append(
            StateMetricsItem(
                state=state,
                colleges_count=colleges_count,
                active_colleges_count=active_colleges_count,
                approved_intake=approved_intake,
                regular_admitted=regular_admitted,
                supernumerary_admitted=supernumerary_admitted,
                total_enrolled=total_enrolled,
                utilization_rate=utilization,
                over_intake_colleges=over_intake_colleges,
                exceptions_count=exceptions_count,
                duplicates_count=state_dup_counts.get(state, 0),
                submissions_submitted=submitted_cnt,
                submissions_pending=pending_cnt,
                submissions_not_started=not_started_cnt,
            )
        )

    return StateMetricsListResponse(
        academic_year=academic_year,
        total_states=len(items),
        items=items,
    )


# Course Breakdown


def get_by_course(
    db: Session,
    academic_year: str = "2026-27",
    level: str | None = None,
) -> CourseMetricsListResponse:
    """Compute course discipline aggregation across institutions."""
    stmt = (
        select(Course)
        .options(
            joinedload(Course.intakes),
            joinedload(Course.institution),
        )
    )
    if level:
        stmt = stmt.where(Course.level == level)

    courses = list(db.scalars(stmt).unique().all())

    # Pre-query students grouped by course_id and seat_type
    stu_stmt = (
        select(
            Student.course_id,
            Student.seat_type,
            func.count(Student.id).label("cnt"),
        )
        .where(
            Student.academic_year == academic_year,
            Student.status.not_in(["withdrawn", "transferred"]),
            Student.course_id.is_not(None),
        )
        .group_by(Student.course_id, Student.seat_type)
    )
    stu_rows = list(db.execute(stu_stmt).all())
    course_reg_map: dict[int, int] = {}
    course_sup_map: dict[int, int] = {}
    for cid, stype, cnt in stu_rows:
        if cid is not None:
            if stype == "Regular":
                course_reg_map[cid] = course_reg_map.get(cid, 0) + cnt
            else:
                course_sup_map[cid] = course_sup_map.get(cid, 0) + cnt

    # Pre-query exception flags grouped by course_id
    flag_stmt = (
        select(
            ValidationFlag.course_id,
            func.count(distinct(ValidationFlag.id)).label("cnt"),
        )
        .where(
            ValidationFlag.level == "exception",
            ValidationFlag.status.in_(["open", "justified"]),
            ValidationFlag.course_id.is_not(None),
        )
        .group_by(ValidationFlag.course_id)
    )
    flag_rows = list(db.execute(flag_stmt).all())
    course_flag_map = {cid: cnt for cid, cnt in flag_rows if cid is not None}

    # Aggregate by (name, level, branch)
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for c in courses:
        intake_row = next((ci for ci in c.intakes if ci.academic_year == academic_year), None)
        app_intake = intake_row.approved_intake if intake_row else 0
        sup_allowed = intake_row.supernumerary_seats_allowed if intake_row else 0

        reg = course_reg_map.get(c.id, 0)
        sup = course_sup_map.get(c.id, 0)
        exc = course_flag_map.get(c.id, 0)
        is_over = 1 if (reg > app_intake and app_intake > 0) else 0

        key = (c.name, c.level, c.branch)
        if key not in groups:
            groups[key] = {
                "course_name": c.name,
                "level": c.level,
                "branch": c.branch,
                "institutions_count": 0,
                "approved_intake": 0,
                "supernumerary_allowed": 0,
                "regular_admitted": 0,
                "supernumerary_admitted": 0,
                "total_enrolled": 0,
                "over_intake_count": 0,
                "exceptions_count": 0,
            }

        g = groups[key]
        g["institutions_count"] += 1
        g["approved_intake"] += app_intake
        g["supernumerary_allowed"] += sup_allowed
        g["regular_admitted"] += reg
        g["supernumerary_admitted"] += sup
        g["total_enrolled"] += (reg + sup)
        g["over_intake_count"] += is_over
        g["exceptions_count"] += exc

    items: list[CourseMetricsItem] = []
    for g in sorted(groups.values(), key=lambda x: (x["course_name"], x["branch"])):
        tot = g["total_enrolled"]
        app = g["approved_intake"]
        util = round((tot / app * 100), 1) if app > 0 else 0.0
        items.append(
            CourseMetricsItem(
                course_name=g["course_name"],
                level=g["level"],
                branch=g["branch"],
                institutions_count=g["institutions_count"],
                approved_intake=app,
                supernumerary_allowed=g["supernumerary_allowed"],
                regular_admitted=g["regular_admitted"],
                supernumerary_admitted=g["supernumerary_admitted"],
                total_enrolled=tot,
                utilization_rate=util,
                over_intake_count=g["over_intake_count"],
                exceptions_count=g["exceptions_count"],
            )
        )

    return CourseMetricsListResponse(
        academic_year=academic_year,
        total_courses=len(items),
        items=items,
    )


# Submission Progress Tracking


def get_submission_progress(
    db: Session,
    academic_year: str = "2026-27",
    state: str | None = None,
    status_filter: str | None = None,
) -> SubmissionProgressResponse:
    """Detailed submission progress across institutions with exact status tracking."""
    inst_stmt = select(Institution).options(
        joinedload(Institution.courses).joinedload(Course.intakes)
    )
    if state:
        inst_stmt = inst_stmt.where(Institution.state == state)

    inst_stmt = inst_stmt.order_by(Institution.name.asc())
    institutions = list(db.scalars(inst_stmt).unique().all())

    # Pre-load submissions
    subs = list(
        db.scalars(
            select(Submission).where(Submission.academic_year == academic_year)
        ).all()
    )
    sub_map = {s.institution_id: s for s in subs}

    # Pre-query student counts
    stu_stmt = (
        select(
            Student.institution_id,
            func.count(Student.id).label("cnt"),
        )
        .where(
            Student.academic_year == academic_year,
            Student.status.not_in(["withdrawn", "transferred"]),
        )
        .group_by(Student.institution_id)
    )
    stu_map = {iid: cnt for iid, cnt in db.execute(stu_stmt).all()}

    # Pre-query flag counts by institution and level
    flag_stmt = (
        select(
            Student.institution_id,
            ValidationFlag.level,
            func.count(distinct(ValidationFlag.id)).label("cnt"),
        )
        .join(ValidationFlag, ValidationFlag.student_id == Student.id)
        .where(
            Student.academic_year == academic_year,
            ValidationFlag.status.in_(["open", "justified"]),
        )
        .group_by(Student.institution_id, ValidationFlag.level)
    )
    inst_level_flags: dict[int, dict[str, int]] = {}
    for iid, lvl, cnt in db.execute(flag_stmt).all():
        inst_level_flags.setdefault(iid, {})[lvl] = cnt

    items: list[InstitutionSubmissionProgressItem] = []
    submitted_cnt = 0
    pending_cnt = 0
    not_started_cnt = 0
    status_breakdown: dict[str, int] = {
        "accepted": 0,
        "under_review": 0,
        "query_raised": 0,
        "escalated": 0,
        "submitted_clean": 0,
        "submitted_with_exceptions": 0,
        "draft": 0,
        "not_started": 0,
    }

    for inst in institutions:
        sub = sub_map.get(inst.id)
        stu_cnt = stu_map.get(inst.id, 0)

        # Intake total
        app_intake = sum(
            ci.approved_intake
            for c in inst.courses
            for ci in c.intakes
            if ci.academic_year == academic_year
        )

        # Determine effective submission status
        if sub and sub.status in [
            "submitted",
            "submitted_with_exceptions",
            "under_review",
            "accepted",
            "query_raised",
            "escalated",
        ]:
            effective_status = sub.status
            submitted_cnt += 1
            if sub.status == "submitted":
                status_breakdown["submitted_clean"] += 1
            elif sub.status == "submitted_with_exceptions":
                status_breakdown["submitted_with_exceptions"] += 1
            elif sub.status in status_breakdown:
                status_breakdown[sub.status] += 1
        elif (sub and sub.status == "draft") or (stu_cnt > 0):
            effective_status = "draft"
            pending_cnt += 1
            status_breakdown["draft"] += 1
        else:
            effective_status = "not_started"
            not_started_cnt += 1
            status_breakdown["not_started"] += 1

        if status_filter and effective_status != status_filter:
            continue

        flags_for_inst = inst_level_flags.get(inst.id, {})
        items.append(
            InstitutionSubmissionProgressItem(
                institution_id=inst.id,
                aicte_id=inst.aicte_id,
                institution_name=inst.name,
                state=inst.state,
                district=inst.district,
                approval_status=inst.approval_status,
                account_status=inst.account_status,
                submission_status=effective_status,
                submitted_at=sub.submitted_at if sub else None,
                receipt_no=sub.receipt_no if sub else None,
                total_students=stu_cnt,
                approved_intake=app_intake,
                error_count=flags_for_inst.get("error", 0),
                exception_count=flags_for_inst.get("exception", 0),
                warning_count=flags_for_inst.get("warning", 0),
            )
        )

    total_inst = len(institutions)
    sub_pct = round((submitted_cnt / total_inst * 100), 1) if total_inst > 0 else 0.0

    return SubmissionProgressResponse(
        academic_year=academic_year,
        total_institutions=total_inst,
        submitted=submitted_cnt,
        pending=pending_cnt,
        not_started=not_started_cnt,
        submitted_percentage=sub_pct,
        status_breakdown=status_breakdown,
        items=items,
    )


# Compliance Monitoring and Red List


def get_compliance_list(
    db: Session,
    academic_year: str = "2026-27",
    state: str | None = None,
    min_overshoot: int = 1,
) -> ComplianceListResponse:
    """List institutions and courses exceeding approved intake or quotas (Red List)."""
    # 1. Query courses and their approved intake for this academic year
    stmt = (
        select(Course, CourseIntake, Institution)
        .join(Institution, Course.institution_id == Institution.id)
        .join(CourseIntake, CourseIntake.course_id == Course.id)
        .where(
            CourseIntake.academic_year == academic_year,
            Institution.approval_status == "active",
        )
    )
    if state:
        stmt = stmt.where(Institution.state == state)

    course_rows = list(db.execute(stmt).all())

    # Pre-query actual student enrolments by course and seat_type
    stu_stmt = (
        select(
            Student.course_id,
            Student.seat_type,
            func.count(Student.id).label("cnt"),
        )
        .where(
            Student.academic_year == academic_year,
            Student.status.not_in(["withdrawn", "transferred"]),
            Student.course_id.is_not(None),
        )
        .group_by(Student.course_id, Student.seat_type)
    )
    stu_enrolment = list(db.execute(stu_stmt).all())
    course_reg_map: dict[int, int] = {}
    course_sup_map: dict[int, int] = {}
    for cid, stype, cnt in stu_enrolment:
        if cid is not None:
            if stype == "Regular":
                course_reg_map[cid] = course_reg_map.get(cid, 0) + cnt
            else:
                course_sup_map[cid] = course_sup_map.get(cid, 0) + cnt

    # Pre-query INTAKE_EXCEEDED and SUPERNUMERARY_EXCEEDED flags
    flags_stmt = (
        select(ValidationFlag)
        .where(
            ValidationFlag.rule_code.in_(["INTAKE_EXCEEDED", "SUPERNUMERARY_EXCEEDED"]),
            ValidationFlag.status.in_(["open", "justified"]),
        )
        .options(joinedload(ValidationFlag.justifications))
    )
    flag_rows = list(db.scalars(flags_stmt).unique().all())
    course_flag_map: dict[int, ValidationFlag] = {}
    for f in flag_rows:
        if f.course_id is not None:
            course_flag_map[f.course_id] = f

    # Pre-query submissions
    subs = list(
        db.scalars(
            select(Submission).where(Submission.academic_year == academic_year)
        ).all()
    )
    sub_map = {s.institution_id: s for s in subs}

    items: list[ComplianceViolationItem] = []
    red_list_institutions: set[int] = set()
    total_overshoot_seats = 0

    for course, intake, inst in course_rows:
        reg_cnt = course_reg_map.get(course.id, 0)
        sup_cnt = course_sup_map.get(course.id, 0)

        app_intake = intake.approved_intake
        sup_allowed = intake.supernumerary_seats_allowed

        overshoot = max(0, reg_cnt - app_intake)
        sup_overshoot = max(0, sup_cnt - sup_allowed)

        flag_obj = course_flag_map.get(course.id)

        # Include if regular overshoot exceeds min_overshoot OR supernumerary overshoot OR open flag
        if (overshoot >= min_overshoot) or (sup_overshoot > 0) or (flag_obj is not None):
            red_list = overshoot > 0
            if red_list:
                red_list_institutions.add(inst.id)
                total_overshoot_seats += overshoot

            sub = sub_map.get(inst.id)
            has_just = bool(flag_obj and len(flag_obj.justifications) > 0)

            items.append(
                ComplianceViolationItem(
                    institution_id=inst.id,
                    aicte_id=inst.aicte_id,
                    institution_name=inst.name,
                    state=inst.state,
                    district=inst.district,
                    approval_status=inst.approval_status,
                    course_id=course.id,
                    course_name=course.name,
                    level=course.level,
                    branch=course.branch,
                    academic_year=academic_year,
                    approved_intake=app_intake,
                    regular_admitted=reg_cnt,
                    overshoot_amount=overshoot,
                    supernumerary_allowed=sup_allowed,
                    supernumerary_admitted=sup_cnt,
                    supernumerary_overshoot=sup_overshoot,
                    red_list=red_list,
                    submission_status=sub.status if sub else "draft",
                    receipt_no=sub.receipt_no if sub else None,
                    flag_id=flag_obj.id if flag_obj else None,
                    flag_status=flag_obj.status if flag_obj else None,
                    has_justification=has_just,
                )
            )

    # Sort descending by overshoot_amount
    items.sort(key=lambda x: (x.overshoot_amount, x.supernumerary_overshoot), reverse=True)

    return ComplianceListResponse(
        academic_year=academic_year,
        total_violations=len(items),
        red_list_colleges_count=len(red_list_institutions),
        total_overshoot_seats=total_overshoot_seats,
        items=items,
    )


# Drilldown (State -> College -> Course -> Flagged Students)


def get_drilldown(
    db: Session,
    academic_year: str = "2026-27",
    state: str | None = None,
    institution_id: int | None = None,
    course_id: int | None = None,
) -> DrilldownResponse:
    """Hierarchical drilldown supporting State -> College -> Course -> Students navigation."""
    # Level 4: Students in specific course
    if course_id is not None and institution_id is not None:
        course = db.get(Course, course_id)
        institution = db.get(Institution, institution_id)
        if not course or not institution:
            raise ValueError("Institution or Course not found")

        # Query students enrolled in this course for this academic year
        students = list(
            db.scalars(
                select(Student)
                .options(joinedload(Student.flags))
                .where(
                    Student.institution_id == institution_id,
                    Student.course_id == course_id,
                    Student.academic_year == academic_year,
                    Student.status.not_in(["withdrawn", "transferred"]),
                )
                .order_by(Student.name.asc())
            ).unique().all()
        )

        student_items: list[DrilldownStudentItem] = []
        for s in students:
            flag_items = [
                DrilldownStudentFlagItem(
                    id=f.id,
                    rule_code=f.rule_code,
                    level=f.level,
                    field=f.field,
                    message=f.message,
                    fix_hint=f.fix_hint,
                    status=f.status,
                    requires_justification=f.requires_justification,
                )
                for f in s.flags
                if f.status in ["open", "justified"]
            ]
            student_items.append(
                DrilldownStudentItem(
                    student_id=s.id,
                    apaar_id=s.apaar_id,
                    name=s.name,
                    enrolment_no=s.enrolment_no,
                    gender=s.gender,
                    admission_mode=s.admission_mode,
                    seat_type=s.seat_type,
                    status=s.status,
                    flags=flag_items,
                )
            )

        # Prioritize students with flags first
        student_items.sort(key=lambda x: len(x.flags), reverse=True)

        return DrilldownResponse(
            level="course",
            academic_year=academic_year,
            selected_state=institution.state,
            selected_institution={
                "id": institution.id,
                "name": institution.name,
                "aicte_id": institution.aicte_id,
            },
            selected_course={
                "id": course.id,
                "name": course.name,
                "branch": course.branch,
                "level": course.level,
            },
            students=student_items,
        )

    # Level 3: Courses in specific college
    if institution_id is not None:
        institution = db.get(Institution, institution_id)
        if not institution:
            raise ValueError(f"Institution {institution_id} not found")

        courses = list(
            db.scalars(
                select(Course)
                .options(joinedload(Course.intakes))
                .where(Course.institution_id == institution_id)
                .order_by(Course.name.asc())
            ).unique().all()
        )

        # Pre-query students
        stu_stmt = (
            select(
                Student.course_id,
                Student.seat_type,
                func.count(Student.id).label("cnt"),
            )
            .where(
                Student.institution_id == institution_id,
                Student.academic_year == academic_year,
                Student.status.not_in(["withdrawn", "transferred"]),
            )
            .group_by(Student.course_id, Student.seat_type)
        )
        stu_counts = list(db.execute(stu_stmt).all())
        reg_map: dict[int, int] = {}
        sup_map: dict[int, int] = {}
        for cid, stype, cnt in stu_counts:
            if cid is not None:
                if stype == "Regular":
                    reg_map[cid] = reg_map.get(cid, 0) + cnt
                else:
                    sup_map[cid] = sup_map.get(cid, 0) + cnt

        # Pre-query flag counts per course
        flags_stmt = (
            select(
                Student.course_id,
                ValidationFlag.level,
                func.count(distinct(ValidationFlag.id)).label("cnt"),
            )
            .join(ValidationFlag, ValidationFlag.student_id == Student.id)
            .where(
                Student.institution_id == institution_id,
                Student.academic_year == academic_year,
                ValidationFlag.status.in_(["open", "justified"]),
            )
            .group_by(Student.course_id, ValidationFlag.level)
        )
        flag_counts = list(db.execute(flags_stmt).all())
        course_flags: dict[int, dict[str, int]] = {}
        for cid, lvl, cnt in flag_counts:
            if cid is not None:
                course_flags.setdefault(cid, {})[lvl] = cnt

        # Add course-level flags (e.g. INTAKE_EXCEEDED)
        crs_flag_stmt = (
            select(
                ValidationFlag.course_id,
                ValidationFlag.level,
                func.count(distinct(ValidationFlag.id)).label("cnt"),
            )
            .where(
                ValidationFlag.course_id.in_([c.id for c in courses]),
                ValidationFlag.student_id.is_(None),
                ValidationFlag.status.in_(["open", "justified"]),
            )
            .group_by(ValidationFlag.course_id, ValidationFlag.level)
        )
        for cid, lvl, cnt in db.execute(crs_flag_stmt).all():
            if cid is not None:
                c_dict = course_flags.setdefault(cid, {})
                c_dict[lvl] = c_dict.get(lvl, 0) + cnt

        # Flagged students count
        flagged_students_stmt = (
            select(
                Student.course_id,
                func.count(distinct(Student.id)).label("cnt"),
            )
            .join(ValidationFlag, ValidationFlag.student_id == Student.id)
            .where(
                Student.institution_id == institution_id,
                Student.academic_year == academic_year,
                ValidationFlag.status.in_(["open", "justified"]),
            )
            .group_by(Student.course_id)
        )
        flagged_students_map = {
            cid: cnt for cid, cnt in db.execute(flagged_students_stmt).all() if cid is not None
        }

        course_items: list[DrilldownCourseSummary] = []
        for c in courses:
            intake_row = next((ci for ci in c.intakes if ci.academic_year == academic_year), None)
            app_intake = intake_row.approved_intake if intake_row else 0
            sup_allowed = intake_row.supernumerary_seats_allowed if intake_row else 0

            reg = reg_map.get(c.id, 0)
            sup = sup_map.get(c.id, 0)
            tot = reg + sup

            overshoot = max(0, reg - app_intake)
            badge = f"over_by_{overshoot}" if overshoot > 0 else "within_limit"

            c_flags = course_flags.get(c.id, {})

            course_items.append(
                DrilldownCourseSummary(
                    course_id=c.id,
                    course_name=c.name,
                    level=c.level,
                    branch=c.branch,
                    approved_intake=app_intake,
                    supernumerary_allowed=sup_allowed,
                    regular_admitted=reg,
                    supernumerary_admitted=sup,
                    total_enrolled=tot,
                    overshoot_amount=overshoot,
                    status_badge=badge,
                    flagged_students_count=flagged_students_map.get(c.id, 0),
                    error_count=c_flags.get("error", 0),
                    exception_count=c_flags.get("exception", 0),
                    warning_count=c_flags.get("warning", 0),
                )
            )

        return DrilldownResponse(
            level="college",
            academic_year=academic_year,
            selected_state=institution.state,
            selected_institution={
                "id": institution.id,
                "name": institution.name,
                "aicte_id": institution.aicte_id,
            },
            courses=course_items,
        )

    # Level 2: Colleges in specific state
    if state is not None:
        institutions = list(
            db.scalars(
                select(Institution)
                .options(joinedload(Institution.courses).joinedload(Course.intakes))
                .where(Institution.state == state)
                .order_by(Institution.name.asc())
            ).unique().all()
        )

        subs = list(
            db.scalars(
                select(Submission).where(Submission.academic_year == academic_year)
            ).all()
        )
        sub_map = {s.institution_id: s for s in subs}

        # Pre-query student counts
        stu_stmt = (
            select(
                Student.institution_id,
                Student.seat_type,
                func.count(Student.id).label("cnt"),
            )
            .join(Institution, Student.institution_id == Institution.id)
            .where(
                Institution.state == state,
                Student.academic_year == academic_year,
                Student.status.not_in(["withdrawn", "transferred"]),
            )
            .group_by(Student.institution_id, Student.seat_type)
        )
        inst_reg_map: dict[int, int] = {}
        inst_sup_map: dict[int, int] = {}
        for iid, stype, cnt in db.execute(stu_stmt).all():
            if stype == "Regular":
                inst_reg_map[iid] = inst_reg_map.get(iid, 0) + cnt
            else:
                inst_sup_map[iid] = inst_sup_map.get(iid, 0) + cnt

        # Pre-query flag counts
        flags_stmt = (
            select(
                Student.institution_id,
                ValidationFlag.level,
                func.count(distinct(ValidationFlag.id)).label("cnt"),
            )
            .join(ValidationFlag, ValidationFlag.student_id == Student.id)
            .join(Institution, Student.institution_id == Institution.id)
            .where(
                Institution.state == state,
                Student.academic_year == academic_year,
                ValidationFlag.status.in_(["open", "justified"]),
            )
            .group_by(Student.institution_id, ValidationFlag.level)
        )
        inst_flags: dict[int, dict[str, int]] = {}
        for iid, lvl, cnt in db.execute(flags_stmt).all():
            inst_flags.setdefault(iid, {})[lvl] = cnt

        college_items: list[DrilldownCollegeSummary] = []
        for inst in institutions:
            sub = sub_map.get(inst.id)
            app_intake = sum(
                ci.approved_intake
                for c in inst.courses
                for ci in c.intakes
                if ci.academic_year == academic_year
            )
            reg = inst_reg_map.get(inst.id, 0)
            sup = inst_sup_map.get(inst.id, 0)
            tot = reg + sup
            overshoot = max(0, reg - app_intake)

            i_flags = inst_flags.get(inst.id, {})

            college_items.append(
                DrilldownCollegeSummary(
                    institution_id=inst.id,
                    aicte_id=inst.aicte_id,
                    institution_name=inst.name,
                    district=inst.district,
                    approval_status=inst.approval_status,
                    submission_status=sub.status if sub else "draft",
                    courses_count=len(inst.courses),
                    approved_intake=app_intake,
                    actual_enrolment=tot,
                    overshoot_amount=overshoot,
                    error_count=i_flags.get("error", 0),
                    exception_count=i_flags.get("exception", 0),
                    warning_count=i_flags.get("warning", 0),
                )
            )

        return DrilldownResponse(
            level="state",
            academic_year=academic_year,
            selected_state=state,
            colleges=college_items,
        )

    # Level 1: National (All states)
    state_res = get_by_state(db=db, academic_year=academic_year)
    state_summaries = [
        DrilldownStateSummary(
            state=s.state,
            colleges_count=s.colleges_count,
            approved_intake=s.approved_intake,
            actual_enrolment=s.total_enrolled,
            exceptions_count=s.exceptions_count,
            over_intake_colleges=s.over_intake_colleges,
        )
        for s in state_res.items
    ]

    return DrilldownResponse(
        level="national",
        academic_year=academic_year,
        states=state_summaries,
    )


# Action Tools (Notice dispatch and flag resolution)


def send_institution_notice(
    db: Session,
    current_user: User,
    institution_id: int,
    subject: str,
    message: str,
    urgency: str = "normal",
    redis_client: redis.Redis | None = None,
) -> NoticeResponse:
    """Dispatch official AICTE notice to an institution with SSE and audit log."""
    institution = db.get(Institution, institution_id)
    if not institution:
        raise ValueError(f"Institution {institution_id} not found")

    payload = {
        "subject": subject,
        "message": message,
        "urgency": urgency,
        "sender": current_user.email,
        "sent_at": datetime.now(UTC).isoformat(),
    }

    notification = Notification(
        institution_id=institution_id,
        type="AICTE_COMPLIANCE_NOTICE",
        payload_json=payload,
    )
    db.add(notification)
    db.flush()

    # Audit log
    record_audit(
        db=db,
        action="analytics.notice_sent",
        actor_id=str(current_user.id),
        actor_role=current_user.role,
        entity="institution",
        entity_id=str(institution_id),
        after_json=payload,
    )

    db.commit()
    db.refresh(notification)

    # Broadcast via SSE
    publish_sse_event(
        redis_client=redis_client,
        event_type="notice_sent",
        data={
            "notification_id": notification.id,
            "institution_id": institution_id,
            "institution_name": institution.name,
            "subject": subject,
            "urgency": urgency,
        },
    )

    return NoticeResponse(
        id=notification.id,
        institution_id=institution_id,
        type=notification.type,
        payload=notification.payload_json,
        created_at=notification.created_at,
    )


def resolve_validation_flag(
    db: Session,
    current_user: User,
    flag_id: int,
    note: str,
    action: str = "resolve",
    redis_client: redis.Redis | None = None,
) -> ResolveFlagResponse:
    """Mark a validation flag as resolved or dismissed by AICTE officer."""
    flag = db.get(ValidationFlag, flag_id)
    if not flag:
        raise ValueError(f"ValidationFlag {flag_id} not found")

    old_status = flag.status
    new_status = "resolved" if action == "resolve" else "dismissed"
    flag.status = new_status

    # If linked to student, check if other open blocking flags remain
    if flag.student_id is not None:
        student = db.get(Student, flag.student_id)
        if student and student.status == "flagged":
            open_blocking = db.scalar(
                select(func.count(ValidationFlag.id)).where(
                    ValidationFlag.student_id == student.id,
                    ValidationFlag.id != flag.id,
                    ValidationFlag.level.in_(["error", "exception"]),
                    ValidationFlag.status.in_(["open"]),
                )
            )
            if open_blocking == 0:
                student.status = "valid"

    # Audit log
    record_audit(
        db=db,
        action="analytics.flag_resolved",
        actor_id=str(current_user.id),
        actor_role=current_user.role,
        entity="validation_flag",
        entity_id=str(flag_id),
        before_json={"status": old_status},
        after_json={"status": new_status, "note": note, "action": action},
    )

    db.commit()
    db.refresh(flag)

    # Broadcast via SSE
    publish_sse_event(
        redis_client=redis_client,
        event_type="flag_resolved",
        data={
            "flag_id": flag.id,
            "rule_code": flag.rule_code,
            "level": flag.level,
            "status": flag.status,
            "note": note,
        },
    )

    return ResolveFlagResponse(
        flag_id=flag.id,
        rule_code=flag.rule_code,
        status=flag.status,
        resolution_note=note,
        updated_at=datetime.now(UTC),
    )
