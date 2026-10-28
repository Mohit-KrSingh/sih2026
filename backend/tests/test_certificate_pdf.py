"""Tests for Degree Certificate PDF generation, institutional endpoints, and QR verify flow.

Spec: Section 17 & 21, TASKS.md T35:
- Sample degree certificate with college student ID and APAAR ID side by side and the QR code.
- Endpoint for institutions; scanning the QR leads to the verify flow.
- Enforces strict RBAC, institutional IDOR protection, and hash-chained audit logging.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import verify_chain
from app.auth.security import create_access_token
from app.models import AuditLog, Course, Institution, Student, User
from app.verification.certificate import (
    format_apaar_display,
    generate_certificate_pdf,
    resolve_degree_details,
)
from app.verification.router import create_student_token
from app.verification.service import (
    generate_student_certificate_service,
    issue_verified_record,
)


def _token_for(user: User) -> str:
    """Helper to generate JWT bearer token matching authentication contract."""
    return create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cert_institution_a(db_session: Session) -> Institution:
    inst = db_session.scalar(select(Institution).where(Institution.aicte_id == "CERT-INST-A"))
    if not inst:
        inst = Institution(
            aicte_id="CERT-INST-A",
            name="Pune Institute of Advanced Technology",
            state="Maharashtra",
            district="Pune",
            address="100 Technology Park, Pune",
            official_email="contact@piat-pune.edu.in",
            official_phone="+919876543210",
            head_name="Dr. S. K. Joshi",
            affiliating_university="Savitribai Phule Pune University",
            approval_status="active",
            account_status="active",
        )
        db_session.add(inst)
        db_session.commit()
        db_session.refresh(inst)
    return inst


@pytest.fixture
def cert_institution_b(db_session: Session) -> Institution:
    inst = db_session.scalar(select(Institution).where(Institution.aicte_id == "CERT-INST-B"))
    if not inst:
        inst = Institution(
            aicte_id="CERT-INST-B",
            name="Mumbai Institute of Information Technology",
            state="Maharashtra",
            district="Mumbai",
            address="200 Marine Lines, Mumbai",
            official_email="contact@miit-mumbai.edu.in",
            official_phone="+919876543211",
            head_name="Dr. R. N. Mehta",
            affiliating_university="University of Mumbai",
            approval_status="active",
            account_status="active",
        )
        db_session.add(inst)
        db_session.commit()
        db_session.refresh(inst)
    return inst


@pytest.fixture
def cert_course(db_session: Session, cert_institution_a: Institution) -> Course:
    course = db_session.scalar(
        select(Course).where(
            Course.institution_id == cert_institution_a.id,
            Course.name == "Computer Science and Engineering",
        )
    )
    if not course:
        course = Course(
            institution_id=cert_institution_a.id,
            name="Computer Science and Engineering",
            level="UG",
            branch="Computer Engineering",
            duration_years=4,
            supernumerary_allowed=True,
        )
        db_session.add(course)
        db_session.commit()
        db_session.refresh(course)
    return course


@pytest.fixture
def cert_student_a(
    db_session: Session, cert_institution_a: Institution, cert_course: Course
) -> Student:
    student = db_session.scalar(select(Student).where(Student.apaar_id == "987654321012"))
    if not student:
        student = Student(
            institution_id=cert_institution_a.id,
            course_id=cert_course.id,
            academic_year="2025-26",
            apaar_id="987654321012",
            name="Priya V. Kulkarni",
            dob_encrypted="gAAAAABtestdobencrypted12345678",
            gender="Female",
            enrolment_no="PIAT-2025-CSE-042",
            admission_date=date(2025, 7, 15),
            admission_mode="State CET Quota",
            seat_type="Regular",
            reservation_category="General",
            status="verified",
            is_locked=True,
            source="manual",
        )
        db_session.add(student)
        db_session.commit()
        db_session.refresh(student)

        # Issue verified credential for student
        issue_verified_record(db=db_session, student=student)
        db_session.commit()
        db_session.refresh(student)
    return student


@pytest.fixture
def cert_student_b(db_session: Session, cert_institution_b: Institution) -> Student:
    student = db_session.scalar(select(Student).where(Student.apaar_id == "987654321099"))
    if not student:
        student = Student(
            institution_id=cert_institution_b.id,
            course_id=None,
            academic_year="2025-26",
            apaar_id="987654321099",
            name="Vikram A. Singhania",
            dob_encrypted="gAAAAABtestdobencrypted12345678",
            gender="Male",
            enrolment_no="MIIT-2025-099",
            admission_date=date(2025, 7, 20),
            admission_mode="Central Counselling",
            seat_type="Regular",
            reservation_category="General",
            status="verified",
            is_locked=True,
            source="manual",
        )
        db_session.add(student)
        db_session.commit()
        db_session.refresh(student)
    return student


@pytest.fixture
def cert_college_admin_a(db_session: Session, cert_institution_a: Institution) -> User:
    email = "admin@piat-pune.edu.in"
    user = db_session.scalar(select(User).where(User.email == email))
    if not user:
        user = User(
            email=email,
            password_hash="mock_argon2_hash",
            role="college_admin",
            institution_id=cert_institution_a.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture
def cert_college_admin_b(db_session: Session, cert_institution_b: Institution) -> User:
    email = "admin@miit-mumbai.edu.in"
    user = db_session.scalar(select(User).where(User.email == email))
    if not user:
        user = User(
            email=email,
            password_hash="mock_argon2_hash",
            role="college_admin",
            institution_id=cert_institution_b.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture
def cert_aicte_officer(db_session: Session) -> User:
    email = "officer_cert_test@aicte-india.org"
    user = db_session.scalar(select(User).where(User.email == email))
    if not user:
        user = User(
            email=email,
            password_hash="mock_argon2_hash",
            role="aicte_officer",
            institution_id=None,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------


def test_format_apaar_display():
    """Verify 12-digit APAAR formatting into 4-digit groups."""
    assert format_apaar_display("123456789012") == "1234 5678 9012"
    assert format_apaar_display("1234 5678 9012") == "1234 5678 9012"
    assert format_apaar_display("short") == "short"


def test_resolve_degree_details():
    """Verify degree titles and disciplines for UG, PG, Diploma, and PGDM levels."""
    deg_ug, br_ug = resolve_degree_details("UG", "Computer Science", "Computer Engineering")
    assert deg_ug == "Bachelor of Technology"
    assert br_ug == "Computer Engineering"

    deg_pg, _ = resolve_degree_details("PG", "Data Science", "Computer Engineering")
    assert deg_pg == "Master of Technology"

    deg_dip, _ = resolve_degree_details("Diploma", "Mechanical", "Mechanical Engineering")
    assert deg_dip == "Diploma in Engineering"

    deg_pgdm, _ = resolve_degree_details("PGDM", "Management", "Business Analytics")
    assert deg_pgdm == "Post Graduate Diploma in Management"


def test_generate_certificate_pdf_structure(db_session: Session, cert_student_a: Student):
    """Verify PDF generator produces valid Landscape A4 single-page PDF with %PDF header."""
    pdf_bytes = generate_certificate_pdf(student=cert_student_a, db=db_session)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 5000
    assert pdf_bytes.startswith(b"%PDF-")

    # Verify single page document (exactly 1 page count)
    page_count = (
        pdf_bytes.count(b"/Type /Page\n")
        + pdf_bytes.count(b"/Type /Page\r")
        + pdf_bytes.count(b"/Type/Page")
    )
    assert page_count == 1, f"Expected 1 page certificate, found {page_count}"


def test_side_by_side_ids_present_in_certificate(db_session: Session, cert_student_a: Student):
    """Verify student's college student ID and APAAR ID are both present in certificate."""
    pdf_bytes = generate_certificate_pdf(student=cert_student_a, db=db_session)

    # With uncompressed page streams, both IDs are present in the PDF byte stream
    enrolment_bytes = cert_student_a.enrolment_no.encode("utf-8")
    assert enrolment_bytes in pdf_bytes

    formatted_apaar = format_apaar_display(cert_student_a.apaar_id).encode("utf-8")
    raw_apaar = cert_student_a.apaar_id.encode("utf-8")
    assert formatted_apaar in pdf_bytes or raw_apaar in pdf_bytes


