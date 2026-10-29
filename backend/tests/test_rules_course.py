"""Unit and integration tests for course-level validation rules (TASKS.md T17 & SPEC.md 9.3).

Rules covered:
1. INTAKE_EXCEEDED (course scope, default: exception)
   - Regular admitted is above approved intake. Message states the exact overshoot.
2. SUPERNUMERARY_EXCEEDED (course scope, default: exception)
   - Supernumerary admitted is above supernumerary seats allowed. Message states exact overshoot.
3. SEAT_DECLARATION_MISMATCH (course scope, default: error)
   - Declared counts differ from uploaded student list. Blocks submit.

Required Acceptance Criteria:
- Count regular and supernumerary separately.
- Message states the exact overshoot.
- 128 students with 8 genuinely supernumerary and allowed passes.
- 130 regular against intake 120 gives an exception of 10.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models import Course, CourseIntake, Institution, SeatDeclaration
from app.validation import (
    INTAKE_EXCEEDED,
    SEAT_DECLARATION_MISMATCH,
    SUPERNUMERARY_EXCEEDED,
    ValidationContext,
    ValidationLevel,
    run_rules,
)
from app.validation.context import RuleConfigOverride


def _make_students(
    count: int,
    seat_type: str = "Regular",
    start_idx: int = 1,
    course: str = "Computer Science and Engineering",
    branch: str = "CSE",
    academic_year: str = "2026-27",
    status: str = "draft",
    nri: str = "No",
    oci: str = "No",
    foreign_national: str = "No",
) -> list[dict[str, Any]]:
    """Helper to generate student rows for test batches."""
    rows = []
    for i in range(start_idx, start_idx + count):
        rows.append(
            {
                "apaar_id": f"9000{i:08d}",
                "name": f"Student {i}",
                "course": course,
                "branch": branch,
                "admission_year": academic_year,
                "enrolment_no": f"ENR-{i:05d}",
                "seat_type": seat_type,
                "status": status,
                "nri": nri,
                "oci": oci,
                "foreign_national": foreign_national,
                "row_number": i,
            }
        )
    return rows


# ============================================================================
# 1. INTAKE_EXCEEDED TESTS
# ============================================================================


def test_intake_exceeded_acceptance_criteria_128_students_passes() -> None:
    """Acceptance criteria: 128 students with 8 genuinely supernumerary and allowed passes.

    120 regular students against intake 120, plus 8 supernumerary students against quota 8.
    """
    regular_students = _make_students(120, seat_type="Regular", start_idx=1)
    supernumerary_students = _make_students(8, seat_type="Supernumerary", start_idx=121)
    all_students = regular_students + supernumerary_students

    assert len(all_students) == 128

    ctx = ValidationContext(
        rows=all_students,
        approved_intake=120,
        approved_supernumerary=8,
    )

    result = run_rules(ctx, rules=[INTAKE_EXCEEDED, SUPERNUMERARY_EXCEEDED])
    assert len(result) == 0
    assert result.is_valid is True


def test_intake_exceeded_acceptance_criteria_130_regular_gives_exception_of_10() -> None:
    """Acceptance criteria: 130 regular against intake 120 gives an exception of 10.

    Message states the exact overshoot of 10.
    """
    regular_students = _make_students(130, seat_type="Regular", start_idx=1)

    ctx = ValidationContext(
        rows=regular_students,
        approved_intake=120,
    )

    result = run_rules(ctx, rules=[INTAKE_EXCEEDED])
    assert len(result) == 1
    flag = result[0]

    assert flag.rule_code == INTAKE_EXCEEDED
    assert flag.level == ValidationLevel.EXCEPTION.value
    assert flag.requires_justification is True
    assert "exceed approved intake (120) by 10" in flag.message
    assert "Regular admissions (130)" in flag.message
    assert flag.field == "approved_intake"


def test_intake_exceeded_pass_below_intake() -> None:
    """Pass: Regular admissions strictly below approved intake."""
    rows = _make_students(50, seat_type="Regular")
    ctx = ValidationContext(rows=rows, approved_intake=60)
    result = run_rules(ctx, rules=[INTAKE_EXCEEDED])
    assert len(result) == 0


def test_intake_exceeded_pass_exact_intake() -> None:
    """Pass: Regular admissions exactly equal to approved intake."""
    rows = _make_students(60, seat_type="Regular")
    ctx = ValidationContext(rows=rows, approved_intake=60)
    result = run_rules(ctx, rules=[INTAKE_EXCEEDED])
    assert len(result) == 0


def test_intake_exceeded_excludes_withdrawn_and_transferred() -> None:
    """Pass: Students with status 'withdrawn' or 'transferred' do not count towards intake."""
    # 130 total regular students, but 15 are withdrawn and 5 transferred -> 110 active
    active_rows = _make_students(110, seat_type="Regular", start_idx=1, status="draft")
    withdrawn_rows = _make_students(15, seat_type="Regular", start_idx=111, status="withdrawn")
    transferred_rows = _make_students(5, seat_type="Regular", start_idx=126, status="transferred")
    rows = active_rows + withdrawn_rows + transferred_rows

    assert len(rows) == 130

    ctx = ValidationContext(rows=rows, approved_intake=120)
    result = run_rules(ctx, rules=[INTAKE_EXCEEDED])
    assert len(result) == 0


def test_intake_exceeded_fail_different_overshoot() -> None:
    """Fail: 75 regular students against intake 60 gives overshoot of 15."""
    rows = _make_students(75, seat_type="Regular", course="Civil Engineering")
    ctx = ValidationContext(rows=rows, approved_intake=60)

    result = run_rules(ctx, rules=[INTAKE_EXCEEDED])
    assert len(result) == 1
    flag = result[0]
    assert "exceed approved intake (60) by 15" in flag.message
    assert "Regular admissions (75)" in flag.message


def test_intake_exceeded_multi_course_selective_flag() -> None:
    """Multi-course: Flags only the course exceeding intake."""
    # CSE: Intake 60 -> 70 regular students (over 10)
    cse_students = _make_students(70, course="Computer Science", branch="CSE")
    # Mech: Intake 60 -> 50 regular students (ok)
    mech_students = _make_students(50, course="Mechanical", branch="Mech")

    ctx = ValidationContext(
        rows=cse_students + mech_students,
        extra={
            "course_intakes": {
                ("Computer Science", "CSE"): 60,
                ("Mechanical", "Mech"): 60,
            }
        },
    )

    result = run_rules(ctx, rules=[INTAKE_EXCEEDED])
    assert len(result) == 1
    flag = result[0]
    assert "Computer Science" in flag.message
    assert "by 10" in flag.message


def test_intake_exceeded_level_override_and_disabled() -> None:
    """Level override changes severity; disabling rule skips it."""
    rows = _make_students(130, seat_type="Regular")
    ctx = ValidationContext(rows=rows, approved_intake=120)

    # 1. Override to warning
    overrides = {INTAKE_EXCEEDED: RuleConfigOverride(rule_code=INTAKE_EXCEEDED, level="warning")}
    res_warn = run_rules(ctx, rules=[INTAKE_EXCEEDED], overrides=overrides)
    assert len(res_warn) == 1
    assert res_warn[0].level == ValidationLevel.WARNING.value

    # 2. Disable rule
    disabled_overrides = {
        INTAKE_EXCEEDED: RuleConfigOverride(rule_code=INTAKE_EXCEEDED, enabled=False)
    }
    res_dis = run_rules(ctx, rules=[INTAKE_EXCEEDED], overrides=disabled_overrides)
    assert len(res_dis) == 0


def test_intake_exceeded_skips_when_intake_unknown() -> None:
    """Edge: Skips check cleanly when intake cannot be resolved."""
    rows = _make_students(50, seat_type="Regular")
    ctx = ValidationContext(rows=rows)
    result = run_rules(ctx, rules=[INTAKE_EXCEEDED])
    assert len(result) == 0


# ============================================================================
# 2. SUPERNUMERARY_EXCEEDED TESTS
# ============================================================================


def test_supernumerary_exceeded_pass_within_limit() -> None:
    """Pass: Supernumerary count is within allowed quota."""
    super_students = _make_students(6, seat_type="Supernumerary")
    ctx = ValidationContext(
        rows=super_students,
        approved_supernumerary=8,
    )
    result = run_rules(ctx, rules=[SUPERNUMERARY_EXCEEDED])
    assert len(result) == 0


def test_supernumerary_exceeded_pass_exact_match() -> None:
    """Pass: Supernumerary count exactly equals allowed quota."""
    super_students = _make_students(8, seat_type="Supernumerary")
    ctx = ValidationContext(
        rows=super_students,
        approved_supernumerary=8,
    )
    result = run_rules(ctx, rules=[SUPERNUMERARY_EXCEEDED])
    assert len(result) == 0


def test_supernumerary_exceeded_fail_overshoot_reported() -> None:
    """Fail: 12 supernumerary students against allowed quota 8 reports overshoot of 4."""
    super_students = _make_students(12, seat_type="Supernumerary")
    ctx = ValidationContext(
        rows=super_students,
        approved_supernumerary=8,
    )

    result = run_rules(ctx, rules=[SUPERNUMERARY_EXCEEDED])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == SUPERNUMERARY_EXCEEDED
    assert flag.level == ValidationLevel.EXCEPTION.value
    assert flag.requires_justification is True
    assert "exceed allowed supernumerary quota (8) by 4" in flag.message
    assert "Supernumerary admissions (12)" in flag.message
    assert flag.field == "supernumerary_seats_allowed"


def test_supernumerary_exceeded_fail_zero_quota_disallowed() -> None:
    """Fail: 3 supernumerary admissions when supernumerary quota is 0 reports overshoot of 3."""
    super_students = _make_students(3, seat_type="Supernumerary")
    ctx = ValidationContext(
        rows=super_students,
        approved_supernumerary=0,
    )
    result = run_rules(ctx, rules=[SUPERNUMERARY_EXCEEDED])
    assert len(result) == 1
    assert "exceed allowed supernumerary quota (0) by 3" in result[0].message


def test_supernumerary_exceeded_excludes_withdrawn_and_transferred() -> None:
    """Pass: Withdrawn/transferred supernumerary students are not counted."""
    active_super = _make_students(8, seat_type="Supernumerary", start_idx=1, status="draft")
    withdrawn_super = _make_students(4, seat_type="Supernumerary", start_idx=9, status="withdrawn")
    rows = active_super + withdrawn_super

    ctx = ValidationContext(rows=rows, approved_supernumerary=8)
    result = run_rules(ctx, rules=[SUPERNUMERARY_EXCEEDED])
    assert len(result) == 0


def test_supernumerary_exceeded_multi_course() -> None:
    """Multi-course: Flags only the course exceeding supernumerary seats."""
    # CSE Quota 6 -> 10 students (over 4)
    cse_super = _make_students(10, seat_type="Supernumerary", course="CSE", branch="CSE")
    # Mech Quota 6 -> 5 students (ok)
    mech_super = _make_students(5, seat_type="Supernumerary", course="Mech", branch="Mech")

    ctx = ValidationContext(
        rows=cse_super + mech_super,
        extra={
            "course_intakes": {
                ("CSE", "CSE"): {"approved_intake": 120, "supernumerary_seats_allowed": 6},
                ("Mech", "Mech"): {"approved_intake": 120, "supernumerary_seats_allowed": 6},
            }
        },
    )

    result = run_rules(ctx, rules=[SUPERNUMERARY_EXCEEDED])
    assert len(result) == 1
    assert "CSE" in result[0].message
    assert "by 4" in result[0].message


def test_supernumerary_exceeded_skips_when_quota_unknown() -> None:
    """Edge: Skips cleanly when supernumerary quota is not configured."""
    super_students = _make_students(5, seat_type="Supernumerary")
    ctx = ValidationContext(rows=super_students)
    result = run_rules(ctx, rules=[SUPERNUMERARY_EXCEEDED])
    assert len(result) == 0


# ============================================================================
# 3. SEAT_DECLARATION_MISMATCH TESTS
# ============================================================================


def test_seat_declaration_mismatch_pass_exact_reconciliation() -> None:
    """Pass: Declared counts match actual student counts perfectly."""
    reg = _make_students(60, seat_type="Regular")
    sup = _make_students(6, seat_type="Supernumerary", start_idx=61)
    rows = reg + sup

    ctx = ValidationContext(
        rows=rows,
        declared_seats={
            "regular_admitted": 60,
            "supernumerary_admitted": 6,
        },
    )

    result = run_rules(ctx, rules=[SEAT_DECLARATION_MISMATCH])
    assert len(result) == 0
    assert result.is_valid is True


def test_seat_declaration_mismatch_pass_with_category_counts() -> None:
    """Pass: Declared regular, supernumerary, NRI, OCI, and FN counts match actuals."""
    reg = _make_students(50, seat_type="Regular", start_idx=1)
    nri = _make_students(5, seat_type="Regular", start_idx=51, nri="Yes")
    oci = _make_students(3, seat_type="Regular", start_idx=56, oci="Yes")
    fn = _make_students(2, seat_type="Regular", start_idx=59, foreign_national="Yes")
    sup = _make_students(8, seat_type="Supernumerary", start_idx=61)
    rows = reg + nri + oci + fn + sup  # total 68: 60 regular (5 NRI, 3 OCI, 2 FN), 8 supernumerary

    ctx = ValidationContext(
        rows=rows,
        declared_seats={
            "regular_admitted": 60,
            "supernumerary_admitted": 8,
            "nri_count": 5,
            "oci_count": 3,
            "fn_count": 2,
        },
    )

    result = run_rules(ctx, rules=[SEAT_DECLARATION_MISMATCH])
    assert len(result) == 0


def test_seat_declaration_mismatch_fail_regular_count() -> None:
    """Fail: Declared regular count differs from uploaded regular students."""
    rows = _make_students(65, seat_type="Regular")
    ctx = ValidationContext(
        rows=rows,
        declared_seats={
            "regular_admitted": 60,  # Declared 60, but uploaded 65
        },
    )

    result = run_rules(ctx, rules=[SEAT_DECLARATION_MISMATCH])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == SEAT_DECLARATION_MISMATCH
    assert flag.level == ValidationLevel.ERROR.value
    assert flag.requires_justification is False
    assert "regular admitted (declared 60 vs actual 65)" in flag.message


def test_seat_declaration_mismatch_fail_supernumerary_count() -> None:
    """Fail: Declared supernumerary count differs from uploaded supernumerary students."""
    reg = _make_students(60, seat_type="Regular")
    sup = _make_students(10, seat_type="Supernumerary", start_idx=61)
    rows = reg + sup

    ctx = ValidationContext(
        rows=rows,
        declared_seats={
            "regular_admitted": 60,
            "supernumerary_admitted": 8,  # Declared 8, but uploaded 10
        },
    )

    result = run_rules(ctx, rules=[SEAT_DECLARATION_MISMATCH])
    assert len(result) == 1
    flag = result[0]
    assert "supernumerary admitted (declared 8 vs actual 10)" in flag.message


def test_seat_declaration_mismatch_fail_multiple_fields() -> None:
    """Fail: Multiple declared fields differ; all are reported in the flag message."""
    reg = _make_students(50, seat_type="Regular")
    sup = _make_students(5, seat_type="Supernumerary", start_idx=51)
    rows = reg + sup

    ctx = ValidationContext(
        rows=rows,
        declared_seats={
            "regular_admitted": 60,        # Declared 60 vs actual 50
            "supernumerary_admitted": 8,   # Declared 8 vs actual 5
            "nri_count": 2,                # Declared 2 vs actual 0
        },
    )

    result = run_rules(ctx, rules=[SEAT_DECLARATION_MISMATCH])
    assert len(result) == 1
    msg = result[0].message
    assert "regular admitted (declared 60 vs actual 50)" in msg
    assert "supernumerary admitted (declared 8 vs actual 5)" in msg
    assert "NRI admitted (declared 2 vs actual 0)" in msg


def test_seat_declaration_mismatch_skips_when_no_declaration() -> None:
    """Edge: Skips check cleanly when no seat declaration is provided."""
    rows = _make_students(60, seat_type="Regular")
    ctx = ValidationContext(rows=rows, declared_seats=None)
    result = run_rules(ctx, rules=[SEAT_DECLARATION_MISMATCH])
    assert len(result) == 0


def test_seat_declaration_mismatch_excludes_withdrawn_students() -> None:
    """Pass: Declared count matches active students; withdrawn students are excluded."""
    active = _make_students(60, seat_type="Regular", start_idx=1, status="draft")
    withdrawn = _make_students(5, seat_type="Regular", start_idx=61, status="withdrawn")
    rows = active + withdrawn

    ctx = ValidationContext(
        rows=rows,
        declared_seats={"regular_admitted": 60},
    )
    result = run_rules(ctx, rules=[SEAT_DECLARATION_MISMATCH])
    assert len(result) == 0


# ============================================================================
# 4. DATABASE INTEGRATION TESTS
# ============================================================================


def test_course_rules_db_integration(db_session: Session) -> None:
    """Database integration test resolving CourseIntake and SeatDeclaration from DB."""
    # 1. Setup institution and course with intake
    inst = Institution(
        aicte_id="1-COURSE-TEST-01",
        name="Course Rule Test College",
        state="Maharashtra",
        district="Pune",
        address="Test Campus",
        official_email="course_test@aicte-test.edu.in",
        official_phone="+919876543299",
        head_name="Dr. Course Head",
        affiliating_university="Savitribai Phule Pune University",
        approval_status="active",
        account_status="active",
    )
    db_session.add(inst)
    db_session.flush()

    course = Course(
        institution_id=inst.id,
        name="Electrical Engineering",
        level="UG",
        branch="Electrical",
        duration_years=4,
        supernumerary_allowed=True,
    )
    db_session.add(course)
    db_session.flush()

    intake = CourseIntake(
        course_id=course.id,
        academic_year="2026-27",
        approved_intake=60,
        supernumerary_seats_allowed=6,
        source="aicte_master",
    )
    db_session.add(intake)

    decl = SeatDeclaration(
        course_id=course.id,
        academic_year="2026-27",
        regular_admitted=60,
        supernumerary_admitted=6,
        status="declared",
    )
    db_session.add(decl)
    db_session.commit()

    # 2. Case A: Compliant batch matching DB values (60 regular, 6 supernumerary)
    comp_reg = _make_students(
        60, course="Electrical Engineering", branch="Electrical", seat_type="Regular", start_idx=1
    )
    comp_sup = _make_students(
        6,
        course="Electrical Engineering",
        branch="Electrical",
        seat_type="Supernumerary",
        start_idx=61,
    )
    ctx_pass = ValidationContext(
        rows=comp_reg + comp_sup,
        institution_id=inst.id,
        academic_year="2026-27",
        db_session=db_session,
    )

    res_pass = run_rules(
        ctx_pass,
        rules=[INTAKE_EXCEEDED, SUPERNUMERARY_EXCEEDED, SEAT_DECLARATION_MISMATCH],
    )
    assert len(res_pass) == 0

    # 3. Case B: Exceeding intake (70 regular) and supernumerary (8) against DB values (60 and 6)
    over_reg = _make_students(
        70, course="Electrical Engineering", branch="Electrical", seat_type="Regular", start_idx=1
    )
    over_sup = _make_students(
        8,
        course="Electrical Engineering",
        branch="Electrical",
        seat_type="Supernumerary",
        start_idx=71,
    )
    ctx_over = ValidationContext(
        rows=over_reg + over_sup,
        institution_id=inst.id,
        academic_year="2026-27",
        db_session=db_session,
    )

    res_over = run_rules(
        ctx_over,
        rules=[INTAKE_EXCEEDED, SUPERNUMERARY_EXCEEDED, SEAT_DECLARATION_MISMATCH],
    )
    assert len(res_over) == 3

    flags_by_code = {f.rule_code: f for f in res_over}
    assert INTAKE_EXCEEDED in flags_by_code
    assert "by 10" in flags_by_code[INTAKE_EXCEEDED].message

    assert SUPERNUMERARY_EXCEEDED in flags_by_code
    assert "by 2" in flags_by_code[SUPERNUMERARY_EXCEEDED].message

    assert SEAT_DECLARATION_MISMATCH in flags_by_code
    decl_msg = flags_by_code[SEAT_DECLARATION_MISMATCH].message
    assert "regular admitted (declared 60 vs actual 70)" in decl_msg
    assert "supernumerary admitted (declared 6 vs actual 8)" in decl_msg


# ============================================================================
# 5. DEMO OVERINTAKE CSV TEST
# ============================================================================


def test_demo_overintake_upload_csv() -> None:
    """Verifies that demo/overintake_upload.csv triggers INTAKE_EXCEEDED with overshoot of 10.

    70 regular students for a 60-seat Mechanical Engineering course.
    """
    import csv
    from pathlib import Path

    csv_path = Path("demo/overintake_upload.csv")
    assert csv_path.exists()

    rows = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, r in enumerate(reader, start=1):
            r["row_number"] = idx
            rows.append(r)

    assert len(rows) == 70

    ctx = ValidationContext(
        rows=rows,
        course={"name": "Mechanical Engineering", "branch": "Mechanical", "approved_intake": 60},
        approved_intake=60,
    )

    result = run_rules(ctx, rules=[INTAKE_EXCEEDED, SUPERNUMERARY_EXCEEDED])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == INTAKE_EXCEEDED
    assert flag.level == ValidationLevel.EXCEPTION.value
    assert "Regular admissions (70)" in flag.message
    assert "exceed approved intake (60) by 10" in flag.message
