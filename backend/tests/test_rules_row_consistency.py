"""Unit tests for row consistency validation rules (TASKS.md T15 & SPEC.md 9.3).

Rules covered:
1. CATEGORY_CONFLICT (row scope, error)
2. COURSE_NOT_APPROVED (row scope, error)
3. AGE_OUT_OF_RANGE (row scope, warning)
4. SEAT_TYPE_NOT_APPROVED (row scope, error)
5. MODE_CATEGORY_MISMATCH (row scope, warning)
6. ADMISSION_YEAR_MISMATCH (row scope, warning)

Each rule has comprehensive tests for pass, fail, edge cases, and configuration overrides.
"""

from typing import Any

from app.integrations.interfaces import AicteCourseInfo
from app.validation import (
    ADMISSION_YEAR_MISMATCH,
    AGE_OUT_OF_RANGE,
    CATEGORY_CONFLICT,
    COURSE_NOT_APPROVED,
    MODE_CATEGORY_MISMATCH,
    SEAT_TYPE_NOT_APPROVED,
    ValidationContext,
    ValidationLevel,
    run_rules,
)
from app.validation.rules.admission_year_mismatch import AdmissionYearMismatchRule
from app.validation.rules.age_out_of_range import AgeOutOfRangeRule
from app.validation.rules.category_conflict import CategoryConflictRule
from app.validation.rules.course_not_approved import CourseNotApprovedRule
from app.validation.rules.mode_category_mismatch import ModeCategoryMismatchRule
from app.validation.rules.seat_type_not_approved import SeatTypeNotApprovedRule

# ============================================================================
# 1. CATEGORY_CONFLICT
# ============================================================================


def test_category_conflict_pass_nri_only() -> None:
    """Pass: NRI is Yes and foreign_national is No."""
    ctx = ValidationContext(
        rows=[{"nri": "Yes", "foreign_national": "No", "row_number": 1}],
    )
    result = run_rules(ctx, rules=[CATEGORY_CONFLICT])
    assert len(result) == 0
    assert result.is_valid is True


def test_category_conflict_pass_foreign_national_only() -> None:
    """Pass: NRI is No and foreign_national is Yes."""
    ctx = ValidationContext(
        rows=[{"nri": "No", "foreign_national": "Yes", "country": "Nepal", "row_number": 1}],
    )
    result = run_rules(ctx, rules=[CATEGORY_CONFLICT])
    assert len(result) == 0
    assert result.is_valid is True


def test_category_conflict_pass_neither() -> None:
    """Pass: Both NRI and foreign_national are No."""
    ctx = ValidationContext(
        rows=[{"nri": "No", "foreign_national": "No", "row_number": 1}],
    )
    result = run_rules(ctx, rules=[CATEGORY_CONFLICT])
    assert len(result) == 0


def test_category_conflict_fail_both_yes() -> None:
    """Fail: Student has both NRI and foreign_national set to Yes."""
    ctx = ValidationContext(
        rows=[
            {
                "nri": "Yes",
                "foreign_national": "Yes",
                "country": "United Arab Emirates",
                "row_number": 12,
            }
        ],
    )
    result = run_rules(ctx, rules=[CATEGORY_CONFLICT])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == CATEGORY_CONFLICT
    assert flag.level == ValidationLevel.ERROR.value
    assert flag.field == "nri"
    assert flag.row_ref == 12
    assert "Student cannot be simultaneously marked" in flag.message
    assert flag.requires_justification is False


def test_category_conflict_edge_casing_and_missing() -> None:
    """Edge cases: Case insensitive 'yes', whitespace, missing or None values."""
    ctx = ValidationContext(
        rows=[
            {"nri": " YES ", "foreign_national": "yes", "row_number": 1},  # Fail
            {"nri": None, "foreign_national": "Yes", "row_number": 2},  # Pass
            {"nri": "No", "foreign_national": None, "row_number": 3},  # Pass
            {},  # Pass
        ],
    )
    rule = CategoryConflictRule()
    flags = rule.check(ctx)
    assert len(flags) == 1
    assert flags[0].row_ref == 1


