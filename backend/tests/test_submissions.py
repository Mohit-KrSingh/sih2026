"""Table-driven test suite for submission state machine, gate evaluations, and submit lifecycle.

SPEC.md Section 10 & TASKS.md T23:
- Table-driven transition tests for every state and gate case in Section 10.
- Declaration with mock OTP.
- Receipt number generation.
- Lock on submit (students and seat declarations).
- Submit screen lists blockers with links to exact rows.
- Only college_admin can submit (403 for staff/viewer).
- Audit log entry verification.
- IDOR isolation between institutions.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, encrypt_dob, hash_password
from app.models import (
    AuditLog,
    Course,
    CourseIntake,
    DevOutbox,
    Institution,
    SeatDeclaration,
    Student,
    User,
    ValidationFlag,
)
from app.submissions.state_machine import (
    InvalidStateTransitionError,
    SubmissionState,
    SubmissionStateMachine,
)

# ---------------------------------------------------------------------------
# Unit Tests: Table-driven State Machine Transitions (SPEC.md Section 10)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("from_state", "to_state", "is_valid"),
    [
        # Legal transitions
        (SubmissionState.DRAFT, SubmissionState.SUBMITTED, True),
        (SubmissionState.DRAFT, SubmissionState.SUBMITTED_WITH_EXCEPTIONS, True),
        (SubmissionState.SUBMITTED_WITH_EXCEPTIONS, SubmissionState.UNDER_REVIEW, True),
        (SubmissionState.SUBMITTED, SubmissionState.ACCEPTED, True),
        (SubmissionState.SUBMITTED, SubmissionState.UNDER_REVIEW, True),
        (SubmissionState.UNDER_REVIEW, SubmissionState.ACCEPTED, True),
        (SubmissionState.UNDER_REVIEW, SubmissionState.QUERY_RAISED, True),
        (SubmissionState.UNDER_REVIEW, SubmissionState.ESCALATED, True),
        (SubmissionState.QUERY_RAISED, SubmissionState.UNDER_REVIEW, True),
        (SubmissionState.ESCALATED, SubmissionState.UNDER_REVIEW, True),
        (SubmissionState.ESCALATED, SubmissionState.ACCEPTED, True),
        # Illegal transitions
        (SubmissionState.DRAFT, SubmissionState.ACCEPTED, False),
        (SubmissionState.DRAFT, SubmissionState.UNDER_REVIEW, False),
        (SubmissionState.DRAFT, SubmissionState.QUERY_RAISED, False),
        (SubmissionState.DRAFT, SubmissionState.ESCALATED, False),
        (SubmissionState.SUBMITTED_WITH_EXCEPTIONS, SubmissionState.ACCEPTED, False),
        (SubmissionState.SUBMITTED_WITH_EXCEPTIONS, SubmissionState.DRAFT, False),
        (SubmissionState.SUBMITTED, SubmissionState.DRAFT, False),
        (SubmissionState.ACCEPTED, SubmissionState.DRAFT, False),
        (SubmissionState.ACCEPTED, SubmissionState.UNDER_REVIEW, False),
        (SubmissionState.QUERY_RAISED, SubmissionState.ACCEPTED, False),
        (SubmissionState.QUERY_RAISED, SubmissionState.DRAFT, False),
        (SubmissionState.ESCALATED, SubmissionState.DRAFT, False),
    ],
)
def test_state_machine_transitions(from_state: str, to_state: str, is_valid: bool) -> None:
    """Table-driven verification of every legal and illegal submission lifecycle transition."""
    assert SubmissionStateMachine.can_transition(from_state, to_state) is is_valid

    if is_valid:
        SubmissionStateMachine.validate_transition(from_state, to_state)
    else:
        with pytest.raises(InvalidStateTransitionError):
            SubmissionStateMachine.validate_transition(from_state, to_state)


# ---------------------------------------------------------------------------
# Unit Tests: Table-driven Gate Evaluation Cases (SPEC.md Section 10 Table)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    (
        "open_errors",
        "unjust_exceptions",
        "unjust_warnings",
        "seat_mismatch",
        "just_exceptions",
        "just_warnings",
        "expected_can_submit",
        "expected_target_state",
        "expected_situation",
    ),
    [
        # Case 1: Open error flag blocks submit regardless of justifications
        (
            1,
            0,
            0,
            False,
            0,
            0,
            False,
            None,
            "OPEN_ERRORS",
        ),
        (
            2,
            0,
            0,
            False,
            2,
            1,
            False,
            None,
            "OPEN_ERRORS",
        ),
        # Case 2: Declared seat counts differ from student list (SEAT_DECLARATION_MISMATCH)
        (
            0,
            0,
            0,
            True,
            0,
            0,
            False,
            None,
            "SEAT_DECLARATION_MISMATCH",
        ),
        # Case 3: Open compliance exception without justification blocks submit
        (
            0,
            1,
            0,
            False,
            0,
            0,
            False,
            None,
            "UNJUSTIFIED_EXCEPTIONS",
        ),
        # Case 4: Open warning that requires justification blocks submit
        (
            0,
            0,
            1,
            False,
            0,
            0,
            False,
            None,
            "UNJUSTIFIED_WARNINGS",
        ),
        # Case 5: Only justified exceptions or warnings -> Allowed (submitted_with_exceptions)
        (
            0,
            0,
            0,
            False,
            1,
            0,
            True,
            SubmissionState.SUBMITTED_WITH_EXCEPTIONS,
            "JUSTIFIED_EXCEPTIONS",
        ),
        (
            0,
            0,
            0,
            False,
            2,
            3,
            True,
            SubmissionState.SUBMITTED_WITH_EXCEPTIONS,
            "JUSTIFIED_EXCEPTIONS",
        ),
        # Case 6: Clean submission (0 errors, 0 seat mismatch, 0 exceptions) -> Allowed (submitted)
        (
            0,
            0,
            0,
            False,
            0,
            0,
            True,
            SubmissionState.SUBMITTED,
            "CLEAN",
        ),
    ],
)
def test_submit_gate_evaluation_cases(
    open_errors: int,
    unjust_exceptions: int,
    unjust_warnings: int,
    seat_mismatch: bool,
    just_exceptions: int,
    just_warnings: int,
    expected_can_submit: bool,
    expected_target_state: SubmissionState | None,
    expected_situation: str,
) -> None:
    """Table-driven test covering every situation in the Section 10 submit gate table."""
    result = SubmissionStateMachine.evaluate_gate(
        open_error_count=open_errors,
        unjustified_exception_count=unjust_exceptions,
        unjustified_warning_count=unjust_warnings,
        seat_declaration_mismatch=seat_mismatch,
        justified_exception_count=just_exceptions,
        justified_warning_count=just_warnings,
        total_students=120,
    )

    assert result.can_submit is expected_can_submit
    assert result.target_state == expected_target_state
    assert result.situation == expected_situation
    if not expected_can_submit:
        assert len(result.blocker_reasons) > 0


# ---------------------------------------------------------------------------
# Integration Tests: End-to-end API Gate, OTP, Submit, Receipt, and IDOR
# ---------------------------------------------------------------------------


def _setup_college(
    db: Session,
    suffix: str = "sub1",
) -> tuple[Institution, Course, User, User, str, str]:
    """Helper to provision test institution, course, admin, staff, and tokens."""
    inst = Institution(
        aicte_id=f"1-TEST-SUB-{suffix.upper()}",
        name=f"College of Engineering {suffix}",
        state="Karnataka",
        district="Bengaluru",
        address="Whitefield",
        official_email=f"admin_{suffix}@college.edu.in",
        official_phone="9876543210",
        head_name="Principal Dr. Rao",
        affiliating_university="VTU",
        approval_status="active",
        account_status="active",
    )
    db.add(inst)
    db.flush()

    course = Course(
        institution_id=inst.id,
        name="Information Science",
        level="UG",
        branch="Information Science and Engineering",
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

    admin_user = User(
        email=f"admin_{suffix}@college.edu.in",
        password_hash=hash_password("AdminPass123!"),
        role="college_admin",
        institution_id=inst.id,
        is_active=True,
    )
    staff_user = User(
        email=f"staff_{suffix}@college.edu.in",
        password_hash=hash_password("StaffPass123!"),
        role="college_staff",
        institution_id=inst.id,
        is_active=True,
    )
    db.add_all([admin_user, staff_user])
    db.flush()

    admin_token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        role=admin_user.role,
        institution_id=inst.id,
    )
    staff_token = create_access_token(
        user_id=staff_user.id,
        email=staff_user.email,
        role=staff_user.role,
        institution_id=inst.id,
    )
    return inst, course, admin_user, staff_user, admin_token, staff_token


def test_submit_gate_blocked_by_open_error(client: TestClient, db_session: Session) -> None:
    """Test submit gate returns blockers with links to exact rows when error flags exist."""
    inst, course, admin, _staff, admin_token, _ = _setup_college(db_session, "err1")

    # Add student with DOB format error
    student = Student(
        institution_id=inst.id,
        course_id=course.id,
        academic_year="2026-27",
        apaar_id="111122223333",
        name="Anand Kumar",
        dob_encrypted=encrypt_dob("2004-05-15"),
        gender="Male",
        enrolment_no="ISE-001",
        admission_date="2026-08-01",
        admission_mode="JEE Main counselling",
        seat_type="Regular",
        reservation_category="General",
        status="flagged",
    )
    db_session.add(student)
    db_session.flush()

    # Add Seat Declaration matching the 1 regular student
    decl = SeatDeclaration(
        course_id=course.id,
        academic_year="2026-27",
        regular_admitted=1,
        supernumerary_admitted=0,
        status="declared",
    )
    db_session.add(decl)

    # Add open error flag on the student
    flag = ValidationFlag(
        student_id=student.id,
        course_id=course.id,
        rule_code="DOB_INVALID",
        level="error",
        field="dob",
        message="Date of birth is invalid",
        fix_hint="Enter a valid date in YYYY-MM-DD format",
        requires_justification=False,
        status="open",
    )
    db_session.add(flag)
    db_session.commit()

    # Query gate
    resp = client.get(
        f"/api/v1/institutions/{inst.id}/submissions/gate?academic_year=2026-27",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["can_submit"] is False
    assert data["open_errors_count"] == 1
    assert data["total_students"] == 1
    assert len(data["blockers"]) == 1

    blocker = data["blockers"][0]
    assert blocker["rule_code"] == "DOB_INVALID"
    assert blocker["level"] == "error"
    assert blocker["student_id"] == student.id
    assert blocker["target_link"] == f"/college/students/{student.id}/edit"


def test_submit_gate_blocked_by_seat_declaration_mismatch(
    client: TestClient, db_session: Session
) -> None:
    """Test submit gate blocks when declared counts differ from student records."""
    inst, course, admin, _staff, admin_token, _ = _setup_college(db_session, "mismatch1")

    # Add 2 students
    for i in range(2):
        s = Student(
            institution_id=inst.id,
            course_id=course.id,
            academic_year="2026-27",
            apaar_id=f"22223333444{i}",
            name=f"Student {i}",
            dob_encrypted=encrypt_dob("2004-01-01"),
            gender="Male",
            enrolment_no=f"ISE-00{i}",
            admission_date="2026-08-01",
            admission_mode="State counselling",
            seat_type="Regular",
            reservation_category="General",
            status="valid",
        )
        db_session.add(s)
    db_session.flush()

    # Seat declaration declared 5 regular (differs from actual 2)
    decl = SeatDeclaration(
        course_id=course.id,
        academic_year="2026-27",
        regular_admitted=5,
        supernumerary_admitted=0,
        status="declared",
    )
    db_session.add(decl)
    db_session.commit()

    resp = client.get(
        f"/api/v1/institutions/{inst.id}/submissions/gate?academic_year=2026-27",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["can_submit"] is False
    assert data["seat_mismatch_detected"] is True
    assert any(b["rule_code"] == "SEAT_DECLARATION_MISMATCH" for b in data["blockers"])
    mismatch_blocker = next(
        b for b in data["blockers"] if b["rule_code"] == "SEAT_DECLARATION_MISMATCH"
    )
    assert mismatch_blocker["target_link"] == "/college/seats"


def test_submit_gate_with_justified_exception(client: TestClient, db_session: Session) -> None:
    """Submit gate allows submission as submitted_with_exceptions when exception is justified."""
    inst, course, admin, staff, admin_token, staff_token = _setup_college(db_session, "justified1")

    # Add student
    student = Student(
        institution_id=inst.id,
        course_id=course.id,
        academic_year="2026-27",
        apaar_id="333344445555",
        name="Deepak Verma",
        dob_encrypted=encrypt_dob("2003-09-12"),
        gender="Male",
        enrolment_no="ISE-101",
        admission_date="2026-08-01",
        admission_mode="Management quota",
        seat_type="Regular",
        reservation_category="General",
        status="flagged",
    )
    db_session.add(student)
    db_session.flush()

    decl = SeatDeclaration(
        course_id=course.id,
        academic_year="2026-27",
        regular_admitted=1,
        supernumerary_admitted=0,
        status="declared",
    )
    db_session.add(decl)

    # Add exception flag
    flag = ValidationFlag(
        student_id=student.id,
        course_id=course.id,
        rule_code="INTAKE_EXCEEDED",
        level="exception",
        message="Regular intake exceeded by 1 student",
        requires_justification=True,
        status="open",
    )
    db_session.add(flag)
    db_session.flush()

    # Step 1: Open exception blocks submit
    gate1 = client.get(
        f"/api/v1/institutions/{inst.id}/submissions/gate?academic_year=2026-27",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()
    assert gate1["can_submit"] is False
    assert gate1["unjustified_exceptions_count"] == 1

    # Step 2: Staff justifies the exception
    just_resp = client.post(
        f"/api/v1/institutions/{inst.id}/flags/{flag.id}/justifications",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "text": "Admitted on court directive WP 1234/2026 pending regularisation by DTE.",
            "document_ref": "storage/court_order.pdf",
        },
    )
    assert just_resp.status_code == 201

    # Step 3: Gate now allows submission with exceptions
    gate2 = client.get(
        f"/api/v1/institutions/{inst.id}/submissions/gate?academic_year=2026-27",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()
    assert gate2["can_submit"] is True
    assert gate2["target_status"] == "submitted_with_exceptions"
    assert gate2["justified_exceptions_count"] == 1
    assert len(gate2["blockers"]) == 0


def test_declaration_otp_and_submit_workflow(client: TestClient, db_session: Session) -> None:
    """Test full declaration OTP generation, submit gate check, data locking, receipt, and audit."""
    inst, course, admin, staff, admin_token, staff_token = _setup_college(db_session, "clean1")

    # Add valid student and matching declaration
    student = Student(
        institution_id=inst.id,
        course_id=course.id,
        academic_year="2026-27",
        apaar_id="444455556666",
        name="Sunita Rao",
        dob_encrypted=encrypt_dob("2004-11-20"),
        gender="Female",
        enrolment_no="ISE-201",
        admission_date="2026-08-05",
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="OBC",
        status="valid",
    )
    db_session.add(student)
    db_session.flush()

    decl = SeatDeclaration(
        course_id=course.id,
        academic_year="2026-27",
        regular_admitted=1,
        supernumerary_admitted=0,
        status="declared",
    )
    db_session.add(decl)
    db_session.commit()

    # 1. Non-admin staff cannot request OTP or submit (403 Forbidden)
    otp_staff_resp = client.post(
        f"/api/v1/institutions/{inst.id}/submissions/declaration-otp",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={"academic_year": "2026-27"},
    )
    assert otp_staff_resp.status_code == 403

    # 2. Admin requests declaration OTP
    otp_resp = client.post(
        f"/api/v1/institutions/{inst.id}/submissions/declaration-otp",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"academic_year": "2026-27"},
    )
    assert otp_resp.status_code == 200
    otp_data = otp_resp.json()
    assert otp_data["status"] == "sent"
    assert otp_data["recipient"] == admin.email

    # Retrieve generated OTP code from dev_outbox
    outbox_msg = db_session.scalar(
        select(DevOutbox)
        .where(DevOutbox.recipient == admin.email)
        .order_by(DevOutbox.id.desc())
    )
    assert outbox_msg is not None
    # Code is embedded in the outbox message body: "Your APAAR verification OTP code is: XXXXXX"
    # Code is embedded in the outbox message body: "Your EduTrace verification OTP code is: XXXXXX"
    prefix = "Your EduTrace verification OTP code is: "
    otp_code = outbox_msg.body.split(prefix)[1].split(".")[0].strip()
    assert len(otp_code) == 6

    # 3. Non-admin staff attempting to submit gets 403
    staff_submit_resp = client.post(
        f"/api/v1/institutions/{inst.id}/submissions/submit",
        headers={"Authorization": f"Bearer {staff_token}"},
        json={
            "academic_year": "2026-27",
            "confirmed_declaration": True,
            "declaration_text": "I confirm this data is authentic and authorized.",
            "otp_code": otp_code,
        },
    )
    assert staff_submit_resp.status_code == 403

    # 4. Admin submits with incorrect OTP -> 400
    bad_otp_resp = client.post(
        f"/api/v1/institutions/{inst.id}/submissions/submit",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "academic_year": "2026-27",
            "confirmed_declaration": True,
            "declaration_text": "I confirm this data is authentic and authorized.",
            "otp_code": "000000",
        },
    )
    assert bad_otp_resp.status_code == 400
    assert "OTP verification failed" in bad_otp_resp.json()["detail"]

    # 5. Admin submits with valid OTP and confirmed declaration -> 200
    submit_resp = client.post(
        f"/api/v1/institutions/{inst.id}/submissions/submit",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "academic_year": "2026-27",
            "confirmed_declaration": True,
            "declaration_text": "I confirm this data is authentic and authorized.",
            "otp_code": otp_code,
        },
    )
    assert submit_resp.status_code == 200
    receipt = submit_resp.json()

    assert receipt["status"] == "submitted"
    assert receipt["is_locked"] is True
    assert receipt["receipt_no"].startswith("REC-2026-27-")
    assert receipt["total_students"] == 1
    assert receipt["regular_students"] == 1

    # 6. Verify data locking in database
    db_session.expire_all()
    locked_student = db_session.get(Student, student.id)
    assert locked_student.is_locked is True
    assert locked_student.status == "submitted"
    assert locked_student.submission_id == receipt["submission_id"]

    locked_decl = db_session.get(SeatDeclaration, decl.id)
    assert locked_decl.status == "locked"

    # 7. Verify hash-chained audit log entry
    audit_entry = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.entity == "submission",
            AuditLog.entity_id == str(receipt["submission_id"]),
            AuditLog.action == "submission.submit",
        )
    )
    assert audit_entry is not None
    assert audit_entry.actor_id == str(admin.id)
    assert audit_entry.actor_role == "college_admin"
    assert audit_entry.after_json["receipt_no"] == receipt["receipt_no"]
    assert audit_entry.hash is not None

    # 8. Second submit attempt is blocked (already submitted/locked)
    dup_submit = client.post(
        f"/api/v1/institutions/{inst.id}/submissions/submit",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "academic_year": "2026-27",
            "confirmed_declaration": True,
            "declaration_text": "Trying to resubmit",
            "otp_code": otp_code,
        },
    )
    assert dup_submit.status_code == 400

    # 9. Query receipt endpoint
    receipt_resp = client.get(
        f"/api/v1/institutions/{inst.id}/submissions/receipt?academic_year=2026-27",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert receipt_resp.status_code == 200
    assert receipt_resp.json()["receipt_no"] == receipt["receipt_no"]


def test_submission_idor_protection(client: TestClient, db_session: Session) -> None:
    """Verify College A cannot view or submit College B's submission gate (403 IDOR)."""
    inst_a, _, _, _, token_a, _ = _setup_college(db_session, "idor_a")
    inst_b, _, _, _, token_b, _ = _setup_college(db_session, "idor_b")

    # College A tries to view College B's gate -> 403 Forbidden
    resp = client.get(
        f"/api/v1/institutions/{inst_b.id}/submissions/gate?academic_year=2026-27",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403

    # College A tries to request OTP for College B -> 403 Forbidden
    otp_resp = client.post(
        f"/api/v1/institutions/{inst_b.id}/submissions/declaration-otp",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"academic_year": "2026-27"},
    )
    assert otp_resp.status_code == 403
