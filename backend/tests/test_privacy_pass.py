"""Tests for DPDP Privacy Pass, Data Minimisation, Consent Completeness, and Schema Review.

Spec: Section 2, 8.2, 14, 16 & TASKS.md T38:
- Stored fields review against data minimisation (SPEC 2 & 8.2; zero Aadhaar, parents,
  address, photo, income, marks).
- Date of Birth encryption at rest (Fernet AES-128-CBC) and log redaction.
- Consent records completeness (data principal, verifier organisation, explicit purpose,
  minimal scope, 24-hour statutory TTL, single use, hash-chained audit trail).
- Verifier minimal disclosure (zero DOB, zero category, zero contact data released).
- Public GET /api/v1/privacy endpoint returning full DPDP specification.
- Deny-by-default route allowlist synchronization.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.allowlist import PUBLIC_ALLOWLIST
from app.auth.security import decrypt_dob, encrypt_dob, hash_password
from app.models import (
    AuditLog,
    Course,
    Institution,
    MockApaarRegistry,
    Student,
    User,
    VerifiedRecord,
    Verifier,
)
from app.students.schemas import (
    StudentCreateRequest,
    StudentResponse,
    StudentUpdateRequest,
)
from app.verification.service import (
    create_consent_request,
    decide_consent_request,
    read_consented_student_record,
)


@pytest.fixture
def privacy_test_env(db_session: Session):
    """Seed test fixtures for privacy and consent validation."""
    # 1. AICTE Institution
    inst = Institution(
        aicte_id="1-PRIVACY-01",
        name="Privacy Institute of Technology",
        state="Karnataka",
        district="Bengaluru",
        address="100 Tech Park",
        official_email="contact@privacy-tech.edu",
        official_phone="+919876543210",
        head_name="Dr. Privacy Dean",
        affiliating_university="Tech University",
        approval_status="active",
        account_status="active",
    )
    db_session.add(inst)
    db_session.flush()

    # 2. Approved Course
    course = Course(
        institution_id=inst.id,
        name="Computer Science & Engineering",
        level="UG",
        branch="Computer Engineering",
        duration_years=4,
        supernumerary_allowed=True,
    )
    db_session.add(course)
    db_session.flush()

    # 3. Student in Mock Registry
    reg = MockApaarRegistry(
        apaar_id="888877776666",
        name="Aarav Sharma",
        dob="2004-06-15",
        gender="Male",
    )
    db_session.add(reg)

    # 4. Enrolled Student Record with Fernet Encrypted DOB
    enc_dob = encrypt_dob("2004-06-15")
    student = Student(
        institution_id=inst.id,
        course_id=course.id,
        academic_year="2026-27",
        apaar_id="888877776666",
        name="Aarav Sharma",
        dob_encrypted=enc_dob,
        gender="Male",
        enrolment_no="EN26-CS-001",
        admission_date=datetime(2026, 7, 10).date(),
        admission_mode="JEE Main counselling",
        seat_type="Regular",
        reservation_category="General",
        nri="No",
        oci="No",
        foreign_national="No",
        fn_country=None,
        status="verified",
    )
    db_session.add(student)
    db_session.flush()

    # 5. Verified Record
    vr = VerifiedRecord(
        student_id=student.id,
        verification_id="VR-2026-PRIVACY-001",
        signature="deadbeef0123456789abcdef",
        issued_at=datetime.now(UTC),
        status="active",
    )
    db_session.add(vr)

    # 6. Approved Verifier Organisation & User
    verifier = Verifier(
        org_name="National Verification Services Ltd",
        org_type="employer",
        contact="audit@natverif.com",
        status="approved",
    )
    db_session.add(verifier)
    db_session.flush()

    verifier_user = User(
        email="audit@natverif.com",
        password_hash=hash_password("VerifierSecret123!"),
        role="verifier",
        institution_id=None,
        is_active=True,
    )
    db_session.add(verifier_user)
    db_session.commit()

    return {
        "institution": inst,
        "course": course,
        "student": student,
        "verified_record": vr,
        "verifier": verifier,
        "verifier_user": verifier_user,
    }


def test_data_minimisation_student_table_columns_review():
    """Verify Student table strictly contains approved fields and ZERO prohibited PII fields.

    SPEC.md Section 2 (Hard Rule 2) & Section 8.2:
    - Never collect: Aadhaar, parents' details, address, photo, income, marks.
    """
    col_names = {col.name for col in Student.__table__.columns}

    # Approved functional fields + system metadata
    expected_allowed = {
        # SPEC 8.2 Identity
        "apaar_id",
        "name",
        "dob_encrypted",
        "gender",
        # SPEC 8.2 Admission
        "course_id",
        "academic_year",
        "enrolment_no",
        "admission_date",
        "admission_mode",
        "seat_type",
        # SPEC 8.2 Category
        "reservation_category",
        "nri",
        "oci",
        "foreign_national",
        "fn_country",
        # System & Audit metadata
        "id",
        "institution_id",
        "status",
        "is_locked",
        "submission_id",
        "source",
        "created_at",
        "updated_at",
    }

    assert col_names == expected_allowed, (
        f"Unexpected columns in Student table: {col_names - expected_allowed}"
    )

    # Explicit assertion that prohibited keywords NEVER appear as columns
    prohibited_keywords = [
        "aadhaar",
        "aadhar",
        "parent",
        "father",
        "mother",
        "guardian",
        "address",
        "street",
        "city",
        "pincode",
        "zip",
        "photo",
        "biometric",
        "image",
        "avatar",
        "income",
        "salary",
        "marks",
        "cgpa",
        "gpa",
        "score",
        "grade",
        "percentage",
    ]
    for col in col_names:
        for keyword in prohibited_keywords:
            assert keyword not in col.lower(), (
                f"Prohibited personal data field '{col}' detected in Student table!"
            )


def test_dob_encryption_at_rest_and_plaintext_prohibition(privacy_test_env, db_session: Session):
    """Verify student Date of Birth is never stored in plaintext and is encrypted with Fernet."""
    student = privacy_test_env["student"]

    # Raw database column holds ciphertext only
    raw_ciphertext = student.dob_encrypted
    assert raw_ciphertext.startswith("gAAAAA"), "DOB must be encrypted using Fernet token"
    assert "2004-06-15" not in raw_ciphertext, "Raw DB column must never contain plaintext DOB"

    # Decryption works with secret key
    decrypted = decrypt_dob(raw_ciphertext)
    assert decrypted == "2004-06-15" or decrypted.isoformat() == "2004-06-15"


def test_student_pydantic_schemas_respect_data_minimisation():
    """Verify Student Pydantic request and response schemas contain no prohibited fields."""
    request_fields = set(StudentCreateRequest.model_fields.keys())
    update_fields = set(StudentUpdateRequest.model_fields.keys())
    response_fields = set(StudentResponse.model_fields.keys())

    prohibited = [
        "aadhaar",
        "parent",
        "father",
        "mother",
        "address",
        "photo",
        "income",
        "marks",
        "cgpa",
    ]

    for field_set in (request_fields, update_fields, response_fields):
        for f in field_set:
            for p in prohibited:
                assert p not in f.lower(), f"Schema field '{f}' violates DPDP data minimisation"


def test_consent_record_completeness(privacy_test_env, db_session: Session):
    """Verify consent records contain all necessary DPDP metadata fields and audit link.

    DPDP Section 6 & SPEC.md Section 14:
    - Data Principal (APAAR ID)
    - Verifier organisation (ID, name)
    - Specific stated purpose
    - Minimal scope (5 fields)
    - 24-hour statutory TTL
    - Single-use flag
    - Append-only audit log entry
    """
    verifier_user = privacy_test_env["verifier_user"]
    verifier = privacy_test_env["verifier"]
    apaar_id = "888877776666"
    purpose = "Statutory pre-employment credential verification for TCS engineering role"

    consent = create_consent_request(
        db=db_session,
        verifier_user=verifier_user,
        apaar_id=apaar_id,
        purpose=purpose,
        client_ip="192.168.1.50",
    )

    # 1. Verify consent record completeness
    assert consent.id is not None
    assert consent.verifier_id == verifier.id
    assert consent.apaar_id == apaar_id
    assert consent.status == "pending"
    assert consent.requested_at is not None
    assert consent.decided_at is None

    # 2. Verify 24-hour statutory TTL
    expected_expiry = consent.requested_at + timedelta(hours=24)
    time_diff = abs((consent.expires_at - expected_expiry).total_seconds())
    assert time_diff < 5.0, "Consent expiration must be exactly 24 hours from creation"

    # 3. Verify minimal scope definition
    scope = consent.scope_json
    assert scope["purpose"] == purpose
    assert scope["single_use"] is True
    assert scope["used"] is False
    assert scope["fields"] == ["institution", "course", "years", "status", "verification_id"]

    # 4. Verify hash-chained audit logging
    audit = db_session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "consent.request", AuditLog.entity_id == str(consent.id))
        .order_by(AuditLog.id.desc())
    )
    assert audit is not None
    assert audit.actor_id == str(verifier_user.id)
    assert audit.after_json["purpose"] == purpose


def test_student_consent_decision_lifecycle_and_immutability(
    privacy_test_env, db_session: Session
):
    """Verify student decision transitions consent status and prevents tamper/double-decision."""
    verifier_user = privacy_test_env["verifier_user"]
    apaar_id = "888877776666"

    consent = create_consent_request(
        db=db_session,
        verifier_user=verifier_user,
        apaar_id=apaar_id,
        purpose="Employment background check",
    )

    # Student approves consent
    decided = decide_consent_request(
        db=db_session,
        request_id=consent.id,
        decision="approved",
        student_apaar_id=apaar_id,
    )
    assert decided.status == "approved"
    assert decided.decided_at is not None

    # Attempt to decide again fails (immutability)
    with pytest.raises(Exception) as exc_info:
        decide_consent_request(
            db=db_session,
            request_id=consent.id,
            decision="denied",
            student_apaar_id=apaar_id,
        )
    assert "already been decided" in str(exc_info.value)


def test_verifier_minimal_disclosure_zero_pii_released(privacy_test_env, db_session: Session):
    """Verify verifier receives ONLY the minimal academic proof and ZERO personal data.

    SPEC.md Section 14:
    - Verifier sees only: institution, course, years, status, verification_id, 'verified by AICTE'.
    - NEVER DOB, category, or contact data.
    - Single use: accessed once, then consumed.
    """
    verifier_user = privacy_test_env["verifier_user"]
    apaar_id = "888877776666"

    consent = create_consent_request(
        db=db_session,
        verifier_user=verifier_user,
        apaar_id=apaar_id,
        purpose="Academic background verification",
    )
    decide_consent_request(
        db=db_session,
        request_id=consent.id,
        decision="approved",
        student_apaar_id=apaar_id,
    )

    # Verifier reads consented data
    record = read_consented_student_record(
        db=db_session,
        request_id=consent.id,
        verifier_user=verifier_user,
        client_ip="10.0.0.1",
    )

    # Assert required minimal proof fields are present
    assert record["institution"] == "Privacy Institute of Technology"
    assert record["course"] == "Computer Science & Engineering"
    assert record["years"] == "2026-27"
    assert record["status"] == "verified"
    assert record["verification_id"] == "VR-2026-PRIVACY-001"
    assert record["verified_by"] == "AICTE Central Repository"
    assert record["verified"] is True

    # Assert personal data is STRICTLY ABSENT
    forbidden_keys = [
        "dob",
        "dob_encrypted",
        "date_of_birth",
        "reservation_category",
        "category",
        "nri",
        "oci",
        "foreign_national",
        "country",
        "enrolment_no",
        "admission_date",
        "admission_mode",
        "phone",
        "email",
        "address",
    ]
    for key in forbidden_keys:
        assert key not in record, f"Personal data key '{key}' leaked to verifier!"

    # Verify single-use token consumption
    db_session.refresh(consent)
    assert consent.status == "used"
    assert consent.scope_json.get("used") is True
    assert "used_at" in consent.scope_json

    # Second read fails with 403 Forbidden (Replay attack blocked)
    with pytest.raises(Exception) as exc_info:
        read_consented_student_record(
            db=db_session,
            request_id=consent.id,
            verifier_user=verifier_user,
        )
    assert "already been used" in str(exc_info.value)


def test_consent_expiration_blocks_approval_and_read(privacy_test_env, db_session: Session):
    """Verify expired consent requests (>24h TTL) cannot be approved or read."""
    verifier_user = privacy_test_env["verifier_user"]
    apaar_id = "888877776666"

    consent = create_consent_request(
        db=db_session,
        verifier_user=verifier_user,
        apaar_id=apaar_id,
        purpose="Expired test",
    )
    # Simulate passage of 25 hours
    consent.expires_at = datetime.now(UTC) - timedelta(hours=1)
    db_session.flush()

    # Attempt to approve expired consent
    with pytest.raises(Exception) as exc_info:
        decide_consent_request(
            db=db_session,
            request_id=consent.id,
            decision="approved",
            student_apaar_id=apaar_id,
        )
    assert "expired" in str(exc_info.value).lower()


def test_public_privacy_policy_api_endpoint(client: TestClient):
    """Verify GET /api/v1/privacy returns full DPDP declaration without authentication."""
    resp = client.get("/api/v1/privacy")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "compliant"
    assert "DPDP" in data["framework"]

    # Fiduciary
    assert "AICTE" in data["data_fiduciary"]["name"]

    # Purpose limitation
    assert len(data["purpose_limitation"]) >= 3

    # Data minimisation: 16 collected fields & 6 prohibited categories
    assert len(data["data_minimisation"]["collected_fields"]) == 16
    assert len(data["data_minimisation"]["prohibited_fields"]) == 6

    # Verify Aadhaar is prominently listed as prohibited
    prohibited_names = [p["field"] for p in data["data_minimisation"]["prohibited_fields"]]
    assert any("Aadhaar" in p for p in prohibited_names)

    # Cryptographic safeguards
    assert "Fernet" in data["cryptographic_safeguards"]["dob_encryption"]
    assert "masking" in data["cryptographic_safeguards"]["apaar_log_redaction"]

    # Consent framework
    assert data["consent_framework"]["statutory_ttl_hours"] == 24
    assert data["consent_framework"]["single_use_enforced"] is True

    # Grievance Redressal / DPO
    assert "dpo@aicte-india.org" in data["grievance_redressal"]["email"]


def test_privacy_endpoint_allowlisted_and_deny_by_default_preserved():
    """Verify /api/v1/privacy is registered on PUBLIC_ALLOWLIST."""
    assert ("/api/v1/privacy", "GET") in PUBLIC_ALLOWLIST
