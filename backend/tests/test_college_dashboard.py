"""Tests for College Dashboard APIs and Notification Read workflows.

SPEC.md Section 13 & TASKS.md T30:
- Course summary and seat declarations
- Validation flags grouped by level
- Submission status and receipt
- AICTE clarification queries
- Institutional notifications (duplicate enrolment alerts, intake adjustments)
- Mark single/all notifications as read with RBAC and IDOR enforcement
"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.models import Course, CourseIntake, Institution, Notification, User


def _create_test_institution(
    db: Session, aicte_id: str = "1-DASH-101", name: str = "Dashboard College"
) -> Institution:
    inst = Institution(
        aicte_id=aicte_id,
        name=name,
        state="Karnataka",
        district="Bengaluru",
        address="100 Tech Hub, Electronic City",
        official_email=f"{aicte_id.lower()}@college.edu",
        official_phone="+919876543210",
        head_name="Dr. Director",
        affiliating_university="VTU Belagavi",
        approval_status="active",
        approval_valid_to=date(2028, 6, 30),
        account_status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def _create_test_user(
    db: Session, email: str, role: str, institution_id: int | None = None
) -> tuple[User, str]:
    user = User(
        email=email,
        password_hash=hash_password("SecurePass123!"),
        role=role,
        institution_id=institution_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.email, user.role, institution_id)
    return user, token


def test_notification_mark_read_and_mark_all_read(client: TestClient, db_session: Session) -> None:
    """Test marking individual and all notifications as read."""
    inst = _create_test_institution(db_session, "1-DASH-NOTIF-1")
    _, token = _create_test_user(db_session, "admin@dash-notif.edu", "college_admin", inst.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Seed 3 notifications
    n1 = Notification(
        institution_id=inst.id,
        type="duplicate_enrolment_detected",
        payload_json={"apaar_id": "111122223333", "message": "Cross-college duplicate caught"},
    )
    n2 = Notification(
        institution_id=inst.id,
        type="intake_updated",
        payload_json={"course_name": "CSE", "new_intake": 120},
    )
    n3 = Notification(
        institution_id=inst.id,
        type="compliance_notice",
        payload_json={"message": "Submit annual report by Nov 30"},
    )
    db_session.add_all([n1, n2, n3])
    db_session.commit()
    db_session.refresh(n1)
    db_session.refresh(n2)
    db_session.refresh(n3)

    # 1. Fetch notifications
    resp = client.get(f"/api/v1/institutions/{inst.id}/notifications", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 3
    assert all(item["read_at"] is None for item in items[:3])

    # 2. Mark single notification as read
    patch_resp = client.patch(
        f"/api/v1/institutions/{inst.id}/notifications/{n1.id}/read",
        headers=headers,
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["status"] == "success"
    assert patch_data["id"] == n1.id
    assert patch_data["read_at"] is not None

    # Verify n1 is read and n2/n3 remain unread
    db_session.refresh(n1)
    db_session.refresh(n2)
    assert n1.read_at is not None
    assert n2.read_at is None

    # 3. Mark all remaining notifications as read
    all_resp = client.post(
        f"/api/v1/institutions/{inst.id}/notifications/mark-all-read",
        headers=headers,
    )
    assert all_resp.status_code == 200
    all_data = all_resp.json()
    assert all_data["status"] == "success"
    assert all_data["marked_read_count"] >= 2

    # Verify n2 and n3 are now read
    db_session.refresh(n2)
    db_session.refresh(n3)
    assert n2.read_at is not None
    assert n3.read_at is not None


def test_notification_mark_read_idor_and_rbac(client: TestClient, db_session: Session) -> None:
    """Test IDOR protection: College A staff cannot read/mark College B notifications."""
    inst_a = _create_test_institution(db_session, "1-DASH-IDOR-A")
    inst_b = _create_test_institution(db_session, "1-DASH-IDOR-B")

    _, token_a = _create_test_user(db_session, "staff@dash-a.edu", "college_staff", inst_a.id)
    _, token_b = _create_test_user(db_session, "staff@dash-b.edu", "college_staff", inst_b.id)

    notif_b = Notification(
        institution_id=inst_b.id,
        type="duplicate_enrolment_detected",
        payload_json={"message": "Alert for B"},
    )
    db_session.add(notif_b)
    db_session.commit()
    db_session.refresh(notif_b)

    # College A attempts to mark College B notification: 403 Forbidden
    resp = client.patch(
        f"/api/v1/institutions/{inst_b.id}/notifications/{notif_b.id}/read",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403

    # College A attempts to mark-all College B notifications: 403 Forbidden
    resp_all = client.post(
        f"/api/v1/institutions/{inst_b.id}/notifications/mark-all-read",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_all.status_code == 403

    # Non-existent notification ID: 404 Not Found
    resp_404 = client.patch(
        f"/api/v1/institutions/{inst_b.id}/notifications/999999/read",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_404.status_code == 404


def test_college_dashboard_data_endpoints_integration(
    client: TestClient, db_session: Session
) -> None:
    """Test that all 5 college dashboard data sources are accessible and scoped."""
    inst = _create_test_institution(db_session, "1-DASH-INT-1")
    _, token = _create_test_user(db_session, "viewer@dash-int.edu", "college_viewer", inst.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Add course with intake
    course = Course(
        institution_id=inst.id,
        name="Computer Science & Engineering",
        branch="Computer Engineering",
        level="UG",
        duration_years=4,
    )
    db_session.add(course)
    db_session.flush()

    intake = CourseIntake(
        course_id=course.id,
        academic_year="2026-27",
        approved_intake=120,
        supernumerary_seats_allowed=12,
        source="aicte_master",
    )
    db_session.add(intake)
    db_session.commit()

    # 1. Course Summary and Seat Declarations
    resp_seats = client.get(
        f"/api/v1/institutions/{inst.id}/seat-declarations?academic_year=2026-27",
        headers=headers,
    )
    assert resp_seats.status_code == 200
    seats_data = resp_seats.json()
    assert seats_data["total_approved_intake"] == 120
    assert len(seats_data["courses"]) == 1
    assert seats_data["courses"][0]["course_name"] == "Computer Science & Engineering"

    # 2. Validation Flags
    resp_flags = client.get(
        f"/api/v1/institutions/{inst.id}/flags?academic_year=2026-27",
        headers=headers,
    )
    assert resp_flags.status_code == 200
    flags_data = resp_flags.json()
    assert "summary" in flags_data
    assert "items" in flags_data

    # 3. Submission Gate Status
    resp_gate = client.get(
        f"/api/v1/institutions/{inst.id}/submissions/gate?academic_year=2026-27",
        headers=headers,
    )
    assert resp_gate.status_code == 200
    gate_data = resp_gate.json()
    assert "current_status" in gate_data
    assert "can_submit" in gate_data

    # 4. Clarification Queries
    resp_queries = client.get(
        f"/api/v1/institutions/{inst.id}/queries?academic_year=2026-27",
        headers=headers,
    )
    assert resp_queries.status_code == 200
    queries_data = resp_queries.json()
    assert "items" in queries_data

    # 5. Notifications
    resp_notifs = client.get(
        f"/api/v1/institutions/{inst.id}/notifications",
        headers=headers,
    )
    assert resp_notifs.status_code == 200
    notifs_data = resp_notifs.json()
    assert isinstance(notifs_data, list)
