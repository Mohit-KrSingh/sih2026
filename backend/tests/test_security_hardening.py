"""Comprehensive security hardening tests.

SPEC.md Section 16 & TASKS.md T37:
- DOB encryption at rest (Fernet key, ciphertext verification in database).
- Security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy).
- Strict CORS configuration (whitelisted origins, methods, headers).
- Request body size limits (reject payloads > 15MB with HTTP 413).
- Log masking (automatic redaction of 12-digit APAAR IDs in logs).
- Dependency audit verification.
- Security tests:
  - IDOR on every college endpoint.
  - Verifier access without consent.
  - Expired and tampered tokens.
  - Role escalation attempts across college and AICTE roles.
"""

import io
import logging
from datetime import UTC, date, datetime, timedelta

import jwt
import pytest
from cryptography.fernet import Fernet, InvalidToken
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.schemas import Role
from app.auth.security import create_access_token, create_refresh_token, decrypt_dob, encrypt_dob
from app.config import get_settings
from app.logging_config import ApaarIdMaskingFilter, mask_apaar_string
from app.models import ConsentRequest, Course, Institution, Student, User, ValidationFlag, Verifier


def _setup_security_fixtures(db: Session):
    """Create test institutions, courses, users, and students for security assertions."""
    # College Alpha (1-SEC-A)
    inst_a = Institution(
        aicte_id="1-SEC-A",
        name="Alpha Security Institute",
        state="Maharashtra",
        district="Pune",
        address="123 Alpha Road",
        official_email="contact@alpha.edu",
        official_phone="+919876543210",
        head_name="Dr. Alpha Head",
        affiliating_university="Alpha Tech University",
        approval_status="active",
        account_status="active",
    )
    # College Beta (1-SEC-B)
    inst_b = Institution(
        aicte_id="1-SEC-B",
        name="Beta Security Institute",
        state="Karnataka",
        district="Bengaluru",
        address="456 Beta Road",
        official_email="contact@beta.edu",
        official_phone="+919876543211",
        head_name="Dr. Beta Head",
        affiliating_university="Beta Tech University",
        approval_status="active",
        account_status="active",
    )
    db.add_all([inst_a, inst_b])
    db.commit()
    db.refresh(inst_a)
    db.refresh(inst_b)

    course_a = Course(
        institution_id=inst_a.id,
        name="Computer Science and Engineering",
        level="UG",
        branch="Computer Science & Engineering",
        duration_years=4,
        supernumerary_allowed=True,
    )
    course_b = Course(
        institution_id=inst_b.id,
        name="Electronics and Communication Engineering",
        level="UG",
        branch="Electronics & Communication",
        duration_years=4,
        supernumerary_allowed=True,
    )
    db.add_all([course_a, course_b])
    db.commit()
    db.refresh(course_a)
    db.refresh(course_b)

    # Users for College A
    admin_a = User(
        email="admin@alpha.sec.edu",
        password_hash="fake_hash",
        role=Role.COLLEGE_ADMIN.value,
        institution_id=inst_a.id,
        is_active=True,
    )
    staff_a = User(
        email="staff@alpha.sec.edu",
        password_hash="fake_hash",
        role=Role.COLLEGE_STAFF.value,
        institution_id=inst_a.id,
        is_active=True,
    )
    viewer_a = User(
        email="viewer@alpha.sec.edu",
        password_hash="fake_hash",
        role=Role.COLLEGE_VIEWER.value,
        institution_id=inst_a.id,
        is_active=True,
    )
    # User for College B
    admin_b = User(
        email="admin@beta.sec.edu",
        password_hash="fake_hash",
        role=Role.COLLEGE_ADMIN.value,
        institution_id=inst_b.id,
        is_active=True,
    )
    # Global AICTE User
    user_aicte_admin = User(
        email="sec_aicte_admin@aicte-india.org",
        password_hash="fake_hash",
        role=Role.AICTE_ADMIN.value,
        institution_id=None,
        is_active=True,
    )
    # Verifier User and Verifier Org
    verifier_org = Verifier(
        org_name="BGV Security Corp",
        org_type="employer",
        contact="sec_auditor@bgv-company.com",
        status="approved",
    )
    db.add(verifier_org)
    db.commit()
    db.refresh(verifier_org)

    user_verifier = User(
        email="sec_auditor@bgv-company.com",
        password_hash="fake_hash",
        role=Role.VERIFIER.value,
        institution_id=None,
        is_active=True,
    )

    db.add_all([admin_a, staff_a, viewer_a, admin_b, user_aicte_admin, user_verifier])
    db.commit()
    for u in [admin_a, staff_a, viewer_a, admin_b, user_aicte_admin, user_verifier]:
        db.refresh(u)

    # Student in College A
    dob_secret = date(2003, 4, 15)
    student_a = Student(
        institution_id=inst_a.id,
        course_id=course_a.id,
        academic_year="2026-27",
        apaar_id="112233445566",
        name="Alpha Student",
        dob_encrypted=encrypt_dob(dob_secret),
        gender="Male",
        enrolment_no="EN26-ALPHA-001",
        admission_date=date(2026, 7, 10),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        status="draft",
        is_locked=False,
    )
    # Student in College B
    student_b = Student(
        institution_id=inst_b.id,
        course_id=course_b.id,
        academic_year="2026-27",
        apaar_id="998877665544",
        name="Beta Student",
        dob_encrypted=encrypt_dob(date(2003, 8, 20)),
        gender="Female",
        enrolment_no="EN26-BETA-001",
        admission_date=date(2026, 7, 12),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="OBC",
        status="draft",
        is_locked=False,
    )
    db.add_all([student_a, student_b])
    db.commit()
    db.refresh(student_a)
    db.refresh(student_b)

    # Validation flag for College A for justification permission tests
    flag_a = ValidationFlag(
        course_id=course_a.id,
        rule_code="INTAKE_EXCEEDED",
        level="exception",
        message="Intake exceeded test flag",
        requires_justification=True,
        status="open",
    )
    db.add(flag_a)
    db.commit()
    db.refresh(flag_a)

    tokens = {
        "admin_a": create_access_token(admin_a.id, admin_a.email, admin_a.role, inst_a.id),
        "staff_a": create_access_token(staff_a.id, staff_a.email, staff_a.role, inst_a.id),
        "viewer_a": create_access_token(viewer_a.id, viewer_a.email, viewer_a.role, inst_a.id),
        "admin_b": create_access_token(admin_b.id, admin_b.email, admin_b.role, inst_b.id),
        "aicte": create_access_token(
            user_aicte_admin.id, user_aicte_admin.email, user_aicte_admin.role, None
        ),
        "verifier": create_access_token(
            user_verifier.id, user_verifier.email, user_verifier.role, None
        ),
    }

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "course_a": course_a,
        "course_b": course_b,
        "student_a": student_a,
        "student_b": student_b,
        "flag_a": flag_a,
        "verifier_org": verifier_org,
        "users": {
            "admin_a": admin_a,
            "staff_a": staff_a,
            "viewer_a": viewer_a,
            "admin_b": admin_b,
            "aicte": user_aicte_admin,
            "verifier": user_verifier,
        },
        "tokens": tokens,
    }


