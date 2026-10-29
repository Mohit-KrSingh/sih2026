"""Unit and integration tests for T24: Promotion to central repository and cross-checks.

SPEC.md Section 10, 12 & TASKS.md T24:
- On submit: status updates, cross-college rules re-run with all data,
  notifications to affected colleges, SSE event published, review items created for exceptions.
- Key acceptance test: two colleges submit the same APAAR ID; both are notified and
  AICTE sees one duplicate record.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import sse
from app.analytics.schemas import DuplicateRecordResponse
from app.auth.security import create_access_token
from app.models import (
    Course,
    CourseIntake,
    Institution,
    Notification,
    ReviewItem,
    SeatDeclaration,
    Student,
    Submission,
    User,
    ValidationFlag,
)
from app.students.duplicate_service import (
    DUP_ACTIVE_OTHER_COLLEGE,
    DUP_SAME_COURSE_OTHER_COLLEGE,
    get_duplicate_records,
    resolve_duplicate_flags_on_status_change,
)
from app.submissions.promotion_service import promote_submission_and_run_cross_checks

# =============================================================================
# Helper Fixtures and Factories
# =============================================================================


def _make_institution(db: Session, aicte_id: str, name: str) -> Institution:
    inst = Institution(
        aicte_id=aicte_id,
        name=name,
        state="Maharashtra",
        district="Pune",
        address=f"Campus of {name}",
        official_email=f"contact_{aicte_id.lower().replace('-', '_')}@test.edu",
        official_phone="+919876543210",
        head_name="Dr. Director",
        affiliating_university="Tech University",
        approval_status="active",
        account_status="active",
    )
    db.add(inst)
    db.flush()
    return inst


def _make_course(db: Session, institution_id: int, name: str, branch: str = "General") -> Course:
    course = Course(
        institution_id=institution_id,
        name=name,
        level="UG",
        branch=branch,
        duration_years=4,
        supernumerary_allowed=True,
    )
    db.add(course)
    db.flush()

    intake = CourseIntake(
        course_id=course.id,
        academic_year="2026-27",
        approved_intake=60,
        supernumerary_seats_allowed=10,
        source="AICTE",
    )
    db.add(intake)
    db.flush()
    return course


def _make_user(db: Session, email: str, role: str, institution_id: int | None = None) -> User:
    user = User(
        email=email,
        password_hash="argon2_fake_hash",
        role=role,
        institution_id=institution_id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _make_student(
    db: Session,
    institution_id: int,
    course_id: int,
    apaar_id: str,
    name: str,
    enrolment_no: str,
    academic_year: str = "2026-27",
    seat_type: str = "Regular",
    status: str = "draft",
) -> Student:
    student = Student(
        institution_id=institution_id,
        course_id=course_id,
        academic_year=academic_year,
        apaar_id=apaar_id,
        name=name,
        dob_encrypted="encrypted_dob",
        gender="Male",
        enrolment_no=enrolment_no,
        admission_date=date(2026, 8, 1),
        admission_mode="State counselling",
        seat_type=seat_type,
        reservation_category="General",
        status=status,
        is_locked=False,
    )
    db.add(student)
    db.flush()
    return student


# =============================================================================
# 1. Promotion to Central Repository Tests
# =============================================================================


def test_submission_promotion_status_updates(db_session: Session) -> None:
    """Test that on submission:
    - Active students are marked 'submitted' and locked (is_locked=True)
    - Withdrawn students remain 'withdrawn' but are locked
    - Seat declarations are marked 'locked'
    - Submission receipt and status are generated
    """
    inst = _make_institution(db_session, "T24-INST-01", "Institute of Tech A")
    course = _make_course(db_session, inst.id, "Computer Science & Engineering")
    admin = _make_user(db_session, "admin@tech-a.edu", "college_admin", inst.id)

    # Add active and withdrawn students
    st1 = _make_student(db_session, inst.id, course.id, "999900001111", "Alice Sharma", "EN-A-01")
    st2 = _make_student(
        db_session,
        inst.id,
        course.id,
        "999900001112",
        "Bob Patil",
        "EN-A-02",
        seat_type="Supernumerary",
    )
    st_withdrawn = _make_student(
        db_session,
        inst.id,
        course.id,
        "999900001113",
        "Charlie Deshmukh",
        "EN-A-03",
        status="withdrawn",
    )

    # Seat declaration
    decl = SeatDeclaration(
        course_id=course.id,
        academic_year="2026-27",
        regular_admitted=1,
        supernumerary_admitted=1,
        nri_count=0,
        oci_count=0,
        fn_count=0,
        status="draft",
    )
    db_session.add(decl)

    sub = Submission(
        institution_id=inst.id,
        academic_year="2026-27",
        status="draft",
        receipt_no="REC-202627-T24-INST-01-TEST1",
        submitted_by=admin.id,
        submitted_at=datetime.now(UTC),
    )
    db_session.add(sub)
    db_session.flush()

    # Run promotion
    res = promote_submission_and_run_cross_checks(
        db=db_session,
        submission=sub,
        user=admin,
        redis_client=None,
    )

    assert res["status"] == "submitted"
    assert res["total_students"] == 3
    assert res["regular_students"] == 1
    assert res["supernumerary_students"] == 1

    # Verify central repository status in DB
    db_session.refresh(st1)
    db_session.refresh(st2)
    db_session.refresh(st_withdrawn)
    db_session.refresh(decl)
    db_session.refresh(sub)

    assert st1.is_locked is True
    assert st1.status == "submitted"
    assert st1.submission_id == sub.id

    assert st2.is_locked is True
    assert st2.status == "submitted"
    assert st2.submission_id == sub.id

    assert st_withdrawn.is_locked is True
    assert st_withdrawn.status == "withdrawn"  # Preserved withdrawn state

    assert decl.status == "locked"
    assert sub.status == "submitted"


# =============================================================================
# 2. Key Acceptance Test: Two Colleges Submit the Same APAAR ID
# =============================================================================


def test_two_colleges_submit_same_apaar_both_notified_aicte_sees_one_duplicate(
    db_session: Session,
) -> None:
    """Acceptance criterion from TASKS.md T24:
    Two colleges submit the same APAAR ID; both notified; AICTE sees one duplicate.
    """
    sse.clear_recent_events()

    # Setup College A and College B
    inst_a = _make_institution(db_session, "1-10000001", "College Alpha")
    inst_b = _make_institution(db_session, "1-10000002", "College Beta")

    course_a = _make_course(db_session, inst_a.id, "Computer Science & Engineering")
    course_b = _make_course(db_session, inst_b.id, "Electronics Engineering")

    admin_a = _make_user(db_session, "admin@alpha.edu", "college_admin", inst_a.id)
    admin_b = _make_user(db_session, "admin@beta.edu", "college_admin", inst_b.id)

    # Same APAAR ID enrolled at both colleges
    shared_apaar = "888877776666"
    student_name = "Devansh Verma"

    st_a = _make_student(
        db_session,
        inst_a.id,
        course_a.id,
        shared_apaar,
        student_name,
        "EN-ALPHA-101",
    )
    st_b = _make_student(
        db_session,
        inst_b.id,
        course_b.id,
        shared_apaar,
        student_name,
        "EN-BETA-202",
    )

    decl_a = SeatDeclaration(
        course_id=course_a.id,
        academic_year="2026-27",
        regular_admitted=1,
        supernumerary_admitted=0,
        status="draft",
    )
    decl_b = SeatDeclaration(
        course_id=course_b.id,
        academic_year="2026-27",
        regular_admitted=1,
        supernumerary_admitted=0,
        status="draft",
    )
    db_session.add_all([decl_a, decl_b])

    # 1. College Alpha submits
    sub_a = Submission(
        institution_id=inst_a.id,
        academic_year="2026-27",
        status="draft",
        receipt_no="REC-202627-1-10000001-A1B2C3",
        submitted_by=admin_a.id,
        submitted_at=datetime.now(UTC),
    )
    db_session.add(sub_a)
    db_session.flush()

    promo_a = promote_submission_and_run_cross_checks(
        db=db_session,
        submission=sub_a,
        user=admin_a,
        redis_client=None,
    )
    assert promo_a["status"] == "submitted"

    # 2. College Beta submits
    sub_b = Submission(
        institution_id=inst_b.id,
        academic_year="2026-27",
        status="draft",
        receipt_no="REC-202627-1-10000002-X9Y8Z7",
        submitted_by=admin_b.id,
        submitted_at=datetime.now(UTC),
    )
    db_session.add(sub_b)
    db_session.flush()

    promo_b = promote_submission_and_run_cross_checks(
        db=db_session,
        submission=sub_b,
        user=admin_b,
        redis_client=None,
    )
    assert promo_b["status"] == "submitted"
    assert promo_b["duplicates_detected"] >= 1

    # =========================================================================
    # Verification 1: Both Colleges are notified
    # =========================================================================
    notifs_a = list(
        db_session.scalars(
            select(Notification).where(
                Notification.institution_id == inst_a.id,
                Notification.type == "DUPLICATE_ENROLMENT_DETECTED",
            )
        ).all()
    )
    notifs_b = list(
        db_session.scalars(
            select(Notification).where(
                Notification.institution_id == inst_b.id,
                Notification.type == "DUPLICATE_ENROLMENT_DETECTED",
            )
        ).all()
    )

    assert len(notifs_a) >= 1, "College Alpha must receive duplicate enrolment notification"
    assert len(notifs_b) >= 1, "College Beta must receive duplicate enrolment notification"

    payload_a = notifs_a[0].payload_json
    payload_b = notifs_b[0].payload_json

    assert payload_a["apaar_id"] == shared_apaar
    assert payload_a["other_institution_id"] == inst_b.id
    assert "College Beta" in payload_a["message"]

    assert payload_b["apaar_id"] == shared_apaar
    assert payload_b["other_institution_id"] == inst_a.id
    assert "College Alpha" in payload_b["message"]

    # Also verify validation flags created on both students
    flag_a = db_session.scalar(
        select(ValidationFlag).where(
            ValidationFlag.student_id == st_a.id,
            ValidationFlag.rule_code.in_([DUP_ACTIVE_OTHER_COLLEGE, DUP_SAME_COURSE_OTHER_COLLEGE]),
        )
    )
    flag_b = db_session.scalar(
        select(ValidationFlag).where(
            ValidationFlag.student_id == st_b.id,
            ValidationFlag.rule_code.in_([DUP_ACTIVE_OTHER_COLLEGE, DUP_SAME_COURSE_OTHER_COLLEGE]),
        )
    )
    assert flag_a is not None, "Validation flag must be created for student at College Alpha"
    assert flag_b is not None, "Validation flag must be created for student at College Beta"

    # =========================================================================
    # Verification 2: AICTE sees exactly ONE duplicate record
    # =========================================================================
    dup_records = get_duplicate_records(db_session, academic_year="2026-27")

    # Filter to the shared APAAR ID under test
    target_dups = [d for d in dup_records if d.apaar_id == shared_apaar]
    assert len(target_dups) == 1, (
        f"AICTE must see exactly ONE duplicate record for APAAR ID {shared_apaar}, "
        f"got {len(target_dups)}"
    )

    dup_rec: DuplicateRecordResponse = target_dups[0]
    assert dup_rec.apaar_id == shared_apaar
    assert dup_rec.institutions_count == 2
    assert dup_rec.status == "open"
    assert dup_rec.rule_code == DUP_ACTIVE_OTHER_COLLEGE
    assert dup_rec.level == "warning"

    inst_ids_in_record = {inst_detail.institution_id for inst_detail in dup_rec.institutions}
    assert inst_ids_in_record == {inst_a.id, inst_b.id}

    # Verify receipt numbers are populated
    receipts = {inst_detail.receipt_no for inst_detail in dup_rec.institutions}
    assert "REC-202627-1-10000001-A1B2C3" in receipts
    assert "REC-202627-1-10000002-X9Y8Z7" in receipts

    # =========================================================================
    # Verification 3: SSE Events were published
    # =========================================================================
    events = sse.get_recent_events()
    event_types = [e["event"] for e in events]
    assert "submission_submitted" in event_types
    assert "duplicate_enrolment_detected" in event_types


# =============================================================================
# 3. Review Items Created for Exceptions Test
# =============================================================================


def test_review_items_created_for_exception_flags(db_session: Session) -> None:
    """Test that when a submission contains exception-level flags:
    - ReviewItem records are created in review_items table with status='pending'
    - submission.status transitions to 'submitted_with_exceptions'
    - review_item_created SSE event is broadcast
    """
    sse.clear_recent_events()

    inst = _make_institution(db_session, "T24-INST-EXC", "Exception Tech College")
    course = _make_course(db_session, inst.id, "Mechanical Engineering")
    admin = _make_user(db_session, "admin@exc-tech.edu", "college_admin", inst.id)

    st = _make_student(db_session, inst.id, course.id, "111122223333", "Rohan Mehta", "EN-EXC-01")

    sub = Submission(
        institution_id=inst.id,
        academic_year="2026-27",
        status="draft",
        receipt_no="REC-202627-EXC-01",
        submitted_by=admin.id,
        submitted_at=datetime.now(UTC),
    )
    db_session.add(sub)
    db_session.flush()

    # Create an exception-level flag (e.g. INTAKE_EXCEEDED or justified DUP_SAME_COURSE)
    exc_flag = ValidationFlag(
        student_id=st.id,
        course_id=course.id,
        submission_id=sub.id,
        rule_code="INTAKE_EXCEEDED",
        level="exception",
        field="enrolment",
        message="Regular enrolment exceeds approved intake by 2 students.",
        fix_hint="Submit justification or adjust intake.",
        audience="both",
        requires_justification=True,
        status="justified",
    )
    db_session.add(exc_flag)
    db_session.flush()

    # Run promotion
    res = promote_submission_and_run_cross_checks(
        db=db_session,
        submission=sub,
        user=admin,
        redis_client=None,
    )

    assert res["status"] == "submitted_with_exceptions"
    assert res["review_items_created"] == 1
    assert res["exception_flags_count"] == 1

    # Check ReviewItem record in database
    review_item = db_session.scalar(
        select(ReviewItem).where(ReviewItem.submission_id == sub.id)
    )
    assert review_item is not None
    assert review_item.status == "pending"
    assert exc_flag.id in review_item.flag_ids

    # Verify SSE event
    events = sse.get_recent_events(event_type="review_item_created")
    assert len(events) >= 1
    assert events[0]["data"]["submission_id"] == sub.id


# =============================================================================
# 4. Duplicate Resolution Test: Student Withdrawn Resolves Flags
# =============================================================================


def test_duplicate_resolved_when_student_withdrawn(db_session: Session) -> None:
    """Test that when a duplicate student is marked withdrawn at one college:
    - Flags at both colleges are updated to 'resolved'
    - Resolution notifications are dispatched to both colleges
    - AICTE duplicate listing shows status as 'resolved'
    """
    inst_a = _make_institution(db_session, "1-10000003", "College Gamma")
    inst_b = _make_institution(db_session, "1-10000004", "College Delta")

    course_a = _make_course(db_session, inst_a.id, "Civil Engineering")
    course_b = _make_course(db_session, inst_b.id, "Civil Engineering")

    admin_a = _make_user(db_session, "admin@gamma.edu", "college_admin", inst_a.id)
    admin_b = _make_user(db_session, "admin@delta.edu", "college_admin", inst_b.id)

    shared_apaar = "555544443333"

    st_a = _make_student(db_session, inst_a.id, course_a.id, shared_apaar, "Karan Joshi", "EN-G-01")
    st_b = _make_student(db_session, inst_b.id, course_b.id, shared_apaar, "Karan Joshi", "EN-D-01")

    sub_a = Submission(
        institution_id=inst_a.id,
        academic_year="2026-27",
        status="draft",
        receipt_no="REC-202627-GAMMA-01",
        submitted_by=admin_a.id,
        submitted_at=datetime.now(UTC),
    )
    sub_b = Submission(
        institution_id=inst_b.id,
        academic_year="2026-27",
        status="draft",
        receipt_no="REC-202627-DELTA-01",
        submitted_by=admin_b.id,
        submitted_at=datetime.now(UTC),
    )
    db_session.add_all([sub_a, sub_b])
    db_session.flush()

    promote_submission_and_run_cross_checks(db_session, sub_a, admin_a)
    promote_submission_and_run_cross_checks(db_session, sub_b, admin_b)

    # Both have duplicate flags open
    flag_a = db_session.scalar(
        select(ValidationFlag).where(
            ValidationFlag.student_id == st_a.id,
            ValidationFlag.status == "open",
        )
    )
    flag_b = db_session.scalar(
        select(ValidationFlag).where(
            ValidationFlag.student_id == st_b.id,
            ValidationFlag.status == "open",
        )
    )
    assert flag_a is not None and flag_b is not None

    # Karan withdraws from College Gamma
    resolved_flags = resolve_duplicate_flags_on_status_change(
        db=db_session,
        student=st_a,
        new_status="withdrawn",
    )
    db_session.flush()

    assert len(resolved_flags) >= 2
    assert flag_a.status == "resolved"
    assert flag_b.status == "resolved"

    # Check resolution notifications
    res_notifs = list(
        db_session.scalars(
            select(Notification).where(
                Notification.type == "DUPLICATE_ENROLMENT_RESOLVED",
            )
        ).all()
    )
    assert len(res_notifs) >= 2

    # Check AICTE duplicate status
    dups = get_duplicate_records(db_session, academic_year="2026-27")
    target = next((d for d in dups if d.apaar_id == shared_apaar), None)
    assert target is not None
    assert target.status == "resolved"


# =============================================================================
# 5. REST Endpoints & RBAC Integration Tests
# =============================================================================


def test_analytics_duplicates_api_officer_access(client: TestClient, db_session: Session) -> None:
    """Test GET /api/v1/analytics/duplicates:
    - AICTE officer can access and view duplicates
    - Returns typed DuplicateListResponse schema
    """
    officer = _make_user(db_session, "officer_test@aicte-india.org", "aicte_officer", None)
    token = create_access_token(officer.id, officer.email, officer.role, None)

    resp = client.get(
        "/api/v1/analytics/duplicates?academic_year=2026-27",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_duplicates" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_analytics_duplicates_api_college_forbidden(
    client: TestClient, db_session: Session
) -> None:
    """Test GET /api/v1/analytics/duplicates:
    - College admin or staff cannot access AICTE centralized analytics (403 Forbidden)
    """
    inst = _make_institution(db_session, "T24-INST-RBAC", "RBAC Test College")
    user = _make_user(db_session, "admin_rbac@college.edu", "college_admin", inst.id)
    token = create_access_token(user.id, user.email, user.role, inst.id)

    resp = client.get(
        "/api/v1/analytics/duplicates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_analytics_events_api(client: TestClient, db_session: Session) -> None:
    """Test GET /api/v1/analytics/events:
    - AICTE role can query recent system events
    """
    sse.publish_sse_event(
        redis_client=None,
        event_type="test_event",
        data={"key": "value"},
    )

    officer = _make_user(db_session, "officer_events@aicte-india.org", "aicte_officer", None)
    token = create_access_token(officer.id, officer.email, officer.role, None)

    resp = client.get(
        "/api/v1/analytics/events?limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(e["event"] == "test_event" for e in data)


def test_institution_notifications_api(client: TestClient, db_session: Session) -> None:
    """Test GET /api/v1/institutions/{id}/notifications:
    - Institution staff can view their notifications
    - College A cannot view College B's notifications (IDOR protected)
    """
    inst_a = _make_institution(db_session, "T24-NOTIF-A", "Notif College A")
    inst_b = _make_institution(db_session, "T24-NOTIF-B", "Notif College B")

    user_a = _make_user(db_session, "admin@notif-a.edu", "college_admin", inst_a.id)
    user_b = _make_user(db_session, "admin@notif-b.edu", "college_admin", inst_b.id)

    notif = Notification(
        institution_id=inst_a.id,
        type="TEST_NOTIFICATION",
        payload_json={"message": "Welcome College A"},
    )
    db_session.add(notif)
    db_session.flush()

    token_a = create_access_token(user_a.id, user_a.email, user_a.role, inst_a.id)
    token_b = create_access_token(user_b.id, user_b.email, user_b.role, inst_b.id)

    # College A can view own notifications
    resp_a = client.get(
        f"/api/v1/institutions/{inst_a.id}/notifications",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a.status_code == 200
    items = resp_a.json()
    assert len(items) >= 1
    assert items[0]["type"] == "TEST_NOTIFICATION"

    # College B accessing College A: 403 Forbidden (IDOR prevented!)
    resp_idor = client.get(
        f"/api/v1/institutions/{inst_a.id}/notifications",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_idor.status_code == 403
