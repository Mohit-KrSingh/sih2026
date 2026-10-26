"""Unit and integration tests for the seed script, demo data, and validation of 2025-26 history.

Acceptance criteria (TASKS.md T03):
- make seed creates colleges, courses, intake per year, mock APAAR registry,
  2025-26 history, 2026-27 mixed states, planted anomalies, demo accounts,
  and generates the four demo CSVs in demo/.
- Idempotent: running twice does not duplicate. Prints counts.
- Test that the seeded history passes the engine without error-level flags.
"""

import csv

from argon2 import PasswordHasher
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ConsentRequest,
    Course,
    CourseIntake,
    Institution,
    Justification,
    MockApaarRegistry,
    Student,
    Submission,
    User,
    ValidationFlag,
    VerifiedRecord,
    Verifier,
)
from app.seed import DEMO_DIR, DEMO_PASSWORD, seed_all, validate_student_record

ph = PasswordHasher()


def test_seed_idempotency_and_counts(db_session: Session) -> None:
    """Test that seed_all creates all required data and is strictly idempotent."""
    # First seed execution
    summary1 = seed_all(db_session)

    assert summary1["institutions"] == 30
    assert summary1["courses"] >= 70
    assert summary1["course_intake"] >= 140
    assert summary1["mock_apaar_registry"] >= 8000
    assert summary1["students_2025_26"] == 3000
    assert summary1["students_2026_27"] >= 900
    assert summary1["submissions"] >= 20
    assert summary1["validation_flags"] >= 5
    assert summary1["demo_accounts"] >= 6
    assert len(summary1["demo_csvs"]) == 4

    # Second seed execution (idempotency test)
    summary2 = seed_all(db_session)

    assert summary2["institutions"] == summary1["institutions"]
    assert summary2["courses"] == summary1["courses"]
    assert summary2["course_intake"] == summary1["course_intake"]
    assert summary2["mock_apaar_registry"] == summary1["mock_apaar_registry"]
    assert summary2["students_2025_26"] == 3000
    assert summary2["students_2026_27"] == summary1["students_2026_27"]
    assert summary2["submissions"] == summary1["submissions"]
    assert summary2["validation_flags"] == summary1["validation_flags"]
    assert summary2["demo_accounts"] == summary1["demo_accounts"]


def test_demo_accounts_authentication(db_session: Session) -> None:
    """Verify demo accounts exist with correct roles and Argon2 hashed password."""
    seed_all(db_session)

    expected_accounts = [
        ("aicte_admin@aicte-india.org", "aicte_admin"),
        ("aicte_officer@aicte-india.org", "aicte_officer"),
        ("admin@piaet-pune.edu.in", "college_admin"),
        ("admin@mmit-mumbai.ac.in", "college_admin"),
        ("admin@ngec-nagpur.gov.in", "college_admin"),
        ("verifier@tcs-verifications.com", "verifier"),
    ]

    for email, role in expected_accounts:
        user = db_session.scalar(select(User).where(User.email == email))
        assert user is not None, f"Account {email} must exist"
        assert user.role == role
        assert user.is_active is True
        # Verify Argon2 password hashing
        assert ph.verify(user.password_hash, DEMO_PASSWORD) is True

    # Verify approved verifier organization
    verifier = db_session.scalar(
        select(Verifier).where(Verifier.contact == "verifier@tcs-verifications.com")
    )
    assert verifier is not None
    assert verifier.status == "approved"
    assert "Tata Consultancy Services" in verifier.org_name

    # Verify demo student record and consent
    demo_student = db_session.scalar(select(Student).where(Student.apaar_id == "111122223333"))
    assert demo_student is not None
    assert demo_student.name == "Aarav Sharma"

    vr = db_session.scalar(
        select(VerifiedRecord).where(VerifiedRecord.student_id == demo_student.id)
    )
    assert vr is not None
    assert vr.verification_id == "VR-2025-111122223333"
    assert vr.status == "active"

    consent = db_session.scalar(
        select(ConsentRequest).where(ConsentRequest.apaar_id == "111122223333")
    )
    assert consent is not None
    assert consent.status == "approved"


def test_2025_26_history_passes_validation_without_error_flags(
    db_session: Session,
) -> None:
    """Test that ~3,000 students in 2025-26 history pass field validations with 0 errors."""
    seed_all(db_session)

    # Fetch all students in 2025-26
    students_2025 = db_session.scalars(
        select(Student).where(Student.academic_year == "2025-26")
    ).all()
    assert len(students_2025) == 3000

    # Fetch courses and mock registry map
    courses = db_session.scalars(select(Course)).all()
    registry_entries = db_session.scalars(select(MockApaarRegistry)).all()
    registry_map = {r.apaar_id: r for r in registry_entries}

    total_error_flags = 0
    flagged_students: list[tuple[str, list[str]]] = []

    for s in students_2025:
        reg_entry = registry_map.get(s.apaar_id)
        inst_courses = [c for c in courses if c.institution_id == s.institution_id]
        errors = validate_student_record(s, reg_entry, inst_courses)
        if errors:
            total_error_flags += len(errors)
            flagged_students.append((s.apaar_id, errors))

    assert total_error_flags == 0, (
        f"Found validation errors in 2025-26 history: {flagged_students[:5]}"
    )

    # Verify intake compliance for every course in 2025-26 (regular admitted <= approved intake)
    intakes = db_session.scalars(
        select(CourseIntake).where(CourseIntake.academic_year == "2025-26")
    ).all()
    for intake in intakes:
        regular_count = db_session.scalar(
            select(func.count(Student.id)).where(
                Student.course_id == intake.course_id,
                Student.academic_year == "2025-26",
                Student.seat_type == "Regular",
            )
        )
        assert regular_count <= intake.approved_intake, (
            f"Course {intake.course_id} exceeded approved intake in 2025-26: "
            f"{regular_count} > {intake.approved_intake}"
        )