def test_certificate_service_ensures_verified_record(db_session: Session, cert_student_b: Student):
    """Verify service automatically issues active VerifiedRecord if missing."""
    assert cert_student_b.verified_record is None

    pdf_bytes, filename = generate_student_certificate_service(
        db=db_session,
        student_id=cert_student_b.id,
    )
    assert isinstance(pdf_bytes, bytes)
    assert filename == f"certificate_{cert_student_b.enrolment_no}.pdf"

    # Refresh student from DB and check verified_record is now present and active
    db_session.refresh(cert_student_b)
    assert cert_student_b.verified_record is not None
    assert cert_student_b.verified_record.status == "active"
    assert cert_student_b.verified_record.verification_id.startswith("VR-2025-")


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------


def test_institution_certificate_endpoint_success(
    client: TestClient, cert_college_admin_a: User, cert_student_a: Student
):
    """College admin retrieves degree certificate PDF for a student of their institution."""
    token = _token_for(cert_college_admin_a)
    inst_id = cert_student_a.institution_id
    url = f"/api/v1/institutions/{inst_id}/students/{cert_student_a.id}/certificate"

    response = client.get(url, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert (
        f'inline; filename="certificate_{cert_student_a.enrolment_no}.pdf"'
        in response.headers["content-disposition"]
    )
    assert response.content.startswith(b"%PDF-")


def test_institution_certificate_endpoint_download_flag(
    client: TestClient, cert_college_admin_a: User, cert_student_a: Student
):
    """Test ?download=true sets Content-Disposition to attachment."""
    token = _token_for(cert_college_admin_a)
    inst_id = cert_student_a.institution_id
    url = f"/api/v1/institutions/{inst_id}/students/{cert_student_a.id}/certificate?download=true"

    response = client.get(url, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert (
        f'attachment; filename="certificate_{cert_student_a.enrolment_no}.pdf"'
        in response.headers["content-disposition"]
    )


def test_institution_certificate_endpoint_idor_blocked(
    client: TestClient, cert_college_admin_b: User, cert_student_a: Student
):
    """College B admin attempting to download College A's student certificate gets 403 Forbidden."""
    token = _token_for(cert_college_admin_b)
    inst_id = cert_student_a.institution_id
    url = f"/api/v1/institutions/{inst_id}/students/{cert_student_a.id}/certificate"

    response = client.get(url, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_aicte_officer_certificate_access(
    client: TestClient, cert_aicte_officer: User, cert_student_a: Student
):
    """AICTE officer can inspect degree certificates across institutions."""
    token = _token_for(cert_aicte_officer)
    inst_id = cert_student_a.institution_id
    url = f"/api/v1/institutions/{inst_id}/students/{cert_student_a.id}/certificate"

    response = client.get(url, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_verification_router_certificate_endpoint(
    client: TestClient, cert_college_admin_a: User, cert_student_a: Student
):
    """Verify alias endpoint GET /api/v1/verification/students/{id}/certificate works with RBAC."""
    token = _token_for(cert_college_admin_a)
    url = f"/api/v1/verification/students/{cert_student_a.id}/certificate"

    response = client.get(url, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_nonexistent_student_certificate_returns_404(
    client: TestClient, cert_college_admin_a: User, cert_institution_a: Institution
):
    """Requesting certificate for non-existent student returns 404."""
    token = _token_for(cert_college_admin_a)
    url = f"/api/v1/institutions/{cert_institution_a.id}/students/99999999/certificate"

    response = client.get(url, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_unauthenticated_certificate_request_blocked(client: TestClient, cert_student_a: Student):
    """Unauthenticated request without JWT token returns 401 Unauthorized."""
    inst_id = cert_student_a.institution_id
    url = f"/api/v1/institutions/{inst_id}/students/{cert_student_a.id}/certificate"
    response = client.get(url)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Student Portal Endpoint & Consent Auth Tests
# ---------------------------------------------------------------------------


def test_student_portal_certificate_endpoint_success(client: TestClient, cert_student_a: Student):
    """Student with active OTP session token can download their degree certificate."""
    token = create_student_token(
        apaar_id=cert_student_a.apaar_id,
        student_name=cert_student_a.name,
    )
    url = f"/api/v1/verification/student/records/{cert_student_a.id}/certificate"

    response = client.get(url, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_student_portal_cross_student_certificate_blocked(
    client: TestClient, cert_student_a: Student, cert_student_b: Student
):
    """Student cannot download another student's certificate (returns 403 Forbidden)."""
    token = create_student_token(
        apaar_id=cert_student_a.apaar_id,
        student_name=cert_student_a.name,
    )
    url = f"/api/v1/verification/student/records/{cert_student_b.id}/certificate"

    response = client.get(url, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Audit Log & Verification Flow Tests
# ---------------------------------------------------------------------------


def test_certificate_generation_writes_audit_log(
    client: TestClient, db_session: Session, cert_college_admin_a: User, cert_student_a: Student
):
    """Verify that certificate generation appends an audit log entry."""
    token = _token_for(cert_college_admin_a)
    inst_id = cert_student_a.institution_id
    url = f"/api/v1/institutions/{inst_id}/students/{cert_student_a.id}/certificate"

    client.get(url, headers={"Authorization": f"Bearer {token}"})

    # Query latest audit log entry
    latest_audit = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == "certificate.generate",
            AuditLog.entity_id == str(cert_student_a.id),
        )
        .order_by(AuditLog.id.desc())
    )
    assert latest_audit is not None
    assert latest_audit.actor_id == str(cert_college_admin_a.id)
    assert latest_audit.actor_role == cert_college_admin_a.role
    assert latest_audit.after_json["enrolment_no"] == cert_student_a.enrolment_no

    # Verify hash-chain remains valid
    verify_result = verify_chain(db_session)
    assert verify_result["verified"] is True


def test_qr_verification_round_trip(
    client: TestClient, db_session: Session, cert_student_a: Student
):
    """Scanning the QR leads to the verify flow; prove the verification ID resolves."""
    # Ensure verified record
    vr = cert_student_a.verified_record
    assert vr is not None

    # Call verify endpoint with the VID from the certificate
    response = client.get(f"/api/v1/verification/verify?vid={vr.verification_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["verified"] is True
    assert data["status"] == "active"
    assert data["verification_id"] == vr.verification_id
    assert data["institution"] == cert_student_a.institution.name
    assert "signature_preview" in data
    # Enforce DPDP minimal disclosure (zero PII in verification flow)
    assert "dob" not in data
    assert "reservation_category" not in data
    assert "official_email" not in data
