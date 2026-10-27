"""Tests for AICTE Analytics API, database count parity, and real-time SSE streaming.

Spec: Section 10, 12 & TASKS.md T28:
- Direct database aggregation matching exact integer counts (100% parity).
- Overview metrics: colleges, students, intake, exceptions, duplicates, anomalies, progress.
- Breakdown by state and course.
- Submission progress tracking with status breakdown.
- Compliance monitoring and red list (over-intake colleges & overshoot seats).
- Hierarchical drilldown (National -> State -> College -> Course -> Flagged Students).
- Action tools: notice dispatch and flag resolution with hash-chained audit logs.
- RBAC protection: strictly AICTE roles only (403 for college roles).
- SSE event publishing and live buffer inspection.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics import sse
from app.auth.security import create_access_token, encrypt_dob
from app.models import (
    AnomalyScore,
    AuditLog,
    Course,
    CourseIntake,
    Institution,
    Notification,
    Student,
    Submission,
    User,
    ValidationFlag,
)


@pytest.fixture
def aicte_officer_token(db_session: Session) -> str:
    """Generate access token for an AICTE officer."""
    officer = db_session.scalar(select(User).where(User.role == "aicte_officer"))
    if not officer:
        officer = User(
            email="test_officer_analytics@aicte-india.org",
            password_hash="test_hash",
            role="aicte_officer",
            is_active=True,
        )
        db_session.add(officer)
        db_session.flush()
    return create_access_token(
        user_id=officer.id,
        email=officer.email,
        role=officer.role,
        institution_id=officer.institution_id,
    )


@pytest.fixture
def aicte_admin_token(db_session: Session) -> str:
    """Generate access token for an AICTE admin."""
    admin = db_session.scalar(select(User).where(User.role == "aicte_admin"))
    if not admin:
        admin = User(
            email="test_admin_analytics@aicte-india.org",
            password_hash="test_hash",
            role="aicte_admin",
            is_active=True,
        )
        db_session.add(admin)
        db_session.flush()
    return create_access_token(
        user_id=admin.id,
        email=admin.email,
        role=admin.role,
        institution_id=admin.institution_id,
    )


@pytest.fixture
def college_admin_token(db_session: Session) -> str:
    """Generate access token for a college admin."""
    admin = db_session.scalar(select(User).where(User.role == "college_admin"))
    if not admin:
        inst = db_session.scalar(select(Institution))
        if not inst:
            inst = Institution(
                aicte_id="1-99999999",
                name="Test Analytics College",
                state="Maharashtra",
                district="Pune",
                address="Test Campus",
                official_email="test@analytics.edu",
                official_phone="9876543210",
                head_name="Dr. Principal",
                affiliating_university="Test University",
                approval_status="active",
                account_status="active",
            )
            db_session.add(inst)
            db_session.flush()
        admin = User(
            email="test_college_admin_analytics@college.edu",
            password_hash="test_hash",
            role="college_admin",
            institution_id=inst.id,
            is_active=True,
        )
        db_session.add(admin)
        db_session.flush()
    return create_access_token(
        user_id=admin.id,
        email=admin.email,
        role=admin.role,
        institution_id=admin.institution_id,
    )


@pytest.fixture
def seeded_analytics_data(db_session: Session) -> dict[str, int]:
    """Seed comprehensive, deterministic analytics data in the test database session."""
    academic_year = "2026-27"

    # 1. Institutions across two states
    inst1 = Institution(
        aicte_id="1-TEST-MAH-01",
        name="Pune Engineering Institute",
        state="Maharashtra",
        district="Pune",
        address="100 Shivaji Road, Pune",
        official_email="principal@pei-pune.edu",
        official_phone="9876543210",
        head_name="Dr. Anand Deshmukh",
        affiliating_university="Savitribai Phule Pune University",
        approval_status="active",
        account_status="active",
    )
    inst2 = Institution(
        aicte_id="1-TEST-KAR-02",
        name="Bengaluru Institute of Technology",
        state="Karnataka",
        district="Bengaluru",
        address="200 Tech Boulevard, Bengaluru",
        official_email="director@bit-bengaluru.edu",
        official_phone="9876543211",
        head_name="Dr. Suresh Gowda",
        affiliating_university="Visvesvaraya Technological University",
        approval_status="active",
        account_status="active",
    )
    db_session.add_all([inst1, inst2])
    db_session.flush()

    # 2. Courses
    c1 = Course(
        institution_id=inst1.id,
        name="Computer Science and Engineering",
        level="UG",
        branch="Software Engineering",
        duration_years=4,
        supernumerary_allowed=True,
    )
    c2 = Course(
        institution_id=inst1.id,
        name="Mechanical Engineering",
        level="UG",
        branch="Robotics",
        duration_years=4,
        supernumerary_allowed=False,
    )
    c3 = Course(
        institution_id=inst2.id,
        name="Computer Science and Engineering",
        level="UG",
        branch="Artificial Intelligence",
        duration_years=4,
        supernumerary_allowed=True,
    )
    db_session.add_all([c1, c2, c3])
    db_session.flush()

    # 3. Course Intake for 2026-27
    ci1 = CourseIntake(
        course_id=c1.id,
        academic_year=academic_year,
        approved_intake=60,
        supernumerary_seats_allowed=6,
        source="aicte_master",
    )
    ci2 = CourseIntake(
        course_id=c2.id,
        academic_year=academic_year,
        approved_intake=30,
        supernumerary_seats_allowed=0,
        source="aicte_master",
    )
    ci3 = CourseIntake(
        course_id=c3.id,
        academic_year=academic_year,
        approved_intake=60,
        supernumerary_seats_allowed=6,
        source="aicte_master",
    )
    db_session.add_all([ci1, ci2, ci3])
    db_session.flush()

    # 4. Submissions
    sub1 = Submission(
        institution_id=inst1.id,
        academic_year=academic_year,
        status="submitted_with_exceptions",
        receipt_no="REC-202627-MAH01-001",
    )
    sub2 = Submission(
        institution_id=inst2.id,
        academic_year=academic_year,
        status="draft",
    )
    db_session.add_all([sub1, sub2])
    db_session.flush()

    # 5. Students
    # In c1: approved 60. We enroll 70 regular students -> 10 overshoot!
    enc_dob = encrypt_dob("2005-04-12")
    students: list[Student] = []
    for i in range(1, 71):
        s = Student(
            institution_id=inst1.id,
            course_id=c1.id,
            academic_year=academic_year,
            apaar_id=f"90000000{i:04d}",
            name=f"Student Regular {i}",
            dob_encrypted=enc_dob,
            gender="Male" if i % 2 == 0 else "Female",
            enrolment_no=f"ENR-CSE-{i:04d}",
            admission_date=date(2026, 7, 10),
            admission_mode="JEE Main counselling",
            seat_type="Regular",
            reservation_category="General",
            status="submitted",
            is_locked=True,
            submission_id=sub1.id,
        )
        students.append(s)

    # In c2: approved 30. We enroll 15 regular students -> within limit.
    for i in range(1, 16):
        s = Student(
            institution_id=inst1.id,
            course_id=c2.id,
            academic_year=academic_year,
            apaar_id=f"91000000{i:04d}",
            name=f"Student Mech {i}",
            dob_encrypted=enc_dob,
            gender="Female",
            enrolment_no=f"ENR-MEC-{i:04d}",
            admission_date=date(2026, 7, 15),
            admission_mode="State counselling",
            seat_type="Regular",
            reservation_category="OBC",
            status="submitted",
            is_locked=True,
            submission_id=sub1.id,
        )
        students.append(s)

    # In c3: approved 60. We enroll 20 regular students -> within limit.
    for i in range(1, 21):
        s = Student(
            institution_id=inst2.id,
            course_id=c3.id,
            academic_year=academic_year,
            apaar_id=f"92000000{i:04d}",
            name=f"Student AI {i}",
            dob_encrypted=enc_dob,
            gender="Male",
            enrolment_no=f"ENR-AI-{i:04d}",
            admission_date=date(2026, 7, 20),
            admission_mode="Management quota",
            seat_type="Regular",
            reservation_category="General",
            status="draft",
            is_locked=False,
            submission_id=sub2.id,
        )
        students.append(s)

    db_session.add_all(students)
    db_session.flush()

    # 6. Validation Flags
    # INTAKE_EXCEEDED exception on c1
    flag_intake = ValidationFlag(
        course_id=c1.id,
        submission_id=sub1.id,
        rule_code="INTAKE_EXCEEDED",
        level="exception",
        message="Regular admitted (70) exceeds approved intake (60) by 10 seats.",
        fix_hint="Reduce admissions or submit an official justification.",
        audience="both",
        requires_justification=True,
        status="open",
    )
    # Student warning flag on first student
    flag_stu = ValidationFlag(
        student_id=students[0].id,
        submission_id=sub1.id,
        rule_code="APAAR_NAME_MISMATCH",
        level="warning",
        message="Name similarity below threshold.",
        fix_hint="Verify identity against APAAR card.",
        audience="both",
        requires_justification=False,
        status="open",
    )
    db_session.add_all([flag_intake, flag_stu])
    db_session.flush()

    # 7. Anomaly Score
    anom = AnomalyScore(
        institution_id=inst1.id,
        course_id=c1.id,
        academic_year=academic_year,
        score=-0.25,
        flagged=True,
        features_json={
            "summary": "Sudden growth in student enrolments over approved intake",
            "yoy_growth": 0.35,
        },
    )
    db_session.add(anom)
    db_session.flush()

    return {
        "inst1_id": inst1.id,
        "inst2_id": inst2.id,
        "c1_id": c1.id,
        "c2_id": c2.id,
        "c3_id": c3.id,
        "sub1_id": sub1.id,
        "total_students": len(students),
    }


# ---------------------------------------------------------------------------
# 1. Overview Metrics Parity with Direct DB Counts
# ---------------------------------------------------------------------------


def test_overview_metrics_parity_with_database(
    client: TestClient,
    db_session: Session,
    aicte_officer_token: str,
    seeded_analytics_data: dict[str, int],
):
    """Test that GET /api/v1/analytics/overview matches direct database counts exactly."""
    academic_year = "2026-27"
    response = client.get(
        f"/api/v1/analytics/overview?academic_year={academic_year}",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    # Direct database counts
    db_total_colleges = db_session.scalar(select(func.count(Institution.id)))
    db_active_colleges = db_session.scalar(
        select(func.count(Institution.id)).where(
            Institution.approval_status == "active",
            Institution.account_status == "active",
        )
    )
    db_total_students = db_session.scalar(
        select(func.count(Student.id)).where(
            Student.academic_year == academic_year,
            Student.status.not_in(["withdrawn", "transferred"]),
        )
    )
    db_approved_intake = db_session.scalar(
        select(func.coalesce(func.sum(CourseIntake.approved_intake), 0)).where(
            CourseIntake.academic_year == academic_year
        )
    )
    db_supernumerary_intake = db_session.scalar(
        select(func.coalesce(func.sum(CourseIntake.supernumerary_seats_allowed), 0)).where(
            CourseIntake.academic_year == academic_year
        )
    )
    db_total_courses = db_session.scalar(select(func.count(Course.id)))
    db_flagged_anomalies = db_session.scalar(
        select(func.count(AnomalyScore.id)).where(
            AnomalyScore.academic_year == academic_year,
            AnomalyScore.flagged.is_(True),
        )
    )

    # Assert exact equality
    assert data["academic_year"] == academic_year
    assert data["total_colleges"] == db_total_colleges
    assert data["active_colleges"] == db_active_colleges
    assert data["total_students"] == db_total_students
    assert data["approved_intake_total"] == db_approved_intake
    assert data["supernumerary_intake_total"] == db_supernumerary_intake
    assert data["actual_enrolment_total"] == db_total_students
    assert data["total_courses"] == db_total_courses
    assert data["anomalies_count"] == db_flagged_anomalies

    # Submission progress totals
    prog = data["submission_progress"]
    assert prog["total"] == db_active_colleges
    assert prog["submitted"] + prog["pending"] + prog["not_started"] == prog["total"]


# ---------------------------------------------------------------------------
# 2. State Breakdown Parity
# ---------------------------------------------------------------------------


def test_by_state_metrics_parity(
    client: TestClient,
    db_session: Session,
    aicte_officer_token: str,
    seeded_analytics_data: dict[str, int],
):
    """Test that GET /api/v1/analytics/by-state matches database group by state."""
    academic_year = "2026-27"
    response = client.get(
        f"/api/v1/analytics/by-state?academic_year={academic_year}",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    items = data["items"]
    assert len(items) >= 2

    # Total colleges sum across states must equal total colleges in DB
    db_total_colleges = db_session.scalar(select(func.count(Institution.id)))
    assert sum(item["colleges_count"] for item in items) == db_total_colleges

    # Total enrolled sum across states must equal total active students in DB
    db_total_students = db_session.scalar(
        select(func.count(Student.id)).where(
            Student.academic_year == academic_year,
            Student.status.not_in(["withdrawn", "transferred"]),
        )
    )
    assert sum(item["total_enrolled"] for item in items) == db_total_students

    # Test Maharashtra specific metrics
    mah_item = next(i for i in items if i["state"] == "Maharashtra")
    assert mah_item["colleges_count"] == 1
    assert mah_item["regular_admitted"] == 85  # 70 + 15
    assert mah_item["approved_intake"] == 90  # 60 + 30
    assert mah_item["over_intake_colleges"] == 1


# ---------------------------------------------------------------------------
# 3. Course Breakdown Parity
# ---------------------------------------------------------------------------


def test_by_course_metrics_parity(
    client: TestClient,
    db_session: Session,
    aicte_officer_token: str,
    seeded_analytics_data: dict[str, int],
):
    """Test that GET /api/v1/analytics/by-course matches discipline aggregations."""
    academic_year = "2026-27"
    response = client.get(
        f"/api/v1/analytics/by-course?academic_year={academic_year}",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    items = data["items"]
    assert len(items) >= 2

    # Sum of approved intake across courses must equal approved intake total in DB
    db_approved_intake = db_session.scalar(
        select(func.coalesce(func.sum(CourseIntake.approved_intake), 0)).where(
            CourseIntake.academic_year == academic_year
        )
    )
    assert sum(item["approved_intake"] for item in items) == db_approved_intake

    # Test filter by course level
    ug_response = client.get(
        f"/api/v1/analytics/by-course?academic_year={academic_year}&level=UG",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert ug_response.status_code == 200
    ug_items = ug_response.json()["items"]
    assert all(item["level"] == "UG" for item in ug_items)


# ---------------------------------------------------------------------------
# 4. Submission Progress Tracking
# ---------------------------------------------------------------------------


def test_submission_progress_endpoint(
    client: TestClient,
    db_session: Session,
    aicte_officer_token: str,
    seeded_analytics_data: dict[str, int],
):
    """Test GET /api/v1/analytics/submission-progress list and status breakdown."""
    academic_year = "2026-27"
    response = client.get(
        f"/api/v1/analytics/submission-progress?academic_year={academic_year}",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    db_total_institutions = db_session.scalar(select(func.count(Institution.id)))
    assert data["total_institutions"] == db_total_institutions
    assert len(data["items"]) == db_total_institutions

    # Check progress breakdown totals
    assert data["submitted"] + data["pending"] + data["not_started"] == data["total_institutions"]

    # Filter by state
    state_res = client.get(
        f"/api/v1/analytics/submission-progress?academic_year={academic_year}&state=Maharashtra",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert state_res.status_code == 200
    state_items = state_res.json()["items"]
    assert all(item["state"] == "Maharashtra" for item in state_items)


# ---------------------------------------------------------------------------
# 5. Compliance Monitoring & Red List
# ---------------------------------------------------------------------------


def test_compliance_monitoring_and_red_list(
    client: TestClient,
    db_session: Session,
    aicte_officer_token: str,
    seeded_analytics_data: dict[str, int],
):
    """Test GET /api/v1/analytics/compliance flags over-intake courses and institutions."""
    academic_year = "2026-27"
    response = client.get(
        f"/api/v1/analytics/compliance?academic_year={academic_year}&min_overshoot=1",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    items = data["items"]
    assert len(items) >= 1
    top_violation = items[0]
    assert top_violation["course_name"] == "Computer Science and Engineering"
    assert top_violation["approved_intake"] == 60
    assert top_violation["regular_admitted"] == 70
    assert top_violation["overshoot_amount"] == 10
    assert top_violation["red_list"] is True
    assert data["red_list_colleges_count"] >= 1


# ---------------------------------------------------------------------------
# 6. Hierarchical Drilldown (State -> College -> Course -> Students)
# ---------------------------------------------------------------------------


def test_hierarchical_drilldown_workflow(
    client: TestClient,
    db_session: Session,
    aicte_officer_token: str,
    seeded_analytics_data: dict[str, int],
):
    """Test multi-tier drilldown: National -> State -> College -> Course -> Flagged Students."""
    academic_year = "2026-27"

    # Level 1: National (All states)
    res_l1 = client.get(
        f"/api/v1/analytics/drilldown?academic_year={academic_year}",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert res_l1.status_code == 200, res_l1.text
    data_l1 = res_l1.json()
    assert data_l1["level"] == "national"
    assert data_l1["states"] is not None
    assert len(data_l1["states"]) >= 2

    # Level 2: State -> Colleges
    res_l2 = client.get(
        f"/api/v1/analytics/drilldown?academic_year={academic_year}&state=Maharashtra",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert res_l2.status_code == 200, res_l2.text
    data_l2 = res_l2.json()
    assert data_l2["level"] == "state"
    assert data_l2["selected_state"] == "Maharashtra"
    assert data_l2["colleges"] is not None
    assert len(data_l2["colleges"]) >= 1

    selected_inst_id = data_l2["colleges"][0]["institution_id"]

    # Level 3: College -> Courses
    res_l3 = client.get(
        f"/api/v1/analytics/drilldown?academic_year={academic_year}&institution_id={selected_inst_id}",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert res_l3.status_code == 200, res_l3.text
    data_l3 = res_l3.json()
    assert data_l3["level"] == "college"
    assert data_l3["selected_institution"]["id"] == selected_inst_id
    assert data_l3["courses"] is not None
    assert len(data_l3["courses"]) >= 2

    selected_course_id = data_l3["courses"][0]["course_id"]

    # Level 4: Course -> Students
    res_l4 = client.get(
        f"/api/v1/analytics/drilldown?academic_year={academic_year}&institution_id={selected_inst_id}&course_id={selected_course_id}",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert res_l4.status_code == 200, res_l4.text
    data_l4 = res_l4.json()
    assert data_l4["level"] == "course"
    assert data_l4["selected_course"]["id"] == selected_course_id
    assert data_l4["students"] is not None
    assert len(data_l4["students"]) > 0


# ---------------------------------------------------------------------------
# 7. Action Tools: Send Notice and Resolve Flag
# ---------------------------------------------------------------------------


def test_action_tools_send_notice(
    client: TestClient,
    db_session: Session,
    aicte_officer_token: str,
    seeded_analytics_data: dict[str, int],
):
    """Test POST /api/v1/analytics/action/notice dispatches notice with audit logging."""
    institution = db_session.scalar(select(Institution))
    assert institution is not None

    payload = {
        "institution_id": institution.id,
        "subject": "Over-Intake Compliance Directive",
        "message": "Your CSE intake exceeds approved limit by 10 seats. Rectify immediately.",
        "urgency": "urgent",
    }
    response = client.post(
        "/api/v1/analytics/action/notice",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
        json=payload,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["institution_id"] == institution.id
    assert data["payload"]["subject"] == payload["subject"]
    assert data["payload"]["urgency"] == "urgent"

    # Verify notification created in DB
    notif = db_session.scalar(
        select(Notification).where(
            Notification.institution_id == institution.id,
            Notification.type == "AICTE_COMPLIANCE_NOTICE",
        ).order_by(Notification.id.desc())
    )
    assert notif is not None
    assert notif.payload_json["subject"] == payload["subject"]

    # Verify audit log entry
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "analytics.notice_sent",
            AuditLog.entity_id == str(institution.id),
        ).order_by(AuditLog.id.desc())
    )
    assert audit is not None


def test_action_tools_resolve_flag(
    client: TestClient,
    db_session: Session,
    aicte_officer_token: str,
    seeded_analytics_data: dict[str, int],
):
    """Test POST /api/v1/analytics/action/resolve-flag updates flag status with audit log."""
    flag = db_session.scalar(select(ValidationFlag).where(ValidationFlag.status == "open"))
    assert flag is not None

    payload = {
        "flag_id": flag.id,
        "note": "Resolved after review of submitted justification documents.",
        "action": "resolve",
    }
    response = client.post(
        "/api/v1/analytics/action/resolve-flag",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
        json=payload,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["flag_id"] == flag.id
    assert data["status"] == "resolved"
    assert data["resolution_note"] == payload["note"]

    # Verify updated in DB
    db_session.refresh(flag)
    assert flag.status == "resolved"

    # Verify audit log entry
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "analytics.flag_resolved",
            AuditLog.entity_id == str(flag.id),
        ).order_by(AuditLog.id.desc())
    )
    assert audit is not None


# ---------------------------------------------------------------------------
# 8. Server-Sent Events (SSE) Live Buffer and Event Stream
# ---------------------------------------------------------------------------


def test_sse_live_events_buffer(
    client: TestClient,
    aicte_officer_token: str,
):
    """Test GET /api/v1/analytics/events retrieves recent system broadcast events."""
    sse.clear_recent_events()
    sse.publish_sse_event(
        redis_client=None,
        event_type="test_submission_event",
        data={"submission_id": 999, "status": "submitted"},
    )

    response = client.get(
        "/api/v1/analytics/events?limit=10",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert response.status_code == 200, response.text
    events = response.json()
    assert len(events) >= 1
    assert any(e["event"] == "test_submission_event" for e in events)


# ---------------------------------------------------------------------------
# 9. Role-Based Access Control (RBAC) Protection
# ---------------------------------------------------------------------------


def test_analytics_rbac_protection(
    client: TestClient,
    college_admin_token: str,
):
    """Test that college accounts receive HTTP 403 Forbidden on all analytics routes."""
    endpoints = [
        "/api/v1/analytics/overview",
        "/api/v1/analytics/by-state",
        "/api/v1/analytics/by-course",
        "/api/v1/analytics/submission-progress",
        "/api/v1/analytics/compliance",
        "/api/v1/analytics/drilldown",
        "/api/v1/analytics/duplicates",
        "/api/v1/analytics/anomalies",
        "/api/v1/analytics/events",
    ]

    for ep in endpoints:
        # 1. Unauthenticated -> 401
        res_unauth = client.get(ep)
        assert res_unauth.status_code == 401, f"{ep} unauth expected 401"

        # 2. College Admin -> 403 Forbidden
        res_college = client.get(ep, headers={"Authorization": f"Bearer {college_admin_token}"})
        assert res_college.status_code == 403, f"{ep} college expected 403"
