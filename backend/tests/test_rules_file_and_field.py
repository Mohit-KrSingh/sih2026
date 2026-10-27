"""Unit tests for file and field validation rules (TASKS.md T13 & SPEC.md 9.3).

Rules covered:
1. FILE_TEMPLATE (file scope, error)
2. FILE_EMPTY (file scope, error)
3. FILE_TOO_LARGE (file scope, error)
4. APAAR_REQUIRED (row scope, error)
5. APAAR_FORMAT (row scope, error)
6. NAME_REQUIRED (row scope, error)
7. NAME_FORMAT (row scope, error)
8. DOB_INVALID (row scope, error)
9. ENUM_INVALID (row scope, error)
10. COUNTRY_REQUIRED (row scope, error)
11. ADMISSION_DATE_WINDOW (row scope, warning)

Each rule has at least three dedicated tests: pass, fail, edge case.
"""

from datetime import date, timedelta

from app.validation import (
    ADMISSION_DATE_WINDOW,
    APAAR_FORMAT,
    APAAR_REQUIRED,
    COUNTRY_REQUIRED,
    DOB_INVALID,
    ENUM_INVALID,
    FILE_EMPTY,
    FILE_TEMPLATE,
    FILE_TOO_LARGE,
    NAME_FORMAT,
    NAME_REQUIRED,
    ValidationContext,
    ValidationLevel,
    run_rules,
)
from app.validation.rules.file_template import EXPECTED_COLUMNS

# ---------------------------------------------------------------------------
# 1. FILE_TEMPLATE
# ---------------------------------------------------------------------------


def test_file_template_pass() -> None:
    """Pass: standard template with all 16 required columns."""
    ctx = ValidationContext(file_metadata={"headers": list(EXPECTED_COLUMNS)})
    result = run_rules(ctx, rules=[FILE_TEMPLATE])
    assert len(result) == 0
    assert result.is_valid is True


def test_file_template_fail_missing_columns() -> None:
    """Fail: headers missing 'dob' and 'country' columns."""
    incomplete = [c for c in EXPECTED_COLUMNS if c not in ("dob", "country")]
    ctx = ValidationContext(file_metadata={"headers": incomplete})
    result = run_rules(ctx, rules=[FILE_TEMPLATE])

    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == FILE_TEMPLATE
    assert flag.level == ValidationLevel.ERROR.value
    assert "dob" in flag.message
    assert "country" in flag.message
    assert "Download the standard CSV template" in flag.fix_hint
    assert flag.audience == "college"


def test_file_template_edge_case_whitespace_and_order() -> None:
    """Edge cases: whitespace, mixed case, and fallback to dict row keys."""
    # 1. Mixed case and surrounding whitespace
    headers_dirty = [f" {c.upper()} " for c in reversed(EXPECTED_COLUMNS)]
    ctx_dirty = ValidationContext(file_metadata={"headers": headers_dirty})
    result_dirty = run_rules(ctx_dirty, rules=[FILE_TEMPLATE])
    assert len(result_dirty) == 0

    # 2. Empty headers list
    ctx_empty = ValidationContext(file_metadata={"headers": []})
    result_empty = run_rules(ctx_empty, rules=[FILE_TEMPLATE])
    assert len(result_empty) == 1
    assert "Missing required column(s)" in result_empty[0].message

    # 3. Fallback to dict keys when file_metadata is missing
    dict_row = {col: "val" for col in EXPECTED_COLUMNS}
    ctx_dict = ValidationContext(rows=[dict_row])
    result_dict = run_rules(ctx_dict, rules=[FILE_TEMPLATE])
    assert len(result_dict) == 0


# ---------------------------------------------------------------------------
# 2. FILE_EMPTY
# ---------------------------------------------------------------------------


def test_file_empty_pass() -> None:
    """Pass: context contains at least one data row."""
    ctx = ValidationContext(rows=[{"apaar_id": "300000000001", "name": "Aman"}])
    result = run_rules(ctx, rules=[FILE_EMPTY])
    assert len(result) == 0


def test_file_empty_fail_no_rows() -> None:
    """Fail: rows list is completely empty."""
    ctx = ValidationContext(rows=[])
    result = run_rules(ctx, rules=[FILE_EMPTY])

    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == FILE_EMPTY
    assert flag.level == ValidationLevel.ERROR.value
    assert "contains no student data rows" in flag.message
    assert flag.audience == "college"


