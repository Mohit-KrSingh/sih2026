"""Tests for College Activation Backend.

SPEC.md Section 11 & TASKS.md T08:
- Claim by AICTE ID, OTP to on-file contacts, mock signatory identity check,
  authorisation letter upload, pending request, AICTE approve or reject,
  primary admin created with MFA.
- Tests: unknown ID rejected; OTP never sent to a typed-in address;
  non-approved college cannot log in.
"""

import base64
import json
import time
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.rate_limiter import reset_rate_limit
from app.auth.security import create_access_token, hash_password
from app.integrations.factory import get_storage
from app.models import (
    AuditLog,
    DevOutbox,
    Institution,
    User,
)


@pytest.fixture(autouse=True)
def clean_rate_limits(redis_conn):
    reset_rate_limit(redis_conn, "activation_otp")
    reset_rate_limit(redis_conn, "login")
    yield
    reset_rate_limit(redis_conn, "activation_otp")
    reset_rate_limit(redis_conn, "login")


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    return {"Authorization": f"Bearer {token}"}


def _create_user(
    db: Session,
    email: str,
    role: str = "aicte_officer",
    institution_id: int | None = None,
    password: str = "Password@12345",
    mfa_secret: str | None = None,
) -> User:
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        role=role,
        institution_id=institution_id,
        mfa_secret=mfa_secret,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_test_institution(
    db: Session,
    aicte_id: str,
    name: str,
    account_status: str = "not_activated",
    approval_status: str = "active",
) -> Institution:
    inst = Institution(
        aicte_id=aicte_id,
        name=name,
        state="Maharashtra",
        district="Pune",
        address="100 Tech Park, Hinjawadi, Pune",
        official_email=f"registrar_{aicte_id.lower().replace('-', '_')}@college.edu",
        official_phone="+919876543210",
        head_name="Dr. Director",
        affiliating_university="Savitribai Phule Pune University",
        approval_status=approval_status,
        approval_valid_to=date(2028, 6, 30),
        account_status=account_status,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def test_unknown_id_rejected(client: TestClient):
    """Test 1: Unknown AICTE ID is rejected immediately with HTTP 404 Not Found."""
    resp = client.post(
        "/api/v1/institutions/activation/initiate",
        json={"aicte_id": "UNKNOWN-INST-99999"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_otp_never_sent_to_typed_in_address(client: TestClient, db_session: Session, redis_conn):
    """Test 2: OTP goes ONLY to official email and phone on file, NEVER to a typed-in address.

    SPEC.md section 11: 'OTP goes only to the official email and phone already on file with AICTE,
    never to a typed-in address.'
    """
    ts = int(time.time() * 1000)
    inst = _create_test_institution(db_session, f"ACT-OTP-{ts}", f"Test Academy {ts}")

    official_email = inst.official_email
    attacker_email = f"attacker_{ts}@hacker.org"
    attacker_phone = "+910000000000"

    # Attacker attempts to inject custom recipient address in body
    resp = client.post(
        "/api/v1/institutions/activation/initiate",
        json={
            "aicte_id": inst.aicte_id,
            "email": attacker_email,
            "phone": attacker_phone,
            "recipient": attacker_email,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["aicte_id"] == inst.aicte_id
    assert data["status"] == "otp_dispatched"

    # Verify masked contact belongs to official email on file, not attacker
    assert data["masked_email"].endswith(official_email.split("@")[1])
    assert "attacker" not in data["masked_email"].lower()

    # Verify OTP was stored in Redis ONLY for official email
    official_key = f"otp:activation:{official_email.lower()}"
    attacker_key = f"otp:activation:{attacker_email.lower()}"
    assert redis_conn.get(official_key) is not None
    assert redis_conn.get(attacker_key) is None

    # Verify dev_outbox has record for official on-file email, NOT attacker
    outbox_entry = db_session.scalar(
        select(DevOutbox).where(DevOutbox.recipient == official_email).order_by(DevOutbox.id.desc())
    )
    assert outbox_entry is not None
    assert "activation claim" in outbox_entry.body.lower()

    attacker_entry = db_session.scalar(
        select(DevOutbox).where(DevOutbox.recipient == attacker_email)
    )
    assert attacker_entry is None


def test_non_approved_approval_status_cannot_activate(client: TestClient, db_session: Session):
    """Test 3: Institution whose approval status is not active cannot initiate activation.

    SPEC.md section 11: 'Rules: approval must be active for the year'.
    """
    ts = int(time.time() * 1000)
    inst_suspended = _create_test_institution(
        db_session, f"ACT-SUSP-{ts}", "Suspended College", approval_status="suspended"
    )
    resp_susp = client.post(
        "/api/v1/institutions/activation/initiate",
        json={"aicte_id": inst_suspended.aicte_id},
    )
    assert resp_susp.status_code == 400
    assert "suspended" in resp_susp.json()["detail"].lower()

    inst_withdrawn = _create_test_institution(
        db_session, f"ACT-WITH-{ts}", "Withdrawn College", approval_status="withdrawn"
    )
    resp_with = client.post(
        "/api/v1/institutions/activation/initiate",
        json={"aicte_id": inst_withdrawn.aicte_id},
    )
    assert resp_with.status_code == 400
    assert "withdrawn" in resp_with.json()["detail"].lower()


def test_already_activated_college_cannot_reclaim(client: TestClient, db_session: Session):
    """Test 4: An already active institution cannot initiate account activation again."""
    ts = int(time.time() * 1000)
    inst = _create_test_institution(
        db_session, f"ACT-ACTV-{ts}", "Active College", account_status="active"
    )
    resp = client.post(
        "/api/v1/institutions/activation/initiate",
        json={"aicte_id": inst.aicte_id},
    )
    assert resp.status_code == 400
    assert "already activated" in resp.json()["detail"].lower()


def test_otp_verification_flow(client: TestClient, db_session: Session, redis_conn):
    """Test 5: OTP verification handles invalid attempts and returns signed activation token."""
    ts = int(time.time() * 1000)
    inst = _create_test_institution(db_session, f"ACT-VERIF-{ts}", f"Verification College {ts}")

    # Initiate
    resp_init = client.post(
        "/api/v1/institutions/activation/initiate",
        json={"aicte_id": inst.aicte_id},
    )
    assert resp_init.status_code == 200

    # Read OTP from Redis
    raw_otp = redis_conn.get(f"otp:activation:{inst.official_email.lower()}")
    assert raw_otp is not None
    otp_code = json.loads(raw_otp)["code"]

    # Wrong OTP -> 400 Bad Request
    resp_wrong = client.post(
        "/api/v1/institutions/activation/verify-otp",
        json={"aicte_id": inst.aicte_id, "otp_code": "000000"},
    )
    assert resp_wrong.status_code == 400
    assert "failed" in resp_wrong.json()["detail"].lower()

    # Correct OTP -> 200 OK with activation token
    resp_ok = client.post(
        "/api/v1/institutions/activation/verify-otp",
        json={"aicte_id": inst.aicte_id, "otp_code": otp_code},
    )
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert data["verified"] is True
    assert "activation_token" in data
    assert data["institution_name"] == inst.name


def test_mock_signatory_verification_rejected(client: TestClient, db_session: Session, redis_conn):
    """Test 6: Mock signatory check rejects invalid credentials (MockIdentityVerifier)."""
    ts = int(time.time() * 1000)
    inst = _create_test_institution(db_session, f"ACT-SIG-{ts}", f"Signatory College {ts}")

    client.post(
        "/api/v1/institutions/activation/initiate",
        json={"aicte_id": inst.aicte_id},
    )
    raw_otp = redis_conn.get(f"otp:activation:{inst.official_email.lower()}")
    otp_code = json.loads(raw_otp)["code"]

    resp_verif = client.post(
        "/api/v1/institutions/activation/verify-otp",
        json={"aicte_id": inst.aicte_id, "otp_code": otp_code},
    )
    token = resp_verif.json()["activation_token"]

    # Signatory check fails when signatory_ref contains INVALID
    fake_letter_b64 = base64.b64encode(b"%PDF-1.4 Mock document bytes").decode("utf-8")
    resp_fail = client.post(
        "/api/v1/institutions/activation/submit",
        json={
            "activation_token": token,
            "signatory_name": "Dr. Valid Name",
            "signatory_ref": "DOC-INVALID-CREDENTIALS",
            "letter_content_b64": fake_letter_b64,
        },
    )
    assert resp_fail.status_code == 400
    assert "signatory" in resp_fail.json()["detail"].lower()


def test_activation_claim_submission_and_audit(client: TestClient, db_session: Session, redis_conn):
    """Test 7: Submit activation claim, verify storage, and verify audit log."""
    ts = int(time.time() * 1000)
    inst = _create_test_institution(db_session, f"ACT-SUBM-{ts}", f"Submit College {ts}")

    client.post(
        "/api/v1/institutions/activation/initiate",
        json={"aicte_id": inst.aicte_id},
    )
    raw_otp = redis_conn.get(f"otp:activation:{inst.official_email.lower()}")
    otp_code = json.loads(raw_otp)["code"]

    resp_verif = client.post(
        "/api/v1/institutions/activation/verify-otp",
        json={"aicte_id": inst.aicte_id, "otp_code": otp_code},
    )
    token = resp_verif.json()["activation_token"]

    letter_bytes = b"%PDF-1.4 Official college authorization letter signed by registrar"
    letter_b64 = base64.b64encode(letter_bytes).decode("utf-8")

    resp_submit = client.post(
        "/api/v1/institutions/activation/submit",
        json={
            "activation_token": token,
            "signatory_name": "Dr. Ramesh Sharma",
            "signatory_ref": "DIGILOCKER-REF-889900",
            "letter_content_b64": letter_b64,
            "letter_filename": "official_authorization.pdf",
        },
    )
    assert resp_submit.status_code == 201
    claim_data = resp_submit.json()
    assert claim_data["status"] == "pending"
    assert claim_data["institution_id"] == inst.id
    assert claim_data["signatory_name"] == "Dr. Ramesh Sharma"
    assert "authorisation_letters" in claim_data["letter_ref"]

    # Verify institution state transitioned to pending_approval
    db_session.refresh(inst)
    assert inst.account_status == "pending_approval"

    # Verify audit log recorded institution.activation_requested
    audit_entry = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.entity_id == str(claim_data["id"]),
            AuditLog.action == "institution.activation_requested",
        )
        .order_by(AuditLog.id.desc())
    )
    assert audit_entry is not None
    assert audit_entry.actor_id == inst.aicte_id

    # Verify file stored in Storage interface
    storage = get_storage()
    assert storage.exists(claim_data["letter_ref"]) is True
    assert storage.get(claim_data["letter_ref"]) == letter_bytes


def test_multipart_authorization_letter_upload(client: TestClient, db_session: Session, redis_conn):
    """Test 8: Submit activation claim using multipart form-data file upload."""
    ts = int(time.time() * 1000)
    inst = _create_test_institution(db_session, f"ACT-MULTI-{ts}", f"Multipart College {ts}")

    client.post(
        "/api/v1/institutions/activation/initiate",
        json={"aicte_id": inst.aicte_id},
    )
    raw_otp = redis_conn.get(f"otp:activation:{inst.official_email.lower()}")
    otp_code = json.loads(raw_otp)["code"]

    resp_verif = client.post(
        "/api/v1/institutions/activation/verify-otp",
        json={"aicte_id": inst.aicte_id, "otp_code": otp_code},
    )
    token = resp_verif.json()["activation_token"]

    file_content = b"%PDF-1.4 Scanned letter of authority with college stamp and seal"

    resp = client.post(
        "/api/v1/institutions/activation/submit-form",
        data={
            "activation_token": token,
            "signatory_name": "Prof. S. K. Gupta",
            "signatory_ref": "DIN-99887766",
        },
        files={"letter_file": ("authority_letter.pdf", file_content, "application/pdf")},
    )
    assert resp.status_code == 201
    claim = resp.json()
    assert claim["status"] == "pending"
    assert claim["signatory_name"] == "Prof. S. K. Gupta"

    storage = get_storage()
    assert storage.exists(claim["letter_ref"]) is True
    assert storage.get(claim["letter_ref"]) == file_content


def test_aicte_officer_review_queue_and_permissions(
    client: TestClient, db_session: Session, redis_conn
):
    """Test 9: AICTE officer queue is protected and viewable only by authorized roles."""
    ts = int(time.time() * 1000)
    inst = _create_test_institution(db_session, f"ACT-REV-{ts}", f"Review College {ts}")

    # Create submission
    client.post("/api/v1/institutions/activation/initiate", json={"aicte_id": inst.aicte_id})
    raw_otp = redis_conn.get(f"otp:activation:{inst.official_email.lower()}")
    otp_code = json.loads(raw_otp)["code"]
    resp_verif = client.post(
        "/api/v1/institutions/activation/verify-otp",
        json={"aicte_id": inst.aicte_id, "otp_code": otp_code},
    )
    token = resp_verif.json()["activation_token"]
    resp_sub = client.post(
        "/api/v1/institutions/activation/submit",
        json={
            "activation_token": token,
            "signatory_name": "Principal Review",
            "signatory_ref": "GOV-OFFICER-001",
            "letter_content_b64": base64.b64encode(b"%PDF-1.4 Review letter").decode("utf-8"),
        },
    )
    request_id = resp_sub.json()["id"]

    # College user cannot access AICTE queue -> 403 Forbidden
    college_user = _create_user(
        db_session, f"college_viewer_{ts}@example.edu", "college_viewer", inst.id
    )
    resp_forbidden = client.get(
        "/api/v1/institutions/activation/requests",
        headers=_auth_header(college_user),
    )
    assert resp_forbidden.status_code == 403

    # AICTE officer can access queue -> 200 OK
    officer = _create_user(db_session, f"officer_act_{ts}@aicte-india.org", "aicte_officer")
    resp_officer = client.get(
        "/api/v1/institutions/activation/requests?status=pending",
        headers=_auth_header(officer),
    )
    assert resp_officer.status_code == 200
    queue = resp_officer.json()
    assert any(item["id"] == request_id for item in queue)

    # Download letter as AICTE officer
    resp_letter = client.get(
        f"/api/v1/institutions/activation/requests/{request_id}/letter",
        headers=_auth_header(officer),
    )
    assert resp_letter.status_code == 200
    assert resp_letter.headers["content-type"] == "application/pdf"
    assert resp_letter.content == b"%PDF-1.4 Review letter"


def test_aicte_officer_approve_creates_primary_admin_with_mfa(
    client: TestClient, db_session: Session, redis_conn
):
    """Test 10: AICTE officer approval activates college and creates primary admin with MFA.

    SPEC.md Section 11:
    4. The request goes into the AICTE approval queue. An officer approves or rejects.
    5. On approval the primary admin account is created with MFA enabled.
    """
    ts = int(time.time() * 1000)
    inst = _create_test_institution(db_session, f"ACT-APPR-{ts}", f"Approved College {ts}")

    # Initiate and submit
    client.post("/api/v1/institutions/activation/initiate", json={"aicte_id": inst.aicte_id})
    raw_otp = redis_conn.get(f"otp:activation:{inst.official_email.lower()}")
    otp_code = json.loads(raw_otp)["code"]
    resp_verif = client.post(
        "/api/v1/institutions/activation/verify-otp",
        json={"aicte_id": inst.aicte_id, "otp_code": otp_code},
    )
    token = resp_verif.json()["activation_token"]
    resp_sub = client.post(
        "/api/v1/institutions/activation/submit",
        json={
            "activation_token": token,
            "signatory_name": "Dr. Approved Head",
            "signatory_ref": "REF-APPROVED-100",
            "letter_content_b64": base64.b64encode(b"%PDF-1.4 Letter of approval").decode("utf-8"),
        },
    )
    request_id = resp_sub.json()["id"]

    officer = _create_user(db_session, f"approver_{ts}@aicte-india.org", "aicte_officer")

    # Approve request
    resp_approve = client.post(
        f"/api/v1/institutions/activation/requests/{request_id}/approve",
        headers=_auth_header(officer),
        json={"notes": "All identity checks and authorization letter verified."},
    )
    assert resp_approve.status_code == 200
    decision = resp_approve.json()
    assert decision["status"] == "approved"
    assert decision["institution_account_status"] == "active"
    assert decision["mfa_enabled"] is True
    assert decision["admin_email"] == inst.official_email
    assert decision["mfa_secret"] is not None
    assert decision["initial_password"] is not None

    # Verify primary admin in database
    admin_user = db_session.scalar(select(User).where(User.email == inst.official_email))
    assert admin_user is not None
    assert admin_user.role == "college_admin"
    assert admin_user.institution_id == inst.id
    assert admin_user.mfa_secret is not None

    # Verify institution account status in database
    db_session.refresh(inst)
    assert inst.account_status == "active"

    # Verify audit log
    audit_entry = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.entity_id == str(request_id),
            AuditLog.action == "institution.activation_approved",
        )
        .order_by(AuditLog.id.desc())
    )
    assert audit_entry is not None
    assert audit_entry.actor_id == str(officer.id)


def test_aicte_officer_reject_resets_account_status(
    client: TestClient, db_session: Session, redis_conn
):
    """Test 11: AICTE officer rejection resets institution account status to not_activated."""
    ts = int(time.time() * 1000)
    inst = _create_test_institution(db_session, f"ACT-REJ-{ts}", f"Rejected College {ts}")

    client.post("/api/v1/institutions/activation/initiate", json={"aicte_id": inst.aicte_id})
    raw_otp = redis_conn.get(f"otp:activation:{inst.official_email.lower()}")
    otp_code = json.loads(raw_otp)["code"]
    resp_verif = client.post(
        "/api/v1/institutions/activation/verify-otp",
        json={"aicte_id": inst.aicte_id, "otp_code": otp_code},
    )
    token = resp_verif.json()["activation_token"]
    resp_sub = client.post(
        "/api/v1/institutions/activation/submit",
        json={
            "activation_token": token,
            "signatory_name": "Prof. Defective",
            "signatory_ref": "REF-DEFECTIVE-99",
            "letter_content_b64": base64.b64encode(b"%PDF-1.4 Defective letter").decode("utf-8"),
        },
    )
    request_id = resp_sub.json()["id"]

    officer = _create_user(db_session, f"rejector_{ts}@aicte-india.org", "aicte_officer")

    # Reject request
    resp_reject = client.post(
        f"/api/v1/institutions/activation/requests/{request_id}/reject",
        headers=_auth_header(officer),
        json={"reason": "Authorization letter lacks official governing council seal."},
    )
    assert resp_reject.status_code == 200
    decision = resp_reject.json()
    assert decision["status"] == "rejected"
    assert decision["institution_account_status"] == "not_activated"

    db_session.refresh(inst)
    assert inst.account_status == "not_activated"

    # Audit log entry check
    audit_entry = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.entity_id == str(request_id),
            AuditLog.action == "institution.activation_rejected",
        )
        .order_by(AuditLog.id.desc())
    )
    assert audit_entry is not None
    assert audit_entry.actor_id == str(officer.id)


