"""Tests for seat declarations, course summaries, autosave, and live validation.

SPEC.md Section 8.1 & 13, TASKS.md T19:
- Declare counts per course (regular, supernumerary, NRI, OCI, FN).
- Course summary table with read-only approved intake, calculated enrolment, status badge.
- Live validation on input (overshoot, supernumerary exceeded, category sums, negative numbers).
- Autosave as a draft: invalid values show errors immediately but are still saved.
- RBAC, IDOR protection, audit logging, and suspended approval enforcement.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.models import (
    AuditLog,
    Course,
    CourseIntake,
    Institution,
    SeatDeclaration,
    Student,
    User,
)


@pytest.fixture
def seat_test_env(db_session: Session):
    """Seed test institutions, courses, intakes, and users for seat declaration tests."""
    # 1. Active college 1
    inst1 = Institution(
        aicte_id="1-SEAT-001",
        name="Institute of Technology Alpha",
        state="Maharashtra",
        district="Pune",
        address="Campus One, Tech Park",
        official_email="principal@alpha-tech.edu.in",
        official_phone="+919876543210",
        head_name="Dr. Alpha Head",
        affiliating_university="Savitribai Phule Pune University",
        approval_status="active",
        account_status="active",
    )
    # 2. Active college 2 (for IDOR tests)
    inst2 = Institution(
        aicte_id="1-SEAT-002",
        name="Beta College of Engineering",
        state="Karnataka",
        district="Bengaluru",
        address="Whitefield Road",
        official_email="principal@beta-engg.edu.in",
        official_phone="+919876543211",
        head_name="Dr. Beta Head",
        affiliating_university="VTU Belagavi",
        approval_status="active",
        account_status="active",
    )
    # 3. Suspended college 3 (for upload/edit gate)
    inst3 = Institution(
        aicte_id="1-SEAT-003",
        name="Gamma Polytechnic",
        state="Tamil Nadu",
        district="Chennai",
        address="GST Road",
        official_email="principal@gamma.edu.in",
        official_phone="+919876543212",
        head_name="Dr. Gamma Head",
        affiliating_university="Anna University",
        approval_status="suspended",
        account_status="active",
    )
    db_session.add_all([inst1, inst2, inst3])
    db_session.flush()

    # Courses for inst1
    c1 = Course(
        institution_id=inst1.id,
        name="Computer Science & Engineering",
        level="UG",
        branch="CSE",
        duration_years=4,
        supernumerary_allowed=True,
    )
    c2 = Course(
        institution_id=inst1.id,
        name="Mechanical Engineering",
        level="UG",
        branch="MECH",
        duration_years=4,
        supernumerary_allowed=True,
    )
    # Course for inst2
    c3 = Course(
        institution_id=inst2.id,
        name="Electrical Engineering",
        level="UG",
        branch="EE",
        duration_years=4,
        supernumerary_allowed=False,
    )
    # Course for inst3
    c4 = Course(
        institution_id=inst3.id,
        name="Civil Engineering",
        level="Diploma",
        branch="CIVIL",
        duration_years=3,
        supernumerary_allowed=True,
    )
    db_session.add_all([c1, c2, c3, c4])
    db_session.flush()

    # Approved intake for 2026-27
    intake1 = CourseIntake(
        course_id=c1.id,
        academic_year="2026-27",
        approved_intake=120,
        supernumerary_seats_allowed=12,
        source="aicte_master",
    )
    intake2 = CourseIntake(
        course_id=c2.id,
        academic_year="2026-27",
        approved_intake=60,
        supernumerary_seats_allowed=6,
        source="aicte_master",
    )
    intake3 = CourseIntake(
        course_id=c3.id,
        academic_year="2026-27",
        approved_intake=60,
        supernumerary_seats_allowed=0,
        source="aicte_master",
    )
    intake4 = CourseIntake(
        course_id=c4.id,
        academic_year="2026-27",
        approved_intake=60,
        supernumerary_seats_allowed=6,
        source="aicte_master",
    )
    db_session.add_all([intake1, intake2, intake3, intake4])

    # Users
    u_admin1 = User(
        email="admin@alpha-tech.edu.in",
        password_hash=hash_password("Password123!"),
        role="college_admin",
        institution_id=inst1.id,
        is_active=True,
    )
    u_staff1 = User(
        email="staff@alpha-tech.edu.in",
        password_hash=hash_password("Password123!"),
        role="college_staff",
        institution_id=inst1.id,
        is_active=True,
    )
    u_viewer1 = User(
        email="viewer@alpha-tech.edu.in",
        password_hash=hash_password("Password123!"),
        role="college_viewer",
        institution_id=inst1.id,
        is_active=True,
    )
    u_admin2 = User(
        email="admin@beta-engg.edu.in",
        password_hash=hash_password("Password123!"),
        role="college_admin",
        institution_id=inst2.id,
        is_active=True,
    )
    u_admin3 = User(
        email="admin@gamma.edu.in",
        password_hash=hash_password("Password123!"),
        role="college_admin",
        institution_id=inst3.id,
        is_active=True,
    )
    u_aicte_officer = User(
        email="officer@aicte-india.org",
        password_hash=hash_password("Password123!"),
        role="aicte_officer",
        institution_id=None,
        is_active=True,
    )
    db_session.add_all([u_admin1, u_staff1, u_viewer1, u_admin2, u_admin3, u_aicte_officer])
    db_session.commit()

    return {
        "inst1": inst1,
        "inst2": inst2,
        "inst3": inst3,
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "c4": c4,
        "token_admin1": create_access_token(
            u_admin1.id, u_admin1.email, role="college_admin", institution_id=inst1.id
        ),
        "token_staff1": create_access_token(
            u_staff1.id, u_staff1.email, role="college_staff", institution_id=inst1.id
        ),
        "token_viewer1": create_access_token(
            u_viewer1.id, u_viewer1.email, role="college_viewer", institution_id=inst1.id
        ),
        "token_admin2": create_access_token(
            u_admin2.id, u_admin2.email, role="college_admin", institution_id=inst2.id
        ),
        "token_admin3": create_access_token(
            u_admin3.id, u_admin3.email, role="college_admin", institution_id=inst3.id
        ),
        "token_officer": create_access_token(
            u_aicte_officer.id, u_aicte_officer.email, role="aicte_officer"
        ),
    }


def test_get_institution_seat_declarations_initial(client: TestClient, seat_test_env: dict):
    """Test retrieving seat declarations for a college before any declarations are saved."""
    env = seat_test_env
    inst1 = env["inst1"]

    resp = client.get(
        f"/api/v1/institutions/{inst1.id}/seat-declarations?academic_year=2026-27",
        headers={"Authorization": f"Bearer {env['token_admin1']}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["institution_id"] == inst1.id
    assert data["academic_year"] == "2026-27"
    assert data["total_approved_intake"] == 180  # 120 + 60
    assert data["total_supernumerary_allowed"] == 18  # 12 + 6
    assert data["total_declared"] == 0
    assert data["total_enrolled"] == 0
    assert len(data["courses"]) == 2

    # Check CSE course summary defaults
    cse = next(c for c in data["courses"] if c["course_id"] == env["c1"].id)
    assert cse["course_name"] == "Computer Science & Engineering"
    assert cse["approved_intake"] == 120
    assert cse["supernumerary_seats_allowed"] == 12
    assert cse["regular_admitted"] == 0
    assert cse["supernumerary_admitted"] == 0
    assert cse["total_declared"] == 0
    assert cse["calculated_enrolment"] == 0
    assert cse["status_badge"] == "within_limit"
    assert cse["overshoot"] == 0
    assert cse["flags"] == []


def test_save_course_seat_declaration_within_limit(
    client: TestClient, db_session: Session, seat_test_env: dict
):
    """Test saving a course seat declaration within approved limits."""
    env = seat_test_env
    inst1 = env["inst1"]
    c1 = env["c1"]

    payload = {
        "academic_year": "2026-27",
        "regular_admitted": 110,
        "supernumerary_admitted": 10,
        "nri_count": 5,
        "oci_count": 2,
        "fn_count": 1,
        "status": "draft",
    }

    resp = client.put(
        f"/api/v1/institutions/{inst1.id}/courses/{c1.id}/seat-declaration",
        json=payload,
        headers={"Authorization": f"Bearer {env['token_admin1']}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["course_id"] == c1.id
    assert data["regular_admitted"] == 110
    assert data["supernumerary_admitted"] == 10
    assert data["total_declared"] == 120
    assert data["status_badge"] == "within_limit"
    assert data["overshoot"] == 0
    assert data["supernumerary_overshoot"] == 0
    assert data["flags"] == []

    # Check database persistence
    decl = db_session.scalar(
        select(SeatDeclaration).where(
            SeatDeclaration.course_id == c1.id,
            SeatDeclaration.academic_year == "2026-27",
        )
    )
    assert decl is not None
    assert decl.regular_admitted == 110
    assert decl.supernumerary_admitted == 10
    assert decl.nri_count == 5
    assert decl.status == "draft"

    # Verify audit log entry was created
    audit = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.entity == "seat_declarations",
            AuditLog.entity_id == str(decl.id),
        )
        .order_by(AuditLog.id.desc())
    )
    assert audit is not None
    assert audit.action in ("seat_declaration.create", "seat_declaration.update")


def test_save_course_seat_declaration_intake_exceeded(client: TestClient, seat_test_env: dict):
    """AC: 130 regular against approved intake 120 triggers INTAKE_EXCEEDED with overshoot 10."""
    env = seat_test_env
    inst1 = env["inst1"]
    c1 = env["c1"]

    payload = {
        "academic_year": "2026-27",
        "regular_admitted": 130,  # 10 over approved intake 120
        "supernumerary_admitted": 8,
        "nri_count": 0,
        "oci_count": 0,
        "fn_count": 0,
        "status": "draft",
    }

    resp = client.put(
        f"/api/v1/institutions/{inst1.id}/courses/{c1.id}/seat-declaration",
        json=payload,
        headers={"Authorization": f"Bearer {env['token_staff1']}"},  # staff can save drafts
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["regular_admitted"] == 130
    assert data["approved_intake"] == 120
    assert data["overshoot"] == 10
    assert data["status_badge"] == "over_by_n"

    # Flag INTAKE_EXCEEDED is returned immediately
    intake_flag = next((f for f in data["flags"] if f["rule_code"] == "INTAKE_EXCEEDED"), None)
    assert intake_flag is not None
    assert intake_flag["level"] == "exception"
    assert "exceed approved intake (120) by 10" in intake_flag["message"]


def test_autosave_draft_persists_even_with_invalid_values(
    client: TestClient, db_session: Session, seat_test_env: dict
):
    """Spec 8.1 & T19: Autosave as a draft; invalid values show errors immediately but save."""
    env = seat_test_env
    inst1 = env["inst1"]
    c1 = env["c1"]

    payload = {
        "academic_year": "2026-27",
        "regular_admitted": -5,  # Invalid negative
        "supernumerary_admitted": 20,  # Exceeds allowed quota (12) by 8
        "nri_count": 25,  # Exceeds total declared seats (15)
        "oci_count": 0,
        "fn_count": 0,
        "status": "draft",
    }

    resp = client.put(
        f"/api/v1/institutions/{inst1.id}/courses/{c1.id}/seat-declaration",
        json=payload,
        headers={"Authorization": f"Bearer {env['token_admin1']}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Shows errors immediately
    assert len(data["flags"]) >= 2
    rule_codes = {f["rule_code"] for f in data["flags"]}
    assert "SEAT_DECLARATION_INVALID" in rule_codes
    assert "SUPERNUMERARY_EXCEEDED" in rule_codes

    # But values ARE STILL SAVED as a draft in database
    decl = db_session.scalar(
        select(SeatDeclaration).where(
            SeatDeclaration.course_id == c1.id,
            SeatDeclaration.academic_year == "2026-27",
        )
    )
    assert decl is not None
    assert decl.regular_admitted == -5
    assert decl.supernumerary_admitted == 20
    assert decl.nri_count == 25


def test_declaration_mismatch_with_uploaded_students(
    client: TestClient, db_session: Session, seat_test_env: dict
):
    """Test that mismatch with active student records triggers SEAT_DECLARATION_MISMATCH."""
    env = seat_test_env
    inst1 = env["inst1"]
    c1 = env["c1"]

    # Insert 2 active students in database for c1
    s1 = Student(
        institution_id=inst1.id,
        course_id=c1.id,
        academic_year="2026-27",
        apaar_id="111122223333",
        name="Student One",
        dob_encrypted="enc_dob",
        gender="Male",
        enrolment_no="EN001",
        admission_date="2026-08-01",
        admission_mode="JEE Main counselling",
        seat_type="Regular",
        reservation_category="General",
        status="valid",
    )
    s2 = Student(
        institution_id=inst1.id,
        course_id=c1.id,
        academic_year="2026-27",
        apaar_id="111122223334",
        name="Student Two",
        dob_encrypted="enc_dob",
        gender="Female",
        enrolment_no="EN002",
        admission_date="2026-08-02",
        admission_mode="State counselling",
        seat_type="Supernumerary",
        reservation_category="OBC",
        status="valid",
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    # Save declared counts: 5 reg, 0 super (differs from 1 reg, 1 super in DB)
    payload = {
        "academic_year": "2026-27",
        "regular_admitted": 5,
        "supernumerary_admitted": 0,
        "status": "draft",
    }

    resp = client.put(
        f"/api/v1/institutions/{inst1.id}/courses/{c1.id}/seat-declaration",
        json=payload,
        headers={"Authorization": f"Bearer {env['token_admin1']}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["calculated_enrolment"] == 2
    assert data["calculated_regular"] == 1
    assert data["calculated_supernumerary"] == 1

    # Triggers SEAT_DECLARATION_MISMATCH
    mismatch_flag = next(
        (f for f in data["flags"] if f["rule_code"] == "SEAT_DECLARATION_MISMATCH"), None
    )
    assert mismatch_flag is not None
    assert mismatch_flag["level"] == "error"
    assert "differ from uploaded enrolled records" in mismatch_flag["message"]


def test_batch_save_seat_declarations(client: TestClient, seat_test_env: dict):
    """Test saving declarations for all courses at once via batch endpoint."""
    env = seat_test_env
    inst1 = env["inst1"]
    c1 = env["c1"]
    c2 = env["c2"]

    batch_payload = {
        "academic_year": "2026-27",
        "declarations": [
            {
                "course_id": c1.id,
                "regular_admitted": 100,
                "supernumerary_admitted": 10,
                "nri_count": 0,
                "status": "draft",
            },
            {
                "course_id": c2.id,
                "regular_admitted": 50,
                "supernumerary_admitted": 5,
                "nri_count": 2,
                "status": "draft",
            },
        ],
    }

    resp = client.put(
        f"/api/v1/institutions/{inst1.id}/seat-declarations",
        json=batch_payload,
        headers={"Authorization": f"Bearer {env['token_admin1']}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_declared_regular"] == 150
    assert data["total_declared_supernumerary"] == 15
    assert data["total_declared"] == 165
    assert len(data["courses"]) == 2


def test_idor_and_rbac_protections(client: TestClient, seat_test_env: dict):
    """Test strict institution scoping, role limits, and suspended status checks."""
    env = seat_test_env
    inst1 = env["inst1"]
    inst3 = env["inst3"]
    c1 = env["c1"]
    c4 = env["c4"]

    # 1. IDOR: College 2 admin cannot view College 1 seat declarations
    resp_idor_get = client.get(
        f"/api/v1/institutions/{inst1.id}/seat-declarations",
        headers={"Authorization": f"Bearer {env['token_admin2']}"},
    )
    assert resp_idor_get.status_code == 403

    # 2. IDOR: College 2 admin cannot edit College 1 seat declarations
    resp_idor_put = client.put(
        f"/api/v1/institutions/{inst1.id}/courses/{c1.id}/seat-declaration",
        json={"academic_year": "2026-27", "regular_admitted": 50},
        headers={"Authorization": f"Bearer {env['token_admin2']}"},
    )
    assert resp_idor_put.status_code == 403

    # 3. College viewer cannot modify seat declarations (read-only role)
    resp_viewer_put = client.put(
        f"/api/v1/institutions/{inst1.id}/courses/{c1.id}/seat-declaration",
        json={"academic_year": "2026-27", "regular_admitted": 50},
        headers={"Authorization": f"Bearer {env['token_viewer1']}"},
    )
    assert resp_viewer_put.status_code == 403

    # 4. College viewer CAN read seat declarations
    resp_viewer_get = client.get(
        f"/api/v1/institutions/{inst1.id}/seat-declarations",
        headers={"Authorization": f"Bearer {env['token_viewer1']}"},
    )
    assert resp_viewer_get.status_code == 200

    # 5. AICTE officer CAN read college seat declarations (supervisory)
    resp_officer_get = client.get(
        f"/api/v1/institutions/{inst1.id}/seat-declarations",
        headers={"Authorization": f"Bearer {env['token_officer']}"},
    )
    assert resp_officer_get.status_code == 200

    # 6. AICTE officer CANNOT modify seat declarations (College-owned data per Spec 6)
    resp_officer_put = client.put(
        f"/api/v1/institutions/{inst1.id}/courses/{c1.id}/seat-declaration",
        json={"academic_year": "2026-27", "regular_admitted": 50},
        headers={"Authorization": f"Bearer {env['token_officer']}"},
    )
    assert resp_officer_put.status_code == 403

    # 7. Suspended institution cannot save seat declarations (Spec 6)
    resp_suspended = client.put(
        f"/api/v1/institutions/{inst3.id}/courses/{c4.id}/seat-declaration",
        json={"academic_year": "2026-27", "regular_admitted": 40},
        headers={"Authorization": f"Bearer {env['token_admin3']}"},
    )
    assert resp_suspended.status_code == 403
    assert "suspended" in resp_suspended.json()["detail"].lower()

    # 8. Unauthenticated request is rejected with 401
    resp_unauth = client.get(f"/api/v1/institutions/{inst1.id}/seat-declarations")
    assert resp_unauth.status_code == 401