def test_file_empty_edge_case_row_count_metadata_zero() -> None:
    """Edge case: file_metadata explicitly specifies row_count=0."""
    ctx = ValidationContext(file_metadata={"row_count": 0})
    result = run_rules(ctx, rules=[FILE_EMPTY])
    assert len(result) == 1
    assert result[0].rule_code == FILE_EMPTY


# ---------------------------------------------------------------------------
# 3. FILE_TOO_LARGE
# ---------------------------------------------------------------------------


def test_file_too_large_pass() -> None:
    """Pass: row count is within standard 10,000 row limit."""
    ctx = ValidationContext(file_metadata={"row_count": 9999})
    result = run_rules(ctx, rules=[FILE_TOO_LARGE])
    assert len(result) == 0

    # Exactly 10,000 rows
    ctx_boundary = ValidationContext(file_metadata={"row_count": 10000})
    result_boundary = run_rules(ctx_boundary, rules=[FILE_TOO_LARGE])
    assert len(result_boundary) == 0


def test_file_too_large_fail() -> None:
    """Fail: 10,001 rows exceeds the default 10,000 row limit."""
    ctx = ValidationContext(file_metadata={"row_count": 10001})
    result = run_rules(ctx, rules=[FILE_TOO_LARGE])

    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == FILE_TOO_LARGE
    assert flag.level == ValidationLevel.ERROR.value
    assert "10,001" in flag.message
    assert "10,000" in flag.message
    assert flag.audience == "college"


def test_file_too_large_edge_case_parameter_override() -> None:
    """Edge case: max_rows threshold overridden via rule config."""
    # Custom limit of 100
    ctx = ValidationContext(
        file_metadata={"row_count": 101},
        params={"max_rows": 100},
    )
    result = run_rules(
        ctx,
        rules=[FILE_TOO_LARGE],
        overrides={"FILE_TOO_LARGE": {"params": {"max_rows": 100}}},
    )
    assert len(result) == 1
    assert "100" in result[0].message


# ---------------------------------------------------------------------------
# 4. APAAR_REQUIRED
# ---------------------------------------------------------------------------


def test_apaar_required_pass() -> None:
    """Pass: valid non-empty APAAR ID provided."""
    ctx = ValidationContext(rows=[{"row_number": 1, "apaar_id": "300000000001"}])
    result = run_rules(ctx, rules=[APAAR_REQUIRED])
    assert len(result) == 0


def test_apaar_required_fail_empty() -> None:
    """Fail: apaar_id is None or empty string."""
    ctx = ValidationContext(
        rows=[
            {"row_number": 2, "apaar_id": None},
            {"row_number": 3, "apaar_id": ""},
        ]
    )
    result = run_rules(ctx, rules=[APAAR_REQUIRED])

    assert len(result) == 2
    assert result[0].row_ref == 2
    assert result[0].field == "apaar_id"
    assert result[0].level == ValidationLevel.ERROR.value
    assert result[1].row_ref == 3


def test_apaar_required_edge_case_whitespace_and_single_row() -> None:
    """Edge case: string with only whitespace or single_row context."""
    ctx = ValidationContext(single_row={"row_number": 1, "apaar_id": "   "})
    result = run_rules(ctx, rules=[APAAR_REQUIRED])
    assert len(result) == 1
    assert result[0].rule_code == APAAR_REQUIRED


# ---------------------------------------------------------------------------
# 5. APAAR_FORMAT
# ---------------------------------------------------------------------------


def test_apaar_format_pass() -> None:
    """Pass: exactly 12 numeric digits."""
    ctx = ValidationContext(rows=[{"row_number": 1, "apaar_id": "300000000001"}])
    result = run_rules(ctx, rules=[APAAR_FORMAT])
    assert len(result) == 0


def test_apaar_format_fail_incorrect_length() -> None:
    """Fail: 11 digits (messy_upload:3) or 13 digits."""
    ctx = ValidationContext(
        rows=[
            {"row_number": 3, "apaar_id": "12345678901"},  # 11 digits
            {"row_number": 4, "apaar_id": "1234567890123"},  # 13 digits
        ]
    )
    result = run_rules(ctx, rules=[APAAR_FORMAT])

    assert len(result) == 2
    assert result[0].row_ref == 3
    assert "12345678901" in result[0].message
    assert "must be exactly 12 numeric digits" in result[0].message
    assert result[0].level == ValidationLevel.ERROR.value
    assert result[1].row_ref == 4