# ============================================================================
# 2. COURSE_NOT_APPROVED
# ============================================================================


def test_course_not_approved_pass_matching_course_branch() -> None:
    """Pass: Row matches an approved course by name and branch."""
    approved = [
        {"name": "Mechanical Engineering", "branch": "Mechanical"},
        {"name": "Computer Science and Engineering", "branch": "Computer Science"},
    ]
    ctx = ValidationContext(
        rows=[
            {
                "course": "Mechanical Engineering",
                "branch": "Mechanical",
                "row_number": 1,
            }
        ],
        extra={"approved_courses": approved},
    )
    result = run_rules(ctx, rules=[COURSE_NOT_APPROVED])
    assert len(result) == 0


def test_course_not_approved_pass_matching_course_id() -> None:
    """Pass: Row matches approved course by integer course_id."""
    approved = [
        AicteCourseInfo(
            name="Civil Engineering",
            level="UG",
            branch="Civil",
            duration_years=4,
            approved_intake=60,
        )
    ]
    ctx = ValidationContext(
        rows=[
            {
                "course": "Civil Engineering",
                "branch": "Civil",
                "row_number": 1,
            }
        ],
        extra={"approved_courses": approved},
    )
    result = run_rules(ctx, rules=[COURSE_NOT_APPROVED])
    assert len(result) == 0


def test_course_not_approved_fail_unapproved_course() -> None:
    """Fail: Row contains an unapproved course and branch."""
    approved = [
        {"name": "Computer Science and Engineering", "branch": "Computer Science"},
    ]
    ctx = ValidationContext(
        rows=[
            {
                "course": "Astrophysics & Space Flight",
                "branch": "Aerospace",
                "row_number": 13,
            }
        ],
        extra={"approved_courses": approved},
    )
    result = run_rules(ctx, rules=[COURSE_NOT_APPROVED])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == COURSE_NOT_APPROVED
    assert flag.level == ValidationLevel.ERROR.value
    assert flag.field == "course"
    assert flag.row_ref == 13
    assert "Astrophysics & Space Flight" in flag.message
    assert "Aerospace" in flag.message
    assert flag.requires_justification is False


def test_course_not_approved_edge_case_insensitive_and_no_context() -> None:
    """Edge cases: Case insensitive matching, and skip check when course context not set."""
    approved = [
        {"name": "MECHANICAL ENGINEERING", "branch": "MECHANICAL"},
    ]
    # Case insensitivity check passes
    ctx_case = ValidationContext(
        rows=[{"course": "mechanical engineering", "branch": "mechanical", "row_number": 1}],
        extra={"approved_courses": approved},
    )
    rule = CourseNotApprovedRule()
    assert len(rule.check(ctx_case)) == 0

    # No course context in context: gracefully skips check without raising false positives
    ctx_empty = ValidationContext(
        rows=[{"course": "Any Course", "branch": "Any Branch", "row_number": 1}]
    )
    assert len(rule.check(ctx_empty)) == 0


# ============================================================================
# 3. AGE_OUT_OF_RANGE
# ============================================================================


def test_age_out_of_range_pass_standard_ug() -> None:
    """Pass: UG student born 2004 admitted in 2026 (age 22, inside 15-30 band)."""
    ctx = ValidationContext(
        rows=[
            {
                "dob": "2004-05-15",
                "admission_date": "2026-07-20",
                "level": "UG",
                "row_number": 1,
            }
        ],
    )
    result = run_rules(ctx, rules=[AGE_OUT_OF_RANGE])
    assert len(result) == 0


