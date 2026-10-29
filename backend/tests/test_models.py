"""Tests for database models, unique constraints, and required indexes."""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.db import Base
from app.models import (
    AnomalyScore,
    ApiKey,
    Course,
    CourseIntake,
    Institution,
    MockApaarRegistry,
    RuleConfig,
    SeatDeclaration,
    Student,
    Submission,
    User,
    VerifiedRecord,
)


def test_metadata_has_all_26_tables():
    """Verify that all 26 required domain tables from SPEC.md section 7 exist in Base.metadata."""
    expected_tables = {
        "users",
        "institutions",
        "courses",
        "course_intake",
        "course_intake_history",
        "activation_requests",
        "correction_requests",
        "seat_declarations",
        "students",
        "uploads",
        "validation_flags",
        "justifications",
        "submissions",
        "review_items",
        "queries",
        "change_requests",
        "notifications",
        "verified_records",
        "verifiers",
        "consent_requests",
        "audit_log",
        "api_keys",
        "rule_config",
        "anomaly_scores",
        "mock_apaar_registry",
        "dev_outbox",
    }
    actual_tables = set(Base.metadata.tables.keys())
    missing = expected_tables - actual_tables
    assert not missing, f"Missing tables in metadata: {missing}"


def test_required_indexes_exist():
    """Verify explicit required indexes from TASKS.md:

    - students(apaar_id, academic_year)
    - validation_flags(submission_id, level)
    """
    students_table = Base.metadata.tables["students"]
    students_index_cols = [tuple(c.name for c in idx.columns) for idx in students_table.indexes]
    assert ("apaar_id", "academic_year") in students_index_cols

    flags_table = Base.metadata.tables["validation_flags"]
    flags_index_cols = [tuple(c.name for c in idx.columns) for idx in flags_table.indexes]
    assert ("submission_id", "level") in flags_index_cols


def test_unique_constraint_institution_aicte_id(db_session):
    """Verify institutions.aicte_id uniqueness."""
    inst1 = Institution(
        aicte_id="1-12345678",
        name="Apex Engineering College",
        state="Maharashtra",
        district="Pune",
        address="123 Tech Park",
        official_email="contact@apex.edu",
        official_phone="9876543210",
        head_name="Dr. Sharma",
        affiliating_university="Pune University",
    )
    db_session.add(inst1)
    db_session.flush()

    inst2 = Institution(
        aicte_id="1-12345678",  # duplicate
        name="Duplicate College",
        state="Karnataka",
        district="Bengaluru",
        address="456 Other Rd",
        official_email="dup@apex.edu",
        official_phone="9876543211",
        head_name="Dr. Verma",
        affiliating_university="VTU",
    )
    db_session.add(inst2)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.flush()


def test_unique_constraint_user_email(db_session):
    """Verify users.email uniqueness."""
    u1 = User(
        email="admin@college.edu",
        password_hash="argon2id$hashed",
        role="college_admin",
    )
    db_session.add(u1)
    db_session.flush()

    u2 = User(
        email="admin@college.edu",  # duplicate
        password_hash="argon2id$hashed2",
        role="college_staff",
    )
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.flush()


def test_unique_constraint_course_intake_year(db_session):
    """Verify course_intake unique (course_id, academic_year)."""
    inst = Institution(
        aicte_id="1-INTAKE-TEST",
        name="Intake Test College",
        state="Delhi",
        district="New Delhi",
        address="Connaught Place",
        official_email="intake@test.edu",
        official_phone="9876543212",
        head_name="Dr. Head",
        affiliating_university="Delhi University",
    )
    db_session.add(inst)
    db_session.flush()

    c = Course(
        institution_id=inst.id,
        name="Computer Science and Engineering",
        level="UG",
        branch="CSE",
        duration_years=4,
    )
    db_session.add(c)
    db_session.flush()

    ci1 = CourseIntake(
        course_id=c.id,
        academic_year="2026-27",
        approved_intake=120,
        supernumerary_seats_allowed=12,
    )
    db_session.add(ci1)
    db_session.flush()

    ci2 = CourseIntake(
        course_id=c.id,
        academic_year="2026-27",  # duplicate year for same course
        approved_intake=180,
        supernumerary_seats_allowed=18,
    )
    db_session.add(ci2)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.flush()


