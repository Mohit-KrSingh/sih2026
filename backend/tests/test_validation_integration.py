"""Integration tests for validation engine entry points and justification retention.

Spec: Section 9.4, 10 & TASKS.md T18:
- validate_rows, validate_course, validate_submission entry points.
- Persist flags with row references.
- Idempotent re-run keeping valid justifications.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import encrypt_dob
from app.models import (
    Course,
    CourseIntake,
    Institution,
    Justification,
    MockApaarRegistry,
    SeatDeclaration,
    Student,
    Submission,
    ValidationFlag,
)
from app.validation.codes import (
    APAAR_FORMAT,
    DUP_ACTIVE_OTHER_COLLEGE,
    INTAKE_EXCEEDED,
    NAME_FORMAT,
    SEAT_DECLARATION_MISMATCH,
)
from app.validation.rules_doc import generate_rules_doc
from app.validation.service import (
    student_model_to_row,
    validate_course,
    validate_rows,
    validate_submission,
)


@pytest.fixture
def test_setup(db_session: Session) -> dict[str, Any]:
    """Seed test institutions, courses, intakes, and submissions in database."""
    # 1. Institutions
    inst1 = Institution(
        aicte_id="1-TEST-INST1",
        name="Test Institute of Technology",
        state="Maharashtra",
        district="Pune",
        address="Campus 1, Pune",
        official_email="contact@test-inst1.edu",
        official_phone="9876543210",
        head_name="Dr. Director One",
        affiliating_university="Pune University",
        approval_status="active",
        account_status="active",
    )
    inst2 = Institution(
        aicte_id="1-TEST-INST2",
        name="Second Engineering College",
        state="Maharashtra",
        district="Mumbai",
        address="Campus 2, Mumbai",
        official_email="contact@test-inst2.edu",
        official_phone="9876543211",
        head_name="Dr. Director Two",
        affiliating_university="Mumbai University",
        approval_status="active",
        account_status="active",
    )
    db_session.add_all([inst1, inst2])
    db_session.flush()

    # 2. Courses
    c1 = Course(
        institution_id=inst1.id,
        name="Computer Science and Engineering",
        level="UG",
        branch="Computer Science",
        duration_years=4,
        supernumerary_allowed=True,
    )
    c2 = Course(
        institution_id=inst1.id,
        name="Mechanical Engineering",
        level="UG",
        branch="Mechanical",
        duration_years=4,
        supernumerary_allowed=False,
    )
    c_other = Course(
        institution_id=inst2.id,
        name="Civil Engineering",
        level="UG",
        branch="Civil",
        duration_years=4,
        supernumerary_allowed=True,
    )
    db_session.add_all([c1, c2, c_other])
    db_session.flush()

    # 3. Course Intakes
    ci1 = CourseIntake(
        course_id=c1.id,
        academic_year="2026-27",
        approved_intake=60,
        supernumerary_seats_allowed=6,
        source="aicte_master",
    )
    ci2 = CourseIntake(
        course_id=c2.id,
        academic_year="2026-27",
        approved_intake=60,
        supernumerary_seats_allowed=0,
        source="aicte_master",
    )
    db_session.add_all([ci1, ci2])
    db_session.flush()

    # 4. Submissions
    sub1 = Submission(
        institution_id=inst1.id,
        academic_year="2026-27",
        status="draft",
    )
    sub2 = Submission(
        institution_id=inst2.id,
        academic_year="2026-27",
        status="draft",
    )
    db_session.add_all([sub1, sub2])
    db_session.flush()

    # 5. Mock APAAR Registry
    mock_reg = MockApaarRegistry(
        apaar_id="111122223333",
        name="Rahul Sharma",
        dob=date(2004, 5, 15),
        gender="Male",
    )
    db_session.add(mock_reg)
    db_session.flush()

    return {
        "inst1": inst1,
        "inst2": inst2,
        "c1": c1,
        "c2": c2,
        "c_other": c_other,
        "sub1": sub1,
        "sub2": sub2,
    }


def test_student_model_to_row_conversion(db_session: Session, test_setup: dict[str, Any]) -> None:
    """Test converting ORM Student model into validation dictionary format."""
    c1 = test_setup["c1"]
    inst1 = test_setup["inst1"]

    student = Student(
        institution_id=inst1.id,
        course_id=c1.id,
        academic_year="2026-27",
        apaar_id="111122223333",
        name="Rahul Sharma",
        dob_encrypted=encrypt_dob(date(2004, 5, 15)),
        gender="Male",
        enrolment_no="ENR-001",
        admission_date=date(2026, 7, 10),
        admission_mode="JEE Main counselling",
        seat_type="Regular",
        reservation_category="General",
        nri="No",
        oci="No",
        foreign_national="No",
        status="draft",
    )
    db_session.add(student)
    db_session.flush()

    row = student_model_to_row(student, row_number=5)

    assert row["apaar_id"] == "111122223333"
    assert row["name"] == "Rahul Sharma"
    assert row["dob"] == "2004-05-15"
    assert row["course"] == "Computer Science and Engineering"
    assert row["branch"] == "Computer Science"
    assert row["admission_year"] == "2026-27"
    assert row["enrolment_no"] == "ENR-001"
    assert row["row_number"] == 5
    assert row["student_id"] == student.id


def test_validate_rows_single_and_batch_entry(
    db_session: Session, test_setup: dict[str, Any]
) -> None:
    """Test validate_rows on single row and batch rows without requiring database persistence."""
    valid_row = {
        "apaar_id": "111122223333",
        "name": "Rahul Sharma",
        "dob": "2004-05-15",
        "gender": "Male",
        "course": "Computer Science and Engineering",
        "branch": "Computer Science",
        "admission_year": "2026-27",
        "enrolment_no": "ENR-001",
        "admission_date": "2026-07-10",
        "admission_mode": "JEE Main counselling",
        "seat_type": "Regular",
        "reservation_category": "General",
        "nri": "No",
        "oci": "No",
        "foreign_national": "No",
        "country": "",
    }

    # 1. Single valid row passes
    res_single = validate_rows(valid_row, db_session=db_session)
    assert res_single.is_valid is True
    assert len(res_single.errors) == 0

    # 2. Row with format errors returns immediate flags
    invalid_row = dict(valid_row)
    invalid_row["apaar_id"] = "12345"  # APAAR_FORMAT
    invalid_row["name"] = "Rahul123"  # NAME_FORMAT

    res_invalid = validate_rows(invalid_row, db_session=db_session)
    assert res_invalid.is_valid is False
    codes = {f.rule_code for f in res_invalid}
    assert APAAR_FORMAT in codes
    assert NAME_FORMAT in codes


def test_validate_rows_with_persistence_and_student_references(
    db_session: Session, test_setup: dict[str, Any]
) -> None:
    """Test validate_rows persisting flags with exact student_id references."""
    c1 = test_setup["c1"]
    inst1 = test_setup["inst1"]
    sub1 = test_setup["sub1"]

    # Create student with invalid name
    student = Student(
        institution_id=inst1.id,
        course_id=c1.id,
        submission_id=sub1.id,
        academic_year="2026-27",
        apaar_id="111122223333",
        name="Rahul99 Sharma",  # Triggers NAME_FORMAT
        dob_encrypted=encrypt_dob(date(2004, 5, 15)),
        gender="Male",
        enrolment_no="ENR-001",
        admission_date=date(2026, 7, 10),
        admission_mode="JEE Main counselling",
        seat_type="Regular",
        reservation_category="General",
        nri="No",
        oci="No",
        foreign_national="No",
        status="draft",
    )
    db_session.add(student)
    db_session.flush()

    res = validate_rows(
        rows=[student],
        institution_id=inst1.id,
        academic_year="2026-27",
        submission_id=sub1.id,
        db_session=db_session,
        persist=True,
    )

    assert res.is_valid is False
    assert any(f.rule_code == NAME_FORMAT for f in res)

    # Check database persistence
    flags_in_db = db_session.scalars(
        select(ValidationFlag).where(ValidationFlag.student_id == student.id)
    ).all()
    assert len(flags_in_db) >= 1
    persisted_flag = next(f for f in flags_in_db if f.rule_code == NAME_FORMAT)
    assert persisted_flag.student_id == student.id
    assert persisted_flag.course_id == c1.id
    assert persisted_flag.submission_id == sub1.id
    assert persisted_flag.status == "open"

    # Verify student status was automatically transitioned to 'flagged'
    assert student.status == "flagged"


def test_validate_course_quotas_and_intake(
    db_session: Session, test_setup: dict[str, Any]
) -> None:
    """Test validate_course correctly catches INTAKE_EXCEEDED and SEAT_DECLARATION_MISMATCH."""
    c1 = test_setup["c1"]
    inst1 = test_setup["inst1"]
    sub1 = test_setup["sub1"]

    # Intake is 60. Create 65 regular students to exceed intake by 5
    students = []
    for i in range(65):
        apaar_id = f"2000000000{i:02d}"
        s = Student(
            institution_id=inst1.id,
            course_id=c1.id,
            submission_id=sub1.id,
            academic_year="2026-27",
            apaar_id=apaar_id,
            name=f"Student {i} Kumar",
            dob_encrypted=encrypt_dob(date(2004, 5, 15)),
            gender="Male",
            enrolment_no=f"CSE-{i:03d}",
            admission_date=date(2026, 7, 10),
            admission_mode="JEE Main counselling",
            seat_type="Regular",
            reservation_category="General",
            nri="No",
            oci="No",
            foreign_national="No",
            status="draft",
        )
        students.append(s)
    db_session.add_all(students)
    db_session.flush()

    # Set declaration matching 60
    decl = SeatDeclaration(
        course_id=c1.id,
        academic_year="2026-27",
        regular_admitted=60,
        supernumerary_admitted=0,
        nri_count=0,
        oci_count=0,
        fn_count=0,
    )
    db_session.add(decl)
    db_session.flush()

    res = validate_course(
        institution_id=inst1.id,
        course_id=c1.id,
        academic_year="2026-27",
        submission_id=sub1.id,
        db_session=db_session,
        persist=True,
    )

    codes = {f.rule_code for f in res}
    assert INTAKE_EXCEEDED in codes
    assert SEAT_DECLARATION_MISMATCH in codes

    # Check message states exact overshoot of 5
    intake_flag = next(f for f in res if f.rule_code == INTAKE_EXCEEDED)
    assert "exceed approved intake (60) by 5" in intake_flag.message
    assert intake_flag.level == "exception"
    assert intake_flag.requires_justification is True


def test_idempotent_re_run_keeps_valid_justifications(
    db_session: Session, test_setup: dict[str, Any]
) -> None:
    """Test idempotent re-run keeps justifications on still-valid flags and resolves fixed flags."""
    c1 = test_setup["c1"]
    inst1 = test_setup["inst1"]
    sub1 = test_setup["sub1"]

    # Create 1 student with invalid name (error) and over-intake (exception)
    student = Student(
        institution_id=inst1.id,
        course_id=c1.id,
        submission_id=sub1.id,
        academic_year="2026-27",
        apaar_id="111122223333",
        name="Rahul99 Sharma",  # Error: NAME_FORMAT
        dob_encrypted=encrypt_dob(date(2004, 5, 15)),
        gender="Male",
        enrolment_no="ENR-001",
        admission_date=date(2026, 7, 10),
        admission_mode="JEE Main counselling",
        seat_type="Regular",
        reservation_category="General",
        nri="No",
        oci="No",
        foreign_national="No",
        status="draft",
    )
    db_session.add(student)
    db_session.flush()

    # Step 1: Run submission validation
    res1 = validate_submission(
        submission_id=sub1.id,
        db_session=db_session,
        persist=True,
    )
    assert any(f.rule_code == NAME_FORMAT for f in res1)

    # Find the persisted NAME_FORMAT flag
    name_flag = db_session.scalar(
        select(ValidationFlag).where(
            ValidationFlag.student_id == student.id,
            ValidationFlag.rule_code == NAME_FORMAT,
        )
    )
    assert name_flag is not None
    assert name_flag.status == "open"
    initial_flag_id = name_flag.id

    # Add a justification to the flag
    justification = Justification(
        flag_id=name_flag.id,
        text="Typo in official matriculation certificate verified by principal.",
        document_ref="doc_123.pdf",
    )
    db_session.add(justification)
    name_flag.status = "justified"
    db_session.flush()

    # Step 2: Re-run validation without fixing data (flag still applies)
    res2 = validate_submission(
        submission_id=sub1.id,
        db_session=db_session,
        persist=True,
        keep_justifications=True,
    )
    assert any(f.rule_code == NAME_FORMAT for f in res2)

    # Assert flag still exists, has SAME primary key ID, status remains 'justified'
    rechecked_flag = db_session.scalar(
        select(ValidationFlag).where(
            ValidationFlag.student_id == student.id,
            ValidationFlag.rule_code == NAME_FORMAT,
        )
    )
    assert rechecked_flag is not None
    assert rechecked_flag.id == initial_flag_id
    assert rechecked_flag.status == "justified"
    assert len(rechecked_flag.justifications) == 1
    assert rechecked_flag.justifications[0].text == justification.text

    # Step 3: Now fix the error in student's data
    student.name = "Rahul Sharma"
    db_session.flush()

    # Step 4: Re-run validation again
    res3 = validate_submission(
        submission_id=sub1.id,
        db_session=db_session,
        persist=True,
        keep_justifications=True,
    )
    assert not any(f.rule_code == NAME_FORMAT for f in res3)

    # Check that the fixed flag is now marked 'resolved'
    resolved_flag = db_session.scalar(
        select(ValidationFlag).where(ValidationFlag.id == initial_flag_id)
    )
    assert resolved_flag is not None
    assert resolved_flag.status == "resolved"

    # Student status is now clean/valid!
    assert student.status == "valid"


def test_cross_college_duplicate_detection_in_submission(
    db_session: Session, test_setup: dict[str, Any]
) -> None:
    """Test validate_submission detects concurrent active student at another institution."""
    c1 = test_setup["c1"]
    inst1 = test_setup["inst1"]
    sub1 = test_setup["sub1"]

    c_other = test_setup["c_other"]
    inst2 = test_setup["inst2"]
    sub2 = test_setup["sub2"]

    shared_apaar = "999988887777"

    # Enrol student at Institution 2
    student2 = Student(
        institution_id=inst2.id,
        course_id=c_other.id,
        submission_id=sub2.id,
        academic_year="2026-27",
        apaar_id=shared_apaar,
        name="Vikram Rao",
        dob_encrypted=encrypt_dob(date(2003, 8, 20)),
        gender="Male",
        enrolment_no="CE-001",
        admission_date=date(2026, 7, 5),
        admission_mode="JEE Main counselling",
        seat_type="Regular",
        reservation_category="General",
        status="submitted",
    )
    db_session.add(student2)
    db_session.flush()

    # Enrol same student at Institution 1
    student1 = Student(
        institution_id=inst1.id,
        course_id=c1.id,
        submission_id=sub1.id,
        academic_year="2026-27",
        apaar_id=shared_apaar,
        name="Vikram Rao",
        dob_encrypted=encrypt_dob(date(2003, 8, 20)),
        gender="Male",
        enrolment_no="CSE-001",
        admission_date=date(2026, 7, 8),
        admission_mode="JEE Main counselling",
        seat_type="Regular",
        reservation_category="General",
        status="draft",
    )
    db_session.add(student1)
    db_session.flush()

    res = validate_submission(
        submission_id=sub1.id,
        db_session=db_session,
        persist=True,
    )

    codes = {f.rule_code for f in res}
    assert DUP_ACTIVE_OTHER_COLLEGE in codes

    # Verify persisted flag has student_id matching student1
    dup_flag = db_session.scalar(
        select(ValidationFlag).where(
            ValidationFlag.student_id == student1.id,
            ValidationFlag.rule_code == DUP_ACTIVE_OTHER_COLLEGE,
        )
    )
    assert dup_flag is not None
    assert dup_flag.student_id == student1.id
    assert dup_flag.status == "open"


def test_rules_doc_generator() -> None:
    """Test generating docs/RULES.md from the registry and metadata catalogue."""
    content = generate_rules_doc()

    assert "# APAAR Validation Rules Catalogue" in content
    assert "INTAKE_EXCEEDED" in content
    assert "DUP_APAAR_IN_FILE" in content
    assert "APAAR_REQUIRED" in content
    assert "SEAT_DECLARATION_MISMATCH" in content
    assert "cheap-checks-first" in content