def test_age_out_of_range_pass_pg_and_diploma() -> None:
    """Pass: PG student age 35 (inside 19-45) and Diploma student age 16 (inside 14-30)."""
    ctx = ValidationContext(
        rows=[
            {
                "dob": "1991-03-10",
                "admission_date": "2026-07-20",
                "level": "PG",
                "row_number": 1,
            },
            {
                "dob": "2010-01-15",
                "admission_date": "2026-07-20",
                "level": "Diploma",
                "row_number": 2,
            },
        ],
    )
    result = run_rules(ctx, rules=[AGE_OUT_OF_RANGE])
    assert len(result) == 0


def test_age_out_of_range_fail_too_old() -> None:
    """Fail: UG student born 1955 (age 71 in 2026, exceeds UG max 30) from messy seed."""
    ctx = ValidationContext(
        rows=[
            {
                "name": "Govind Prasad",
                "dob": "1955-03-10",
                "admission_date": "2026-07-15",
                "level": "UG",
                "row_number": 14,
            }
        ],
    )
    result = run_rules(ctx, rules=[AGE_OUT_OF_RANGE])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == AGE_OUT_OF_RANGE
    assert flag.level == ValidationLevel.WARNING.value
    assert flag.field == "dob"
    assert flag.row_ref == 14
    assert "71 years is outside the standard UG age band (15-30 years)" in flag.message


def test_age_out_of_range_fail_too_young() -> None:
    """Fail: UG student born 2015 (age 11 in 2026, below UG min 15)."""
    ctx = ValidationContext(
        rows=[
            {
                "dob": "2015-08-10",
                "admission_date": "2026-08-01",
                "level": "UG",
                "row_number": 1,
            }
        ],
    )
    result = run_rules(ctx, rules=[AGE_OUT_OF_RANGE])
    assert len(result) == 1
    assert "below" in result[0].message.lower() or "outside" in result[0].message.lower()


def test_age_out_of_range_config_override() -> None:
    """Override: bands parameter allows custom age brackets per program."""
    custom_bands = {"UG": (18, 25)}
    ctx = ValidationContext(
        rows=[
            {
                # Age 28 in 2026 -> valid in default (15-30), invalid in (18-25)
                "dob": "1998-05-10",
                "admission_date": "2026-07-20",
                "level": "UG",
                "row_number": 1,
            }
        ],
    )
    # Default band: pass
    assert len(run_rules(ctx, rules=[AGE_OUT_OF_RANGE])) == 0

    # Custom band override: fail
    override_result = run_rules(
        ctx,
        rules=[AGE_OUT_OF_RANGE],
        overrides={AGE_OUT_OF_RANGE: {"params": {"bands": custom_bands}}},
    )
    assert len(override_result) == 1
    assert "18-25 years" in override_result[0].message


def test_age_out_of_range_edge_cases() -> None:
    """Edge cases: missing/invalid DOB skipped, infer level from course name."""
    ctx = ValidationContext(
        rows=[
            {"dob": None, "row_number": 1},  # Missing DOB skipped
            {"dob": "not-a-date", "row_number": 2},  # Bad format skipped
            {
                # Infer Diploma from course name: born 1980, age 46 exceeds Diploma (14-30)
                "course": "Diploma in Mechanical Engineering",
                "dob": "1980-01-01",
                "admission_year": "2026-27",
                "row_number": 3,
            },
        ],
    )
    rule = AgeOutOfRangeRule()
    flags = rule.check(ctx)
    assert len(flags) == 1
    assert flags[0].row_ref == 3
    assert "Diploma" in flags[0].message


# ============================================================================
# 4. SEAT_TYPE_NOT_APPROVED
# ============================================================================


def test_seat_type_not_approved_pass_regular_seat() -> None:
    """Pass: Regular seat type is always permitted regardless of supernumerary status."""
    approved = [{"name": "Mechanical Engineering", "supernumerary_allowed": False}]
    ctx = ValidationContext(
        rows=[{"seat_type": "Regular", "row_number": 1}],
        extra={"approved_courses": approved},
    )
    result = run_rules(ctx, rules=[SEAT_TYPE_NOT_APPROVED])
    assert len(result) == 0


