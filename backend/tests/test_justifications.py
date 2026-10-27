"""Test suite for validation flags, justifications, storage integration, and submit gate checks.

TASKS.md T22 & SPEC.md Sections 9.1, 10:
- Write a justification and attach a document per exception or warning.
- Stored through the Storage interface.
- Flag status changes to 'justified'.
- A justification is kept when validation re-runs and the flag still applies.
- Error-level flags cannot be justified; underlying data must be fixed.
- Hash-chained audit log entry recorded.
- Strict institution scoping (IDOR) and role access limits (college_viewer cannot justify).
"""

from __future__ import annotations

import io
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, encrypt_dob, hash_password
from app.integrations.factory import get_storage
from app.models import (
    AuditLog,
    Course,
    CourseIntake,
    Institution,
    SeatDeclaration,
    Student,
    User,
    ValidationFlag,
)
from app.validation.service import validate_course


def _setup_test_institution(
    db: Session,
    suffix: str = "just1",
) -> tuple[Institution, Course, User, User, str, str]:
    """Provision institution, course, college_admin, college_viewer, and access tokens."""
    inst = Institution(
        aicte_id=f"1-TEST-J-{suffix.upper()}",
        name=f"Institute of Technology {suffix}",
        state="Maharashtra",
        district="Mumbai",
        address="Bandra West",
        official_email=f"admin_{suffix}@tech.ac.in",
        official_phone="9876543210",
        head_name="Director Dr. Kulkarni",
        affiliating_university="Mumbai University",
        approval_status="active",
        account_status="active",
    )
    db.add(inst)
    db.flush()

    course = Course(
        institution_id=inst.id,
        name="Computer Engineering",
        level="UG",
        branch="Computer Engineering",
        duration_years=4,
        supernumerary_allowed=True,
    )
    db.add(course)
    db.flush()

    intake = CourseIntake(
        course_id=course.id,
        academic_year="2026-27",
        approved_intake=60,
        supernumerary_seats_allowed=6,
        source="AICTE Master Approval",
        set_by="system",
    )
    db.add(intake)

    decl = SeatDeclaration(
        course_id=course.id,
        academic_year="2026-27",
        regular_admitted=60,
        supernumerary_admitted=0,
        nri_count=0,
        oci_count=0,
        fn_count=0,
        status="declared",
    )
    db.add(decl)
    db.flush()

    admin_user = User(
        email=f"admin_{suffix}@tech.ac.in",
        password_hash=hash_password("Password123!"),
        role="college_admin",
        institution_id=inst.id,
        is_active=True,
    )
    db.add(admin_user)

    viewer_user = User(
        email=f"viewer_{suffix}@tech.ac.in",
        password_hash=hash_password("Password123!"),
        role="college_viewer",
        institution_id=inst.id,
        is_active=True,
    )
    db.add(viewer_user)
    db.flush()

    admin_token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        role=admin_user.role,
        institution_id=inst.id,
    )
    viewer_token = create_access_token(
        user_id=viewer_user.id,
        email=viewer_user.email,
        role=viewer_user.role,
        institution_id=inst.id,
    )

    return inst, course, admin_user, viewer_user, admin_token, viewer_token