def test_non_approved_college_cannot_log_in(client: TestClient, db_session: Session):
    """Test 12: Non-approved / unactivated college accounts cannot log in (HTTP 403 Forbidden).

    TASKS.md T08: 'non-approved college cannot log in'.
    """
    ts = int(time.time() * 1000)
    password = "SecurePassword@123"

    # 1. Institution is not_activated
    inst_not_act = _create_test_institution(
        db_session, f"LOGIN-NOT-{ts}", "Not Activated Inst", account_status="not_activated"
    )
    user_not_act = _create_user(
        db_session,
        f"admin_not_act_{ts}@college.edu",
        role="college_admin",
        institution_id=inst_not_act.id,
        password=password,
    )

    resp_not_act = client.post(
        "/api/v1/auth/login",
        json={"email": user_not_act.email, "password": password},
    )
    assert resp_not_act.status_code == 403
    assert "not activated or approved" in resp_not_act.json()["detail"].lower()

    # 2. Institution is pending_approval
    inst_pending = _create_test_institution(
        db_session, f"LOGIN-PEND-{ts}", "Pending Inst", account_status="pending_approval"
    )
    user_pending = _create_user(
        db_session,
        f"admin_pending_{ts}@college.edu",
        role="college_admin",
        institution_id=inst_pending.id,
        password=password,
    )

    resp_pending = client.post(
        "/api/v1/auth/login",
        json={"email": user_pending.email, "password": password},
    )
    assert resp_pending.status_code == 403
    assert "not activated or approved" in resp_pending.json()["detail"].lower()

    # 3. Once approved/active, login succeeds
    inst_pending.account_status = "active"
    db_session.commit()

    resp_active = client.post(
        "/api/v1/auth/login",
        json={"email": user_pending.email, "password": password},
    )
    assert resp_active.status_code == 200
    assert "access_token" in resp_active.json()