def test_seat_type_not_approved_pass_supernumerary_permitted() -> None:
    """Pass: Supernumerary seat in a course with supernumerary_allowed=True."""
    ctx = ValidationContext(
        course={"name": "Computer Science and Engineering", "supernumerary_allowed": True},
        rows=[{"seat_type": "Supernumerary", "row_number": 1}],
    )
    result = run_rules(ctx, rules=[SEAT_TYPE_NOT_APPROVED])
    assert len(result) == 0


def test_seat_type_not_approved_fail_disallowed() -> None:
    """Fail: Supernumerary seat in Mechanical Engineering where supernumerary is False."""
    course_mech = {
        "name": "Mechanical Engineering",
        "branch": "Mechanical",
        "supernumerary_allowed": False,
    }
    ctx = ValidationContext(
        course=course_mech,
        rows=[
            {
                "name": "Pooja Hegde",
                "course": "Mechanical Engineering",
                "branch": "Mechanical",
                "seat_type": "Supernumerary",
                "row_number": 15,
            }
        ],
    )
    result = run_rules(ctx, rules=[SEAT_TYPE_NOT_APPROVED])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == SEAT_TYPE_NOT_APPROVED
    assert flag.level == ValidationLevel.ERROR.value
    assert flag.field == "seat_type"
    assert flag.row_ref == 15
    assert "Supernumerary seat type is not approved" in flag.message


def test_seat_type_not_approved_edge_cases() -> None:
    """Edge cases: check via approved_supernumerary=0 and case-insensitivity."""
    ctx_approved_zero = ValidationContext(
        approved_supernumerary=0,
        rows=[{"seat_type": "supernumerary", "course": "Civil", "row_number": 1}],
    )
    rule = SeatTypeNotApprovedRule()
    flags = rule.check(ctx_approved_zero)
    assert len(flags) == 1
    assert flags[0].row_ref == 1

    # Empty context without course data skips gracefully
    ctx_no_course = ValidationContext(rows=[{"seat_type": "Supernumerary", "row_number": 2}])
    assert len(rule.check(ctx_no_course)) == 0


# ============================================================================
# 5. MODE_CATEGORY_MISMATCH
# ============================================================================


def test_mode_category_mismatch_pass_compliant() -> None:
    """Pass: Regular domestic student and international quota student match properly."""
    ctx = ValidationContext(
        rows=[
            {
                "nri": "No",
                "oci": "No",
                "foreign_national": "No",
                "admission_mode": "State counselling",
                "row_number": 1,
            },
            {
                "nri": "Yes",
                "oci": "No",
                "foreign_national": "No",
                "admission_mode": "NRI/OCI/foreign quota",
                "row_number": 2,
            },
            {
                "nri": "No",
                "oci": "Yes",
                "foreign_national": "No",
                "admission_mode": "NRI/OCI/foreign quota",
                "row_number": 3,
            },
            {
                "nri": "No",
                "oci": "No",
                "foreign_national": "Yes",
                "country": "Nepal",
                "admission_mode": "NRI/OCI/foreign quota",
                "row_number": 4,
            },
        ],
    )
    result = run_rules(ctx, rules=[MODE_CATEGORY_MISMATCH])
    assert len(result) == 0


def test_mode_category_mismatch_fail_nri_under_state_counselling() -> None:
    """Fail: NRI is Yes but admission mode is State counselling (from messy seed row 16)."""
    ctx = ValidationContext(
        rows=[
            {
                "name": "Ananya Singhania",
                "nri": "Yes",
                "admission_mode": "State counselling",
                "row_number": 16,
            }
        ],
    )
    result = run_rules(ctx, rules=[MODE_CATEGORY_MISMATCH])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == MODE_CATEGORY_MISMATCH
    assert flag.level == ValidationLevel.WARNING.value
    assert flag.field == "admission_mode"
    assert flag.row_ref == 16
    assert "Student is marked as NRI status" in flag.message
    assert "'State counselling'" in flag.message