def test_unique_constraint_seat_declarations_year(db_session):
    """Verify seat_declarations unique (course_id, academic_year)."""
    inst = Institution(
        aicte_id="1-SEAT-TEST",
        name="Seat Test College",
        state="Tamil Nadu",
        district="Chennai",
        address="Anna Salai",
        official_email="seat@test.edu",
        official_phone="9876543213",
        head_name="Dr. Raman",
        affiliating_university="Anna University",
    )
    db_session.add(inst)
    db_session.flush()

    c = Course(
        institution_id=inst.id,
        name="Mechanical Engineering",
        level="UG",
        branch="ME",
        duration_years=4,
    )
    db_session.add(c)
    db_session.flush()

    sd1 = SeatDeclaration(
        course_id=c.id,
        academic_year="2026-27",
        regular_admitted=60,
        supernumerary_admitted=6,
    )
    db_session.add(sd1)
    db_session.flush()

    sd2 = SeatDeclaration(
        course_id=c.id,
        academic_year="2026-27",  # duplicate
        regular_admitted=60,
        supernumerary_admitted=6,
    )
    db_session.add(sd2)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.flush()


def test_unique_constraint_submissions_inst_year(db_session):
    """Verify submissions unique (institution_id, academic_year)."""
    inst = Institution(
        aicte_id="1-SUBM-TEST",
        name="Submission Test College",
        state="Karnataka",
        district="Mysuru",
        address="Ring Road",
        official_email="subm@test.edu",
        official_phone="9876543214",
        head_name="Dr. Rao",
        affiliating_university="VTU",
    )
    db_session.add(inst)
    db_session.flush()

    sub1 = Submission(institution_id=inst.id, academic_year="2026-27", status="draft")
    db_session.add(sub1)
    db_session.flush()

    sub2 = Submission(institution_id=inst.id, academic_year="2026-27", status="submitted")
    db_session.add(sub2)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.flush()


def test_unique_constraint_student_inst_course_year_apaar(db_session):
    """Verify students unique (institution_id, course_id, academic_year, apaar_id)."""
    inst = Institution(
        aicte_id="1-STUDENT-TEST",
        name="Student Test College",
        state="Maharashtra",
        district="Mumbai",
        address="Fort",
        official_email="student@test.edu",
        official_phone="9876543215",
        head_name="Dr. Kulkarni",
        affiliating_university="Mumbai University",
    )
    db_session.add(inst)
    db_session.flush()

    c = Course(
        institution_id=inst.id,
        name="Information Technology",
        level="UG",
        branch="IT",
        duration_years=4,
    )
    db_session.add(c)
    db_session.flush()

    s1 = Student(
        institution_id=inst.id,
        course_id=c.id,
        academic_year="2026-27",
        apaar_id="123456789012",
        name="Aarav Sharma",
        dob_encrypted="enc_dob_test_val",
        gender="Male",
        enrolment_no="IT-2026-001",
        admission_date=date(2026, 8, 15),
        admission_mode="JEE Main counselling",
        seat_type="Regular",
        reservation_category="General",
    )
    db_session.add(s1)
    db_session.flush()

    s2 = Student(
        institution_id=inst.id,
        course_id=c.id,
        academic_year="2026-27",
        apaar_id="123456789012",  # duplicate APAAR for same inst, course, and year
        name="Aarav Sharma",
        dob_encrypted="enc_dob_test_val",
        gender="Male",
        enrolment_no="IT-2026-002",
        admission_date=date(2026, 8, 15),
        admission_mode="JEE Main counselling",
        seat_type="Regular",
        reservation_category="General",
    )
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.flush()


