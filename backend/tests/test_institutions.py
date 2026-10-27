"""Tests for AICTE-owned data APIs, intake history, master sync, and upload gating.

SPEC.md Section 6 & TASKS.md T07:
- Read endpoints for institution, courses, intake per academic year (read-only for colleges).
- AICTE officer endpoints to change intake, courses and approval status with full history and audit.
- Mock AICTE master sync endpoint.
- Correction requests: college creates, AICTE resolves.
- Tests: college gets 403 on every attempt to change AICTE-owned data; history rows written;
  suspended approval blocks uploads.
"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.models import (
    AuditLog,
    Course,
    CourseIntake,
    CourseIntakeHistory,
    Institution,
    Notification,
    User,
)


def _create_institution(
    db: Session,
    aicte_id: str,
    name: str,
    approval_status: str = "active",
) -> Institution:
    inst = Institution(
        aicte_id=aicte_id,
        name=name,
        state="Maharashtra",
        district="Pune",
        address="100 Tech Park, Hinjawadi, Pune",
        official_email=f"contact_{aicte_id.lower()}@college.edu",
        official_phone="+919876543210",
        head_name="Dr. Principal",
        affiliating_university="Savitribai Phule Pune University",
        approval_status=approval_status,
        approval_valid_to=date(2028, 6, 30),
        account_status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def _create_course(
    db: Session,
    institution_id: int,
    name: str = "Computer Science and Engineering",
    level: str = "UG",
    branch: str = "Computer Science",
    intake: int = 120,
    supernumerary: int = 6,
    year: str = "2026-27",
) -> tuple[Course, CourseIntake]:
    course = Course(
        institution_id=institution_id,
        name=name,
        level=level,
        branch=branch,
        duration_years=4,
        supernumerary_allowed=True,
    )
    db.add(course)
    db.flush()

    course_intake = CourseIntake(
        course_id=course.id,
        academic_year=year,
        approved_intake=intake,
        supernumerary_seats_allowed=supernumerary,
        source="aicte_master",
        set_by="init",
    )
    db.add(course_intake)

    history = CourseIntakeHistory(
        course_id=course.id,
        academic_year=year,
        approved_intake=intake,
        supernumerary_seats_allowed=supernumerary,
        source="aicte_master",
        set_by="init",
        change_reason="Initial approval",
    )
    db.add(history)
    db.commit()
    db.refresh(course)
    db.refresh(course_intake)
    return course, course_intake


def _create_user(
    db: Session,
    email: str,
    role: str,
    institution_id: int | None = None,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password("SecurePassword123!"),
        role=role,
        institution_id=institution_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    return {"Authorization": f"Bearer {token}"}


# =========================================================================
# Read Endpoints & Scoping Tests
# =========================================================================


def test_read_institution_and_courses_scoping(client: TestClient, db_session: Session):
    """Verify read endpoints respect institution scoping:

    - AICTE officer can view any college.
    - College user can view their own college.
    - College A user receives 403 when trying to access College B.
    """
    inst_a = _create_institution(db_session, "1-T070001", "College Alpha")
    inst_b = _create_institution(db_session, "1-T070002", "College Beta")

    course_a, intake_a = _create_course(db_session, inst_a.id, "B.Tech CSE")
    course_b, intake_b = _create_course(db_session, inst_b.id, "B.Tech Mech")

    officer = _create_user(db_session, "officer_t07_1@aicte.gov", "aicte_officer")
    user_a = _create_user(db_session, "admin_a@alpha.edu", "college_admin", inst_a.id)
    _create_user(db_session, "admin_b@beta.edu", "college_admin", inst_b.id)

    # 1. AICTE officer lists all institutions
    resp = client.get("/api/v1/institutions", headers=_auth_header(officer))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2

    # 2. College A lists institutions -> sees only College A
    resp_a = client.get("/api/v1/institutions", headers=_auth_header(user_a))
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert data_a["total"] == 1
    assert data_a["items"][0]["id"] == inst_a.id

    # 3. College A accesses its own institution detail
    resp_detail = client.get(f"/api/v1/institutions/{inst_a.id}", headers=_auth_header(user_a))
    assert resp_detail.status_code == 200
    assert resp_detail.json()["aicte_id"] == "1-T070001"

    # 4. College A tries to view College B detail -> 403 Forbidden (IDOR)
    resp_idor = client.get(f"/api/v1/institutions/{inst_b.id}", headers=_auth_header(user_a))
    assert resp_idor.status_code == 403

    # 5. College A views its courses
    resp_courses = client.get(
        f"/api/v1/institutions/{inst_a.id}/courses", headers=_auth_header(user_a)
    )
    assert resp_courses.status_code == 200
    assert len(resp_courses.json()) == 1

    # 6. College A views its course intake
    resp_intake = client.get(
        f"/api/v1/institutions/{inst_a.id}/courses/{course_a.id}/intake",
        headers=_auth_header(user_a),
    )
    assert resp_intake.status_code == 200
    assert resp_intake.json()[0]["approved_intake"] == 120

    # 7. College A tries to view College B courses -> 403 Forbidden
    resp_courses_b = client.get(
        f"/api/v1/institutions/{inst_b.id}/courses", headers=_auth_header(user_a)
    )
    assert resp_courses_b.status_code == 403


# =========================================================================
# College 403 on AICTE-Owned Data Tests (Hard Rule 1)
# =========================================================================


def test_college_gets_403_on_mutating_aicte_owned_data(client: TestClient, db_session: Session):
    """Hard Rule 1: Colleges never edit AICTE-owned data (approved intake, approved courses,

    approval status, official contacts). They can only raise a correction request.
    Test that a college gets 403 on every attempt.
    """
    inst = _create_institution(db_session, "1-T070003", "Strict College")
    course, _ = _create_course(db_session, inst.id, "B.Tech Civil")
    college_admin = _create_user(db_session, "admin@strict.edu", "college_admin", inst.id)
    college_staff = _create_user(db_session, "staff@strict.edu", "college_staff", inst.id)

    for caller in [college_admin, college_staff]:
        headers = _auth_header(caller)

        # 1. College attempts to update intake directly -> 403
        resp_intake = client.put(
            f"/api/v1/institutions/{inst.id}/courses/{course.id}/intake",
            json={
                "academic_year": "2026-27",
                "approved_intake": 240,
                "supernumerary_seats_allowed": 12,
            },
            headers=headers,
        )
        assert resp_intake.status_code == 403, f"Intake edit returned {resp_intake.status_code}"

        # 2. College attempts to add an approved course -> 403
        resp_course = client.post(
            f"/api/v1/institutions/{inst.id}/courses",
            json={
                "name": "B.Tech Robotics",
                "level": "UG",
                "branch": "Robotics",
                "duration_years": 4,
            },
            headers=headers,
        )
        assert resp_course.status_code == 403, f"Course add returned {resp_course.status_code}"

        # 3. College attempts to edit course info -> 403
        resp_course_edit = client.put(
            f"/api/v1/institutions/{inst.id}/courses/{course.id}",
            json={"name": "Altered Course Name"},
            headers=headers,
        )
        assert resp_course_edit.status_code == 403

        # 4. College attempts to alter approval status -> 403
        resp_approval = client.patch(
            f"/api/v1/institutions/{inst.id}/approval-status",
            json={"approval_status": "active"},
            headers=headers,
        )
        assert resp_approval.status_code == 403

        # 5. College attempts to edit official institution info -> 403
        resp_info = client.patch(
            f"/api/v1/institutions/{inst.id}",
            json={"official_email": "hacked@strict.edu"},
            headers=headers,
        )
        assert resp_info.status_code == 403, f"Institution edit returned {resp_info.status_code}"

        # 6. College attempts to trigger master sync -> 403
        resp_sync = client.post(
            "/api/v1/institutions/sync",
            json={"academic_year": "2026-27"},
            headers=headers,
        )
        assert resp_sync.status_code == 403, f"Sync returned {resp_sync.status_code}"

        # 7. College attempts to view all correction requests queue -> 403
        resp_all_cr = client.get(
            "/api/v1/institutions/correction-requests",
            headers=headers,
        )
        assert resp_all_cr.status_code == 403, f"All CR returned {resp_all_cr.status_code}"

        # 8. College attempts to resolve a correction request -> 403
        resp_resolve = client.patch(
            "/api/v1/institutions/correction-requests/1/resolve",
            json={"status": "approved"},
            headers=headers,
        )
        assert resp_resolve.status_code == 403, f"Resolve CR returned {resp_resolve.status_code}"


# =========================================================================
# AICTE Intake Updates, History and Audit
# =========================================================================


def test_aicte_officer_intake_updates_write_history_and_audit(
    client: TestClient, db_session: Session
):
    """Test AICTE officer endpoints to change intake with full history and audit."""
    inst = _create_institution(db_session, "1-T070004", "Intake History College")
    course, _ = _create_course(
        db_session, inst.id, "B.Tech IT", intake=60, supernumerary=3, year="2026-27"
    )
    officer = _create_user(db_session, "officer_intake@aicte.gov", "aicte_officer")

    # Verify initial history row from creation
    history_rows = db_session.scalars(
        select(CourseIntakeHistory).where(CourseIntakeHistory.course_id == course.id)
    ).all()
    assert len(list(history_rows)) == 1

    # 1. AICTE Officer updates approved intake from 60 to 120
    update_payload = {
        "academic_year": "2026-27",
        "approved_intake": 120,
        "supernumerary_seats_allowed": 6,
        "change_reason": "AICTE EC Approval Resolution 45/2026",
    }
    resp = client.put(
        f"/api/v1/institutions/{inst.id}/courses/{course.id}/intake",
        json=update_payload,
        headers=_auth_header(officer),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["approved_intake"] == 120
    assert data["supernumerary_seats_allowed"] == 6

    # 2. Verify second history row appended with officer details
    history_rows_after = list(
        db_session.scalars(
            select(CourseIntakeHistory)
            .where(CourseIntakeHistory.course_id == course.id)
            .order_by(CourseIntakeHistory.id.desc())
        ).all()
    )
    assert len(history_rows_after) == 2
    latest_hist = history_rows_after[0]
    assert latest_hist.approved_intake == 120
    assert latest_hist.supernumerary_seats_allowed == 6
    assert latest_hist.source == "aicte_officer"
    assert latest_hist.set_by == officer.email
    assert latest_hist.change_reason == "AICTE EC Approval Resolution 45/2026"

    # 3. Read history endpoint returns both rows
    resp_hist = client.get(
        f"/api/v1/institutions/{inst.id}/courses/{course.id}/intake/history",
        headers=_auth_header(officer),
    )
    assert resp_hist.status_code == 200
    hist_json = resp_hist.json()
    assert len(hist_json) == 2
    assert hist_json[0]["approved_intake"] == 120
    assert hist_json[1]["approved_intake"] == 60

    # 4. Verify audit log entry recorded
    audit_entry = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == "intake.update",
            AuditLog.entity == "course_intake",
        )
        .order_by(AuditLog.id.desc())
    )
    assert audit_entry is not None
    assert audit_entry.actor_id == str(officer.id)
    assert audit_entry.before_json["approved_intake"] == 60
    assert audit_entry.after_json["approved_intake"] == 120

    # 5. Verify notification generated for institution
    notif = db_session.scalar(
        select(Notification)
        .where(
            Notification.institution_id == inst.id,
            Notification.type == "intake_change",
        )
        .order_by(Notification.id.desc())
    )
    assert notif is not None
    assert notif.payload_json["new_approved_intake"] == 120


# =========================================================================
# Mock AICTE Master Sync Tests
# =========================================================================


def test_master_sync_endpoint(client: TestClient, db_session: Session):
    """Test mock AICTE master sync endpoint imports or updates institutions and intake."""
    officer = _create_user(db_session, "sync_officer@aicte.gov", "aicte_officer")

    # Sync single known institution from MockAicteMasterClient
    # 1-10000001 is Pune Institute of Advanced Engineering & Technology in the mock
    resp = client.post(
        "/api/v1/institutions/sync",
        json={"aicte_id": "1-10000001", "academic_year": "2026-27"},
        headers=_auth_header(officer),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["synced_institutions"] == 1
    assert data["synced_courses"] >= 2
    assert data["synced_intakes"] >= 2

    # Verify institution exists in DB
    inst = db_session.scalar(select(Institution).where(Institution.aicte_id == "1-10000001"))
    assert inst is not None
    assert "Pune" in inst.name

    # Verify intake and history exist
    course = db_session.scalar(select(Course).where(Course.institution_id == inst.id))
    assert course is not None
    history = db_session.scalar(
        select(CourseIntakeHistory).where(CourseIntakeHistory.course_id == course.id)
    )
    assert history is not None
    assert history.source == "aicte_master"

    # Verify audit log recorded
    audit_entry = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "institution.sync").order_by(AuditLog.id.desc())
    )
    assert audit_entry is not None


# =========================================================================
# Correction Requests Workflow Tests
# =========================================================================


def test_correction_requests_workflow(client: TestClient, db_session: Session):
    """Acceptance criterion: Correction requests: college creates, AICTE resolves."""
    inst = _create_institution(db_session, "1-T070005", "Correction Test College")
    course, _ = _create_course(db_session, inst.id, "B.Tech EE", intake=60)
    college_admin = _create_user(db_session, "admin@correct.edu", "college_admin", inst.id)
    officer = _create_user(db_session, "resolver@aicte.gov", "aicte_officer")

    # 1. College creates a correction request to update contact email
    create_payload = {
        "kind": "contact_details",
        "payload_json": {
            "official_email": "updated_official@correct.edu",
            "reason": "Official college domain renamed",
        },
    }
    resp = client.post(
        f"/api/v1/institutions/{inst.id}/correction-requests",
        json=create_payload,
        headers=_auth_header(college_admin),
    )
    assert resp.status_code == 201
    cr_data = resp.json()
    assert cr_data["status"] == "pending"
    assert cr_data["kind"] == "contact_details"
    req_id = cr_data["id"]

    # 2. College views its correction requests
    resp_list = client.get(
        f"/api/v1/institutions/{inst.id}/correction-requests",
        headers=_auth_header(college_admin),
    )
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1

    # 3. AICTE officer views global correction requests queue
    resp_officer = client.get(
        "/api/v1/institutions/correction-requests?status=pending",
        headers=_auth_header(officer),
    )
    assert resp_officer.status_code == 200
    all_reqs = resp_officer.json()
    assert any(r["id"] == req_id for r in all_reqs)

    # 4. AICTE officer approves the request with apply_changes=True
    resolve_payload = {
        "status": "approved",
        "decision_note": "Domain registration verified with NIC",
        "apply_changes": True,
    }
    resp_resolve = client.patch(
        f"/api/v1/institutions/correction-requests/{req_id}/resolve",
        json=resolve_payload,
        headers=_auth_header(officer),
    )
    assert resp_resolve.status_code == 200
    assert resp_resolve.json()["status"] == "approved"
    assert resp_resolve.json()["resolved_by"] == officer.id

    # 5. Verify the official institution email was updated in DB
    db_session.refresh(inst)
    assert inst.official_email == "updated_official@correct.edu"

    # 6. Verify notification and audit log created
    audit_resolve = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "correction_request.resolve",
            AuditLog.entity_id == str(req_id),
        )
    )
    assert audit_resolve is not None

    notif = db_session.scalar(
        select(Notification).where(
            Notification.institution_id == inst.id,
            Notification.type == "correction_request_resolved",
        )
    )
    assert notif is not None
    assert notif.payload_json["status"] == "approved"

    # 7. Trying to resolve an already resolved request returns 409 Conflict
    resp_replay = client.patch(
        f"/api/v1/institutions/correction-requests/{req_id}/resolve",
        json={"status": "rejected"},
        headers=_auth_header(officer),
    )
    assert resp_replay.status_code == 409


# =========================================================================
# Suspended Approval Blocks Uploads Tests
# =========================================================================


def test_suspended_approval_blocks_uploads(client: TestClient, db_session: Session):
    """Acceptance criterion: Suspended approval blocks uploads (Spec 6 & Tasks T07)."""
    inst = _create_institution(
        db_session, "1-T070006", "Approval Gate College", approval_status="active"
    )
    staff = _create_user(db_session, "staff@approval.edu", "college_staff", inst.id)
    officer = _create_user(db_session, "status_officer@aicte.gov", "aicte_officer")

    # 1. When status is 'active', upload session is successfully created
    upload_payload = {"filename": "students_batch1.csv", "row_count": 50}
    resp_active = client.post(
        f"/api/v1/institutions/{inst.id}/uploads",
        json=upload_payload,
        headers=_auth_header(staff),
    )
    assert resp_active.status_code == 201
    assert resp_active.json()["status"] == "processing"

    # 2. AICTE officer changes approval status to 'suspended'
    resp_suspend = client.patch(
        f"/api/v1/institutions/{inst.id}/approval-status",
        json={
            "approval_status": "suspended",
            "reason": "Investigation into irregular admission practices",
        },
        headers=_auth_header(officer),
    )
    assert resp_suspend.status_code == 200
    assert resp_suspend.json()["approval_status"] == "suspended"

    # 3. College staff attempts upload while suspended -> HTTP 403 Forbidden
    resp_blocked = client.post(
        f"/api/v1/institutions/{inst.id}/uploads",
        json=upload_payload,
        headers=_auth_header(staff),
    )
    assert resp_blocked.status_code == 403
    assert "suspended" in resp_blocked.json()["detail"].lower()
    assert "blocked" in resp_blocked.json()["detail"].lower()

    # 4. Status 'withdrawn' and 'expired' also block uploads
    for blocked_status in ["withdrawn", "expired"]:
        client.patch(
            f"/api/v1/institutions/{inst.id}/approval-status",
            json={"approval_status": blocked_status},
            headers=_auth_header(officer),
        )
        resp = client.post(
            f"/api/v1/institutions/{inst.id}/uploads",
            json=upload_payload,
            headers=_auth_header(staff),
        )
        assert resp.status_code == 403

    # 5. Restoring status to 'active' re-enables uploads
    client.patch(
        f"/api/v1/institutions/{inst.id}/approval-status",
        json={"approval_status": "active"},
        headers=_auth_header(officer),
    )
    resp_restored = client.post(
        f"/api/v1/institutions/{inst.id}/uploads",
        json=upload_payload,
        headers=_auth_header(staff),
    )
    assert resp_restored.status_code == 201