def test_mode_category_mismatch_fail_reverse_domestic_under_nri_quota() -> None:
    """Fail: Reverse direction: Domestic student admitted through NRI/OCI/foreign quota."""
    ctx = ValidationContext(
        rows=[
            {
                "name": "Rajesh Kumar",
                "nri": "No",
                "oci": "No",
                "foreign_national": "No",
                "admission_mode": "NRI/OCI/foreign quota",
                "row_number": 1,
            }
        ],
    )
    result = run_rules(ctx, rules=[MODE_CATEGORY_MISMATCH])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == MODE_CATEGORY_MISMATCH
    assert flag.level == ValidationLevel.WARNING.value
    assert "none of NRI, OCI, or Foreign National are marked 'Yes'" in flag.message


def test_mode_category_mismatch_edge_cases() -> None:
    """Edge cases: Spacing around slashes in admission mode, multiple international tags."""
    ctx = ValidationContext(
        rows=[
            {
                # Valid variant with spaces around slashes
                "nri": "Yes",
                "admission_mode": "NRI / OCI / Foreign Quota",
                "row_number": 1,
            },
            {
                # Student marked as both OCI and Foreign National under Management quota -> Mismatch
                "oci": "Yes",
                "foreign_national": "Yes",
                "admission_mode": "Management quota",
                "row_number": 2,
            },
            {},  # Empty row skipped
        ],
    )
    rule = ModeCategoryMismatchRule()
    flags = rule.check(ctx)
    assert len(flags) == 1
    assert flags[0].row_ref == 2
    assert "OCI/Foreign National" in flags[0].message


# ============================================================================
# 6. ADMISSION_YEAR_MISMATCH
# ============================================================================


def test_admission_year_mismatch_pass_within_academic_year() -> None:
    """Pass: Admission date falls within standard academic year span."""
    ctx = ValidationContext(
        rows=[
            {
                "admission_year": "2026-27",
                "admission_date": "2026-07-20",  # Summer 2026
                "row_number": 1,
            },
            {
                "admission_year": "2026-27",
                "admission_date": "2027-01-15",  # Spring 2027
                "row_number": 2,
            },
        ],
    )
    result = run_rules(ctx, rules=[ADMISSION_YEAR_MISMATCH])
    assert len(result) == 0


def test_admission_year_mismatch_fail_earlier_year() -> None:
    """Fail: admission_year is 2026-27 but admission_date is 2024-05-10 (from messy seed row 17)."""
    ctx = ValidationContext(
        rows=[
            {
                "name": "Harish Chandra",
                "admission_year": "2026-27",
                "admission_date": "2024-05-10",
                "row_number": 17,
            }
        ],
    )
    result = run_rules(ctx, rules=[ADMISSION_YEAR_MISMATCH])
    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == ADMISSION_YEAR_MISMATCH
    assert flag.level == ValidationLevel.WARNING.value
    assert flag.field == "admission_date"
    assert flag.row_ref == 17
    assert "does not fall within academic year 2026-27" in flag.message


def test_admission_year_mismatch_fail_later_year() -> None:
    """Fail: admission_year is 2026-27 but admission_date is in 2028."""
    ctx = ValidationContext(
        rows=[
            {
                "admission_year": "2026-27",
                "admission_date": "2028-08-01",
                "row_number": 1,
            }
        ],
    )
    result = run_rules(ctx, rules=[ADMISSION_YEAR_MISMATCH])
    assert len(result) == 1
    assert "does not fall within academic year" in result[0].message


