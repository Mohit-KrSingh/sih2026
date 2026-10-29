"""Unit and integration tests for hash-chained audit logging and verification.

SPEC.md section 15, TASKS.md T06:
- audit.record(...) append-only table, prev_hash and hash.
- Tamper-evident verification reporting first broken row.
- Role-based access control (AICTE roles only).
- Query filtering and pagination.
- Automatic APAAR ID masking in audit payloads.
"""

import time

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.audit.service import compute_hash, serialize_canonical_row, verify_chain
from app.auth.security import create_access_token, hash_password
from app.models import AuditLog, Institution, User


def _create_user(
    db: Session,
    email: str,
    role: str,
    institution_id: int | None = None,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password("Password123!"),
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


def test_audit_record_genesis_and_chaining(db_session: Session):
    """Test that genesis row has None prev_hash and subsequent rows are linked cryptographically."""
    # Ensure clean slate within transaction
    initial_verification = verify_chain(db_session)
    assert initial_verification["verified"] is True

    # 1. Record first entry (genesis)
    entry1 = audit.record(
        db=db_session,
        action="institution.activate",
        actor_id="1",
        actor_role="aicte_admin",
        entity="institution",
        entity_id="101",
        after_json={"status": "active"},
        ip="192.168.1.1",
    )
    db_session.flush()

    assert entry1.id is not None
    assert entry1.prev_hash is None
    assert len(entry1.hash) == 64

    # Verify genesis hash matches SHA256("" + canonical_row)
    expected_canonical1 = serialize_canonical_row(
        ts=entry1.ts,
        actor_id=entry1.actor_id,
        actor_role=entry1.actor_role,
        action=entry1.action,
        entity=entry1.entity,
        entity_id=entry1.entity_id,
        before_json=entry1.before_json,
        after_json=entry1.after_json,
        ip=entry1.ip,
    )
    assert entry1.hash == compute_hash(None, expected_canonical1)

    # 2. Record second entry
    entry2 = audit.record(
        db=db_session,
        action="intake.update",
        actor_id="1",
        actor_role="aicte_admin",
        entity="course_intake",
        entity_id="5",
        before_json={"approved_intake": 60},
        after_json={"approved_intake": 120},
        ip="192.168.1.1",
    )
    db_session.flush()

    assert entry2.id > entry1.id
    assert entry2.prev_hash == entry1.hash
    assert len(entry2.hash) == 64

    # 3. Record third entry
    entry3 = audit.record(
        db=db_session,
        action="student.upload",
        actor_id="2",
        actor_role="college_admin",
        entity="upload",
        entity_id="99",
        after_json={"filename": "admissions_2026.csv", "rows": 120},
        ip="10.0.0.5",
    )
    db_session.flush()

    assert entry3.id > entry2.id
    assert entry3.prev_hash == entry2.hash

    # Verify chain integrity
    result = verify_chain(db_session)
    assert result["verified"] is True
    assert result["first_broken_id"] is None
    assert result["latest_hash"] == entry3.hash


def test_audit_masks_apaar_ids(db_session: Session):
    """Test that APAAR IDs are masked in audit payloads and entity IDs."""
    raw_apaar = "123456789012"
    entry = audit.record(
        db=db_session,
        action="student.verify",
        actor_id="10",
        actor_role="verifier",
        entity="student",
        entity_id=raw_apaar,
        before_json={"apaar_id": raw_apaar, "notes": f"Checked {raw_apaar}"},
        after_json={"apaar_id": raw_apaar, "status": "verified"},
    )
    db_session.flush()

    expected_masked = "********9012"
    assert raw_apaar not in str(entry.entity_id)
    assert entry.entity_id == expected_masked
    assert entry.before_json["apaar_id"] == expected_masked
    assert entry.after_json["apaar_id"] == expected_masked

    # The canonical serialization should also carry the masked value
    canonical = serialize_canonical_row(
        ts=entry.ts,
        actor_id=entry.actor_id,
        actor_role=entry.actor_role,
        action=entry.action,
        entity=entry.entity,
        entity_id=entry.entity_id,
        before_json=entry.before_json,
        after_json=entry.after_json,
        ip=entry.ip,
    )
    assert raw_apaar not in canonical
    assert expected_masked in canonical


def test_tamper_detection_reports_first_broken_row(db_session: Session):
    """Test that modifying a past row's content is detected and reports the exact broken row."""
    # Seed 5 consecutive records
    records = []
    for i in range(5):
        r = audit.record(
            db=db_session,
            action=f"action_{i}",
            actor_id="1",
            actor_role="aicte_admin",
            entity="test_entity",
            entity_id=str(i),
            after_json={"iteration": i},
        )
        records.append(r)
    db_session.flush()

    # Initial check must pass
    valid_result = verify_chain(db_session)
    assert valid_result["verified"] is True
    assert valid_result["first_broken_id"] is None

    # Tamper with record at index 2 (the 3rd row)
    target_row = records[2]
    target_id = target_row.id
    target_row.action = "action_tampered_maliciously"
    db_session.flush()

    # Verify that tampering is detected and reports target_id as first broken row
    tampered_result = verify_chain(db_session)
    assert tampered_result["verified"] is False
    assert tampered_result["first_broken_id"] == target_id
    assert tampered_result["broken_at_index"] == 2
    assert "Row content tampered" in tampered_result["reason"]


def test_tamper_detection_when_hash_is_also_modified(db_session: Session):
    """Test that tampering with data and recomputing that row's hash breaks the NEXT row's link."""
    records = []
    for i in range(4):
        r = audit.record(
            db=db_session,
            action=f"event_{i}",
            actor_id="1",
            actor_role="aicte_admin",
            entity="event",
            entity_id=str(i),
        )
        records.append(r)
    db_session.flush()

    # Tamper with row 1: alter action AND update row 1's hash to match its tampered content
    tampered_row = records[1]
    tampered_row.action = "event_altered"
    canonical_tampered = serialize_canonical_row(
        ts=tampered_row.ts,
        actor_id=tampered_row.actor_id,
        actor_role=tampered_row.actor_role,
        action=tampered_row.action,
        entity=tampered_row.entity,
        entity_id=tampered_row.entity_id,
        before_json=tampered_row.before_json,
        after_json=tampered_row.after_json,
        ip=tampered_row.ip,
    )
    tampered_row.hash = compute_hash(tampered_row.prev_hash, canonical_tampered)
    db_session.flush()

    # verify_chain should detect that row 2's prev_hash does not match row 1's new hash!
    result = verify_chain(db_session)
    assert result["verified"] is False
    # Next row in sequence is records[2]
    next_id = records[2].id
    assert result["first_broken_id"] == next_id
    assert result["broken_at_index"] == 2
    assert "Chain linkage mismatch" in result["reason"]


def test_audit_endpoints_role_protection(client: TestClient, db_session: Session):
    """Verify that only AICTE roles can query audit logs and verify the chain."""
    ts = int(time.time())
    inst = Institution(
        aicte_id=f"TEST-INST-AUDIT-{ts}",
        name="Test Audit Institution",
        state="Karnataka",
        district="Bengaluru",
        address="100 Tech Park",
        official_email=f"inst_{ts}@example.edu",
        official_phone="+919876543210",
        head_name="Dr. Director",
        affiliating_university="VTU",
        approval_status="active",
        account_status="active",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    aicte_admin = _create_user(db_session, f"aicte_admin_{ts}@example.com", "aicte_admin")
    aicte_officer = _create_user(db_session, f"aicte_officer_{ts}@example.com", "aicte_officer")
    college_admin = _create_user(
        db_session, f"college_admin_{ts}@example.com", "college_admin", inst.id
    )
    college_staff = _create_user(
        db_session, f"college_staff_{ts}@example.com", "college_staff", inst.id
    )
    college_viewer = _create_user(
        db_session, f"college_viewer_{ts}@example.com", "college_viewer", inst.id
    )
    verifier = _create_user(db_session, f"verifier_{ts}@example.com", "verifier")

    # 1. Unauthenticated requests must fail with 401
    assert client.get("/api/v1/audit").status_code == 401
    assert client.get("/api/v1/audit/verify-chain").status_code == 401

    # 2. Non-AICTE roles must fail with 403 Forbidden
    for user in [college_admin, college_staff, college_viewer, verifier]:
        resp_list = client.get("/api/v1/audit", headers=_auth_header(user))
        assert resp_list.status_code == 403, f"Expected 403 for role {user.role}"

        resp_chain = client.get("/api/v1/audit/verify-chain", headers=_auth_header(user))
        assert resp_chain.status_code == 403, f"Expected 403 for role {user.role}"

    # 3. AICTE roles must succeed with 200 OK
    for user in [aicte_admin, aicte_officer]:
        resp_list = client.get("/api/v1/audit", headers=_auth_header(user))
        assert resp_list.status_code == 200, f"Expected 200 for role {user.role}"
        data = resp_list.json()
        assert "items" in data
        assert "total" in data

        resp_chain = client.get("/api/v1/audit/verify-chain", headers=_auth_header(user))
        assert resp_chain.status_code == 200, f"Expected 200 for role {user.role}"
        chain_data = resp_chain.json()
        assert "verified" in chain_data


def test_audit_filtering_and_pagination(client: TestClient, db_session: Session):
    """Test query filtering by action, actor, entity, and pagination parameters."""
    ts = int(time.time())
    admin = _create_user(db_session, f"aicte_filter_{ts}@example.com", "aicte_admin")
    headers = _auth_header(admin)

    # Seed varied audit entries
    audit.record(
        db=db_session,
        action="user.create",
        actor_id=str(admin.id),
        actor_role="aicte_admin",
        entity="user",
        entity_id="101",
    )
    audit.record(
        db=db_session,
        action="user.update",
        actor_id=str(admin.id),
        actor_role="aicte_admin",
        entity="user",
        entity_id="101",
    )
    audit.record(
        db=db_session,
        action="intake.approve",
        actor_id="999",
        actor_role="aicte_officer",
        entity="course_intake",
        entity_id="202",
    )
    db_session.flush()

    # Filter by action
    res_action = client.get("/api/v1/audit?action=intake.approve", headers=headers)
    assert res_action.status_code == 200
    action_data = res_action.json()
    assert action_data["total"] >= 1
    assert all(item["action"] == "intake.approve" for item in action_data["items"])

    # Filter by actor_role
    res_role = client.get("/api/v1/audit?actor_role=aicte_officer", headers=headers)
    assert res_role.status_code == 200
    role_data = res_role.json()
    assert all(item["actor_role"] == "aicte_officer" for item in role_data["items"])

    # Filter by entity
    res_entity = client.get("/api/v1/audit?entity=course_intake", headers=headers)
    assert res_entity.status_code == 200
    entity_data = res_entity.json()
    assert all(item["entity"] == "course_intake" for item in entity_data["items"])

    # Pagination test
    res_page = client.get("/api/v1/audit?limit=2&offset=0", headers=headers)
    assert res_page.status_code == 200
    page_data = res_page.json()
    assert len(page_data["items"]) <= 2
    assert page_data["limit"] == 2
    assert page_data["offset"] == 0


def test_login_creates_audit_record(client: TestClient, db_session: Session):
    """Test that a successful login writes an append-only audit log entry."""
    ts = int(time.time())
    email = f"audit_login_{ts}@example.com"
    user = _create_user(db_session, email=email, role="aicte_admin")

    initial_count = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "auth.login", AuditLog.actor_id == str(user.id))
    )
    assert initial_count is None

    # Perform login
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert resp.status_code == 200

    # Query audit log for recorded login entry
    login_entry = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "auth.login", AuditLog.actor_id == str(user.id))
    )
    assert login_entry is not None
    assert login_entry.actor_role == "aicte_admin"
    assert login_entry.entity == "user"
    assert login_entry.entity_id == str(user.id)
    assert login_entry.after_json["email"] == email
    assert len(login_entry.hash) == 64