def test_apaar_format_edge_case_letters_hyphens_and_empty_skip() -> None:
    """Edge cases: alphanumeric characters, hyphens, and empty values skipped."""
    ctx = ValidationContext(
        rows=[
            {"row_number": 1, "apaar_id": "30000000003A"},  # Has letter
            {"row_number": 2, "apaar_id": "1234-5678-9012"},  # Formatted with hyphens
            {"row_number": 3, "apaar_id": ""},  # Empty: should be skipped by format rule
            {"row_number": 4, "apaar_id": None},  # None: should be skipped
        ]
    )
    result = run_rules(ctx, rules=[APAAR_FORMAT])

    # Only rows 1 and 2 fail APAAR_FORMAT; rows 3 and 4 are handled by APAAR_REQUIRED
    assert len(result) == 2
    assert {r.row_ref for r in result} == {1, 2}


# ---------------------------------------------------------------------------
# 6. NAME_REQUIRED
# ---------------------------------------------------------------------------


def test_name_required_pass() -> None:
    """Pass: valid student name provided."""
    ctx = ValidationContext(rows=[{"row_number": 1, "name": "Radha Om"}])
    result = run_rules(ctx, rules=[NAME_REQUIRED])
    assert len(result) == 0


def test_name_required_fail_empty() -> None:
    """Fail: student name is None or empty string (messy_upload:4)."""
    ctx = ValidationContext(
        rows=[
            {"row_number": 4, "name": ""},
            {"row_number": 5, "name": None},
        ]
    )
    result = run_rules(ctx, rules=[NAME_REQUIRED])

    assert len(result) == 2
    assert result[0].row_ref == 4
    assert result[0].field == "name"
    assert result[0].level == ValidationLevel.ERROR.value
    assert "Student name is missing" in result[0].message


def test_name_required_edge_case_whitespace() -> None:
    """Edge case: string of whitespace."""
    ctx = ValidationContext(rows=[{"row_number": 1, "name": "     "}])
    result = run_rules(ctx, rules=[NAME_REQUIRED])
    assert len(result) == 1
    assert result[0].rule_code == NAME_REQUIRED


# ---------------------------------------------------------------------------
# 7. NAME_FORMAT
# ---------------------------------------------------------------------------


def test_name_format_pass() -> None:
    """Pass: name containing letters, spaces, dots, and hyphens."""
    ctx = ValidationContext(
        rows=[
            {"row_number": 1, "name": "Radha Om"},
            {"row_number": 2, "name": "Dr. B. R. Ambedkar"},
            {"row_number": 3, "name": "Mary-Jane Watson"},
        ]
    )
    result = run_rules(ctx, rules=[NAME_FORMAT])
    assert len(result) == 0


def test_name_format_fail_digits() -> None:
    """Fail: name with numbers (messy_upload:5 'Rahul123 Sharma')."""
    ctx = ValidationContext(rows=[{"row_number": 5, "name": "Rahul123 Sharma"}])
    result = run_rules(ctx, rules=[NAME_FORMAT])

    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == NAME_FORMAT
    assert flag.row_ref == 5
    assert flag.field == "name"
    assert "Rahul123 Sharma" in flag.message
    assert "digits or illegal characters" in flag.message
    assert flag.level == ValidationLevel.ERROR.value


def test_name_format_edge_case_special_chars_and_no_letters() -> None:
    """Edge cases: special symbols, punctuation-only strings, and empty value skipping."""
    ctx = ValidationContext(
        rows=[
            {"row_number": 1, "name": "Amit@Verma"},  # Contains '@'
            {"row_number": 2, "name": "John $mith"},  # Contains '$'
            {"row_number": 3, "name": "---"},  # Hyphens only, no letters
            {"row_number": 4, "name": "..."},  # Dots only, no letters
            {"row_number": 5, "name": ""},  # Empty: skipped (handled by NAME_REQUIRED)
        ]
    )
    result = run_rules(ctx, rules=[NAME_FORMAT])
    assert len(result) == 4
    assert {r.row_ref for r in result} == {1, 2, 3, 4}


# ---------------------------------------------------------------------------
# 8. DOB_INVALID
# ---------------------------------------------------------------------------


def test_dob_invalid_pass() -> None:
    """Pass: valid past date in ISO format (string or date object)."""
    ctx = ValidationContext(
        rows=[
            {"row_number": 1, "dob": "2006-06-25"},
            {"row_number": 2, "dob": date(2004, 5, 10)},
        ]
    )
    result = run_rules(ctx, rules=[DOB_INVALID])
    assert len(result) == 0