def test_admission_year_mismatch_edge_cases() -> None:
    """Edge cases: Academic year from context, single 4-digit year, unparseable dates."""
    ctx = ValidationContext(
        academic_year="2025-26",
        rows=[
            # Context fallback works
            {"admission_date": "2025-08-15", "row_number": 1},  # Pass
            {"admission_date": "2023-08-15", "row_number": 2},  # Fail
            # Missing or unparseable dates skipped
            {"admission_date": None, "row_number": 3},
            {"admission_date": "bad-date", "row_number": 4},
        ],
    )
    rule = AdmissionYearMismatchRule()
    flags = rule.check(ctx)
    assert len(flags) == 1
    assert flags[0].row_ref == 2


# ============================================================================
# 7. Integration: All Row Consistency Rules Executed Together
# ============================================================================


def test_row_consistency_integration_all_rules_on_messy_records() -> None:
    """Verify that all 6 row consistency rules run together seamlessly in run_rules."""
    approved_courses = [
        {
            "name": "Mechanical Engineering",
            "branch": "Mechanical",
            "supernumerary_allowed": False,
            "level": "UG",
        },
        {
            "name": "Computer Science and Engineering",
            "branch": "Computer Science",
            "supernumerary_allowed": True,
            "level": "UG",
        },
    ]

    test_rows: list[dict[str, Any]] = [
        # 1. CATEGORY_CONFLICT
        {
            "row_number": 1,
            "nri": "Yes",
            "foreign_national": "Yes",
            "admission_mode": "NRI/OCI/foreign quota",
            "course": "Computer Science and Engineering",
            "branch": "Computer Science",
            "dob": "2004-05-15",
            "admission_year": "2026-27",
            "admission_date": "2026-07-20",
            "seat_type": "Regular",
        },
        # 2. COURSE_NOT_APPROVED
        {
            "row_number": 2,
            "nri": "No",
            "foreign_national": "No",
            "admission_mode": "State counselling",
            "course": "Astrophysics & Space Flight",
            "branch": "Aerospace",
            "dob": "2004-05-15",
            "admission_year": "2026-27",
            "admission_date": "2026-07-20",
            "seat_type": "Regular",
        },
        # 3. AGE_OUT_OF_RANGE
        {
            "row_number": 3,
            "nri": "No",
            "foreign_national": "No",
            "admission_mode": "State counselling",
            "course": "Computer Science and Engineering",
            "branch": "Computer Science",
            "dob": "1955-03-10",  # Age 71
            "admission_year": "2026-27",
            "admission_date": "2026-07-20",
            "seat_type": "Regular",
        },
        # 4. SEAT_TYPE_NOT_APPROVED
        {
            "row_number": 4,
            "nri": "No",
            "foreign_national": "No",
            "admission_mode": "State counselling",
            "course": "Mechanical Engineering",
            "branch": "Mechanical",
            "dob": "2004-05-15",
            "admission_year": "2026-27",
            "admission_date": "2026-07-20",
            "seat_type": "Supernumerary",  # Not allowed in Mechanical
        },
        # 5. MODE_CATEGORY_MISMATCH
        {
            "row_number": 5,
            "nri": "Yes",
            "foreign_national": "No",
            "admission_mode": "State counselling",  # Mismatch
            "course": "Computer Science and Engineering",
            "branch": "Computer Science",
            "dob": "2004-05-15",
            "admission_year": "2026-27",
            "admission_date": "2026-07-20",
            "seat_type": "Regular",
        },
        # 6. ADMISSION_YEAR_MISMATCH
        {
            "row_number": 6,
            "nri": "No",
            "foreign_national": "No",
            "admission_mode": "State counselling",
            "course": "Computer Science and Engineering",
            "branch": "Computer Science",
            "dob": "2004-05-15",
            "admission_year": "2026-27",
            "admission_date": "2024-05-10",  # 2 years prior
            "seat_type": "Regular",
        },
    ]

    ctx = ValidationContext(
        rows=test_rows,
        extra={"approved_courses": approved_courses},
    )

    t15_rules = [
        CATEGORY_CONFLICT,
        COURSE_NOT_APPROVED,
        AGE_OUT_OF_RANGE,
        SEAT_TYPE_NOT_APPROVED,
        MODE_CATEGORY_MISMATCH,
        ADMISSION_YEAR_MISMATCH,
    ]

    result = run_rules(ctx, rules=t15_rules)
    assert len(result) == 6

    fired_codes = {f.rule_code for f in result}
    assert fired_codes == set(t15_rules)

    # Check level counts: 3 errors, 3 warnings
    errors = result.errors
    warnings = result.warnings
    assert len(errors) == 3
    assert {e.rule_code for e in errors} == {
        CATEGORY_CONFLICT,
        COURSE_NOT_APPROVED,
        SEAT_TYPE_NOT_APPROVED,
    }
    assert len(warnings) == 3
    assert {w.rule_code for w in warnings} == {
        AGE_OUT_OF_RANGE,
        MODE_CATEGORY_MISMATCH,
        ADMISSION_YEAR_MISMATCH,
    }