# ==============================================================================
# 1. Security Headers & Strict CORS Tests
# ==============================================================================

def test_security_headers_present_on_all_responses(client: TestClient):
    """Verify that every API response includes mandatory security headers per SPEC 16."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert "max-age=31536000" in headers.get("strict-transport-security", "")
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers.get("permissions-policy", "")
    assert "frame-ancestors 'none'" in headers.get("content-security-policy", "")


def test_strict_cors_whitelisted_and_rejected_origins(client: TestClient):
    """Strict CORS: Allowed frontend origins receive CORS headers; unauthorized origins do not."""
    settings = get_settings()

    # 1. Allowed origin gets Access-Control-Allow-Origin
    resp_allowed = client.get(
        "/api/v1/health",
        headers={"Origin": settings.FRONTEND_URL},
    )
    assert resp_allowed.status_code == 200
    assert resp_allowed.headers.get("access-control-allow-origin") == settings.FRONTEND_URL
    assert resp_allowed.headers.get("access-control-allow-credentials") == "true"

    # 2. Localhost 5173 is also whitelisted
    resp_local = client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert resp_local.status_code == 200
    assert resp_local.headers.get("access-control-allow-origin") == "http://localhost:5173"

    # 3. Disallowed origin does NOT receive Access-Control-Allow-Origin
    resp_disallowed = client.get(
        "/api/v1/health",
        headers={"Origin": "https://malicious-attacker-domain.com"},
    )
    assert resp_disallowed.status_code == 200
    assert "access-control-allow-origin" not in resp_disallowed.headers

    # 4. CORS preflight OPTIONS request
    resp_options = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert resp_options.status_code == 200
    assert resp_options.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ==============================================================================
# 2. Request Body Size Limits Tests
# ==============================================================================

def test_request_body_size_limits_rejects_payload_too_large(client: TestClient):
    """Enforce request body size limits returning HTTP 413 Payload Too Large."""
    # 1. Normal small payload succeeds
    resp_ok = client.post("/api/v1/health", json={"test": "small"})
    # (health is GET, but 405 Method Not Allowed proves it passed size limiter)
    assert resp_ok.status_code in (200, 405)

    # 2. Request with Content-Length exceeding 15MB is rejected with 413
    resp_oversized = client.post(
        "/api/v1/health",
        headers={"Content-Length": str(20 * 1024 * 1024)},  # 20 MB
    )
    assert resp_oversized.status_code == 413
    assert "Request entity too large" in resp_oversized.json()["detail"]
    assert "15MB" in resp_oversized.json()["detail"]


# ==============================================================================
# 3. Date of Birth (DOB) Encryption at Rest Tests
# ==============================================================================

def test_dob_encryption_at_rest_and_key_isolation(db_session: Session):
    """Verify that DOB is stored encrypted at rest using Fernet and never in plaintext."""
    test_dob = date(2004, 3, 25)
    encrypted_ciphertext = encrypt_dob(test_dob)

    # Ciphertext must not contain the plaintext ISO date string
    assert "2004-03-25" not in encrypted_ciphertext
    assert encrypted_ciphertext.startswith("gAAAAA")  # Fernet signature token prefix

    # Decrypting with authorized key works
    decrypted_date = decrypt_dob(encrypted_ciphertext)
    assert decrypted_date == test_dob

    # Decrypting with an incorrect Fernet key raises InvalidToken
    wrong_key = Fernet.generate_key()
    wrong_fernet = Fernet(wrong_key)
    with pytest.raises(InvalidToken):
        wrong_fernet.decrypt(encrypted_ciphertext.encode())

    # Verify directly from raw database query
    inst = Institution(
        aicte_id="1-DOB-TEST",
        name="DOB Test College",
        state="Delhi",
        district="New Delhi",
        address="1 Test St",
        official_email="dob@test.edu",
        official_phone="+919876543299",
        head_name="Principal Test",
        affiliating_university="Delhi Tech",
        approval_status="active",
        account_status="active",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    st = Student(
        institution_id=inst.id,
        academic_year="2026-27",
        apaar_id="888877776666",
        name="Encrypted Student",
        dob_encrypted=encrypt_dob(test_dob),
        gender="Female",
        enrolment_no="EN26-DOB-01",
        admission_date=date(2026, 7, 10),
        admission_mode="Direct admission",
        seat_type="Regular",
        reservation_category="General",
        status="draft",
        is_locked=False,
    )
    db_session.add(st)
    db_session.commit()
    db_session.refresh(st)

    # Execute raw SQL query bypassing ORM to inspect bytes stored at rest
    row = db_session.execute(
        text("SELECT dob_encrypted FROM students WHERE id = :sid"),
        {"sid": st.id},
    ).fetchone()

    assert row is not None
    raw_db_value = row[0]
    assert "2004-03-25" not in raw_db_value
    assert raw_db_value.startswith("gAAAAA")


# ==============================================================================
# 4. APAAR ID Log Masking Tests
# ==============================================================================

def test_apaar_id_log_masking():
    """Verify that APAAR IDs are masked in log records and formatted messages."""
    # 1. Test string masking utility directly
    assert mask_apaar_string("APAAR 123456789012 submitted") == "APAAR ********9012 submitted"
    assert mask_apaar_string("Formatted 1234 5678 9012 id") == "Formatted ********9012 id"
    assert mask_apaar_string("Hyphenated 1234-5678-9012 id") == "Hyphenated ********9012 id"

    # 2. Test logging filter attached to a logger
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("test_security_logger")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.addFilter(ApaarIdMaskingFilter())

    logger.info("Processing student with APAAR %s for college %d", "999988887777", 101)
    output = stream.getvalue()
    assert "999988887777" not in output
    assert "********7777" in output


# ==============================================================================
# 5. IDOR on Every College Endpoint
# ==============================================================================

def test_idor_on_every_college_endpoint(client: TestClient, db_session: Session):
    """Enforce strict institutional scoping: College A cannot access ANY of College B routes."""
    fixtures = _setup_security_fixtures(db_session)
    inst_a = fixtures["inst_a"]
    inst_b = fixtures["inst_b"]
    course_b = fixtures["course_b"]
    token_a = fixtures["tokens"]["admin_a"]  # College A Admin token
    b_id = inst_b.id
    student_b_id = fixtures["student_b"].id

    auth_headers = {"Authorization": f"Bearer {token_a}"}

    # List of tuples: (HTTP Method, Route URL, JSON Body)
    college_b_endpoints = [
        # Institution endpoints
        ("GET", f"/api/v1/institutions/{b_id}", None),
        ("GET", f"/api/v1/institutions/{b_id}/courses", None),
        ("GET", f"/api/v1/institutions/{b_id}/courses/{course_b.id}/intake", None),
        ("GET", f"/api/v1/institutions/{b_id}/staff", None),
        (
            "POST",
            f"/api/v1/institutions/{b_id}/staff",
            {"name": "Hacker", "email": "h@b.edu", "role": "college_staff"},
        ),
        (
            "PATCH",
            f"/api/v1/institutions/{b_id}/staff/999",
            {"role": "college_staff", "is_active": False},
        ),
        ("DELETE", f"/api/v1/institutions/{b_id}/staff/999", None),
        ("GET", f"/api/v1/institutions/{b_id}/correction-requests", None),
        (
            "POST",
            f"/api/v1/institutions/{b_id}/correction-requests",
            {
                "course_id": course_b.id,
                "field_name": "intake",
                "requested_value": "100",
                "reason": "hack",
            },
        ),
        # Student management endpoints
        ("GET", f"/api/v1/institutions/{b_id}/students", None),
        (
            "POST",
            f"/api/v1/institutions/{b_id}/students",
            {
                "academic_year": "2026-27",
                "course_id": course_b.id,
                "apaar_id": "123412341234",
                "name": "Rogue",
                "dob": "2002-01-01",
                "gender": "Male",
                "enrolment_no": "ROGUE-01",
                "admission_date": "2026-07-01",
                "admission_mode": "Management quota",
                "seat_type": "Regular",
                "reservation_category": "General",
            },
        ),
        ("GET", f"/api/v1/institutions/{b_id}/students/{student_b_id}", None),
        (
            "PUT",
            f"/api/v1/institutions/{b_id}/students/{student_b_id}",
            {
                "academic_year": "2026-27",
                "course_id": course_b.id,
                "apaar_id": "998877665544",
                "name": "Hacked Name",
                "dob": "2003-08-20",
                "gender": "Female",
                "enrolment_no": "EN26-BETA-001",
                "admission_date": "2026-07-12",
                "admission_mode": "State counselling",
                "seat_type": "Regular",
                "reservation_category": "OBC",
            },
        ),
        ("DELETE", f"/api/v1/institutions/{b_id}/students/{student_b_id}", None),
        ("GET", f"/api/v1/institutions/{b_id}/students/uploads", None),
        ("GET", f"/api/v1/institutions/{b_id}/students/upload/template", None),
        ("GET", f"/api/v1/institutions/{b_id}/flags", None),
        (
            "POST",
            f"/api/v1/institutions/{b_id}/flags/1/justifications",
            {"text": "Rogue explanation"},
        ),
        # API Keys endpoints
        ("GET", f"/api/v1/institutions/{b_id}/api-keys", None),
        (
            "POST",
            f"/api/v1/institutions/{b_id}/api-keys",
            {"name": "Rogue Key", "scopes": ["students:write"]},
        ),
        ("POST", f"/api/v1/institutions/{b_id}/api-keys/1/rotate", None),
        ("POST", f"/api/v1/institutions/{b_id}/api-keys/1/revoke", None),
        ("DELETE", f"/api/v1/institutions/{b_id}/api-keys/1", None),
        # Integration endpoint
        (
            "POST",
            f"/api/v1/integration/institutions/{b_id}/students/bulk",
            {
                "academic_year": "2026-27",
                "students": [
                    {
                        "apaar_id": "900012345678",
                        "name": "Rogue Integration Student",
                        "dob": "2004-01-01",
                        "gender": "Male",
                        "course": "Computer Science and Engineering",
                        "enrolment_no": "ROGUE-INT-01",
                        "admission_date": "2026-07-01",
                    }
                ],
            },
        ),
        # Seat declarations & submissions endpoints
        ("GET", f"/api/v1/institutions/{b_id}/seat-declarations", None),
        (
            "PUT",
            f"/api/v1/institutions/{b_id}/seat-declarations",
            {"academic_year": "2026-27", "declarations": []},
        ),
        ("GET", f"/api/v1/institutions/{b_id}/submissions/gate", None),
        (
            "POST",
            f"/api/v1/institutions/{b_id}/submissions/submit",
            {"academic_year": "2026-27", "declaration_accepted": True, "otp": "123456"},
        ),
        ("GET", f"/api/v1/institutions/{b_id}/submissions/receipt", None),
        # Notifications endpoints
        ("GET", f"/api/v1/institutions/{b_id}/notifications", None),
        ("PATCH", f"/api/v1/institutions/{b_id}/notifications/1/read", None),
        ("POST", f"/api/v1/institutions/{b_id}/notifications/mark-all-read", None),
        # Review queries endpoints
        ("GET", f"/api/v1/institutions/{b_id}/queries", None),
        (
            "POST",
            f"/api/v1/institutions/{b_id}/queries/1/respond",
            {"response_text": "Unauthorized answer"},
        ),
        # Change requests endpoints
        ("GET", f"/api/v1/institutions/{b_id}/change-requests", None),
        (
            "POST",
            f"/api/v1/institutions/{b_id}/change-requests",
            {
                "student_id": student_b_id,
                "field_name": "name",
                "new_value": "Injected Name",
                "reason": "Test IDOR",
            },
        ),
        # Reports endpoint
        ("GET", f"/api/v1/institutions/{b_id}/reports/submission?format=csv", None),
    ]

    # Create an API key for College A for integration IDOR testing
    key_resp = client.post(
        f"/api/v1/institutions/{inst_a.id}/api-keys",
        json={"name": "Alpha Integration Key", "scopes": ["students:write"]},
        headers=auth_headers,
    )
    assert key_resp.status_code == 201
    api_key_a = key_resp.json()["raw_key"]

    for method, path, body in college_b_endpoints:
        req_headers = auth_headers
        if "/integration/institutions/" in path:
            req_headers = {"X-API-Key": api_key_a}

        if method == "GET":
            resp = client.get(path, headers=req_headers)
        elif method == "POST":
            if "flags" in path and "justifications" in path:
                resp = client.post(path, data=body, headers=req_headers)
            else:
                resp = client.post(path, json=body, headers=req_headers)
        elif method == "PUT":
            resp = client.put(path, json=body, headers=req_headers)
        elif method == "PATCH":
            resp = client.patch(path, json=body, headers=req_headers)
        elif method == "DELETE":
            resp = client.delete(path, headers=req_headers)
        else:
            pytest.fail(f"Unsupported method: {method}")

        assert resp.status_code == 403, (
            f"IDOR vulnerability detected! Endpoint {method} {path} returned {resp.status_code} "
            f"instead of 403 Forbidden for cross-institution user."
        )


# ==============================================================================
# 6. Verifier Access Without Consent Tests
# ==============================================================================

def test_verifier_access_without_consent_denied(client: TestClient, db_session: Session):
    """Enforce privacy: Verifiers cannot read student records without student consent."""
    fixtures = _setup_security_fixtures(db_session)
    student_a = fixtures["student_a"]
    verifier_token = fixtures["tokens"]["verifier"]
    verifier_org = fixtures["verifier_org"]
    v_headers = {"Authorization": f"Bearer {verifier_token}"}

    # 1. Verifier attempts to fetch student verification record directly -> 403 Forbidden
    resp_no_consent = client.get(
        f"/api/v1/verification/students/{student_a.id}",
        headers=v_headers,
    )
    assert resp_no_consent.status_code == 403

    # 2. Consent request exists but is still PENDING -> Verifier denied
    consent_pending = ConsentRequest(
        verifier_id=verifier_org.id,
        apaar_id=student_a.apaar_id,
        scope_json={"fields": ["institution", "course", "years", "status"], "used": False},
        status="pending",
        requested_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(consent_pending)
    db_session.commit()
    db_session.refresh(consent_pending)

    resp_pending = client.get(
        f"/api/v1/verification/consent-requests/{consent_pending.id}/record",
        headers=v_headers,
    )
    assert resp_pending.status_code == 403
    assert "pending" in resp_pending.json()["detail"].lower()

    # 3. Consent request exists but is DENIED -> Verifier denied
    consent_denied = ConsentRequest(
        verifier_id=verifier_org.id,
        apaar_id=student_a.apaar_id,
        scope_json={"fields": ["institution", "course", "years", "status"], "used": False},
        status="denied",
        requested_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(consent_denied)
    db_session.commit()
    db_session.refresh(consent_denied)

    resp_denied = client.get(
        f"/api/v1/verification/consent-requests/{consent_denied.id}/record",
        headers=v_headers,
    )
    assert resp_denied.status_code == 403
    assert "denied" in resp_denied.json()["detail"].lower()

    # 4. Consent request was approved but has EXPIRED (>24 hours) -> Verifier denied
    consent_expired = ConsentRequest(
        verifier_id=verifier_org.id,
        apaar_id=student_a.apaar_id,
        scope_json={"fields": ["institution", "course", "years", "status"], "used": False},
        status="approved",
        requested_at=datetime.now(UTC) - timedelta(hours=26),
        expires_at=datetime.now(UTC) - timedelta(hours=2),  # Expired 2 hrs ago
    )
    db_session.add(consent_expired)
    db_session.commit()
    db_session.refresh(consent_expired)

    resp_expired = client.get(
        f"/api/v1/verification/consent-requests/{consent_expired.id}/record",
        headers=v_headers,
    )
    assert resp_expired.status_code == 403
    assert "expired" in resp_expired.json()["detail"].lower()


# ==============================================================================
# 7. Expired & Tampered Token Tests
# ==============================================================================

def test_expired_and_tampered_jwt_tokens(client: TestClient):
    """Enforce token validation: expired, corrupted, or mismatched tokens are rejected."""
    settings = get_settings()

    # 1. Expired access token (expired 10 seconds ago)
    now = datetime.now(UTC)
    expired_payload = {
        "sub": "1",
        "email": "test@example.com",
        "role": Role.COLLEGE_ADMIN.value,
        "institution_id": 1,
        "type": "access",
        "iat": int((now - timedelta(seconds=60)).timestamp()),
        "exp": int((now - timedelta(seconds=10)).timestamp()),
    }
    expired_token = jwt.encode(
        expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )

    resp_exp = client.get(
        "/api/v1/institutions/1/students",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp_exp.status_code == 401
    assert "Token has expired" in resp_exp.json()["detail"]

    # 2. Corrupted signature / Wrong signing secret
    tampered_token = jwt.encode(
        expired_payload,
        "completely-wrong-secret-key-32-characters-minimum",
        algorithm=settings.JWT_ALGORITHM,
    )
    resp_tampered = client.get(
        "/api/v1/institutions/1/students",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert resp_tampered.status_code == 401

    # 3. Presenting a refresh token to an access-protected endpoint
    refresh_token = create_refresh_token(1, "test@example.com", Role.COLLEGE_ADMIN.value, 1)
    resp_wrong_type = client.get(
        "/api/v1/institutions/1/students",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert resp_wrong_type.status_code == 401
    assert "expected access token" in resp_wrong_type.json()["detail"]


# ==============================================================================
# 8. Role Escalation Attempts Tests
# ==============================================================================

def test_role_escalation_attempts_blocked(client: TestClient, db_session: Session):
    """Verify that lower privilege roles cannot perform actions requiring higher privileges."""
    fixtures = _setup_security_fixtures(db_session)
    inst_a = fixtures["inst_a"]
    a_id = inst_a.id
    flag_a = fixtures["flag_a"]

    token_staff = fixtures["tokens"]["staff_a"]
    token_viewer = fixtures["tokens"]["viewer_a"]
    token_admin_a = fixtures["tokens"]["admin_a"]
    token_verifier = fixtures["tokens"]["verifier"]

    # 1. College Staff attempts to submit (College Admin only) -> 403 Forbidden
    resp_staff_submit = client.post(
        f"/api/v1/institutions/{a_id}/submissions/submit",
        json={"academic_year": "2026-27", "declaration_accepted": True, "otp": "123456"},
        headers={"Authorization": f"Bearer {token_staff}"},
    )
    assert resp_staff_submit.status_code == 403

    # 2. College Staff attempts to manage staff -> 403 Forbidden
    resp_staff_add = client.post(
        f"/api/v1/institutions/{a_id}/staff",
        json={"name": "New Staff", "email": "new@alpha.edu", "role": "college_staff"},
        headers={"Authorization": f"Bearer {token_staff}"},
    )
    assert resp_staff_add.status_code == 403

    # 3. College Staff attempts to create API keys -> 403 Forbidden
    resp_staff_keys = client.post(
        f"/api/v1/institutions/{a_id}/api-keys",
        json={"name": "Key", "scopes": ["students:write"]},
        headers={"Authorization": f"Bearer {token_staff}"},
    )
    assert resp_staff_keys.status_code == 403

    # 4. College Viewer attempts write action (create student) -> 403 Forbidden
    resp_viewer_create = client.post(
        f"/api/v1/institutions/{a_id}/students",
        json={
            "academic_year": "2026-27",
            "course_id": fixtures["course_a"].id,
            "apaar_id": "123412341234",
            "name": "Viewer Student",
            "dob": "2002-01-01",
            "gender": "Male",
            "enrolment_no": "VIEW-01",
            "admission_date": "2026-07-01",
            "admission_mode": "Management quota",
            "seat_type": "Regular",
            "reservation_category": "General",
        },
        headers={"Authorization": f"Bearer {token_viewer}"},
    )
    assert resp_viewer_create.status_code == 403

    # 5. College Viewer attempts to write a justification -> 403 Forbidden
    resp_viewer_just = client.post(
        f"/api/v1/institutions/{a_id}/flags/{flag_a.id}/justifications",
        data={"text": "Viewer text"},
        headers={"Authorization": f"Bearer {token_viewer}"},
    )
    assert resp_viewer_just.status_code == 403

    # 6. College Admin attempts AICTE supervisory endpoints -> 403 Forbidden
    aicte_endpoints = [
        "/api/v1/audit",
        "/api/v1/analytics/anomalies",
        "/api/v1/review/items",
        "/api/v1/rules",
    ]
    for aicte_path in aicte_endpoints:
        r = client.get(aicte_path, headers={"Authorization": f"Bearer {token_admin_a}"})
        assert r.status_code == 403, f"College admin was able to access AICTE route: {aicte_path}"

    # 7. Verifier attempts to access college endpoints -> 403 Forbidden
    resp_verifier_notifs = client.get(
        f"/api/v1/institutions/{a_id}/notifications",
        headers={"Authorization": f"Bearer {token_verifier}"},
    )
    assert resp_verifier_notifs.status_code == 403

    resp_verifier_seats = client.get(
        f"/api/v1/institutions/{a_id}/seat-declarations",
        headers={"Authorization": f"Bearer {token_verifier}"},
    )
    assert resp_verifier_seats.status_code == 403