def test_list_institution_flags_and_gate_summary(client: TestClient, db_session: Session):
    """Test flags list endpoint, filtering, and statistical gate calculation."""
    inst, course, admin_user, _, admin_token, _ = _setup_test_institution(db_session, "list1")

    # Seed 1 open error, 1 open exception, 1 open warning
    error_flag = ValidationFlag(
        course_id=course.id,
        rule_code="SEAT_DECLARATION_MISMATCH",
        level="error",
        message="Declared seat count does not match student records.",
        requires_justification=False,
        status="open",
    )
    exception_flag = ValidationFlag(
        course_id=course.id,
        rule_code="INTAKE_EXCEEDED",
        level="exception",
        message="Admitted regular students exceed approved intake by 5.",
        requires_justification=True,
        status="open",
    )
    warning_flag = ValidationFlag(
        course_id=course.id,
        rule_code="AGE_OUT_OF_RANGE",
        level="warning",
        message="Candidate age is outside typical UG band.",
        requires_justification=False,
        status="open",
    )
    db_session.add_all([error_flag, exception_flag, warning_flag])
    db_session.commit()

    resp = client.get(
        f"/api/v1/institutions/{inst.id}/flags",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    assert payload["institution_id"] == inst.id
    summary = payload["summary"]
    assert summary["total_flags"] == 3
    assert summary["open_count"] == 3
    assert summary["justified_count"] == 0
    assert summary["error_count"] == 1
    assert summary["exception_count"] == 1
    assert summary["warning_count"] == 1
    # Submit blockers: error + exception requiring justification
    assert summary["blocking_count"] == 2
    assert summary["can_submit"] is False

    # Filter by level
    res_exc = client.get(
        f"/api/v1/institutions/{inst.id}/flags?level=exception",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_exc.status_code == 200
    items = res_exc.json()["items"]
    assert len(items) == 1
    assert items[0]["rule_code"] == "INTAKE_EXCEEDED"


def test_add_justification_for_exception_transitions_status(
    client: TestClient, db_session: Session
):
    """Test adding justification to an exception flag transitions status to justified."""
    inst, course, admin_user, _, admin_token, _ = _setup_test_institution(db_session, "just_exc")

    exception_flag = ValidationFlag(
        course_id=course.id,
        rule_code="INTAKE_EXCEEDED",
        level="exception",
        message="Regular intake exceeded by 8 candidates.",
        requires_justification=True,
        status="open",
    )
    db_session.add(exception_flag)
    db_session.commit()

    justification_payload = {
        "text": (
            "Special admission quota granted under High Court interim writ petition "
            "WP(C)/2026/4582 allowing 8 merit candidates."
        ),
    }

    resp = client.post(
        f"/api/v1/institutions/{inst.id}/flags/{exception_flag.id}/justifications",
        headers={"Authorization": f"Bearer {admin_token}"},
        data=justification_payload,
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()

    assert created["flag_id"] == exception_flag.id
    assert created["text"] == justification_payload["text"]
    assert created["by_user"] == admin_user.id
    assert created["author_name"] == admin_user.email

    # Check updated flag in database
    db_session.refresh(exception_flag)
    assert exception_flag.status == "justified"
    assert len(exception_flag.justifications) == 1

    # Check audit log entry
    audit_entry = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity == "justification",
            AuditLog.entity_id == str(created["id"]),
        )
    )
    assert audit_entry is not None
    assert audit_entry.action == "justification.create"
    assert audit_entry.actor_id == str(admin_user.id)
    assert audit_entry.after_json["status"] == "justified"

    # Verify summary updates
    flags_res = client.get(
        f"/api/v1/institutions/{inst.id}/flags",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    summary = flags_res.json()["summary"]
    assert summary["justified_count"] == 1
    assert summary["blocking_count"] == 0
    assert summary["can_submit"] is True


def test_add_justification_with_document_upload(client: TestClient, db_session: Session):
    """Test uploading a supporting document via Storage interface with justification."""
    inst, course, admin_user, _, admin_token, _ = _setup_test_institution(db_session, "doc_up")

    exception_flag = ValidationFlag(
        course_id=course.id,
        rule_code="SUPERNUMERARY_EXCEEDED",
        level="exception",
        message="Supernumerary quota overshoot by 2 seats.",
        requires_justification=True,
        status="open",
    )
    db_session.add(exception_flag)
    db_session.commit()

    sample_pdf = b"%PDF-1.4 sample approval letter content for SIH 2026 test"
    files = {
        "document": ("official_court_order.pdf", io.BytesIO(sample_pdf), "application/pdf"),
    }
    data = {
        "text": "Attached official state government notification approving 2 additional seats.",
    }

    resp = client.post(
        f"/api/v1/institutions/{inst.id}/flags/{exception_flag.id}/justifications",
        headers={"Authorization": f"Bearer {admin_token}"},
        data=data,
        files=files,
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()

    assert created["document_ref"] is not None
    assert "official_court_order" in created["document_ref"]
    assert created["document_url"] is not None

    # Check Storage interface
    storage = get_storage()
    assert storage.exists(created["document_ref"]) is True
    stored_bytes = storage.get(created["document_ref"])
    assert stored_bytes == sample_pdf

    # Download document endpoint
    doc_resp = client.get(
        f"/api/v1/institutions/{inst.id}/justifications/{created['id']}/document",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert doc_resp.status_code == 200
    assert doc_resp.content == sample_pdf
    assert "official_court_order.pdf" in doc_resp.headers.get("content-disposition", "")


def test_cannot_justify_error_level_flags(client: TestClient, db_session: Session):
    """SPEC.md Section 9.1: error flags cannot be justified; underlying data must be fixed."""
    inst, course, admin_user, _, admin_token, _ = _setup_test_institution(db_session, "err_block")

    error_flag = ValidationFlag(
        course_id=course.id,
        rule_code="COURSE_NOT_APPROVED",
        level="error",
        message="Course is not approved by AICTE for this academic year.",
        requires_justification=False,
        status="open",
    )
    db_session.add(error_flag)
    db_session.commit()

    resp = client.post(
        f"/api/v1/institutions/{inst.id}/flags/{error_flag.id}/justifications",
        headers={"Authorization": f"Bearer {admin_token}"},
        data={"text": "Please approve this unapproved course anyway."},
    )
    assert resp.status_code == 400
    assert "Error-level flags" in resp.json()["detail"]
    assert "cannot be justified" in resp.json()["detail"]

    # Verify status unchanged
    db_session.refresh(error_flag)
    assert error_flag.status == "open"
    assert len(error_flag.justifications) == 0


def test_justification_persists_across_validation_rerun(
    client: TestClient, db_session: Session
):
    """T22: A justification is kept when validation re-runs and flag still applies."""
    inst, course, admin_user, _, admin_token, _ = _setup_test_institution(db_session, "rerun_keep")

    # Set approved intake to 10
    intake = db_session.scalar(
        select(CourseIntake).where(CourseIntake.course_id == course.id)
    )
    intake.approved_intake = 10
    db_session.flush()

    # Enrol 12 students in this course (overshoot of 2)
    students: list[Student] = []
    for i in range(1, 13):
        st = Student(
            institution_id=inst.id,
            course_id=course.id,
            academic_year="2026-27",
            apaar_id=f"90000000{i:04d}",
            name=f"Student {i}",
            dob_encrypted=encrypt_dob(datetime(2005, 5, 15, tzinfo=UTC).date()),
            gender="Male",
            enrolment_no=f"ENR-{i:04d}",
            admission_date=datetime(2026, 8, 1, tzinfo=UTC).date(),
            admission_mode="State counselling",
            seat_type="Regular",
            reservation_category="General",
            status="draft",
        )
        students.append(st)
        db_session.add(st)
    db_session.commit()

    # 1. First validation run generates INTAKE_EXCEEDED flag
    res1 = validate_course(
        institution_id=inst.id,
        course_id=course.id,
        academic_year="2026-27",
        db_session=db_session,
        persist=True,
    )
    intake_flag = next(f for f in res1 if f.rule_code == "INTAKE_EXCEEDED")
    assert intake_flag is not None

    # Retrieve flag from DB
    db_flag = db_session.scalar(
        select(ValidationFlag).where(
            ValidationFlag.course_id == course.id,
            ValidationFlag.rule_code == "INTAKE_EXCEEDED",
        )
    )
    assert db_flag is not None
    assert db_flag.status == "open"

    # 2. Add justification
    resp = client.post(
        f"/api/v1/institutions/{inst.id}/flags/{db_flag.id}/justifications",
        headers={"Authorization": f"Bearer {admin_token}"},
        data={"text": "Over-intake of 2 students permitted under government quota allotment."},
    )
    assert resp.status_code == 201
    db_session.refresh(db_flag)
    assert db_flag.status == "justified"
    flag_db_id = db_flag.id

    # 3. Re-run validation with the exact same condition (students still 12 > 10)
    validate_course(
        institution_id=inst.id,
        course_id=course.id,
        academic_year="2026-27",
        db_session=db_session,
        persist=True,
        keep_justifications=True,
    )

    # 4. Verify flag ID, status 'justified', and justification record are PRESERVED!
    db_session.expire_all()
    rerun_flag = db_session.get(ValidationFlag, flag_db_id)
    assert rerun_flag is not None
    assert rerun_flag.status == "justified"
    assert len(rerun_flag.justifications) == 1
    assert "Over-intake of 2 students" in rerun_flag.justifications[0].text


def test_flag_resolved_when_underlying_issue_clears(client: TestClient, db_session: Session):
    """Test that when underlying data issue is resolved, flag transitions to 'resolved'."""
    inst, course, admin_user, _, admin_token, _ = _setup_test_institution(db_session, "resolve_fl")

    # Set approved intake to 10, enrol 11 students
    intake = db_session.scalar(
        select(CourseIntake).where(CourseIntake.course_id == course.id)
    )
    intake.approved_intake = 10
    db_session.flush()

    for i in range(1, 12):
        st = Student(
            institution_id=inst.id,
            course_id=course.id,
            academic_year="2026-27",
            apaar_id=f"91000000{i:04d}",
            name=f"Student {i}",
            dob_encrypted=encrypt_dob(datetime(2005, 5, 15, tzinfo=UTC).date()),
            gender="Male",
            enrolment_no=f"ENR2-{i:04d}",
            admission_date=datetime(2026, 8, 1, tzinfo=UTC).date(),
            admission_mode="State counselling",
            seat_type="Regular",
            reservation_category="General",
            status="draft",
        )
        db_session.add(st)
    db_session.commit()

    # Initial validation run -> INTAKE_EXCEEDED
    validate_course(
        institution_id=inst.id,
        course_id=course.id,
        academic_year="2026-27",
        db_session=db_session,
        persist=True,
    )
    db_flag = db_session.scalar(
        select(ValidationFlag).where(
            ValidationFlag.course_id == course.id,
            ValidationFlag.rule_code == "INTAKE_EXCEEDED",
        )
    )
    assert db_flag.status == "open"

    # Increase approved intake to 15 (now 11 <= 15, no overshoot)
    intake.approved_intake = 15
    db_session.commit()

    # Re-validate
    validate_course(
        institution_id=inst.id,
        course_id=course.id,
        academic_year="2026-27",
        db_session=db_session,
        persist=True,
        keep_justifications=True,
    )

    db_session.refresh(db_flag)
    assert db_flag.status == "resolved"


def test_idor_protection_cross_institution_forbidden(client: TestClient, db_session: Session):
    """Hard Rule 7 & SPEC.md 16: College A cannot view or justify College B's flags."""
    inst_a, course_a, _, _, token_a, _ = _setup_test_institution(db_session, "idor_a")
    inst_b, course_b, _, _, token_b, _ = _setup_test_institution(db_session, "idor_b")

    flag_a = ValidationFlag(
        course_id=course_a.id,
        rule_code="INTAKE_EXCEEDED",
        level="exception",
        message="Intake exceeded for college A.",
        requires_justification=True,
        status="open",
    )
    db_session.add(flag_a)
    db_session.commit()

    # College B attempts to view College A's flags
    resp_get = client.get(
        f"/api/v1/institutions/{inst_a.id}/flags",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_get.status_code == 403

    # College B attempts to justify College A's flag
    resp_post = client.post(
        f"/api/v1/institutions/{inst_a.id}/flags/{flag_a.id}/justifications",
        headers={"Authorization": f"Bearer {token_b}"},
        data={"text": "Rogue justification from college B."},
    )
    assert resp_post.status_code == 403


def test_rbac_college_viewer_forbidden_to_justify(client: TestClient, db_session: Session):
    """SPEC.md Section 5: college_viewer has read-only access and cannot write justifications."""
    inst, course, _, viewer_user, _, viewer_token = _setup_test_institution(db_session, "rbac_vw")

    exception_flag = ValidationFlag(
        course_id=course.id,
        rule_code="INTAKE_EXCEEDED",
        level="exception",
        message="Intake exceeded.",
        requires_justification=True,
        status="open",
    )
    db_session.add(exception_flag)
    db_session.commit()

    # Viewer can read flags (HTTP 200)
    resp_get = client.get(
        f"/api/v1/institutions/{inst.id}/flags",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp_get.status_code == 200

    # Viewer cannot post justification (HTTP 403)
    resp_post = client.post(
        f"/api/v1/institutions/{inst.id}/flags/{exception_flag.id}/justifications",
        headers={"Authorization": f"Bearer {viewer_token}"},
        data={"text": "Unauthorized justification attempt by viewer."},
    )
    assert resp_post.status_code == 403


def test_delete_justification_reverts_flag_to_open(client: TestClient, db_session: Session):
    """Test deleting the only justification reverts flag status to 'open'."""
    inst, course, admin_user, _, admin_token, _ = _setup_test_institution(db_session, "del_rev")

    exception_flag = ValidationFlag(
        course_id=course.id,
        rule_code="INTAKE_EXCEEDED",
        level="exception",
        message="Intake exceeded.",
        requires_justification=True,
        status="open",
    )
    db_session.add(exception_flag)
    db_session.commit()

    # 1. Justify
    resp_post = client.post(
        f"/api/v1/institutions/{inst.id}/flags/{exception_flag.id}/justifications",
        headers={"Authorization": f"Bearer {admin_token}"},
        data={"text": "Valid justification text that was entered by mistake."},
    )
    assert resp_post.status_code == 201
    j_id = resp_post.json()["id"]

    db_session.refresh(exception_flag)
    assert exception_flag.status == "justified"

    # 2. Delete justification
    resp_del = client.delete(
        f"/api/v1/institutions/{inst.id}/justifications/{j_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_del.status_code == 200
    assert resp_del.json()["flag_status"] == "open"

    # 3. Verify flag is open again
    db_session.refresh(exception_flag)
    assert exception_flag.status == "open"
    assert len(exception_flag.justifications) == 0