def test_messy_upload_csv_triggers_all_t15_rules() -> None:
    """Verify that demo/messy_upload.csv triggers each of the 6 T15 row consistency rules."""
    import csv
    from pathlib import Path

    csv_path = Path(__file__).resolve().parents[2] / "demo" / "messy_upload.csv"
    assert csv_path.exists(), f"Messy upload CSV missing at {csv_path}"

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for idx, r in enumerate(reader, start=1):
            r["row_number"] = idx
            rows.append(r)

    approved_courses = [
        {
            "name": "Computer Science and Engineering",
            "branch": "Computer Science",
            "supernumerary_allowed": True,
            "level": "UG",
        },
        {
            "name": "Mechanical Engineering",
            "branch": "Mechanical",
            "supernumerary_allowed": False,
            "level": "UG",
        },
    ]

    ctx = ValidationContext(
        rows=rows,
        extra={"approved_courses": approved_courses},
    )

    t15_rules = [
        CATEGORY_CONFLICT,
        COURSE_NOT_APPROVED,
        AGE_OUT_OF_RANGE,
        SEAT_TYPE_NOT_APPROVED,
        MODE_CATEGORY_MISMATCH,
        ADMISSION_YEAR_MISMATCH,
    ]

    result = run_rules(ctx, rules=t15_rules)
    fired_codes = {f.rule_code for f in result}

    # Ensure every one of the 6 rules fired on messy_upload.csv
    for r_code in t15_rules:
        assert r_code in fired_codes, f"Rule {r_code} failed to fire on demo/messy_upload.csv"

    # Verify specific rows from seed.py contract:
    # Row 12 (Tariq Mansoor): CATEGORY_CONFLICT
    assert any(f.rule_code == CATEGORY_CONFLICT and f.row_ref == 12 for f in result)
    # Row 13 (Suresh Raina): COURSE_NOT_APPROVED
    assert any(f.rule_code == COURSE_NOT_APPROVED and f.row_ref == 13 for f in result)
    # Row 14 (Govind Prasad): AGE_OUT_OF_RANGE
    assert any(f.rule_code == AGE_OUT_OF_RANGE and f.row_ref == 14 for f in result)
    # Row 15 (Pooja Hegde): SEAT_TYPE_NOT_APPROVED
    assert any(f.rule_code == SEAT_TYPE_NOT_APPROVED and f.row_ref == 15 for f in result)
    # Row 16 (Ananya Singhania): MODE_CATEGORY_MISMATCH
    assert any(f.rule_code == MODE_CATEGORY_MISMATCH and f.row_ref == 16 for f in result)
    # Row 17 (Harish Chandra): ADMISSION_YEAR_MISMATCH
    assert any(f.rule_code == ADMISSION_YEAR_MISMATCH and f.row_ref == 17 for f in result)

