"""Comprehensive test suite for Verifier Onboarding, Consent Engine, and Minimal Disclosure.

SPEC.md Section 14 & TASKS.md T33:
- Verifier registration with AICTE admin approval.
- Consent requests, student approve or deny, 24-hour expiry, scope limited to minimal fields.
- Single use enforcement.
- Every read audit logged.
- Acceptance criteria:
  1. No data without approved consent.
  2. Expired consent denied.
  3. Verifier never sees DOB, category, or contacts (data minimisation).
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import verify_chain
from app.auth.rate_limiter import reset_rate_limit
from app.auth.security import create_access_token, hash_password
from app.db import get_redis_client
from app.models import (
    AuditLog,
    ConsentRequest,
    Course,
    DevOutbox,
    Institution,
    Student,
    User,
    VerifiedRecord,
    Verifier,
)
from app.verification.router import create_student_token


@pytest.fixture(autouse=True)
def clean_rate_limits():
    """Clear Redis rate limit bucket before and after each test."""
    r = get_redis_client()
    reset_rate_limit(r, "verify")
    reset_rate_limit(r, "login")
    yield
    reset_rate_limit(r, "verify")
    reset_rate_limit(r, "login")


def _setup_test_data(db: Session) -> dict[str, any]:
    """Helper to set up institutions, courses, verified students, and actors for testing."""
    # 1. AICTE Admin
    aicte_admin = db.scalar(select(User).where(User.email == "aicte_admin@aicte-india.org"))
    if not aicte_admin:
        aicte_admin = User(
            email="aicte_admin@aicte-india.org",
            password_hash=hash_password("Demo@12345"),
            role="aicte_admin",
            institution_id=None,
            is_active=True,
        )
        db.add(aicte_admin)

    # 2. Institution & Course
    inst = db.scalar(select(Institution).where(Institution.aicte_id == "1-10000001"))
    if not inst:
        inst = Institution(
            aicte_id="1-10000001",
            name="Pune Institute of Advanced Engineering & Technology",
            state="Maharashtra",
            district="Pune",
            address="Shivajinagar, Pune 411005",
            official_email="contact@piaet-pune.edu.in",
            official_phone="+912025507000",
            head_name="Dr. Arvind Joshi",
            affiliating_university="Savitribai Phule Pune University",
            approval_status="active",
            account_status="active",
        )
        db.add(inst)
        db.flush()

    course = db.scalar(select(Course).where(Course.institution_id == inst.id))
    if not course:
        course = Course(
            institution_id=inst.id,
            name="Computer Engineering",
            level="UG",
            branch="Computer Science & Engineering",
            duration_years=4,
            supernumerary_allowed=True,
        )
        db.add(course)
        db.flush()

    # 3. Test Student
    test_apaar = "999988887777"
    student = db.scalar(select(Student).where(Student.apaar_id == test_apaar))
    if not student:
        student = Student(
            institution_id=inst.id,
            course_id=course.id,
            academic_year="2025-26",
            apaar_id=test_apaar,
            name="Rohan V. Kulkarni",
            dob_encrypted="gAAAAABtestdobencrypteddummyvalue",
            gender="Male",
            enrolment_no="EN20259999",
            admission_date=datetime.now(UTC).date(),
            admission_mode="State counselling",
            seat_type="Regular",
            reservation_category="OBC",
            nri=False,
            oci=False,
            foreign_national=False,
            fn_country=None,
            status="verified",
            is_locked=True,
            source="form",
        )
        db.add(student)
        db.flush()

    # 4. Verified Record for Student
    vr = db.scalar(select(VerifiedRecord).where(VerifiedRecord.student_id == student.id))
    if not vr:
        vr = VerifiedRecord(
            student_id=student.id,
            verification_id="VR-2025-999988887777",
            signature="a" * 128,
            status="active",
            issued_at=datetime.now(UTC),
        )
        db.add(vr)
        db.flush()

    # 5. Approved Verifier A
    verifier_a_user = db.scalar(select(User).where(User.email == "verifier_a@enterprise.com"))
    if not verifier_a_user:
        verifier_a_user = User(
            email="verifier_a@enterprise.com",
            password_hash=hash_password("Verifier@123"),
            role="verifier",
            institution_id=None,
            is_active=True,
        )
        db.add(verifier_a_user)
        db.flush()

    verifier_a = db.scalar(select(Verifier).where(Verifier.contact == "verifier_a@enterprise.com"))
    if not verifier_a:
        verifier_a = Verifier(
            org_name="Enterprise Verification Corp",
            org_type="employer",
            contact="verifier_a@enterprise.com",
            status="approved",
        )
        db.add(verifier_a)
        db.flush()

    # 6. Approved Verifier B (for cross-organisation testing)
    verifier_b_user = db.scalar(select(User).where(User.email == "verifier_b@competitor.com"))
    if not verifier_b_user:
        verifier_b_user = User(
            email="verifier_b@competitor.com",
            password_hash=hash_password("Verifier@123"),
            role="verifier",
            institution_id=None,
            is_active=True,
        )
        db.add(verifier_b_user)
        db.flush()

    verifier_b = db.scalar(select(Verifier).where(Verifier.contact == "verifier_b@competitor.com"))
    if not verifier_b:
        verifier_b = Verifier(
            org_name="Competitor Backgrounds Ltd",
            org_type="employer",
            contact="verifier_b@competitor.com",
            status="approved",
        )
        db.add(verifier_b)
        db.flush()

    db.commit()

    return {
        "admin": aicte_admin,
        "inst": inst,
        "course": course,
        "student": student,
        "vr": vr,
        "verifier_a_user": verifier_a_user,
        "verifier_a": verifier_a,
        "verifier_b_user": verifier_b_user,
        "verifier_b": verifier_b,
        "apaar_id": test_apaar,
    }


def test_verifier_registration_creates_pending_organisation(
    client: TestClient, db_session: Session
):
    """Test verifier self-registration: defaults to pending, creates inactive user."""
    reg_payload = {
        "org_name": "Infosys Talent Verification Services",
        "org_type": "employer",
        "contact": "hr-verifications@infosys-talent.com",
        "password": "SecurePassword123!",
    }

    # 1. Register new verifier
    resp = client.post("/api/v1/verification/verifiers/register", json=reg_payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["org_name"] == reg_payload["org_name"]
    assert data["contact"] == reg_payload["contact"].lower()
    assert data["status"] == "pending"

    # 2. Verify associated user account is created inactive
    user = db_session.scalar(select(User).where(User.email == reg_payload["contact"].lower()))
    assert user is not None
    assert user.role == "verifier"
    assert user.is_active is False

    # 3. Inactive verifier cannot log in
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": reg_payload["contact"], "password": reg_payload["password"]},
    )
    assert login_resp.status_code == 403
    detail_msg = login_resp.json()["detail"].lower()
    assert "inactive" in detail_msg or "deactivated" in detail_msg

    # 4. Duplicate registration rejected with 409 Conflict
    dup_resp = client.post("/api/v1/verification/verifiers/register", json=reg_payload)
    assert dup_resp.status_code == 409


def test_aicte_admin_approves_and_revokes_verifier(client: TestClient, db_session: Session):
    """AICTE admin lists, approves, and revokes verifier organisations."""
    context = _setup_test_data(db_session)
    admin_token = create_access_token(
        user_id=context["admin"].id, email=context["admin"].email, role="aicte_admin"
    )

    # 1. Register a pending verifier
    email = "recruiters@wipro-hiring.com"
    client.post(
        "/api/v1/verification/verifiers/register",
        json={
            "org_name": "Wipro Background Checks",
            "org_type": "employer",
            "contact": email,
            "password": "Password1234!",
        },
    )
    verifier = db_session.scalar(select(Verifier).where(Verifier.contact == email))
    assert verifier.status == "pending"

    # 2. AICTE Admin lists verifiers with filter
    list_resp = client.get(
        "/api/v1/verification/verifiers?status=pending",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    pending_ids = [item["id"] for item in list_resp.json()["items"]]
    assert verifier.id in pending_ids

    # 3. Non-admin (verifier) receives 403 Forbidden attempting to approve
    verifier_token = create_access_token(
        user_id=context["verifier_a_user"].id,
        email=context["verifier_a_user"].email,
        role="verifier",
    )
    unauth_resp = client.patch(
        f"/api/v1/verification/verifiers/{verifier.id}/approve",
        headers={"Authorization": f"Bearer {verifier_token}"},
    )
    assert unauth_resp.status_code == 403

    # 4. AICTE Admin approves verifier
    approve_resp = client.patch(
        f"/api/v1/verification/verifiers/{verifier.id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "approved", "note": "Verified statutory CIN and corporate credentials"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    # 5. User account is now active and can log in
    db_session.expire_all()
    user = db_session.scalar(select(User).where(User.email == email))
    assert user.is_active is True

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password1234!"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    # 6. AICTE Admin revokes verifier
    revoke_resp = client.patch(
        f"/api/v1/verification/verifiers/{verifier.id}/revoke",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "revoked", "note": "Organisation license suspended"},
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["status"] == "revoked"

    db_session.expire_all()
    user = db_session.scalar(select(User).where(User.email == email))
    assert user.is_active is False


def test_unapproved_verifier_cannot_create_consent_request(client: TestClient, db_session: Session):
    """Verifiers with non-approved status cannot initiate consent requests."""
    context = _setup_test_data(db_session)
    email = "pending_agency@verifyme.com"
    client.post(
        "/api/v1/verification/verifiers/register",
        json={
            "org_name": "Pending Verification Agency",
            "org_type": "employer",
            "contact": email,
            "password": "Password1234!",
        },
    )
    user = db_session.scalar(select(User).where(User.email == email))
    # Test 1: Inactive user gets 403 Forbidden
    token = create_access_token(user_id=user.id, email=email, role="verifier")
    resp_inactive = client.post(
        "/api/v1/verification/consent-requests",
        headers={"Authorization": f"Bearer {token}"},
        json={"apaar_id": context["apaar_id"], "purpose": "Employment check"},
    )
    assert resp_inactive.status_code == 403

    # Test 2: Active user with unapproved verifier organisation gets 403 Forbidden
    user.is_active = True
    db_session.flush()
    resp_unapproved = client.post(
        "/api/v1/verification/consent-requests",
        headers={"Authorization": f"Bearer {token}"},
        json={"apaar_id": context["apaar_id"], "purpose": "Employment check"},
    )
    assert resp_unapproved.status_code == 403
    assert "approval is required" in resp_unapproved.json()["detail"].lower()


def test_verifier_creates_consent_request_with_24h_expiry_and_minimal_scope(
    client: TestClient, db_session: Session
):
    """Approved verifier creates consent request with 24-hour default TTL and minimal scope."""
    context = _setup_test_data(db_session)
    token = create_access_token(
        user_id=context["verifier_a_user"].id,
        email=context["verifier_a_user"].email,
        role="verifier",
    )

    resp = client.post(
        "/api/v1/verification/consent-requests",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "apaar_id": context["apaar_id"],
            "purpose": "Employment credential verification for Cloud Software Engineer role",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["apaar_id"] == context["apaar_id"]
    assert data["status"] == "pending"
    assert data["verifier_name"] == context["verifier_a"].org_name
    # Scope strictly minimal
    assert data["scope_fields"] == ["institution", "course", "years", "status", "verification_id"]

    # 24-hour expiration verification
    req_at = datetime.fromisoformat(data["requested_at"])
    exp_at = datetime.fromisoformat(data["expires_at"])
    delta = exp_at - req_at
    assert abs(delta.total_seconds() - 86400) < 60  # Within 1 minute of 24 hours

    # Verify mock OTP sent to student outbox
    outbox = db_session.scalar(
        select(DevOutbox)
        .where(DevOutbox.recipient == context["apaar_id"])
        .order_by(DevOutbox.id.desc())
    )
    assert outbox is not None
    assert "consent request" in outbox.body.lower()


def test_student_otp_flow_and_academic_records_listing(client: TestClient, db_session: Session):
    """Student logs into student portal via mock OTP and lists institutional records."""
    context = _setup_test_data(db_session)
    apaar_id = context["apaar_id"]

    # 1. Initiate student OTP
    otp_init = client.post(
        "/api/v1/verification/student/otp/send",
        json={"apaar_id": apaar_id},
    )
    assert otp_init.status_code == 200
    assert otp_init.json()["status"] == "sent"

    # 2. Fetch OTP from dev_outbox
    outbox_entry = db_session.scalar(
        select(DevOutbox)
        .where(DevOutbox.recipient == apaar_id)
        .order_by(DevOutbox.id.desc())
    )
    assert outbox_entry is not None
    # Extract 6-digit OTP from message body
    import re
    otp_match = re.search(r"\b(\d{6})\b", outbox_entry.body)
    assert otp_match is not None
    otp_code = otp_match.group(1)

    # 3. Verify OTP and receive student session token
    verify_resp = client.post(
        "/api/v1/verification/student/otp/verify",
        json={"apaar_id": apaar_id, "otp": otp_code},
    )
    assert verify_resp.status_code == 200
    token_data = verify_resp.json()
    assert "access_token" in token_data
    student_token = token_data["access_token"]

    # 4. Student views colleges holding their academic records
    records_resp = client.get(
        "/api/v1/verification/student/records",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert records_resp.status_code == 200
    records = records_resp.json()["records"]
    assert len(records) >= 1
    rec = records[0]
    assert rec["institution_name"] == context["inst"].name
    assert rec["course_name"] == context["course"].name
    assert rec["verification_id"] == context["vr"].verification_id


def test_no_data_without_approved_consent(client: TestClient, db_session: Session):
    """Verifier CANNOT read student data when consent is pending or denied."""
    context = _setup_test_data(db_session)
    verifier_token = create_access_token(
        user_id=context["verifier_a_user"].id,
        email=context["verifier_a_user"].email,
        role="verifier",
    )
    student_token = create_student_token(apaar_id=context["apaar_id"])

    # 1. Create consent request
    create_resp = client.post(
        "/api/v1/verification/consent-requests",
        headers={"Authorization": f"Bearer {verifier_token}"},
        json={"apaar_id": context["apaar_id"], "purpose": "Background check"},
    )
    req_id = create_resp.json()["id"]

    # 2. Verifier tries to read record while consent is STILL PENDING -> 403 Forbidden
    read_pending = client.get(
        f"/api/v1/verification/consent-requests/{req_id}/record",
        headers={"Authorization": f"Bearer {verifier_token}"},
    )
    assert read_pending.status_code == 403
    assert "pending" in read_pending.json()["detail"].lower()

    # 3. Student DENIES consent
    deny_resp = client.post(
        f"/api/v1/verification/student/consent-requests/{req_id}/decide",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"decision": "denied"},
    )
    assert deny_resp.status_code == 200
    assert deny_resp.json()["status"] == "denied"

    # 4. Verifier tries to read record after DENIAL -> 403 Forbidden
    read_denied = client.get(
        f"/api/v1/verification/consent-requests/{req_id}/record",
        headers={"Authorization": f"Bearer {verifier_token}"},
    )
    assert read_denied.status_code == 403
    assert "denied" in read_denied.json()["detail"].lower()


def test_expired_consent_denied(client: TestClient, db_session: Session):
    """Expired consent request CANNOT be approved or accessed (Hard Acceptance Criteria)."""
    context = _setup_test_data(db_session)
    verifier_token = create_access_token(
        user_id=context["verifier_a_user"].id,
        email=context["verifier_a_user"].email,
        role="verifier",
    )
    student_token = create_student_token(apaar_id=context["apaar_id"])

    # Create consent request with expired timestamp (25 hours ago)
    now = datetime.now(UTC)
    cr = ConsentRequest(
        verifier_id=context["verifier_a"].id,
        apaar_id=context["apaar_id"],
        scope_json={"fields": ["institution", "course", "years", "status"], "used": False},
        status="pending",
        requested_at=now - timedelta(hours=26),
        expires_at=now - timedelta(hours=2),
    )
    db_session.add(cr)
    db_session.commit()
    db_session.refresh(cr)

    # 1. Student attempting to approve expired consent -> 400 Bad Request
    approve_expired = client.post(
        f"/api/v1/verification/student/consent-requests/{cr.id}/decide",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"decision": "approved"},
    )
    assert approve_expired.status_code == 400
    assert "expired" in approve_expired.json()["detail"].lower()

    # 2. Verifier attempting to read expired request -> 403 Forbidden
    read_expired = client.get(
        f"/api/v1/verification/consent-requests/{cr.id}/record",
        headers={"Authorization": f"Bearer {verifier_token}"},
    )
    assert read_expired.status_code == 403
    assert "expired" in read_expired.json()["detail"].lower()


def test_single_use_consent_enforcement(client: TestClient, db_session: Session):
    """Approved consent can only be used ONCE. Second read is rejected (Single Use Policy)."""
    context = _setup_test_data(db_session)
    verifier_token = create_access_token(
        user_id=context["verifier_a_user"].id,
        email=context["verifier_a_user"].email,
        role="verifier",
    )
    student_token = create_student_token(apaar_id=context["apaar_id"])

    # 1. Create consent request
    create_resp = client.post(
        "/api/v1/verification/consent-requests",
        headers={"Authorization": f"Bearer {verifier_token}"},
        json={"apaar_id": context["apaar_id"], "purpose": "Pre-employment verification"},
    )
    req_id = create_resp.json()["id"]

    # 2. Student APPROVES consent
    client.post(
        f"/api/v1/verification/student/consent-requests/{req_id}/decide",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"decision": "approved"},
    )

    # 3. First read by verifier SUCCEEDS (200 OK)
    first_read = client.get(
        f"/api/v1/verification/consent-requests/{req_id}/record",
        headers={"Authorization": f"Bearer {verifier_token}"},
    )
    assert first_read.status_code == 200
    assert first_read.json()["verified"] is True

    # 4. Second read of the SAME consent request is REJECTED with 403 Forbidden (Single Use)
    second_read = client.get(
        f"/api/v1/verification/consent-requests/{req_id}/record",
        headers={"Authorization": f"Bearer {verifier_token}"},
    )
    assert second_read.status_code == 403
    assert "already been used" in second_read.json()["detail"].lower()


def test_verifier_never_sees_dob_category_or_contacts(client: TestClient, db_session: Session):
    """Verifier response strictly adheres to DPDP Data Minimisation.

    SPEC.md Section 14:
    On approval verifier sees only: institution, course, years, status, verification ID.
    NEVER DOB, category or contact data.
    """
    context = _setup_test_data(db_session)
    verifier_token = create_access_token(
        user_id=context["verifier_a_user"].id,
        email=context["verifier_a_user"].email,
        role="verifier",
    )
    student_token = create_student_token(apaar_id=context["apaar_id"])

    # Create & approve consent
    create_resp = client.post(
        "/api/v1/verification/consent-requests",
        headers={"Authorization": f"Bearer {verifier_token}"},
        json={"apaar_id": context["apaar_id"], "purpose": "Employment verification"},
    )
    req_id = create_resp.json()["id"]
    client.post(
        f"/api/v1/verification/student/consent-requests/{req_id}/decide",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"decision": "approved"},
    )

    # Verifier reads consented record
    read_resp = client.get(
        f"/api/v1/verification/consent-requests/{req_id}/record",
        headers={"Authorization": f"Bearer {verifier_token}"},
    )
    assert read_resp.status_code == 200
    data = read_resp.json()

    # 1. Allowed minimal fields MUST be present
    assert "institution" in data
    assert "course" in data
    assert "years" in data
    assert "status" in data
    assert "verification_id" in data
    assert data["verified_by"] == "AICTE Central Repository"
    assert data["verified"] is True

    # 2. FORBIDDEN personal & contact fields MUST NEVER BE PRESENT
    forbidden_keys = [
        "dob",
        "dob_encrypted",
        "date_of_birth",
        "birth_date",
        "reservation_category",
        "category",
        "gender",
        "nri",
        "oci",
        "foreign_national",
        "fn_country",
        "enrolment_no",
        "official_email",
        "official_phone",
        "email",
        "phone",
        "contact",
        "address",
        "signatory",
        "parents",
    ]
    for key in forbidden_keys:
        assert key not in data, (
            f"Privacy violation! Key '{key}' was leaked in verifier response: {data}"
        )


def test_cross_organisation_consent_isolation(client: TestClient, db_session: Session):
    """Verifier B cannot access records or consent requests created for Verifier A."""
    context = _setup_test_data(db_session)
    verifier_a_token = create_access_token(
        user_id=context["verifier_a_user"].id,
        email=context["verifier_a_user"].email,
        role="verifier",
    )
    verifier_b_token = create_access_token(
        user_id=context["verifier_b_user"].id,
        email=context["verifier_b_user"].email,
        role="verifier",
    )
    student_token = create_student_token(apaar_id=context["apaar_id"])

    # Verifier A creates consent and student approves it
    create_resp = client.post(
        "/api/v1/verification/consent-requests",
        headers={"Authorization": f"Bearer {verifier_a_token}"},
        json={"apaar_id": context["apaar_id"], "purpose": "Verifier A check"},
    )
    req_id = create_resp.json()["id"]
    client.post(
        f"/api/v1/verification/student/consent-requests/{req_id}/decide",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"decision": "approved"},
    )

    # Verifier B tries to read Verifier A's consent request -> 403 Forbidden
    cross_read = client.get(
        f"/api/v1/verification/consent-requests/{req_id}/record",
        headers={"Authorization": f"Bearer {verifier_b_token}"},
    )
    assert cross_read.status_code == 403
    assert "another organisation" in cross_read.json()["detail"].lower()


def test_audit_logging_and_hash_chain_for_verifier_operations(
    client: TestClient, db_session: Session
):
    """Every verifier read and state change creates a tamper-evident audit log entry."""
    context = _setup_test_data(db_session)
    verifier_token = create_access_token(
        user_id=context["verifier_a_user"].id,
        email=context["verifier_a_user"].email,
        role="verifier",
    )
    student_token = create_student_token(apaar_id=context["apaar_id"])

    # Perform full consent + read cycle
    create_resp = client.post(
        "/api/v1/verification/consent-requests",
        headers={"Authorization": f"Bearer {verifier_token}"},
        json={"apaar_id": context["apaar_id"], "purpose": "Audit trail test verification"},
    )
    req_id = create_resp.json()["id"]

    client.post(
        f"/api/v1/verification/student/consent-requests/{req_id}/decide",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"decision": "approved"},
    )

    read_resp = client.get(
        f"/api/v1/verification/consent-requests/{req_id}/record",
        headers={"Authorization": f"Bearer {verifier_token}"},
    )
    assert read_resp.status_code == 200, f"Failed read: {read_resp.status_code} {read_resp.text}"

    # Verify audit entries exist for all actions
    actions = list(
        db_session.scalars(
            select(AuditLog.action).where(
                AuditLog.action.in_([
                    "consent.request",
                    "consent.approved",
                    "verifier.read_student_data",
                ])
            )
        ).all()
    )
    assert "consent.request" in actions
    assert "consent.approved" in actions
    assert "verifier.read_student_data" in actions

    # Verify cryptographic hash chain integrity
    chain_result = verify_chain(db_session)
    assert chain_result["verified"] is True
    assert chain_result["first_broken_id"] is None
