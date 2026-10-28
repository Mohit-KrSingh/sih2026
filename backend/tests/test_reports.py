"""Comprehensive tests for AICTE Reports Engine (CSV, XLSX, PDF).

Spec: Section 17 & TASKS.md T31:
- All reports in section 17 as CSV, XLSX and PDF, with filters (state, course, year).
- Download buttons on the AICTE screens; a college downloads its own report.
- Tests that report totals match the database.
- IDOR and RBAC protections.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.models import (
    Course,
    CourseIntake,
    Institution,
    Student,
    Submission,
    User,
)
from app.students import duplicate_service

# ---------------------------------------------------------------------------
# Test Data Fixtures
# ---------------------------------------------------------------------------


def get_auth_header(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def reporting_dataset(db_session: Session) -> dict[str, Any]:
    """Seed dedicated reporting data with known institutions, courses, and students."""
    # 1. Institutions
    inst1 = Institution(
        aicte_id="1-REP-PUNE",
        name="Pune Institute of Technology",
        state="Maharashtra",
        district="Pune",
        address="123 University Road, Pune",
        official_email="contact@pune-rep.edu.in",
        official_phone="+919876543210",
        head_name="Dr. Principal Pune",
        affiliating_university="Savitribai Phule Pune University",
        approval_status="active",
        approval_valid_to=date(2028, 6, 30),
        account_status="active",
    )
    inst2 = Institution(
        aicte_id="1-REP-BLR",
        name="Bengaluru College of Engineering",
        state="Karnataka",
        district="Bengaluru",
        address="456 Tech Park, Bengaluru",
        official_email="contact@blr-rep.edu.in",
        official_phone="+919876543211",
        head_name="Dr. Principal Blr",
        affiliating_university="VTU Belagavi",
        approval_status="active",
        approval_valid_to=date(2028, 6, 30),
        account_status="active",
    )
    db_session.add_all([inst1, inst2])
    db_session.commit()
    db_session.refresh(inst1)
    db_session.refresh(inst2)

    # 2. Courses
    c1 = Course(
        institution_id=inst1.id,
        name="Computer Science and Engineering",
        level="UG",
        branch="CSE",
        duration_years=4,
        supernumerary_allowed=True,
    )
    c2 = Course(
        institution_id=inst2.id,
        name="Information Technology",
        level="UG",
        branch="IT",
        duration_years=4,
        supernumerary_allowed=True,
    )
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    # 3. Intake Quotas (2025-26 base year & 2026-27 current year)
    intakes = [
        CourseIntake(
            course_id=c1.id,
            academic_year="2025-26",
            approved_intake=60,
            supernumerary_seats_allowed=6,
            source="aicte_master",
        ),
        CourseIntake(
            course_id=c1.id,
            academic_year="2026-27",
            approved_intake=60,
            supernumerary_seats_allowed=6,
            source="aicte_master",
        ),
        CourseIntake(
            course_id=c2.id,
            academic_year="2025-26",
            approved_intake=120,
            supernumerary_seats_allowed=12,
            source="aicte_master",
        ),
        CourseIntake(
            course_id=c2.id,
            academic_year="2026-27",
            approved_intake=120,
            supernumerary_seats_allowed=12,
            source="aicte_master",
        ),
    ]
    db_session.add_all(intakes)
    db_session.commit()

    # 4. Students
    students = [
        # 2025-26 History
        Student(
            institution_id=inst1.id,
            course_id=c1.id,
            academic_year="2025-26",
            apaar_id="111122223301",
            name="Rahul Sharma",
            dob_encrypted="enc_dob",
            gender="Male",
            enrolment_no="EN25001",
            admission_date=date(2025, 7, 15),
            admission_mode="State Counselling",
            seat_type="Regular",
            reservation_category="General",
            status="submitted",
        ),
        Student(
            institution_id=inst2.id,
            course_id=c2.id,
            academic_year="2025-26",
            apaar_id="111122223302",
            name="Priya Patel",
            dob_encrypted="enc_dob",
            gender="Female",
            enrolment_no="EN25002",
            admission_date=date(2025, 7, 18),
            admission_mode="State Counselling",
            seat_type="Regular",
            reservation_category="OBC",
            status="submitted",
        ),
        # 2026-27 Current Year
        Student(
            institution_id=inst1.id,
            course_id=c1.id,
            academic_year="2026-27",
            apaar_id="111122223303",
            name="Amit Verma",
            dob_encrypted="enc_dob",
            gender="Male",
            enrolment_no="EN26001",
            admission_date=date(2026, 7, 10),
            admission_mode="Central Counselling",
            seat_type="Regular",
            reservation_category="General",
            status="valid",
        ),
        Student(
            institution_id=inst1.id,
            course_id=c1.id,
            academic_year="2026-27",
            apaar_id="111122223304",
            name="Ananya Sen",
            dob_encrypted="enc_dob",
            gender="Female",
            enrolment_no="EN26002",
            admission_date=date(2026, 7, 12),
            admission_mode="Institutional Quota",
            seat_type="Supernumerary",
            reservation_category="General",
            status="valid",
        ),
        Student(
            institution_id=inst2.id,
            course_id=c2.id,
            academic_year="2026-27",
            apaar_id="111122223305",
            name="Kavita Reddy",
            dob_encrypted="enc_dob",
            gender="Female",
            enrolment_no="EN26003",
            admission_date=date(2026, 7, 15),
            admission_mode="State Counselling",
            seat_type="Regular",
            reservation_category="SC",
            status="valid",
        ),
    ]
    db_session.add_all(students)
    db_session.commit()

    # 5. Submissions
    sub1 = Submission(
        institution_id=inst1.id,
        academic_year="2026-27",
        status="submitted",
        receipt_no="REC-2026-1-REP-PUNE-ABCD",
    )
    db_session.add(sub1)
    db_session.commit()

    # 6. Users
    u_aicte = User(
        email="officer_rep_test@aicte-india.org",
        password_hash=hash_password("Pass123!"),
        role="aicte_officer",
        is_active=True,
    )
    u_col1 = User(
        email="admin@pune-rep.edu.in",
        password_hash=hash_password("Pass123!"),
        role="college_admin",
        institution_id=inst1.id,
        is_active=True,
    )
    u_col2 = User(
        email="admin@blr-rep.edu.in",
        password_hash=hash_password("Pass123!"),
        role="college_admin",
        institution_id=inst2.id,
        is_active=True,
    )
    db_session.add_all([u_aicte, u_col1, u_col2])
    db_session.commit()
    db_session.refresh(u_aicte)
    db_session.refresh(u_col1)
    db_session.refresh(u_col2)

    return {
        "inst1": inst1,
        "inst2": inst2,
        "course1": c1,
        "course2": c2,
        "u_aicte": u_aicte,
        "u_col1": u_col1,
        "u_col2": u_col2,
    }


# ---------------------------------------------------------------------------
# 1. Enrolment by State and Course Tests
# ---------------------------------------------------------------------------


def test_report_enrolment_by_state_course_csv(
    client: TestClient, db_session: Session, reporting_dataset: dict[str, Any]
):
    """Verify Enrolment by State and Course CSV matches direct DB totals."""
    u_aicte = reporting_dataset["u_aicte"]
    headers = get_auth_header(u_aicte)
    resp = client.get(
        "/api/v1/reports/enrolment-by-state-course?format=csv&academic_year=2026-27",
        headers=headers,
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM

    # Parse CSV
    csv_text = resp.content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(csv_text))
    rows = [r for r in reader if r and not r[0].startswith("#")]
    assert len(rows) >= 2

    header_col = rows[0]
    assert "State" in header_col
    assert "Approved Intake" in header_col
    assert "Total Admitted" in header_col

    # Totals row is the last row
    totals_row = rows[-1]
    assert "Total" in totals_row[0]

    # Database ground truth
    db_intake = (
        db_session.scalar(
            select(func.coalesce(func.sum(CourseIntake.approved_intake), 0))
            .join(Course, CourseIntake.course_id == Course.id)
            .join(Institution, Course.institution_id == Institution.id)
            .where(
                CourseIntake.academic_year == "2026-27",
                Institution.approval_status == "active",
            )
        )
        or 0
    )

    db_admitted = (
        db_session.scalar(
            select(func.count(Student.id))
            .join(Institution, Student.institution_id == Institution.id)
            .where(
                Student.academic_year == "2026-27",
                Student.status.not_in(["withdrawn", "transferred"]),
                Institution.approval_status == "active",
            )
        )
        or 0
    )

    csv_intake = int(totals_row[header_col.index("Approved Intake")])
    csv_admitted = int(totals_row[header_col.index("Total Admitted")])

    assert csv_intake == db_intake
    assert csv_admitted == db_admitted


def test_report_enrolment_by_state_course_xlsx_and_pdf(
    client: TestClient, reporting_dataset: dict[str, Any]
):
    """Verify XLSX and PDF exports for Enrolment by State and Course."""
    u_aicte = reporting_dataset["u_aicte"]
    headers = get_auth_header(u_aicte)

    # XLSX
    resp_xlsx = client.get(
        "/api/v1/reports/enrolment-by-state-course?format=xlsx&academic_year=2026-27",
        headers=headers,
    )
    assert resp_xlsx.status_code == 200
    assert "spreadsheetml" in resp_xlsx.headers["content-type"]
    wb = openpyxl.load_workbook(io.BytesIO(resp_xlsx.content))
    assert wb.active is not None
    assert wb.active.max_row > 4

    # PDF
    resp_pdf = client.get(
        "/api/v1/reports/enrolment-by-state-course?format=pdf&academic_year=2026-27",
        headers=headers,
    )
    assert resp_pdf.status_code == 200
    assert "application/pdf" in resp_pdf.headers["content-type"]
    assert resp_pdf.content.startswith(b"%PDF")
    assert len(resp_pdf.content) > 1000


def test_report_enrolment_with_state_filter(
    client: TestClient, db_session: Session, reporting_dataset: dict[str, Any]
):
    """Verify filtering by state correctly restricts rows and matches filtered totals."""
    u_aicte = reporting_dataset["u_aicte"]
    test_state = "Maharashtra"

    headers = get_auth_header(u_aicte)
    resp = client.get(
        f"/api/v1/reports/enrolment-by-state-course?format=csv&academic_year=2026-27&state={test_state}",
        headers=headers,
    )
    assert resp.status_code == 200
    csv_text = resp.content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(csv_text))
    rows = [r for r in reader if r and not r[0].startswith("#")]
    header = rows[0]
    data_rows = rows[1:-1]
    totals_row = rows[-1]

    # Every data row must be in the specified state
    for dr in data_rows:
        assert dr[header.index("State")] == test_state

    # Database filtered count for Maharashtra
    db_filtered_admitted = (
        db_session.scalar(
            select(func.count(Student.id))
            .join(Institution, Student.institution_id == Institution.id)
            .where(
                Student.academic_year == "2026-27",
                Student.status.not_in(["withdrawn", "transferred"]),
                Institution.approval_status == "active",
                Institution.state == test_state,
            )
        )
        or 0
    )
    assert int(totals_row[header.index("Total Admitted")]) == db_filtered_admitted


# ---------------------------------------------------------------------------
# 2. Seat Utilisation Tests
# ---------------------------------------------------------------------------


def test_report_seat_utilisation_totals_match(
    client: TestClient, db_session: Session, reporting_dataset: dict[str, Any]
):
    """Verify Seat Utilisation report totals and over-intake tracking."""
    u_aicte = reporting_dataset["u_aicte"]
    headers = get_auth_header(u_aicte)
    resp = client.get(
        "/api/v1/reports/seat-utilisation?format=csv&academic_year=2026-27",
        headers=headers,
    )
    assert resp.status_code == 200
    csv_text = resp.content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(csv_text))
    rows = [r for r in reader if r and not r[0].startswith("#")]
    header = rows[0]
    totals_row = rows[-1]

    db_intake = (
        db_session.scalar(
            select(func.coalesce(func.sum(CourseIntake.approved_intake), 0))
            .join(Course, CourseIntake.course_id == Course.id)
            .join(Institution, Course.institution_id == Institution.id)
            .where(
                CourseIntake.academic_year == "2026-27",
                Institution.approval_status == "active",
            )
        )
        or 0
    )

    db_admitted = (
        db_session.scalar(
            select(func.count(Student.id))
            .join(Institution, Student.institution_id == Institution.id)
            .where(
                Student.academic_year == "2026-27",
                Student.status.not_in(["withdrawn", "transferred"]),
                Institution.approval_status == "active",
            )
        )
        or 0
    )

    csv_intake = int(totals_row[header.index("Approved Intake")])
    csv_admitted = int(totals_row[header.index("Total Admitted")])

    assert csv_intake == db_intake
    assert csv_admitted == db_admitted


# ---------------------------------------------------------------------------
# 3. Colleges with Exceptions Tests
# ---------------------------------------------------------------------------


def test_report_colleges_with_exceptions(
    client: TestClient, reporting_dataset: dict[str, Any]
):
    """Verify Colleges with Exceptions report executes and returns valid CSV/PDF."""
    u_aicte = reporting_dataset["u_aicte"]
    headers = get_auth_header(u_aicte)
    resp = client.get(
        "/api/v1/reports/colleges-with-exceptions?format=csv&academic_year=2026-27",
        headers=headers,
    )
    assert resp.status_code == 200
    csv_text = resp.content.decode("utf-8-sig")
    assert "Rule Code" in csv_text
    assert "Exception Message" in csv_text


# ---------------------------------------------------------------------------
# 4. Duplicate Enrolments Tests
# ---------------------------------------------------------------------------


def test_report_duplicate_enrolments(
    client: TestClient, db_session: Session, reporting_dataset: dict[str, Any]
):
    """Verify Duplicate Enrolments report privacy masking and case count."""
    u_aicte = reporting_dataset["u_aicte"]
    headers = get_auth_header(u_aicte)
    resp = client.get(
        "/api/v1/reports/duplicate-enrolments?format=csv&academic_year=2026-27",
        headers=headers,
    )
    assert resp.status_code == 200
    csv_text = resp.content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(csv_text))
    rows = [r for r in reader if r and not r[0].startswith("#")]
    header = rows[0]
    data_rows = rows[1:-1] if len(rows) > 1 else []

    expected_dups = duplicate_service.get_duplicate_records(db_session, academic_year="2026-27")
    assert len(data_rows) == len(expected_dups)

    # Check APAAR masking
    for dr in data_rows:
        masked_val = dr[header.index("Masked APAAR ID")]
        assert "XXXX" in masked_val


# ---------------------------------------------------------------------------
# 5. Year-over-Year Trends Tests
# ---------------------------------------------------------------------------


def test_report_year_over_year_trends(
    client: TestClient, db_session: Session, reporting_dataset: dict[str, Any]
):
    """Verify YoY Trends report compares 2025-26 history against 2026-27 admissions."""
    u_aicte = reporting_dataset["u_aicte"]
    headers = get_auth_header(u_aicte)
    resp = client.get(
        "/api/v1/reports/year-over-year-trends?format=csv&base_year=2025-26&target_year=2026-27",
        headers=headers,
    )
    assert resp.status_code == 200
    csv_text = resp.content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(csv_text))
    rows = [r for r in reader if r and not r[0].startswith("#")]
    header = rows[0]
    totals_row = rows[-1]

    db_base_admitted = (
        db_session.scalar(
            select(func.count(Student.id))
            .join(Institution, Student.institution_id == Institution.id)
            .where(
                Student.academic_year == "2025-26",
                Student.status.not_in(["withdrawn", "transferred"]),
                Institution.approval_status == "active",
            )
        )
        or 0
    )

    db_target_admitted = (
        db_session.scalar(
            select(func.count(Student.id))
            .join(Institution, Student.institution_id == Institution.id)
            .where(
                Student.academic_year == "2026-27",
                Student.status.not_in(["withdrawn", "transferred"]),
                Institution.approval_status == "active",
            )
        )
        or 0
    )

    csv_base_admitted = int(totals_row[header.index("2025-26 Admitted")])
    csv_target_admitted = int(totals_row[header.index("2026-27 Admitted")])

    assert csv_base_admitted == db_base_admitted
    assert csv_target_admitted == db_target_admitted
    assert int(totals_row[header.index("Net Change")]) == (db_target_admitted - db_base_admitted)


# ---------------------------------------------------------------------------
# 6. Accreditation Snapshot Tests
# ---------------------------------------------------------------------------


def test_report_accreditation_snapshot_and_idor(
    client: TestClient,
    reporting_dataset: dict[str, Any],
):
    """Verify Accreditation Snapshot: college downloads own, 403 on other, AICTE downloads any."""
    inst1 = reporting_dataset["inst1"]
    inst2 = reporting_dataset["inst2"]
    u_col1 = reporting_dataset["u_col1"]
    u_aicte = reporting_dataset["u_aicte"]

    # College admin downloads own accreditation report
    c_headers = get_auth_header(u_col1)
    resp = client.get(
        f"/api/v1/reports/accreditation-snapshot?format=pdf&institution_id={inst1.id}&academic_year=2026-27",
        headers=c_headers,
    )
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")

    # College admin downloads own via convenience route
    resp_conv = client.get(
        f"/api/v1/institutions/{inst1.id}/reports/accreditation?format=xlsx&academic_year=2026-27",
        headers=c_headers,
    )
    assert resp_conv.status_code == 200
    assert "spreadsheetml" in resp_conv.headers["content-type"]

    # IDOR Test: College admin gets 403 on another college's accreditation snapshot
    resp_idor = client.get(
        f"/api/v1/reports/accreditation-snapshot?format=pdf&institution_id={inst2.id}&academic_year=2026-27",
        headers=c_headers,
    )
    assert resp_idor.status_code == 403

    # AICTE officer can download any college's accreditation snapshot
    a_headers = get_auth_header(u_aicte)
    resp_aicte = client.get(
        f"/api/v1/reports/accreditation-snapshot?format=pdf&institution_id={inst1.id}&academic_year=2026-27",
        headers=a_headers,
    )
    assert resp_aicte.status_code == 200


# ---------------------------------------------------------------------------
# 7. College Submission Report Tests
# ---------------------------------------------------------------------------


def test_report_college_submission_matches_roster(
    client: TestClient,
    db_session: Session,
    reporting_dataset: dict[str, Any],
):
    """Verify College Submission Report roster count matches student database records."""
    inst1 = reporting_dataset["inst1"]
    u_col1 = reporting_dataset["u_col1"]
    headers = get_auth_header(u_col1)

    resp = client.get(
        f"/api/v1/reports/college-submission?format=csv&institution_id={inst1.id}&academic_year=2026-27",
        headers=headers,
    )
    assert resp.status_code == 200
    csv_text = resp.content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(csv_text))
    rows = [r for r in reader if r and not r[0].startswith("#")]
    data_rows = rows[1:-1] if len(rows) > 1 else []

    db_student_count = (
        db_session.scalar(
            select(func.count(Student.id)).where(
                Student.institution_id == inst1.id,
                Student.academic_year == "2026-27",
            )
        )
        or 0
    )

    assert len(data_rows) == db_student_count

    # Verify convenience route
    resp_conv = client.get(
        f"/api/v1/institutions/{inst1.id}/reports/submission?format=pdf&academic_year=2026-27",
        headers=headers,
    )
    assert resp_conv.status_code == 200
    assert resp_conv.content.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# 8. Interactive Preview Endpoint Tests
# ---------------------------------------------------------------------------


def test_report_preview_json_endpoint(
    client: TestClient, reporting_dataset: dict[str, Any]
):
    """Verify /api/v1/reports/preview returns structured JSON for UI display."""
    u_aicte = reporting_dataset["u_aicte"]
    headers = get_auth_header(u_aicte)
    resp = client.get(
        "/api/v1/reports/preview?report_type=enrolment-by-state-course&academic_year=2026-27",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["report_type"] == "enrolment-by-state-course"
    assert "columns" in data and len(data["columns"]) > 0
    assert "rows" in data
    assert "summary_boxes" in data and len(data["summary_boxes"]) > 0
    assert "totals_row" in data and data["totals_row"] is not None


# ---------------------------------------------------------------------------
# 9. RBAC & Route Security Tests
# ---------------------------------------------------------------------------


def test_reports_rbac_enforcement(
    client: TestClient, reporting_dataset: dict[str, Any]
):
    """Verify college user is denied access to national AICTE reports."""
    u_col1 = reporting_dataset["u_col1"]
    headers = get_auth_header(u_col1)

    # College user cannot download national reports -> 403 Forbidden
    resp1 = client.get(
        "/api/v1/reports/enrolment-by-state-course?format=csv",
        headers=headers,
    )
    assert resp1.status_code == 403

    resp2 = client.get(
        "/api/v1/reports/seat-utilisation?format=csv",
        headers=headers,
    )
    assert resp2.status_code == 403

    resp3 = client.get(
        "/api/v1/reports/colleges-with-exceptions?format=csv",
        headers=headers,
    )
    assert resp3.status_code == 403

    resp4 = client.get(
        "/api/v1/reports/duplicate-enrolments?format=csv",
        headers=headers,
    )
    assert resp4.status_code == 403

    resp5 = client.get(
        "/api/v1/reports/year-over-year-trends?format=csv",
        headers=headers,
    )
    assert resp5.status_code == 403


def test_reports_unauthenticated_requests(client: TestClient):
    """Verify unauthenticated requests are strictly rejected with 401."""
    resp = client.get("/api/v1/reports/enrolment-by-state-course?format=csv")
    assert resp.status_code == 401
