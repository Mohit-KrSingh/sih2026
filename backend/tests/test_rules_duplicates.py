"""Unit and integration tests for duplicate validation rules (SPEC.md 9.3, 10 & TASKS.md T16).

Rules tested:
1. DUP_APAAR_IN_FILE (file scope, error)
2. DUP_ENROLNO_IN_COURSE (file scope, error)
3. DUP_ACTIVE_OTHER_COLLEGE (cross scope, warning)
4. DUP_SAME_COURSE_OTHER_COLLEGE (cross scope, exception)

Also tests:
- Cross-college querying using (apaar_id, academic_year) index
- Notification dispatch to both affected colleges
- Automated flag resolution at both colleges upon student withdrawal or transfer
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, Institution, Notification, Student, ValidationFlag
from app.students.duplicate_service import (
    notify_duplicate_enrolment,
    query_duplicates_by_apaar_and_year,
    resolve_duplicate_flags_on_status_change,
)
from app.validation import (
    DUP_ACTIVE_OTHER_COLLEGE,
    DUP_APAAR_IN_FILE,
    DUP_ENROLNO_IN_COURSE,
    DUP_SAME_COURSE_OTHER_COLLEGE,
    ValidationContext,
    ValidationLevel,
    run_rules,
)

# ============================================================================
# 1. DUP_APAAR_IN_FILE
# ============================================================================


def test_dup_apaar_in_file_pass_unique() -> None:
    """Pass: Multiple rows with unique APAAR IDs."""
    ctx = ValidationContext(
        rows=[
            {"apaar_id": "111122223333", "row_number": 1, "admission_year": "2026-27"},
            {"apaar_id": "444455556666", "row_number": 2, "admission_year": "2026-27"},
            {"apaar_id": "777788889999", "row_number": 3, "admission_year": "2026-27"},
        ],
        institution_id=1,
        academic_year="2026-27",
    )
    res = run_rules(ctx, rules=[DUP_APAAR_IN_FILE])
    assert len(res) == 0
    assert res.is_valid is True


def test_dup_apaar_in_file_fail_batch_duplicates() -> None:
    """Fail: Same APAAR ID appears twice in the upload batch."""
    ctx = ValidationContext(
        rows=[
            {"apaar_id": "111122223333", "row_number": 1, "admission_year": "2026-27"},
            {"apaar_id": "444455556666", "row_number": 2, "admission_year": "2026-27"},
            {"apaar_id": "111122223333", "row_number": 5, "admission_year": "2026-27"},
        ],
        institution_id=1,
        academic_year="2026-27",
    )
    res = run_rules(ctx, rules=[DUP_APAAR_IN_FILE])
    assert len(res) == 2
    assert res.is_valid is False
    assert res[0].rule_code == DUP_APAAR_IN_FILE
    assert res[0].level == ValidationLevel.ERROR.value
    assert res[0].row_ref == 1
    assert res[1].row_ref == 5
    assert "multiple times" in res[0].message
    assert "rows 1, 5" in res[0].message


def test_dup_apaar_in_file_fail_existing_college_student() -> None:
    """Fail: APAAR ID in upload matches existing college record for the year."""
    ctx = ValidationContext(
        rows=[
            {"apaar_id": "111122223333", "row_number": 1, "admission_year": "2026-27"},
        ],
        institution_id=1,
        academic_year="2026-27",
        all_college_students=[
            {
                "id": 99,
                "apaar_id": "111122223333",
                "academic_year": "2026-27",
                "institution_id": 1,
                "enrolment_no": "EN-EXISTING-01",
                "status": "submitted",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_APAAR_IN_FILE])
    assert len(res) == 1
    assert res[0].rule_code == DUP_APAAR_IN_FILE
    assert res[0].level == ValidationLevel.ERROR.value
    assert "already exists in college records" in res[0].message
    assert "EN-EXISTING-01" in res[0].message


def test_dup_apaar_in_file_pass_same_student_update() -> None:
    """Pass: Re-uploading / updating the same student record does not trigger duplicate flag."""
    ctx = ValidationContext(
        rows=[
            {
                "id": 99,
                "apaar_id": "111122223333",
                "row_number": 1,
                "admission_year": "2026-27",
            },
        ],
        institution_id=1,
        academic_year="2026-27",
        all_college_students=[
            {
                "id": 99,
                "apaar_id": "111122223333",
                "academic_year": "2026-27",
                "institution_id": 1,
                "enrolment_no": "EN-EXISTING-01",
                "status": "submitted",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_APAAR_IN_FILE])
    assert len(res) == 0


def test_dup_apaar_in_file_pass_withdrawn_student() -> None:
    """Pass: APAAR ID in college records with 'withdrawn' status is not treated as conflict."""
    ctx = ValidationContext(
        rows=[
            {"apaar_id": "111122223333", "row_number": 1, "admission_year": "2026-27"},
        ],
        institution_id=1,
        academic_year="2026-27",
        all_college_students=[
            {
                "id": 99,
                "apaar_id": "111122223333",
                "academic_year": "2026-27",
                "institution_id": 1,
                "status": "withdrawn",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_APAAR_IN_FILE])
    assert len(res) == 0


def test_dup_apaar_in_file_skips_invalid_format() -> None:
    """Pass: Rows with missing or non-12-digit APAAR IDs are skipped by duplicate check."""
    ctx = ValidationContext(
        rows=[
            {"apaar_id": "", "row_number": 1},
            {"apaar_id": "123", "row_number": 2},
            {"apaar_id": "123", "row_number": 3},
            {"apaar_id": None, "row_number": 4},
        ],
    )
    res = run_rules(ctx, rules=[DUP_APAAR_IN_FILE])
    assert len(res) == 0


def test_dup_apaar_in_file_level_override() -> None:
    """Verify level override from rule_config."""
    ctx = ValidationContext(
        rows=[
            {"apaar_id": "111122223333", "row_number": 1, "admission_year": "2026-27"},
            {"apaar_id": "111122223333", "row_number": 2, "admission_year": "2026-27"},
        ],
    )
    res = run_rules(
        ctx,
        rules=[DUP_APAAR_IN_FILE],
        overrides={DUP_APAAR_IN_FILE: {"level": "warning"}},
    )
    assert len(res) == 2
    assert res[0].level == ValidationLevel.WARNING.value


# ============================================================================
# 2. DUP_ENROLNO_IN_COURSE
# ============================================================================


def test_dup_enrolno_in_course_pass_unique() -> None:
    """Pass: Distinct enrolment numbers within course and year."""
    ctx = ValidationContext(
        rows=[
            {
                "enrolment_no": "EN-001",
                "course": "Computer Science and Engineering",
                "branch": "Computer Science",
                "admission_year": "2026-27",
                "row_number": 1,
            },
            {
                "enrolment_no": "EN-002",
                "course": "Computer Science and Engineering",
                "branch": "Computer Science",
                "admission_year": "2026-27",
                "row_number": 2,
            },
        ],
        academic_year="2026-27",
    )
    res = run_rules(ctx, rules=[DUP_ENROLNO_IN_COURSE])
    assert len(res) == 0


def test_dup_enrolno_in_course_fail_duplicate_batch() -> None:
    """Fail: Same enrolment number repeated in same course and year in upload."""
    ctx = ValidationContext(
        rows=[
            {
                "enrolment_no": "EN-001",
                "course": "Computer Science and Engineering",
                "branch": "Computer Science",
                "admission_year": "2026-27",
                "row_number": 1,
            },
            {
                "enrolment_no": "EN-001",
                "course": "Computer Science and Engineering",
                "branch": "Computer Science",
                "admission_year": "2026-27",
                "row_number": 4,
            },
        ],
        academic_year="2026-27",
    )
    res = run_rules(ctx, rules=[DUP_ENROLNO_IN_COURSE])
    assert len(res) == 2
    assert res[0].rule_code == DUP_ENROLNO_IN_COURSE
    assert res[0].level == ValidationLevel.ERROR.value
    assert res[0].field == "enrolment_no"
    assert "multiple times" in res[0].message
    assert "rows 1, 4" in res[0].message


def test_dup_enrolno_in_course_pass_different_course() -> None:
    """Pass: Same enrolment number in two different courses."""
    ctx = ValidationContext(
        rows=[
            {
                "enrolment_no": "EN-001",
                "course": "Computer Science and Engineering",
                "admission_year": "2026-27",
                "row_number": 1,
            },
            {
                "enrolment_no": "EN-001",
                "course": "Mechanical Engineering",
                "admission_year": "2026-27",
                "row_number": 2,
            },
        ],
        academic_year="2026-27",
    )
    res = run_rules(ctx, rules=[DUP_ENROLNO_IN_COURSE])
    assert len(res) == 0


def test_dup_enrolno_in_course_pass_different_academic_year() -> None:
    """Pass: Same enrolment number in different academic years."""
    ctx = ValidationContext(
        rows=[
            {
                "enrolment_no": "EN-001",
                "course": "Computer Science and Engineering",
                "admission_year": "2025-26",
                "row_number": 1,
            },
            {
                "enrolment_no": "EN-001",
                "course": "Computer Science and Engineering",
                "admission_year": "2026-27",
                "row_number": 2,
            },
        ],
    )
    res = run_rules(ctx, rules=[DUP_ENROLNO_IN_COURSE])
    assert len(res) == 0


def test_dup_enrolno_in_course_fail_existing_college_record() -> None:
    """Fail: Enrolment number matches existing student in same course and year."""
    ctx = ValidationContext(
        rows=[
            {
                "enrolment_no": "EN-001",
                "course": "Computer Science and Engineering",
                "branch": "Computer Science",
                "admission_year": "2026-27",
                "row_number": 1,
            },
        ],
        institution_id=1,
        academic_year="2026-27",
        all_college_students=[
            {
                "id": 101,
                "enrolment_no": "EN-001",
                "course": "Computer Science and Engineering",
                "branch": "Computer Science",
                "academic_year": "2026-27",
                "institution_id": 1,
                "status": "submitted",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_ENROLNO_IN_COURSE])
    assert len(res) == 1
    assert res[0].rule_code == DUP_ENROLNO_IN_COURSE
    assert "already exists in college records" in res[0].message


# ============================================================================
# 3. DUP_ACTIVE_OTHER_COLLEGE
# ============================================================================


def test_dup_active_other_college_pass_no_conflict() -> None:
    """Pass: APAAR ID has no enrolment at any other college."""
    ctx = ValidationContext(
        rows=[{"apaar_id": "111122223333", "admission_year": "2026-27", "row_number": 1}],
        institution_id=1,
        academic_year="2026-27",
        other_college_students=[],
    )
    res = run_rules(ctx, rules=[DUP_ACTIVE_OTHER_COLLEGE])
    assert len(res) == 0


def test_dup_active_other_college_fail_different_course() -> None:
    """Fail: APAAR ID active at another college in a different course -> warning."""
    ctx = ValidationContext(
        rows=[
            {
                "apaar_id": "555566667777",
                "admission_year": "2026-27",
                "course": "Computer Science and Engineering",
                "row_number": 1,
            }
        ],
        institution_id=1,
        academic_year="2026-27",
        other_college_students=[
            {
                "apaar_id": "555566667777",
                "academic_year": "2026-27",
                "institution_id": 2,
                "institution_name": "Mumbai Metropolitan Institute",
                "aicte_id": "1-10000002",
                "course": "Information Technology",
                "status": "submitted",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_ACTIVE_OTHER_COLLEGE])
    assert len(res) == 1
    assert res[0].rule_code == DUP_ACTIVE_OTHER_COLLEGE
    assert res[0].level == ValidationLevel.WARNING.value
    assert res[0].audience == "both"
    assert res[0].requires_justification is False
    assert "Mumbai Metropolitan Institute" in res[0].message
    assert "1-10000002" in res[0].message


def test_dup_active_other_college_pass_withdrawn() -> None:
    """Pass: Student at other college has withdrawn status -> resolves conflict."""
    ctx = ValidationContext(
        rows=[
            {
                "apaar_id": "555566667777",
                "admission_year": "2026-27",
                "course": "Computer Science and Engineering",
                "row_number": 1,
            }
        ],
        institution_id=1,
        academic_year="2026-27",
        other_college_students=[
            {
                "apaar_id": "555566667777",
                "academic_year": "2026-27",
                "institution_id": 2,
                "status": "withdrawn",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_ACTIVE_OTHER_COLLEGE])
    assert len(res) == 0


def test_dup_active_other_college_pass_transferred() -> None:
    """Pass: Student at other college has transferred status -> resolves conflict."""
    ctx = ValidationContext(
        rows=[
            {
                "apaar_id": "555566667777",
                "admission_year": "2026-27",
                "course": "Computer Science and Engineering",
                "row_number": 1,
            }
        ],
        institution_id=1,
        academic_year="2026-27",
        other_college_students=[
            {
                "apaar_id": "555566667777",
                "academic_year": "2026-27",
                "institution_id": 2,
                "status": "transferred",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_ACTIVE_OTHER_COLLEGE])
    assert len(res) == 0


def test_dup_active_other_college_pass_different_academic_year() -> None:
    """Pass: Active at another college but in a different academic year."""
    ctx = ValidationContext(
        rows=[
            {
                "apaar_id": "555566667777",
                "admission_year": "2026-27",
                "course": "Computer Science and Engineering",
                "row_number": 1,
            }
        ],
        institution_id=1,
        academic_year="2026-27",
        other_college_students=[
            {
                "apaar_id": "555566667777",
                "academic_year": "2025-26",
                "institution_id": 2,
                "status": "submitted",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_ACTIVE_OTHER_COLLEGE])
    assert len(res) == 0


# ============================================================================
# 4. DUP_SAME_COURSE_OTHER_COLLEGE
# ============================================================================


def test_dup_same_course_other_college_pass_different_course() -> None:
    """Pass: Enrolled at other college, but course is different."""
    ctx = ValidationContext(
        rows=[
            {
                "apaar_id": "555566667777",
                "admission_year": "2026-27",
                "course": "Computer Science and Engineering",
                "row_number": 1,
            }
        ],
        institution_id=1,
        academic_year="2026-27",
        other_college_students=[
            {
                "apaar_id": "555566667777",
                "academic_year": "2026-27",
                "institution_id": 2,
                "course": "Civil Engineering",
                "status": "submitted",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_SAME_COURSE_OTHER_COLLEGE])
    assert len(res) == 0


def test_dup_same_course_other_college_fail_same_course() -> None:
    """Fail: Enrolled at other college in the EXACT same course -> exception."""
    ctx = ValidationContext(
        rows=[
            {
                "apaar_id": "555566667777",
                "admission_year": "2026-27",
                "course": "Computer Science and Engineering",
                "branch": "Computer Science",
                "row_number": 1,
            }
        ],
        institution_id=1,
        academic_year="2026-27",
        other_college_students=[
            {
                "apaar_id": "555566667777",
                "academic_year": "2026-27",
                "institution_id": 2,
                "institution_name": "Delhi Technical Campus",
                "aicte_id": "1-10000003",
                "course": "Computer Science and Engineering",
                "branch": "Computer Science",
                "status": "submitted",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_SAME_COURSE_OTHER_COLLEGE])
    assert len(res) == 1
    assert res[0].rule_code == DUP_SAME_COURSE_OTHER_COLLEGE
    assert res[0].level == ValidationLevel.EXCEPTION.value
    assert res[0].audience == "both"
    assert res[0].requires_justification is True
    assert "concurrently enrolled in the same course" in res[0].message
    assert "Delhi Technical Campus" in res[0].message


def test_dup_same_course_other_college_pass_withdrawn() -> None:
    """Pass: Same course at other college, but marked 'withdrawn'."""
    ctx = ValidationContext(
        rows=[
            {
                "apaar_id": "555566667777",
                "admission_year": "2026-27",
                "course": "Computer Science and Engineering",
                "row_number": 1,
            }
        ],
        institution_id=1,
        academic_year="2026-27",
        other_college_students=[
            {
                "apaar_id": "555566667777",
                "academic_year": "2026-27",
                "institution_id": 2,
                "course": "Computer Science and Engineering",
                "status": "withdrawn",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_SAME_COURSE_OTHER_COLLEGE])
    assert len(res) == 0


def test_dup_same_course_other_college_normalized_course_name() -> None:
    """Pass: Fuzzy normalized course name match (& vs and)."""
    ctx = ValidationContext(
        rows=[
            {
                "apaar_id": "555566667777",
                "admission_year": "2026-27",
                "course": "Computer Science & Engineering",
                "row_number": 1,
            }
        ],
        institution_id=1,
        academic_year="2026-27",
        other_college_students=[
            {
                "apaar_id": "555566667777",
                "academic_year": "2026-27",
                "institution_id": 2,
                "institution_name": "Delhi Technical Campus",
                "aicte_id": "1-10000003",
                "course": "Computer Science and Engineering",
                "status": "submitted",
            }
        ],
    )
    res = run_rules(ctx, rules=[DUP_SAME_COURSE_OTHER_COLLEGE])
    assert len(res) == 1
    assert res[0].rule_code == DUP_SAME_COURSE_OTHER_COLLEGE


# ============================================================================
# 5. CROSS-COLLEGE DATABASE & NOTIFICATION & RESOLUTION INTEGRATION TESTS
# ============================================================================


def test_cross_college_duplicate_db_integration(db_session: Session) -> None:
    """End-to-end integration test with real PostgreSQL session and two institutions:

    1. Cross-college query uses the index on (apaar_id, academic_year).
    2. Duplicates detected across two colleges.
    3. Notifications dispatched to both colleges.
    4. Marking student withdrawn at College A resolves the flag at BOTH colleges.
    5. Resolution notifications dispatched to both colleges.
    """
    # 1. Create two test institutions
    inst_a = Institution(
        aicte_id="1-TEST-COLL-A",
        name="Apex College of Technology",
        state="Maharashtra",
        district="Pune",
        address="123 Tech Park, Pune",
        official_email="contact@apex-test.edu",
        official_phone="+919876543210",
        head_name="Dr. Apex Director",
        affiliating_university="Pune University",
        approval_status="active",
    )
    inst_b = Institution(
        aicte_id="1-TEST-COLL-B",
        name="Beacon Engineering College",
        state="Karnataka",
        district="Bengaluru",
        address="456 Silicon Rd, Bengaluru",
        official_email="contact@beacon-test.edu",
        official_phone="+919876543211",
        head_name="Dr. Beacon Director",
        affiliating_university="VTU",
        approval_status="active",
    )
    db_session.add_all([inst_a, inst_b])
    db_session.flush()

    # 2. Create courses
    course_a = Course(
        institution_id=inst_a.id,
        name="Computer Science and Engineering",
        branch="Computer Science",
        level="UG",
        duration_years=4,
    )
    course_b = Course(
        institution_id=inst_b.id,
        name="Information Technology",
        branch="Information Technology",
        level="UG",
        duration_years=4,
    )
    db_session.add_all([course_a, course_b])
    db_session.flush()

    # 3. Create active student at College A
    student_a = Student(
        institution_id=inst_a.id,
        course_id=course_a.id,
        academic_year="2026-27",
        apaar_id="888877776666",
        name="Aarav Sharma",
        dob_encrypted="enc_dob_test",
        gender="Male",
        enrolment_no="EN-APEX-001",
        admission_date=date(2026, 7, 10),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        status="submitted",
        source="csv",
    )
    # Create active student at College B with SAME APAAR ID
    student_b = Student(
        institution_id=inst_b.id,
        course_id=course_b.id,
        academic_year="2026-27",
        apaar_id="888877776666",
        name="Aarav Sharma",
        dob_encrypted="enc_dob_test",
        gender="Male",
        enrolment_no="EN-BEACON-001",
        admission_date=date(2026, 7, 15),
        admission_mode="Management quota",
        seat_type="Regular",
        reservation_category="General",
        status="submitted",
        source="csv",
    )
    db_session.add_all([student_a, student_b])
    db_session.flush()

    # 4. Test indexed duplicate query helper
    found_duplicates = query_duplicates_by_apaar_and_year(
        db_session,
        apaar_ids=["888877776666"],
        academic_year="2026-27",
        exclude_institution_id=inst_a.id,
    )
    assert len(found_duplicates) == 1
    assert found_duplicates[0].id == student_b.id
    assert found_duplicates[0].institution_id == inst_b.id

    # 5. Run validation rules for College A using real db_session
    ctx_a = ValidationContext(
        rows=[
            {
                "apaar_id": "888877776666",
                "admission_year": "2026-27",
                "course": "Computer Science and Engineering",
                "row_number": 1,
                "id": student_a.id,
            }
        ],
        institution_id=inst_a.id,
        academic_year="2026-27",
        db_session=db_session,
    )
    flags_a = run_rules(ctx_a, rules=[DUP_ACTIVE_OTHER_COLLEGE])
    assert len(flags_a) == 1
    assert flags_a[0].rule_code == DUP_ACTIVE_OTHER_COLLEGE
    assert "Beacon Engineering College" in flags_a[0].message
    assert "1-TEST-COLL-B" in flags_a[0].message

    # 6. Plant open flags in DB for both students
    flag_a = ValidationFlag(
        student_id=student_a.id,
        course_id=course_a.id,
        rule_code=DUP_ACTIVE_OTHER_COLLEGE,
        level="warning",
        field="apaar_id",
        message=flags_a[0].message,
        audience="both",
        status="open",
    )
    flag_b = ValidationFlag(
        student_id=student_b.id,
        course_id=course_b.id,
        rule_code=DUP_ACTIVE_OTHER_COLLEGE,
        level="warning",
        field="apaar_id",
        message=f"Active at {inst_a.name}",
        audience="both",
        status="open",
    )
    db_session.add_all([flag_a, flag_b])
    db_session.flush()

    # 7. Test notification dispatch for detection
    notif_a, notif_b = notify_duplicate_enrolment(
        db_session, student_a, student_b, DUP_ACTIVE_OTHER_COLLEGE
    )
    assert notif_a.institution_id == inst_a.id
    assert notif_a.type == "DUPLICATE_ENROLMENT_DETECTED"
    assert notif_b.institution_id == inst_b.id
    assert notif_b.type == "DUPLICATE_ENROLMENT_DETECTED"

    # 8. Mark student_a as 'withdrawn' at College A
    resolved = resolve_duplicate_flags_on_status_change(
        db_session, student_a, new_status="withdrawn"
    )

    # Verify student_a status updated
    assert student_a.status == "withdrawn"
    # Verify both flags were resolved
    assert len(resolved) == 2
    assert flag_a.status == "resolved"
    assert flag_b.status == "resolved"

    # 9. Verify resolution notifications were added for both colleges
    res_notifs = db_session.scalars(
        select(Notification).where(Notification.type == "DUPLICATE_ENROLMENT_RESOLVED")
    ).all()
    assert len(res_notifs) == 2
    res_inst_ids = {n.institution_id for n in res_notifs}
    assert res_inst_ids == {inst_a.id, inst_b.id}


def test_cross_college_duplicate_transfer_resolution(db_session: Session) -> None:
    """Verify that marking a student 'transferred' at one college resolves flags at both."""
    inst_1 = Institution(
        aicte_id="1-TRANSFER-1",
        name="Transfer Inst One",
        state="Gujarat",
        district="Ahmedabad",
        address="100 Ashram Rd, Ahmedabad",
        official_email="t1@inst.edu",
        official_phone="+919876543212",
        head_name="Dr. Transfer One",
        affiliating_university="GTU",
        approval_status="active",
    )
    inst_2 = Institution(
        aicte_id="1-TRANSFER-2",
        name="Transfer Inst Two",
        state="Gujarat",
        district="Surat",
        address="200 Ring Rd, Surat",
        official_email="t2@inst.edu",
        official_phone="+919876543213",
        head_name="Dr. Transfer Two",
        affiliating_university="GTU",
        approval_status="active",
    )
    db_session.add_all([inst_1, inst_2])
    db_session.flush()

    c1 = Course(
        institution_id=inst_1.id,
        name="Electrical Engineering",
        branch="Electrical",
        level="UG",
        duration_years=4,
    )
    c2 = Course(
        institution_id=inst_2.id,
        name="Electrical Engineering",
        branch="Electrical",
        level="UG",
        duration_years=4,
    )
    db_session.add_all([c1, c2])
    db_session.flush()

    s1 = Student(
        institution_id=inst_1.id,
        course_id=c1.id,
        academic_year="2026-27",
        apaar_id="999911112222",
        name="Kavita Reddy",
        dob_encrypted="enc_dob",
        gender="Female",
        enrolment_no="EN-TR-001",
        admission_date=date(2026, 7, 10),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        status="submitted",
        source="csv",
    )
    s2 = Student(
        institution_id=inst_2.id,
        course_id=c2.id,
        academic_year="2026-27",
        apaar_id="999911112222",
        name="Kavita Reddy",
        dob_encrypted="enc_dob",
        gender="Female",
        enrolment_no="EN-TR-002",
        admission_date=date(2026, 7, 12),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        status="submitted",
        source="csv",
    )
    db_session.add_all([s1, s2])
    db_session.flush()

    f1 = ValidationFlag(
        student_id=s1.id,
        course_id=c1.id,
        rule_code=DUP_SAME_COURSE_OTHER_COLLEGE,
        level="exception",
        field="apaar_id",
        message="Duplicate enrolment",
        audience="both",
        status="open",
    )
    f2 = ValidationFlag(
        student_id=s2.id,
        course_id=c2.id,
        rule_code=DUP_SAME_COURSE_OTHER_COLLEGE,
        level="exception",
        field="apaar_id",
        message="Duplicate enrolment",
        audience="both",
        status="open",
    )
    db_session.add_all([f1, f2])
    db_session.flush()

    # Mark transferred
    resolved = resolve_duplicate_flags_on_status_change(db_session, s1, "transferred")
    assert len(resolved) == 2
    assert f1.status == "resolved"
    assert f2.status == "resolved"
