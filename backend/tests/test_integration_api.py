"""Tests for Institutional Integration API Keys, Idempotency, and Bulk JSON Push.

SPEC.md Section 17 & TASKS.md T36:
- Scoped API keys (hashed, rotatable) managed from /college/api-keys.
- JSON bulk endpoint with the unified validation engine.
- Idempotency key header preventing duplicate ingestion.
- Scope enforcement, IDOR protection, and audit logging.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.models import AuditLog, Course, CourseIntake, Institution, Student, User


@pytest.fixture
def test_institution(db_session: Session) -> Institution:
    """Fixture creating an approved active institution with a course and intake."""
    unique_suffix = uuid.uuid4().hex[:6]
    inst = Institution(
        aicte_id=f"1-{unique_suffix}",
        name=f"Engineering College {unique_suffix.upper()}",
        state="Maharashtra",
        district="Pune",
        address="100 Tech Road, Pune",
        official_email=f"admin_{unique_suffix}@college.edu",
        official_phone="+919876543210",
        head_name="Dr. Principal",
        affiliating_university="Pune Tech University",
        approval_status="active",
        account_status="active",
    )
    db_session.add(inst)
    db_session.flush()

    course = Course(
        institution_id=inst.id,
        name="Computer Science and Engineering",
        level="UG",
        branch="Computer Science",
        duration_years=4,
        supernumerary_allowed=True,
    )
    db_session.add(course)
    db_session.flush()

    intake = CourseIntake(
        course_id=course.id,
        academic_year="2026-27",
        approved_intake=60,
        supernumerary_seats_allowed=6,
        source="aicte_master",
        set_by="admin",
    )
    db_session.add(intake)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def college_admin_user(db_session: Session, test_institution: Institution) -> User:
    """Fixture creating a college admin user for test_institution."""
    user = User(
        email=f"admin_{test_institution.aicte_id}@college.edu",
        password_hash="fake_hash",
        role="college_admin",
        institution_id=test_institution.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def college_admin_token(college_admin_user: User) -> str:
    """Generate JWT access token for college admin."""
    return create_access_token(
        user_id=college_admin_user.id,
        email=college_admin_user.email,
        role=college_admin_user.role,
        institution_id=college_admin_user.institution_id,
    )


def test_api_key_lifecycle_create_list_rotate_revoke(
    client: TestClient,
    test_institution: Institution,
    college_admin_token: str,
    db_session: Session,
):
    """Test full API key lifecycle: create, list, rotate, authenticate, and revoke."""
    auth_headers = {"Authorization": f"Bearer {college_admin_token}"}
    inst_id = test_institution.id

    # 1. Create API key
    create_payload = {
        "name": "Production SIS Integration",
        "scopes": ["students:write", "students:read", "courses:read"],
    }
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/api-keys",
        json=create_payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    created_data = resp.json()
    assert "raw_key" in created_data
    assert created_data["raw_key"].startswith("apaar_live_")
    assert created_data["name"] == "Production SIS Integration"
    assert created_data["is_active"] is True
    key_id = created_data["id"]
    raw_key_1 = created_data["raw_key"]

    # 2. List API keys
    list_resp = client.get(
        f"/api/v1/institutions/{inst_id}/api-keys",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    found_key = next((k for k in list_data["items"] if k["id"] == key_id), None)
    assert found_key is not None
    assert "raw_key" not in found_key  # Plaintext key is never exposed on list!
    assert found_key["is_active"] is True

    # 3. Authenticate with raw_key_1 on /api/v1/integration/me
    me_resp_1 = client.get(
        "/api/v1/integration/me",
        headers={"X-API-Key": raw_key_1},
    )
    assert me_resp_1.status_code == 200
    assert me_resp_1.json()["institution_id"] == inst_id
    assert me_resp_1.json()["api_key_id"] == key_id

    # 4. Rotate API key
    rotate_resp = client.post(
        f"/api/v1/institutions/{inst_id}/api-keys/{key_id}/rotate",
        headers=auth_headers,
    )
    assert rotate_resp.status_code == 200
    rotate_data = rotate_resp.json()
    assert "raw_key" in rotate_data
    raw_key_2 = rotate_data["raw_key"]
    assert raw_key_2 != raw_key_1

    # 5. Old key must now fail (401 Unauthorized)
    old_key_resp = client.get(
        "/api/v1/integration/me",
        headers={"X-API-Key": raw_key_1},
    )
    assert old_key_resp.status_code == 401

    # 6. New key must succeed
    new_key_resp = client.get(
        "/api/v1/integration/me",
        headers={"X-API-Key": raw_key_2},
    )
    assert new_key_resp.status_code == 200

    # 7. Revoke API key
    revoke_resp = client.post(
        f"/api/v1/institutions/{inst_id}/api-keys/{key_id}/revoke",
        headers=auth_headers,
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["is_active"] is False

    # 8. Revoked key must fail authentication
    revoked_key_resp = client.get(
        "/api/v1/integration/me",
        headers={"X-API-Key": raw_key_2},
    )
    assert revoked_key_resp.status_code == 401

    # 9. Cannot rotate revoked key
    cant_rotate_resp = client.post(
        f"/api/v1/institutions/{inst_id}/api-keys/{key_id}/rotate",
        headers=auth_headers,
    )
    assert cant_rotate_resp.status_code == 400


def test_scope_enforcement_on_integration_endpoints(
    client: TestClient,
    test_institution: Institution,
    college_admin_token: str,
):
    """Test that API keys lacking required scope cannot perform operations."""
    inst_id = test_institution.id
    auth_headers = {"Authorization": f"Bearer {college_admin_token}"}

    # Create read-only key (lacks students:write)
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/api-keys",
        json={"name": "Read Only Reporting", "scopes": ["students:read"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    read_only_key = resp.json()["raw_key"]

    # Attempt student push with read-only key
    push_payload = {
        "academic_year": "2026-27",
        "students": [
            {
                "apaar_id": "900012345678",
                "name": "Amit Kumar",
                "dob": "2004-05-15",
                "gender": "Male",
                "course": "Computer Science and Engineering",
                "enrolment_no": "ENR-001",
                "admission_date": "2026-07-15",
            }
        ],
    }

    push_resp = client.post(
        "/api/v1/integration/students/bulk",
        json=push_payload,
        headers={"X-API-Key": read_only_key},
    )
    assert push_resp.status_code == 403
    assert "students:write" in push_resp.json()["detail"]


def test_bulk_student_push_and_idempotency_header(
    client: TestClient,
    test_institution: Institution,
    college_admin_token: str,
    db_session: Session,
):
    """Test bulk JSON student push, validation execution, and idempotency key replay."""
    inst_id = test_institution.id
    auth_headers = {"Authorization": f"Bearer {college_admin_token}"}

    # Generate full access key
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/api-keys",
        json={"name": "ERP Push Key", "scopes": ["students:write", "students:read"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    api_key = resp.json()["raw_key"]

    unique_key = f"IDEMPOTENCY-{uuid.uuid4().hex[:12]}"
    push_payload = {
        "academic_year": "2026-27",
        "students": [
            {
                "apaar_id": "900012345678",
                "name": "Rajesh Gupta",
                "dob": "2004-06-20",
                "gender": "Male",
                "course": "Computer Science and Engineering",
                "branch": "Computer Science",
                "enrolment_no": "ENR-CS-2026-01",
                "admission_date": "2026-07-20",
                "admission_mode": "State counselling",
                "seat_type": "Regular",
                "reservation_category": "General",
                "nri": "No",
                "oci": "No",
                "foreign_national": "No",
            },
            {
                "apaar_id": "900012345679",
                "name": "Sunita Rao",
                "dob": "2004-09-14",
                "gender": "Female",
                "course": "Computer Science and Engineering",
                "branch": "Computer Science",
                "enrolment_no": "ENR-CS-2026-02",
                "admission_date": "2026-07-22",
                "admission_mode": "State counselling",
                "seat_type": "Regular",
                "reservation_category": "OBC",
                "nri": "No",
                "oci": "No",
                "foreign_national": "No",
            },
        ],
    }

    # First Submission
    first_resp = client.post(
        "/api/v1/integration/students/bulk",
        json=push_payload,
        headers={
            "X-API-Key": api_key,
            "Idempotency-Key": unique_key,
        },
    )
    assert first_resp.status_code == 201
    assert first_resp.headers.get("x-idempotent-replayed") == "false"
    first_data = first_resp.json()
    assert first_data["row_count"] == 2
    upload_id = first_data["upload_id"]

    # Check student records were saved in database
    students = list(
        db_session.scalars(
            select(Student).where(
                Student.institution_id == inst_id,
                Student.source == "api",
            )
        ).all()
    )
    assert len(students) >= 2

    # Second Submission with IDENTICAL Idempotency-Key
    second_resp = client.post(
        "/api/v1/integration/students/bulk",
        json=push_payload,
        headers={
            "X-API-Key": api_key,
            "Idempotency-Key": unique_key,
        },
    )
    assert second_resp.status_code in (200, 201)
    assert second_resp.headers.get("x-idempotent-replayed") == "true"
    second_data = second_resp.json()
    assert second_data["upload_id"] == upload_id
    assert second_data["row_count"] == 2


def test_cross_institution_idor_prevention(
    client: TestClient,
    test_institution: Institution,
    college_admin_token: str,
    db_session: Session,
):
    """Test that API key for Institution A cannot push to Institution B's endpoint."""
    inst_a_id = test_institution.id
    auth_headers = {"Authorization": f"Bearer {college_admin_token}"}

    # Create other institution B
    inst_b = Institution(
        aicte_id="1-OTHER999",
        name="Other Institute of Tech",
        state="Karnataka",
        district="Bengaluru",
        address="Electronic City",
        official_email="contact@other.edu",
        official_phone="+919999888877",
        head_name="Dr. Director",
        affiliating_university="VTU",
        approval_status="active",
        account_status="active",
    )
    db_session.add(inst_b)
    db_session.commit()
    db_session.refresh(inst_b)

    # Key for Institution A
    resp = client.post(
        f"/api/v1/institutions/{inst_a_id}/api-keys",
        json={"name": "Inst A Key", "scopes": ["students:write"]},
        headers=auth_headers,
    )
    api_key_a = resp.json()["raw_key"]

    # Attempt to push to Institution B's scoped endpoint
    push_resp = client.post(
        f"/api/v1/integration/institutions/{inst_b.id}/students/bulk",
        json={
            "academic_year": "2026-27",
            "students": [
                {
                    "apaar_id": "900012345678",
                    "name": "Test Student",
                    "dob": "2004-01-01",
                    "gender": "Male",
                    "course": "Mechanical Engineering",
                    "enrolment_no": "ENR-01",
                    "admission_date": "2026-07-01",
                }
            ],
        },
        headers={"X-API-Key": api_key_a},
    )
    assert push_resp.status_code == 403