def test_planted_anomalies_and_exceptions(db_session: Session) -> None:
    """Verify that all planted anomalies and exceptions from SPEC.md section 18 are present."""
    seed_all(db_session)

    # 1. Over-intake in College 2 (Mumbai Metropolitan)
    mumbai_inst = db_session.scalar(select(Institution).where(Institution.aicte_id == "1-10000002"))
    assert mumbai_inst is not None

    mumbai_sub = db_session.scalar(
        select(Submission).where(
            Submission.institution_id == mumbai_inst.id,
            Submission.academic_year == "2026-27",
        )
    )
    assert mumbai_sub is not None
    assert mumbai_sub.status == "submitted_with_exceptions"

    overintake_flag = db_session.scalar(
        select(ValidationFlag).where(
            ValidationFlag.submission_id == mumbai_sub.id,
            ValidationFlag.rule_code == "INTAKE_EXCEEDED",
        )
    )
    assert overintake_flag is not None
    assert overintake_flag.level == "exception"
    assert overintake_flag.status == "justified"
    assert overintake_flag.requires_justification is True

    justification = db_session.scalar(
        select(Justification).where(Justification.flag_id == overintake_flag.id)
    )
    assert justification is not None
    assert "court order" in justification.text.lower()

    # 2. Cross-college duplicate (Priya Patel, 555566667777)
    dupe_students = db_session.scalars(
        select(Student).where(
            Student.apaar_id == "555566667777",
            Student.academic_year == "2026-27",
        )
    ).all()
    assert len(dupe_students) == 2
    inst_ids = {s.institution_id for s in dupe_students}
    assert len(inst_ids) == 2  # Enrolled at two different institutions

    dupe_flags = db_session.scalars(
        select(ValidationFlag).where(ValidationFlag.rule_code == "DUP_ACTIVE_OTHER_COLLEGE")
    ).all()
    assert len(dupe_flags) >= 2

    # 3. Sudden enrolment jump anomaly
    jump_flag = db_session.scalar(
        select(ValidationFlag).where(ValidationFlag.rule_code == "ANOM_ENROLMENT_JUMP")
    )
    assert jump_flag is not None
    assert jump_flag.audience == "aicte"
    assert "jumped" in jump_flag.message.lower()

    # 4. DOB cluster anomaly
    dob_flag = db_session.scalar(
        select(ValidationFlag).where(ValidationFlag.rule_code == "ANOM_DOB_CLUSTER")
    )
    assert dob_flag is not None
    assert dob_flag.audience == "aicte"
    assert "cluster" in dob_flag.message.lower()

    # 5. Sequential APAAR anomaly
    seq_flag = db_session.scalar(
        select(ValidationFlag).where(ValidationFlag.rule_code == "ANOM_SEQUENTIAL_APAAR")
    )
    assert seq_flag is not None
    assert seq_flag.audience == "aicte"
    assert "sequential" in seq_flag.message.lower()


def test_demo_csv_files_contract() -> None:
    """Verify four demo CSV files in demo/ have correct headers and match specifications."""
    expected_header = [
        "apaar_id",
        "name",
        "dob",
        "gender",
        "course",
        "branch",
        "admission_year",
        "enrolment_no",
        "admission_date",
        "admission_mode",
        "seat_type",
        "reservation_category",
        "nri",
        "oci",
        "foreign_national",
        "country",
    ]

    csv_files = {
        "clean_upload.csv": 25,
        "messy_upload.csv": 17,
        "overintake_upload.csv": 70,
        "cross_college_dupe.csv": 1,
    }

    for filename, expected_rows in csv_files.items():
        file_path = DEMO_DIR / filename
        assert file_path.exists(), f"Demo file {filename} must exist"

        with open(file_path, newline="", encoding="utf-8") as f:
            reader = list(csv.reader(f))
            assert len(reader) >= 1
            assert reader[0] == expected_header, f"Header mismatch in {filename}"
            data_rows = reader[1:]
            assert len(data_rows) == expected_rows, (
                f"Row count mismatch in {filename}: expected {expected_rows}, got {len(data_rows)}"
            )
            # Verify each row has exactly 16 columns
            for row in data_rows:
                assert len(row) == 16, f"Row in {filename} does not have 16 columns: {row}"
