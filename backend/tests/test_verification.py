"""Comprehensive test suite for Ed25519 record signing, verification IDs, and tamper detection.

SPEC.md Section 14 & TASKS.md T32:
- Ed25519 key handling from environment (PyNaCl).
- Canonical payload serialization covering (verification_id, apaar_id hash, institution,
  course, years, status, issued_at).
- `verified_records` created on clean submission or AICTE review acceptance.
- QR PNG generation endpoint encoding /verify?vid=... without PII.
- Credential revocation with RBAC and institutional IDOR protection.
- Tamper tests: changing ANY signed field in payload or DB causes verification to fail.
- Audit logging on every issuance and revocation.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import nacl.signing
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.models import (
    AuditLog,
    Course,
    Institution,
    ReviewItem,
    SeatDeclaration,
    Student,
    Submission,
    User,
    ValidationFlag,
    VerifiedRecord,
)
from app.review.service import decide_review_item
from app.submissions.promotion_service import promote_submission_and_run_cross_checks
from app.verification.service import (
    issue_verified_record,
    verify_credential_by_id,
)
from app.verification.signing import (
    build_canonical_payload,
    format_canonical_issued_at,
    get_public_key_hex,
    get_signing_key,
    get_verify_key,
    serialize_canonical_payload,
    sign_payload,
    verify_signature,
)


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_setup(db_session: Session):
    inst_a = Institution(
        aicte_id="1-T32001",
        name="Institute of Computer Science",
        state="Maharashtra",
        district="Pune",
        address="University Road",
        official_email="contact@ics.edu",
        official_phone="9876543210",
        head_name="Dr. Head A",
        affiliating_university="Savitribai Phule Pune University",
        approval_status="active",
        account_status="active",
    )
    inst_b = Institution(
        aicte_id="1-T32002",
        name="Metropolitan Institute of Technology",
        state="Maharashtra",
        district="Mumbai",
        address="Bandra West",
        official_email="contact@mit.edu",
        official_phone="9876543211",
        head_name="Dr. Head B",
        affiliating_university="University of Mumbai",
        approval_status="active",
        account_status="active",
    )
    db_session.add_all([inst_a, inst_b])
    db_session.flush()

    course_a = Course(
        institution_id=inst_a.id,
        name="Computer Science & Engineering",
        level="UG",
        branch="CSE",
        duration_years=4,
        supernumerary_allowed=True,
    )
    course_b = Course(
        institution_id=inst_b.id,
        name="Information Technology",
        level="UG",
        branch="IT",
        duration_years=4,
        supernumerary_allowed=True,
    )
    db_session.add_all([course_a, course_b])
    db_session.flush()

    # Users
    col_admin_a = User(
        email="admin@ics.edu",
        password_hash=hash_password("Password123!"),
        role="college_admin",
        institution_id=inst_a.id,
        is_active=True,
    )
    col_admin_b = User(
        email="admin@mit.edu",
        password_hash=hash_password("Password123!"),
        role="college_admin",
        institution_id=inst_b.id,
        is_active=True,
    )
    aicte_admin = User(
        email="admin@aicte-india.org",
        password_hash=hash_password("Password123!"),
        role="aicte_admin",
        is_active=True,
    )
    aicte_officer = User(
        email="officer@aicte-india.org",
        password_hash=hash_password("Password123!"),
        role="aicte_officer",
        is_active=True,
    )
    db_session.add_all([col_admin_a, col_admin_b, aicte_admin, aicte_officer])
    db_session.flush()

    # Student at inst_a
    student_a = Student(
        institution_id=inst_a.id,
        course_id=course_a.id,
        academic_year="2026-27",
        apaar_id="123456789012",
        name="Aarav Sharma",
        dob_encrypted="enc_test_dob_aarav",
        gender="Male",
        enrolment_no="ENR-ICS-001",
        seat_type="Regular",
        admission_mode="Cap Round",
        admission_date=datetime(2026, 8, 10, tzinfo=UTC).date(),
        reservation_category="General",
        status="valid",
    )
    db_session.add(student_a)
    db_session.flush()

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "course_a": course_a,
        "course_b": course_b,
        "col_admin_a": col_admin_a,
        "col_admin_b": col_admin_b,
        "aicte_admin": aicte_admin,
        "aicte_officer": aicte_officer,
        "student_a": student_a,
    }


def test_ed25519_key_handling():
    """Verify Ed25519 key derivation from various seed formats."""
    # 1. Default from environment/passphrase
    sk1 = get_signing_key()
    assert isinstance(sk1, nacl.signing.SigningKey)
    vk1 = get_verify_key(sk1)
    assert isinstance(vk1, nacl.signing.VerifyKey)

    # 2. Hex seed (64 chars)
    hex_seed = "a" * 64
    sk2 = get_signing_key(override_key=hex_seed)
    assert sk2.encode() == bytes.fromhex(hex_seed)

    # 3. Exact 32 bytes
    raw_seed = b"12345678901234567890123456789012"
    sk3 = get_signing_key(override_key=raw_seed)
    assert sk3.encode() == raw_seed

    # 4. Public key hex string
    pk_hex = get_public_key_hex(sk1)
    assert len(pk_hex) == 64
    assert bytes.fromhex(pk_hex) == vk1.encode()


def test_canonical_payload_building_and_serialization():
    """Verify canonical payload structure and deterministic byte serialization."""
    vid = "VR-2026-TEST1234"
    apaar = "123456789012"
    ts = datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC)

    payload = build_canonical_payload(
        verification_id=vid,
        apaar_id=apaar,
        institution="Institute of Computer Science",
        course="Computer Science & Engineering",
        years="2026-27",
        status="verified",
        issued_at=ts,
    )

    # All 7 SPEC.md Section 14 fields present
    assert payload["verification_id"] == vid
    assert payload["apaar_id_hash"] == hashlib.sha256(apaar.encode()).hexdigest()
    assert payload["institution"] == "Institute of Computer Science"
    assert payload["course"] == "Computer Science & Engineering"
    assert payload["years"] == "2026-27"
    assert payload["status"] == "verified"
    assert payload["issued_at"] == format_canonical_issued_at(ts)

    # Raw APAAR is never in the canonical payload
    assert apaar not in str(payload)

    # Deterministic serialization check
    serialized = serialize_canonical_payload(payload)
    parsed = json.loads(serialized.decode("utf-8"))
    assert parsed == payload
    # Check no extra whitespace
    assert b": " not in serialized and b", " not in serialized


def test_tamper_detection_any_signed_field():
    """Tamper test: altering ANY signed field causes signature verification to fail."""
    vid = "VR-2026-TAMPER-TEST"
    apaar = "987654321098"
    ts = datetime(2026, 10, 28, 10, 0, 0, tzinfo=UTC)

    base_payload = build_canonical_payload(
        verification_id=vid,
        apaar_id=apaar,
        institution="College of Engineering",
        course="Mechanical Engineering",
        years="2026-27",
        status="verified",
        issued_at=ts,
    )

    # Sign baseline payload
    sig = sign_payload(base_payload)
    assert len(sig) == 128  # 64-byte Ed25519 signature in hex
    assert verify_signature(base_payload, sig) is True

    # 1. Mutate institution
    p_inst = dict(base_payload)
    p_inst["institution"] = "Fake Malicious University"
    assert verify_signature(p_inst, sig) is False, "Tampered institution must fail"

    # 2. Mutate course
    p_course = dict(base_payload)
    p_course["course"] = "Doctor of Medicine"
    assert verify_signature(p_course, sig) is False, "Tampered course must fail"

    # 3. Mutate academic year
    p_years = dict(base_payload)
    p_years["years"] = "2024-25"
    assert verify_signature(p_years, sig) is False, "Tampered year must fail"

    # 4. Mutate status
    p_status = dict(base_payload)
    p_status["status"] = "withdrawn"
    assert verify_signature(p_status, sig) is False, "Tampered status must fail"

    # 5. Mutate apaar_id_hash
    p_apaar = dict(base_payload)
    p_apaar["apaar_id_hash"] = hashlib.sha256(b"000000000000").hexdigest()
    assert verify_signature(p_apaar, sig) is False, "Tampered APAAR hash must fail"

    # 6. Mutate issued_at
    p_ts = dict(base_payload)
    p_ts["issued_at"] = "2026-10-29T10:00:00+00:00"
    assert verify_signature(p_ts, sig) is False, "Tampered issued_at must fail"

    # 7. Mutate verification_id
    p_vid = dict(base_payload)
    p_vid["verification_id"] = "VR-2026-FORGED"
    assert verify_signature(p_vid, sig) is False, "Tampered verification_id must fail"

    # 8. Mutate signature itself (flip byte)
    tampered_sig = ("00" if sig[:2] != "00" else "ff") + sig[2:]
    assert verify_signature(base_payload, tampered_sig) is False, "Altered signature must fail"


def test_issue_verified_record_and_audit(db_session: Session, test_setup):
    """Test manual and automated record issuance, idempotency, and audit trail."""
    student = test_setup["student_a"]
    col_admin = test_setup["col_admin_a"]

    vr = issue_verified_record(
        db=db_session,
        student=student,
        status_override="verified",
        actor=col_admin,
        client_ip="10.0.0.1",
    )
    db_session.flush()

    assert vr.id is not None
    assert vr.student_id == student.id
    assert vr.verification_id.startswith("VR-2026-")
    assert vr.status == "active"
    assert len(vr.signature) == 128
    assert student.status == "verified"

    # Verify signature over student's current state
    check = verify_credential_by_id(db_session, vr.verification_id)
    assert check["verified"] is True
    assert check["status"] == "active"
    assert check["institution"] == "Institute of Computer Science"
    assert check["course"] == "Computer Science & Engineering"
    assert check["years"] == "2026-27"
    assert check["student_status"] == "verified"
    # Never expose sensitive fields
    assert "dob" not in check
    assert "category" not in check
    assert "mobile_number" not in check
    assert "email" not in check

    # Idempotency check: re-calling returns existing active record
    vr2 = issue_verified_record(db_session, student, actor=col_admin)
    assert vr2.id == vr.id
    assert vr2.verification_id == vr.verification_id

    # Verify audit log entry
    audit_entry = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == "verification.issue",
            AuditLog.entity_id == str(vr.id),
        )
    )
    assert audit_entry is not None
    assert audit_entry.actor_id == str(col_admin.id)
    assert audit_entry.after_json["verification_id"] == vr.verification_id


def test_clean_submission_automatically_creates_verified_records(
    db_session: Session, test_setup
):
    """Clean submission without exceptions automatically issues verified records for students."""
    inst = test_setup["inst_a"]
    course = test_setup["course_a"]
    admin = test_setup["col_admin_a"]

    # Create seat declaration
    decl = SeatDeclaration(
        course_id=course.id,
        academic_year="2026-27",
        regular_admitted=10,
        supernumerary_admitted=0,
        status="approved",
    )
    db_session.add(decl)

    # Create clean student
    clean_student = Student(
        institution_id=inst.id,
        course_id=course.id,
        academic_year="2026-27",
        apaar_id="888877776666",
        name="Pooja Patel",
        dob_encrypted="enc_test_dob_pooja",
        gender="Female",
        enrolment_no="ENR-ICS-002",
        seat_type="Regular",
        admission_mode="Direct",
        admission_date=datetime(2026, 7, 15, tzinfo=UTC).date(),
        reservation_category="General",
        status="valid",
    )
    db_session.add(clean_student)
    db_session.flush()

    submission = Submission(
        institution_id=inst.id,
        academic_year="2026-27",
        status="draft",
    )
    db_session.add(submission)
    db_session.flush()

    # Promote clean submission
    result = promote_submission_and_run_cross_checks(
        db=db_session,
        submission=submission,
        user=admin,
    )
    db_session.flush()

    assert result["status"] == "submitted"
    assert result["verified_records_issued"] >= 1

    # Check verified record created on clean student
    vr = db_session.scalar(
        select(VerifiedRecord).where(VerifiedRecord.student_id == clean_student.id)
    )
    assert vr is not None
    assert vr.status == "active"
    assert clean_student.status == "submitted"

    # Cryptographic verification works
    check = verify_credential_by_id(db_session, vr.verification_id)
    assert check["verified"] is True
    assert check["status"] == "active"
    assert check["student_status"] == "submitted"


def test_review_queue_acceptance_creates_verified_records(
    db_session: Session, test_setup
):
    """Review queue acceptance by AICTE officer automatically creates verified credentials."""
    inst = test_setup["inst_b"]
    course = test_setup["course_b"]
    officer = test_setup["aicte_officer"]

    # Student with exception
    student = Student(
        institution_id=inst.id,
        course_id=course.id,
        academic_year="2026-27",
        apaar_id="555544443333",
        name="Devendra Verma",
        dob_encrypted="enc_test_dob_devendra",
        gender="Male",
        enrolment_no="ENR-MIT-001",
        seat_type="Supernumerary",
        admission_mode="FN",
        admission_date=datetime(2026, 8, 20, tzinfo=UTC).date(),
        reservation_category="General",
        status="flagged",
    )
    db_session.add(student)
    db_session.flush()

    submission = Submission(
        institution_id=inst.id,
        academic_year="2026-27",
        status="submitted_with_exceptions",
    )
    db_session.add(submission)
    db_session.flush()

    flag = ValidationFlag(
        student_id=student.id,
        submission_id=submission.id,
        rule_code="DUP_SAME_COURSE_OTHER_COLLEGE",
        level="exception",
        field="apaar_id",
        message="Cross college duplicate exception",
        status="justified",
    )
    db_session.add(flag)
    db_session.flush()

    rev_item = ReviewItem(
        submission_id=submission.id,
        flag_ids=[flag.id],
        status="pending",
    )
    db_session.add(rev_item)
    db_session.flush()

    # AICTE officer accepts the review item
    decide_review_item(
        db=db_session,
        review_item_id=rev_item.id,
        decision="accept",
        note="Approved under verified interstate transfer documentation.",
        user=officer,
    )
    db_session.flush()

    assert rev_item.status == "accepted"

    # Verified record has been issued for student
    vr = db_session.scalar(
        select(VerifiedRecord).where(VerifiedRecord.student_id == student.id)
    )
    assert vr is not None
    assert vr.status == "active"
    assert student.status == "verified_with_exception"

    # Signature is cryptographically valid
    check = verify_credential_by_id(db_session, vr.verification_id)
    assert check["verified"] is True
    assert check["student_status"] == "verified_with_exception"


def test_verification_api_endpoints(client: TestClient, db_session: Session, test_setup):
    """Test public verification query, record proof, and QR code PNG endpoints."""
    student = test_setup["student_a"]
    vr = issue_verified_record(db=db_session, student=student, status_override="verified")
    db_session.commit()

    # 1. Ready state on empty query
    r_empty = client.get("/api/v1/verification/verify")
    assert r_empty.status_code == 200
    assert r_empty.json()["status"] == "ready"
    assert r_empty.json()["verified"] is False

    # 2. Not found query
    r_nf = client.get("/api/v1/verification/verify?vid=NON-EXISTENT-VID")
    assert r_nf.status_code == 200
    assert r_nf.json()["status"] == "not_found"
    assert r_nf.json()["verified"] is False

    # 3. Valid verification query
    r_valid = client.get(f"/api/v1/verification/verify?vid={vr.verification_id}")
    assert r_valid.status_code == 200
    data = r_valid.json()
    assert data["verified"] is True
    assert data["status"] == "active"
    assert data["verification_id"] == vr.verification_id
    assert data["institution"] == "Institute of Computer Science"
    assert data["course"] == "Computer Science & Engineering"
    assert data["years"] == "2026-27"
    assert data["student_status"] == "verified"
    assert data["verified_by"] == "AICTE Central Repository"
    # Verify no PII leak
    assert "apaar_id" not in data
    assert "student_name" not in data
    assert "email" not in data

    # 4. Public record proof endpoint
    r_rec = client.get(f"/api/v1/verification/records/{vr.verification_id}")
    assert r_rec.status_code == 200
    rec_data = r_rec.json()
    assert rec_data["verification_id"] == vr.verification_id
    assert rec_data["status"] == "active"
    assert rec_data["verified"] is True
    assert rec_data["signature"] == vr.signature

    # 5. Public QR code PNG endpoint
    r_qr = client.get(f"/api/v1/verification/records/{vr.verification_id}/qr")
    assert r_qr.status_code == 200
    assert r_qr.headers["content-type"] == "image/png"
    assert r_qr.content.startswith(b"\x89PNG")
    assert len(r_qr.content) > 500

    # 6. QR code for non-existent VID -> 404
    r_qr_nf = client.get("/api/v1/verification/records/NON-EXISTENT-VID/qr")
    assert r_qr_nf.status_code == 404

    # 7. Public Ed25519 verify key endpoint
    r_pk = client.get("/api/v1/verification/public-key")
    assert r_pk.status_code == 200
    assert r_pk.json()["algorithm"] == "Ed25519-SHA512"
    assert len(r_pk.json()["public_key_hex"]) == 64


def test_revocation_and_idor_protection(client: TestClient, db_session: Session, test_setup):
    """Test credential revocation, audit logging, and institutional IDOR protection."""
    student = test_setup["student_a"]  # Belongs to inst_a
    vr = issue_verified_record(db=db_session, student=student)
    db_session.commit()

    col_admin_a = test_setup["col_admin_a"]
    col_admin_b = test_setup["col_admin_b"]
    aicte_admin = test_setup["aicte_admin"]

    # 1. College B admin attempts to revoke College A's student credential -> 403 Forbidden (IDOR)
    r_idor = client.post(
        f"/api/v1/verification/records/{vr.verification_id}/revoke",
        json={"reason": "Attempting rogue cross-college revocation"},
        headers=_auth(col_admin_b),
    )
    assert r_idor.status_code == 403
    assert (
        "Institutions may only revoke credentials issued to their own students"
        in r_idor.json()["detail"]
    )

    # 2. Authorized AICTE admin revokes credential
    r_revoke = client.post(
        f"/api/v1/verification/records/{vr.verification_id}/revoke",
        json={"reason": "Enrolment cancelled due to falsified secondary transcripts."},
        headers=_auth(aicte_admin),
    )
    assert r_revoke.status_code == 200
    assert r_revoke.json()["status"] == "revoked"

    # 3. Querying /verify now returns revoked status
    r_check = client.get(f"/api/v1/verification/verify?vid={vr.verification_id}")
    assert r_check.status_code == 200
    assert r_check.json()["verified"] is False
    assert r_check.json()["status"] == "revoked"
    assert "revoked by AICTE" in r_check.json()["message"]

    # 4. Attempting to revoke an already-revoked credential -> 400 Bad Request
    r_repeat = client.post(
        f"/api/v1/verification/records/{vr.verification_id}/revoke",
        json={"reason": "Repeat revocation"},
        headers=_auth(col_admin_a),
    )
    assert r_repeat.status_code == 400
    assert "already revoked" in r_repeat.json()["detail"]


def test_tampered_database_row_fails_api_verification(
    client: TestClient, db_session: Session, test_setup
):
    """Direct database tampering with any signed field immediately triggers signature mismatch."""
    student = test_setup["student_a"]
    vr = issue_verified_record(db=db_session, student=student, status_override="verified")
    db_session.commit()

    # Verify baseline is valid
    r_initial = client.get(f"/api/v1/verification/verify?vid={vr.verification_id}")
    assert r_initial.status_code == 200
    assert r_initial.json()["verified"] is True

    # Tamper with student record in database (change course name / course_id)
    student.course_name = "Tampered Unapproved Doctorate Degree"
    student.course_id = None
    db_session.commit()

    # Query verification endpoint again -> must fail with status="tampered"
    r_tampered = client.get(f"/api/v1/verification/verify?vid={vr.verification_id}")
    assert r_tampered.status_code == 200
    assert r_tampered.json()["verified"] is False
    assert r_tampered.json()["status"] == "tampered"
    assert "tampered" in r_tampered.json()["message"]


def test_student_verification_details_and_scoping(
    client: TestClient, db_session: Session, test_setup
):
    """Verify /verification/students/{id} scoping and IDOR guards."""
    student = test_setup["student_a"]
    vr = issue_verified_record(db=db_session, student=student, status_override="verified")
    db_session.commit()

    col_admin_a = test_setup["col_admin_a"]
    col_admin_b = test_setup["col_admin_b"]
    aicte_officer = test_setup["aicte_officer"]

    # College A can view own student's credential details
    r_a = client.get(
        f"/api/v1/verification/students/{student.id}",
        headers=_auth(col_admin_a),
    )
    assert r_a.status_code == 200
    assert r_a.json()["has_credential"] is True
    assert r_a.json()["verification_id"] == vr.verification_id

    # College B cannot view College A's student credential details (IDOR)
    r_b = client.get(
        f"/api/v1/verification/students/{student.id}",
        headers=_auth(col_admin_b),
    )
    assert r_b.status_code == 403

    # AICTE officer can view
    r_aicte = client.get(
        f"/api/v1/verification/students/{student.id}",
        headers=_auth(aicte_officer),
    )
    assert r_aicte.status_code == 200
    assert r_aicte.json()["verification_id"] == vr.verification_id