def test_suspended_institution_cannot_push_via_api(
    client: TestClient,
    test_institution: Institution,
    college_admin_token: str,
    db_session: Session,
):
    """Test that if an institution's approval status is suspended, API push is rejected with 403."""
    inst_id = test_institution.id
    auth_headers = {"Authorization": f"Bearer {college_admin_token}"}

    # Create API key while active
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/api-keys",
        json={"name": "Valid Key", "scopes": ["students:write"]},
        headers=auth_headers,
    )
    api_key = resp.json()["raw_key"]

    # Suspend institution approval
    test_institution.approval_status = "suspended"
    db_session.commit()

    # Attempt API push
    push_resp = client.post(
        "/api/v1/integration/students/bulk",
        json={
            "academic_year": "2026-27",
            "students": [
                {
                    "apaar_id": "900012345678",
                    "name": "Test Student",
                    "dob": "2004-01-01",
                    "gender": "Male",
                    "course": "Computer Science and Engineering",
                    "enrolment_no": "ENR-01",
                    "admission_date": "2026-07-01",
                }
            ],
        },
        headers={"X-API-Key": api_key},
    )
    assert push_resp.status_code == 403
    assert "suspended" in push_resp.json()["detail"].lower()


def test_audit_log_entries_recorded_for_api_lifecycle(
    client: TestClient,
    test_institution: Institution,
    college_admin_token: str,
    db_session: Session,
):
    """Test that audit log entries are generated for API key creation, rotation, and revocation."""
    inst_id = test_institution.id
    auth_headers = {"Authorization": f"Bearer {college_admin_token}"}

    # 1. Create key
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/api-keys",
        json={"name": "Audit Tracked Key", "scopes": ["students:write"]},
        headers=auth_headers,
    )
    key_id = resp.json()["id"]

    # 2. Rotate key
    client.post(
        f"/api/v1/institutions/{inst_id}/api-keys/{key_id}/rotate",
        headers=auth_headers,
    )

    # 3. Revoke key
    client.post(
        f"/api/v1/institutions/{inst_id}/api-keys/{key_id}/revoke",
        headers=auth_headers,
    )

    # Verify audit logs in database
    create_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "api_key.create",
            AuditLog.entity_id == str(key_id),
        )
    )
    assert create_log is not None

    rotate_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "api_key.rotate",
            AuditLog.entity_id == str(key_id),
        )
    )
    assert rotate_log is not None

    revoke_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "api_key.revoke",
            AuditLog.entity_id == str(key_id),
        )
    )
    assert revoke_log is not None