def test_dob_invalid_fail_future_date() -> None:
    """Fail: date in the future (messy_upload:6 '2099-01-01')."""
    future_str = (date.today() + timedelta(days=365)).isoformat()
    ctx = ValidationContext(
        rows=[
            {"row_number": 6, "dob": "2099-01-01"},
            {"row_number": 7, "dob": future_str},
        ]
    )
    result = run_rules(ctx, rules=[DOB_INVALID])

    assert len(result) == 2
    assert result[0].row_ref == 6
    assert result[0].field == "dob"
    assert "in the future" in result[0].message
    assert result[0].level == ValidationLevel.ERROR.value


def test_dob_invalid_edge_case_formats_and_boundaries() -> None:
    """Edge cases: wrong format (DD/MM/YYYY), impossible calendar date, ancient year, empty."""
    ctx = ValidationContext(
        rows=[
            {"row_number": 1, "dob": "25/06/2004"},  # Non-ISO format
            {"row_number": 2, "dob": "2004-02-30"},  # Invalid February date
            {"row_number": 3, "dob": "1850-01-01"},  # Year before 1900
            {"row_number": 4, "dob": ""},  # Missing date
            {"row_number": 5, "dob": "not-a-date"},  # Garbage string
        ]
    )
    result = run_rules(ctx, rules=[DOB_INVALID])

    assert len(result) == 5
    codes = [r.rule_code for r in result]
    assert all(c == DOB_INVALID for c in codes)


# ---------------------------------------------------------------------------
# 9. ENUM_INVALID
# ---------------------------------------------------------------------------


def test_enum_invalid_pass() -> None:
    """Pass: all enumerated fields contain valid permitted values."""
    ctx = ValidationContext(
        rows=[
            {
                "row_number": 1,
                "gender": "Female",
                "reservation_category": "OBC",
                "seat_type": "Regular",
                "admission_mode": "State counselling",
                "nri": "No",
                "oci": "No",
                "foreign_national": "No",
            },
            {
                "row_number": 2,
                "gender": "Male",
                "reservation_category": "General",
                "seat_type": "Supernumerary",
                "admission_mode": "JEE Main counselling",
                "nri": "Yes",
                "oci": "No",
                "foreign_national": "No",
            },
        ]
    )
    result = run_rules(ctx, rules=[ENUM_INVALID])
    assert len(result) == 0


def test_enum_invalid_fail_messy_upload() -> None:
    """Fail: invalid gender and reservation category (messy_upload:7)."""
    ctx = ValidationContext(
        rows=[
            {
                "row_number": 7,
                "gender": "InvalidGender",
                "reservation_category": "AlienCategory",
                "seat_type": "Regular",
                "admission_mode": "State counselling",
                "nri": "No",
                "oci": "No",
                "foreign_national": "No",
            }
        ]
    )
    result = run_rules(ctx, rules=[ENUM_INVALID])

    assert len(result) == 2
    fields = {r.field for r in result}
    assert fields == {"gender", "reservation_category"}
    assert result[0].level == ValidationLevel.ERROR.value


def test_enum_invalid_edge_case_mode_and_booleans() -> None:
    """Edge cases: invalid admission mode, invalid yes/no booleans, and empty values."""
    ctx = ValidationContext(
        rows=[
            {
                "row_number": 1,
                "seat_type": "ManagementQuotaSeat",  # Invalid seat type
                "admission_mode": "Backdoor Entry",  # Invalid mode
                "nri": "Maybe",  # Invalid boolean
                "gender": "Other",  # Valid 'Other'
            },
            {
                "row_number": 2,
                "nri": "",  # Empty optional boolean: skipped
                "gender": "Male",
            },
        ]
    )
    result = run_rules(ctx, rules=[ENUM_INVALID])
    assert len(result) == 3
    bad_fields = {r.field for r in result}
    assert bad_fields == {"seat_type", "admission_mode", "nri"}


# ---------------------------------------------------------------------------
# 10. COUNTRY_REQUIRED
# ---------------------------------------------------------------------------


def test_country_required_pass() -> None:
    """Pass: country provided for foreign national; empty for domestic student."""
    ctx = ValidationContext(
        rows=[
            {"row_number": 1, "foreign_national": "Yes", "country": "Nepal"},
            {"row_number": 2, "foreign_national": "No", "country": ""},
            {"row_number": 3, "foreign_national": "No", "country": None},
        ]
    )
    result = run_rules(ctx, rules=[COUNTRY_REQUIRED])
    assert len(result) == 0


