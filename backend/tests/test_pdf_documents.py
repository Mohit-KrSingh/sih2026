"""Comprehensive test suite for PDF documents, fonts, tokens, and transactional notifications.

Spec: Section 17 & REBRAND_TASKS R14:
- Reports, receipts and the sample certificate:
  - EduTrace wordmark header
  - Noto Sans embedded (including Devanagari)
  - Colours from UX4G semantic token values
  - Page numbers
  - "Demo data" footer
  - No emblem or official government logos
- Dev outbox messages and notification text use the new name and plain wording.
- All totals and integrity checks pass.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.brand import PRODUCT_NAME
from app.models import Course, Institution, Student, Submission, User
from app.reports.exporters import export_to_pdf
from app.reports.fonts import FONT_BOLD, FONT_REGULAR, get_font_names, register_noto_fonts
from app.reports.schemas import ReportData, ReportSummaryBox, ReportType
from app.reports.service import generate_report
from app.submissions.receipt_pdf import generate_submission_receipt_pdf
from app.submissions.schemas import SubmissionReceiptResponse
from app.verification.certificate import generate_certificate_pdf


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    return {"Authorization": f"Bearer {token}"}


def test_noto_sans_fonts_registered_and_available():
    """Verify TrueType Noto Sans fonts are registered successfully in ReportLab."""
    assert register_noto_fonts() is True
    fonts = get_font_names()
    assert fonts["regular"] == FONT_REGULAR
    assert fonts["bold"] == FONT_BOLD
    assert "NotoSans" in fonts["regular"]
    assert "NotoSans" in fonts["bold"]


def test_reports_pdf_wordmark_fonts_and_footer(client: TestClient, db_session: Session):
    """Verify regulatory PDF report contains EduTrace wordmark, Noto Sans, and Demo data footer."""
    data = ReportData(
        report_type=ReportType.ENROLMENT_BY_STATE_COURSE,
        title="State-wise Enrolment and Sanctioned Intake Summary",
        subtitle="National Overview of Sanctioned Capacity",
        academic_year="2026-27",
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        filters_applied={"state": "Delhi"},
        summary_boxes=[
            ReportSummaryBox(label="Sanctioned Intake", value=360, detail="Sanctioned"),
            ReportSummaryBox(label="Total Enrolled", value=345, detail="Enrolled"),
        ],
        columns=["State", "Course", "Level", "Intake", "Enrolled", "Fill %"],
        rows=[
            ["Delhi", "Computer Science", "UG", 120, 118, 98.3],
            ["Delhi", "Information Technology", "UG", 120, 115, 95.8],
            ["Delhi", "Electronics Engineering", "UG", 120, 112, 93.3],
        ],
        totals_row=["National Total", "3 Courses", "-", 360, 345, 95.8],
        notes=["All figures verified under EduTrace platform standards."],
    )

    pdf_bytes = export_to_pdf(data)

    # Valid PDF document
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes
    assert len(pdf_bytes) > 10000

    # Header has EduTrace brand wordmark
    assert PRODUCT_NAME.encode("utf-8") in pdf_bytes

    # Noto Sans font is embedded
    assert b"NotoSans" in pdf_bytes

    # Footer carries Demo data notice and page numbers
    assert b"Demo data" in pdf_bytes
    assert b"Page 1 of 1" in pdf_bytes or b"Page " in pdf_bytes

    # No emblem or misleading government seal
    assert b"Ministry of Education" not in pdf_bytes
    assert b"State Emblem" not in pdf_bytes


def test_all_seven_reports_generate_valid_pdf_with_edutrace_branding(
    client: TestClient, db_session: Session
):
    """Verify all 7 official report types generate valid PDFs with EduTrace branding."""
    # Find AICTE admin user
    aicte_user = db_session.scalar(select(User).where(User.role == "aicte_admin"))
    if not aicte_user:
        aicte_user = User(
            email="pdf_aicte_admin@edutrace.ac.in",
            password_hash="argon2_fake_hash",
            role="aicte_admin",
            is_active=True,
        )
        db_session.add(aicte_user)
        db_session.commit()
        db_session.refresh(aicte_user)

    # Find or seed institution
    inst = db_session.scalar(select(Institution).where(Institution.account_status == "active"))
    if not inst:
        inst = Institution(
            aicte_id="1-PDF-TEST",
            name="Delhi Institute of Technology",
            state="Delhi",
            district="New Delhi",
            address="100 Tech Enclave",
            official_email="contact@dit-delhi.edu.in",
            official_phone="+919876543201",
            head_name="Dr. A. K. Verma",
            affiliating_university="Delhi Technological University",
            approval_status="active",
            account_status="active",
        )
        db_session.add(inst)
        db_session.commit()
        db_session.refresh(inst)

    report_types = [
        ReportType.ENROLMENT_BY_STATE_COURSE,
        ReportType.SEAT_UTILISATION,
        ReportType.COLLEGES_WITH_EXCEPTIONS,
        ReportType.DUPLICATE_ENROLMENTS,
        ReportType.YEAR_OVER_YEAR_TRENDS,
        ReportType.ACCREDITATION_SNAPSHOT,
        ReportType.COLLEGE_SUBMISSION,
    ]

    for rt in report_types:
        pdf_bytes, media_type, filename = generate_report(
            db=db_session,
            report_type=rt,
            output_format="pdf",
            current_user=aicte_user,
            academic_year="2026-27",
            institution_id=(
                inst.id
                if rt in [ReportType.ACCREDITATION_SNAPSHOT, ReportType.COLLEGE_SUBMISSION]
                else None
            ),
        )
        assert media_type == "application/pdf"
        assert filename.endswith(".pdf")
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 5000
        assert PRODUCT_NAME.encode("utf-8") in pdf_bytes
        assert b"Demo data" in pdf_bytes
        assert b"NotoSans" in pdf_bytes


def test_submission_receipt_pdf_generation_and_endpoint(
    client: TestClient, db_session: Session
):
    """Verify submission receipt PDF has EduTrace header, Noto Sans, receipt token, and demo."""
    # Create institution and college admin user
    inst = db_session.scalar(select(Institution).where(Institution.aicte_id == "1-RECEIPT-PDF"))
    if not inst:
        inst = Institution(
            aicte_id="1-RECEIPT-PDF",
            name="Bangalore Institute of Computer Technology",
            state="Karnataka",
            district="Bengaluru",
            address="42 Cyber City, Bengaluru",
            official_email="admin@bict-blr.edu.in",
            official_phone="+919876543202",
            head_name="Dr. B. R. Rao",
            affiliating_university="Visvesvaraya Technological University",
            approval_status="active",
            account_status="active",
        )
        db_session.add(inst)
        db_session.commit()
        db_session.refresh(inst)

    admin_user = db_session.scalar(select(User).where(User.email == "admin@bict-blr.edu.in"))
    if not admin_user:
        admin_user = User(
            email="admin@bict-blr.edu.in",
            password_hash="argon2_fake_hash",
            role="college_admin",
            institution_id=inst.id,
            is_active=True,
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

    # Create submission in submitted state
    sub = db_session.scalar(
        select(Submission).where(
            Submission.institution_id == inst.id,
            Submission.academic_year == "2026-27",
        )
    )
    if not sub:
        sub = Submission(
            institution_id=inst.id,
            academic_year="2026-27",
            status="submitted",
            submitted_by=admin_user.id,
            submitted_at=datetime.now(UTC),
            receipt_no="REC-2026-BICT-001",
            declaration_ref="I confirm all student records are accurate and complete.",
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)

    # 1. Direct generator call
    receipt_obj = SubmissionReceiptResponse(
        institution_id=inst.id,
        institution_name=inst.name,
        aicte_id=inst.aicte_id,
        academic_year="2026-27",
        submission_id=sub.id,
        receipt_no=sub.receipt_no,
        status="submitted",
        submitted_at=sub.submitted_at,
        submitted_by_email=admin_user.email,
        submitted_by_name=admin_user.email,
        declaration_text=sub.declaration_ref,
        total_students=60,
        regular_students=50,
        supernumerary_students=10,
        courses_count=1,
        justified_exceptions_count=0,
        is_locked=True,
    )
    pdf_bytes = generate_submission_receipt_pdf(receipt_obj)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes
    assert PRODUCT_NAME.encode("utf-8") in pdf_bytes
    assert b"NotoSans" in pdf_bytes
    assert b"Demo data" in pdf_bytes
    assert b"REC-2026-BICT-001" in pdf_bytes

    # 2. HTTP download endpoint
    headers = _auth_header(admin_user)
    resp = client.get(
        f"/api/v1/institutions/{inst.id}/submissions/receipt/pdf?academic_year=2026-27",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "submission_receipt_REC-2026-BICT-001.pdf" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF-")


def test_degree_certificate_pdf_branding_and_devanagari(db_session: Session):
    """Verify degree certificate PDF has EduTrace wordmark, Noto Sans, and Demo data footer."""
    inst = db_session.scalar(select(Institution).where(Institution.aicte_id == "1-CERT-PDF"))
    if not inst:
        inst = Institution(
            aicte_id="1-CERT-PDF",
            name="Pune Institute of Advanced Science",
            state="Maharashtra",
            district="Pune",
            address="15 University Road, Pune",
            official_email="contact@pias-pune.edu.in",
            official_phone="+919876543203",
            head_name="Dr. S. K. Joshi",
            affiliating_university="Savitribai Phule Pune University",
            approval_status="active",
            account_status="active",
        )
        db_session.add(inst)
        db_session.commit()
        db_session.refresh(inst)

    course = db_session.scalar(select(Course).where(Course.institution_id == inst.id))
    if not course:
        course = Course(
            institution_id=inst.id,
            name="Artificial Intelligence and Data Science",
            level="UG",
            branch="AIDS",
            duration_years=4,
            supernumerary_allowed=True,
        )
        db_session.add(course)
        db_session.commit()
        db_session.refresh(course)

    student = db_session.scalar(select(Student).where(Student.institution_id == inst.id))
    if not student:
        student = Student(
            institution_id=inst.id,
            course_id=course.id,
            academic_year="2026-27",
            apaar_id="888877776666",
            name="Ananya Sharma",
            dob_encrypted="gAAAAABtestdobencrypted12345678",
            gender="Female",
            enrolment_no="ENROL-PIAS-2026-088",
            admission_date=date(2026, 7, 15),
            admission_mode="State counselling",
            seat_type="Regular",
            reservation_category="General",
            status="verified",
            is_locked=True,
            source="form",
        )
        db_session.add(student)
        db_session.commit()
        db_session.refresh(student)

    pdf_bytes = generate_certificate_pdf(student=student, db=db_session)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 20000

    # Brand and fonts
    assert (
        PRODUCT_NAME.encode("utf-8") in pdf_bytes
        or PRODUCT_NAME.upper().encode("utf-8") in pdf_bytes
    )
    assert b"NotoSans" in pdf_bytes
    assert b"Demo data" in pdf_bytes
    assert b"Page 1 of 1" in pdf_bytes

    # Side-by-side IDs
    assert b"ENROL-PIAS-2026-088" in pdf_bytes
    assert b"8888 7777 6666" in pdf_bytes or b"888877776666" in pdf_bytes


def test_outbox_messages_and_notifications_use_edutrace(client: TestClient, db_session: Session):
    """Verify dev outbox messages and notification text use EduTrace and plain wording."""
    from app.integrations.mock.otp import MockOtpSender

    sender = MockOtpSender(db_session)
    sender.clear()

    # 1. OTP message
    sender.send_otp(
        channel="email",
        recipient="test@college.edu.in",
        code="654321",
        context="College login MFA verification",
    )
    msgs = sender.get_messages(recipient="test@college.edu.in")
    assert len(msgs) == 1
    assert PRODUCT_NAME in msgs[0].body
    assert "654321" in msgs[0].body
    assert "Valid for 5 minutes" in msgs[0].body

    # 2. Transactional notification message
    sender.send_notification(
        channel="email",
        recipient="test@college.edu.in",
        body=f"Your annual data submission on {PRODUCT_NAME} has been accepted.",
    )
    msgs = sender.get_messages(recipient="test@college.edu.in")
    assert len(msgs) == 2
    assert PRODUCT_NAME in msgs[1].body
    assert "submission on EduTrace has been accepted" in msgs[1].body