def test_public_activation_status_check(client: TestClient, db_session: Session):
    """Test 13: Public endpoint allows checking activation status without login."""
    ts = int(time.time() * 1000)
    inst = _create_test_institution(
        db_session, f"ACT-STAT-{ts}", "Status Check College", account_status="pending_approval"
    )

    resp = client.get(f"/api/v1/institutions/activation/status/{inst.aicte_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["aicte_id"] == inst.aicte_id
    assert data["institution_name"] == inst.name
    assert data["account_status"] == "pending_approval"
    assert data["approval_status"] == "active"


def test_activation_otp_rate_limiting(client: TestClient, db_session: Session):
    """Test 14: Rate limit triggers HTTP 429 Too Many Requests when threshold exceeded.

    SPEC.md Section 11: 'OTP expires in 5 minutes, max 5 attempts, rate limited.'
    """
    ts = int(time.time() * 1000)
    inst = _create_test_institution(db_session, f"ACT-RATE-{ts}", f"Rate Limit College {ts}")

    # Exhaust rate limit by sending repeated requests
    last_status = None
    for _ in range(12):
        resp = client.post(
            "/api/v1/institutions/activation/initiate",
            json={"aicte_id": inst.aicte_id},
        )
        last_status = resp.status_code
        if last_status == 429:
            break

    assert last_status == 429
    assert "retry-after" in resp.headers