def test_country_required_fail_foreign_national_missing_country() -> None:
    """Fail: foreign_national is Yes but country is empty (messy_upload:8)."""
    ctx = ValidationContext(
        rows=[
            {"row_number": 8, "foreign_national": "Yes", "country": ""},
            {"row_number": 9, "foreign_national": "Yes", "country": None},
        ]
    )
    result = run_rules(ctx, rules=[COUNTRY_REQUIRED])

    assert len(result) == 2
    assert result[0].row_ref == 8
    assert result[0].field == "country"
    assert result[0].level == ValidationLevel.ERROR.value
    assert "Country is required" in result[0].message
    assert result[1].row_ref == 9


def test_country_required_edge_case_case_insensitivity_and_whitespace() -> None:
    """Edge cases: foreign_national='yes' with whitespace country."""
    ctx = ValidationContext(
        rows=[
            {"row_number": 1, "foreign_national": "YES", "country": "   "},
            {"row_number": 2, "foreign_national": "no", "country": ""},
        ]
    )
    result = run_rules(ctx, rules=[COUNTRY_REQUIRED])
    assert len(result) == 1
    assert result[0].row_ref == 1


# ---------------------------------------------------------------------------
# 11. ADMISSION_DATE_WINDOW
# ---------------------------------------------------------------------------


def test_admission_date_window_pass_in_window() -> None:
    """Pass: admission date falls inside May 1 - Nov 30 window for academic year 2026-27."""
    ctx = ValidationContext(
        rows=[
            {
                "row_number": 1,
                "admission_year": "2026-27",
                "admission_date": "2026-07-15",
            },
            {
                "row_number": 2,
                "admission_year": "2026-27",
                "admission_date": date(2026, 8, 10),
            },
        ]
    )
    result = run_rules(ctx, rules=[ADMISSION_DATE_WINDOW])
    assert len(result) == 0


def test_admission_date_window_fail_before_window() -> None:
    """Fail: admission date in January 2026 before May 1 window start (messy_upload:9)."""
    ctx = ValidationContext(
        rows=[
            {
                "row_number": 9,
                "admission_year": "2026-27",
                "admission_date": "2026-01-05",
            }
        ]
    )
    result = run_rules(ctx, rules=[ADMISSION_DATE_WINDOW])

    assert len(result) == 1
    flag = result[0]
    assert flag.rule_code == ADMISSION_DATE_WINDOW
    assert flag.level == ValidationLevel.WARNING.value
    assert flag.row_ref == 9
    assert flag.field == "admission_date"
    assert "outside the standard admission window" in flag.message
    assert "2026-01-05" in flag.message
    assert flag.audience == "college"
    assert flag.requires_justification is False


def test_admission_date_window_edge_case_after_window_and_params() -> None:
    """Edge cases: admission date in December (after Nov 30) and parameter overrides."""
    # 1. Date in December falls after standard Nov 30 window
    ctx_dec = ValidationContext(
        rows=[
            {
                "row_number": 1,
                "admission_year": "2026-27",
                "admission_date": "2026-12-15",
            }
        ]
    )
    result_dec = run_rules(ctx_dec, rules=[ADMISSION_DATE_WINDOW])
    assert len(result_dec) == 1
    assert "outside the standard admission window" in result_dec[0].message

    # 2. Window start overridden to January 1 allows January 5 to pass
    ctx_jan = ValidationContext(
        rows=[
            {
                "row_number": 1,
                "admission_year": "2026-27",
                "admission_date": "2026-01-05",
            }
        ]
    )
    result_overridden = run_rules(
        ctx_jan,
        rules=[ADMISSION_DATE_WINDOW],
        overrides={"ADMISSION_DATE_WINDOW": {"params": {"start_month": 1, "start_day": 1}}},
    )
    assert len(result_overridden) == 0

    # 3. Missing admission_date or unparseable date is safely skipped
    ctx_missing = ValidationContext(
        rows=[
            {"row_number": 2, "admission_year": "2026-27", "admission_date": ""},
            {"row_number": 3, "admission_year": "2026-27", "admission_date": "invalid-date"},
        ]
    )
    result_missing = run_rules(ctx_missing, rules=[ADMISSION_DATE_WINDOW])
    assert len(result_missing) == 0