def test_unique_constraint_verified_records_id(db_session):
    """Verify verified_records.verification_id uniqueness."""
    inst = Institution(
        aicte_id="1-VR-TEST",
        name="VR Test College",
        state="Gujarat",
        district="Ahmedabad",
        address="SG Highway",
        official_email="vr@test.edu",
        official_phone="9876543216",
        head_name="Dr. Patel",
        affiliating_university="GTU",
    )
    db_session.add(inst)
    db_session.flush()

    c = Course(
        institution_id=inst.id,
        name="Civil Engineering",
        level="UG",
        branch="CE",
        duration_years=4,
    )
    db_session.add(c)
    db_session.flush()

    student = Student(
        institution_id=inst.id,
        course_id=c.id,
        academic_year="2025-26",
        apaar_id="999888777666",
        name="Priya Patel",
        dob_encrypted="enc_dob_test",
        gender="Female",
        enrolment_no="CE-001",
        admission_date=date(2025, 8, 1),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
    )
    db_session.add(student)
    db_session.flush()

    vr1 = VerifiedRecord(
        student_id=student.id,
        verification_id="VR-2026-00001",
        signature="dummy_ed25519_sig_1",
    )
    db_session.add(vr1)
    db_session.flush()

    vr2 = VerifiedRecord(
        student_id=student.id,
        verification_id="VR-2026-00001",  # duplicate verification_id
        signature="dummy_ed25519_sig_2",
    )
    db_session.add(vr2)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.flush()


def test_unique_constraint_rule_config(db_session):
    """Verify rule_config.rule_code uniqueness."""
    rc1 = RuleConfig(rule_code="FILE_EMPTY", level="error")
    db_session.add(rc1)
    db_session.flush()

    rc2 = RuleConfig(rule_code="FILE_EMPTY", level="warning")
    db_session.add(rc2)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.flush()


def test_unique_constraint_mock_apaar_registry(db_session):
    """Verify mock_apaar_registry.apaar_id uniqueness."""
    reg1 = MockApaarRegistry(
        apaar_id="111122223333",
        name="Test Student",
        dob=date(2004, 5, 20),
        gender="Male",
    )
    db_session.add(reg1)
    db_session.flush()

    reg2 = MockApaarRegistry(
        apaar_id="111122223333",  # duplicate
        name="Another Name",
        dob=date(2004, 6, 21),
        gender="Female",
    )
    db_session.add(reg2)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.flush()


def test_unique_constraint_api_key_hash(db_session):
    """Verify api_keys.key_hash uniqueness."""
    inst = Institution(
        aicte_id="1-KEY-TEST",
        name="Key Test College",
        state="Telangana",
        district="Hyderabad",
        address="Hitec City",
        official_email="key@test.edu",
        official_phone="9876543217",
        head_name="Dr. Reddy",
        affiliating_university="JNTU",
    )
    db_session.add(inst)
    db_session.flush()

    k1 = ApiKey(
        institution_id=inst.id,
        name="ERP Sync Key",
        key_hash="hash_sha256_xyz123",
        scopes=["upload:students", "read:intake"],
    )
    db_session.add(k1)
    db_session.flush()

    k2 = ApiKey(
        institution_id=inst.id,
        name="Backup Key",
        key_hash="hash_sha256_xyz123",  # duplicate key_hash
        scopes=["read:intake"],
    )
    db_session.add(k2)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.flush()


def test_unique_constraint_anomaly_scores_inst_course_year(db_session):
    """Verify anomaly_scores unique (institution_id, course_id, academic_year)."""
    inst = Institution(
        aicte_id="1-ANOM-TEST",
        name="Anom Test College",
        state="West Bengal",
        district="Kolkata",
        address="Salt Lake",
        official_email="anom@test.edu",
        official_phone="9876543218",
        head_name="Dr. Banerjee",
        affiliating_university="MAKAUT",
    )
    db_session.add(inst)
    db_session.flush()

    c = Course(
        institution_id=inst.id,
        name="Electrical Engineering",
        level="UG",
        branch="EE",
        duration_years=4,
    )
    db_session.add(c)
    db_session.flush()

    anom1 = AnomalyScore(
        institution_id=inst.id,
        course_id=c.id,
        academic_year="2026-27",
        score=0.88,
        features_json={"jump": 0.45},
        flagged=True,
    )
    db_session.add(anom1)
    db_session.flush()

    anom2 = AnomalyScore(
        institution_id=inst.id,
        course_id=c.id,
        academic_year="2026-27",  # duplicate
        score=0.50,
        features_json={"jump": 0.10},
        flagged=False,
    )
    db_session.add(anom2)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.flush()
