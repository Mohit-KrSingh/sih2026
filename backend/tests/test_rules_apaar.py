"""Tests for APAAR validation rules.

Spec: Section 9.3 & TASKS.md T14:
- APAAR_NOT_FOUND: ID does not exist in registry (level: error).
- APAAR_NAME_MISMATCH: Fuzzy match below threshold (default 85) using RapidFuzz.
- APAAR_DOB_MISMATCH: Date of birth differs from registry (level: error).
- Batched lookup: ApaarClient.lookup_batch is called once per validation run.
- Tests: spelling variants pass (e.g. "Rahul Sharma" vs "SHARMA RAHUL"), different person fails.
- Pass, fail, edge case for each rule.
"""

from datetime import date
from unittest.mock import MagicMock

from app.integrations.interfaces import ApaarClient, ApaarRecord
from app.integrations.mock import MockApaarClient
from app.validation.codes import (
    APAAR_DOB_MISMATCH,
    APAAR_NAME_MISMATCH,
    APAAR_NOT_FOUND,
)
from app.validation.context import ValidationContext
from app.validation.engine import run_rules
from app.validation.rules.apaar_dob_mismatch import ApaarDobMismatchRule
from app.validation.rules.apaar_name_mismatch import ApaarNameMismatchRule
from app.validation.rules.apaar_not_found import ApaarNotFoundRule

# ============================================================================
# Helpers & Fixtures
# ============================================================================


def _create_mock_apaar_client(records: list[ApaarRecord]) -> MockApaarClient:
    """Helper to instantiate MockApaarClient with in-memory records."""
    client = MockApaarClient()
    for rec in records:
        client.add_record(
            apaar_id=rec.apaar_id,
            name=rec.name,
            dob=rec.dob,
            gender=rec.gender,
            persist_to_db=False,
        )
    return client


# ============================================================================
# 1. APAAR_NOT_FOUND Rule Tests (Pass, Fail, Edge Cases)
# ============================================================================


def test_apaar_not_found_pass() -> None:
    """Registered APAAR ID produces no flags."""
    rec = ApaarRecord("111122223333", "Rahul Sharma", date(2004, 5, 15), "Male")
    client = _create_mock_apaar_client([rec])
    ctx = ValidationContext(
        rows=[{"apaar_id": "111122223333", "name": "Rahul Sharma", "dob": "2004-05-15"}],
        apaar_client=client,
    )
    rule = ApaarNotFoundRule()
    flags = rule.check(ctx)
    assert len(flags) == 0


def test_apaar_not_found_fail() -> None:
    """Unregistered 12-digit APAAR ID produces an ERROR flag with plain English hint."""
    client = _create_mock_apaar_client([])  # Empty registry
    ctx = ValidationContext(
        rows=[
            {
                "row_number": 42,
                "apaar_id": "999988887777",
                "name": "Unknown Student",
                "dob": "2005-01-01",
            }
        ],
        apaar_client=client,
    )
    rule = ApaarNotFoundRule()
    flags = rule.check(ctx)

    assert len(flags) == 1
    flag = flags[0]
    assert flag.rule_code == APAAR_NOT_FOUND
    assert flag.level == "error"
    assert flag.row_ref == 42
    assert flag.field == "apaar_id"
    assert "999988887777" in flag.message
    assert "does not exist in the APAAR registry" in flag.message
    assert "Verify the 12-digit APAAR ID" in flag.fix_hint
    assert flag.requires_justification is False


def test_apaar_not_found_edge_cases() -> None:
    """Format-invalid APAAR IDs are safely skipped by this rule (handled by cheap checks)."""
    client = _create_mock_apaar_client([])
    ctx = ValidationContext(
        rows=[
            {"apaar_id": None, "name": "No ID"},
            {"apaar_id": "", "name": "Empty ID"},
            {"apaar_id": "12345", "name": "Too Short"},
            {"apaar_id": "1234567890123", "name": "Too Long"},
            {"apaar_id": "12345678901A", "name": "Alphanumeric"},
        ],
        apaar_client=client,
    )
    rule = ApaarNotFoundRule()
    flags = rule.check(ctx)
    assert len(flags) == 0


# ============================================================================
# 2. APAAR_NAME_MISMATCH Rule Tests (Fuzzy matching with RapidFuzz)
# ============================================================================


def test_apaar_name_mismatch_pass_exact() -> None:
    """Exact name match passes without flags."""
    rec = ApaarRecord("111122223333", "Rahul Sharma", date(2004, 5, 15), "Male")
    client = _create_mock_apaar_client([rec])
    ctx = ValidationContext(
        rows=[{"apaar_id": "111122223333", "name": "Rahul Sharma"}],
        apaar_client=client,
    )
    rule = ApaarNameMismatchRule()
    flags = rule.check(ctx)
    assert len(flags) == 0


def test_apaar_name_mismatch_pass_spelling_variants() -> None:
    """Spelling variants and word-order changes pass (e.g. 'Rahul Sharma' vs 'SHARMA RAHUL')."""
    client = _create_mock_apaar_client(
        [
            ApaarRecord("100000000001", "Rahul Sharma", date(2004, 5, 15), "Male"),
            ApaarRecord("100000000002", "Pooja Sharma", date(2003, 8, 20), "Female"),
            ApaarRecord("100000000003", "Sunita Rao", date(2004, 2, 10), "Female"),
        ]
    )
    ctx = ValidationContext(
        rows=[
            # Word-order inverted + uppercase: "SHARMA RAHUL" -> score 100.0 >= 85
            {"apaar_id": "100000000001", "name": "SHARMA RAHUL"},
            # Minor typo: "Pooja Sarma" -> score 90.9 >= 85
            {"apaar_id": "100000000002", "name": "Pooja Sarma"},
            # Phonetic variant: "Suneeta Rao" -> score 85.7 >= 85
            {"apaar_id": "100000000003", "name": "Suneeta Rao"},
        ],
        apaar_client=client,
    )
    rule = ApaarNameMismatchRule()
    flags = rule.check(ctx)
    assert len(flags) == 0


def test_apaar_name_mismatch_fail_different_person() -> None:
    """A completely different person fails with a WARNING flag and similarity score."""
    rec = ApaarRecord("300000000050", "Vikram Malhotra", date(2004, 8, 12), "Male")
    client = _create_mock_apaar_client([rec])
    # Planted messy case: registry has Vikram Malhotra, upload has Zachary Taylor
    ctx = ValidationContext(
        rows=[
            {
                "row_number": 10,
                "apaar_id": "300000000050",
                "name": "Zachary Taylor",
            }
        ],
        apaar_client=client,
    )
    rule = ApaarNameMismatchRule()
    flags = rule.check(ctx)

    assert len(flags) == 1
    flag = flags[0]
    assert flag.rule_code == APAAR_NAME_MISMATCH
    assert flag.level == "warning"
    assert flag.row_ref == 10
    assert flag.field == "name"
    assert "Zachary Taylor" in flag.message
    assert "Vikram Malhotra" in flag.message
    assert "below threshold 85%" in flag.message
    assert "official APAAR card name 'Vikram Malhotra'" in flag.fix_hint


def test_apaar_name_mismatch_configurable_threshold() -> None:
    """Threshold parameter can be tuned via context params or rule_config overrides."""
    rec = ApaarRecord("111122223333", "Rahul Sharma", date(2004, 5, 15), "Male")
    client = _create_mock_apaar_client([rec])
    # "Rahul K Sharma" vs "Rahul Sharma" has score 92.3
    # At default threshold 85 -> passes
    ctx_default = ValidationContext(
        rows=[{"apaar_id": "111122223333", "name": "Rahul K Sharma"}],
        apaar_client=client,
    )
    rule = ApaarNameMismatchRule()
    assert len(rule.check(ctx_default)) == 0

    # At stricter threshold 95 -> fails
    ctx_strict = ctx_default.with_params({"threshold": 95})
    strict_flags = rule.check(ctx_strict)
    assert len(strict_flags) == 1
    assert "below threshold 95%" in strict_flags[0].message


def test_apaar_name_mismatch_edge_cases() -> None:
    """Missing names, unregistered records, or invalid APAAR IDs do not trigger name mismatch."""
    client = _create_mock_apaar_client([])
    ctx = ValidationContext(
        rows=[
            {"apaar_id": "111122223333", "name": None},  # Missing name
            {"apaar_id": "111122223333", "name": ""},  # Empty name
            {"apaar_id": "999999999999", "name": "Unregistered Person"},  # Not in registry
            {"apaar_id": "123", "name": "Invalid ID Format"},  # Invalid APAAR format
        ],
        apaar_client=client,
    )
    rule = ApaarNameMismatchRule()
    flags = rule.check(ctx)
    assert len(flags) == 0


# ============================================================================
# 3. APAAR_DOB_MISMATCH Rule Tests (Pass, Fail, Edge Cases)
# ============================================================================


def test_apaar_dob_mismatch_pass() -> None:
    """Matching DOB (as date object or ISO string) produces no flags."""
    client = _create_mock_apaar_client(
        [
            ApaarRecord("100000000001", "Aarav", date(2004, 6, 10), "Male"),
            ApaarRecord("100000000002", "Priya", date(2005, 11, 25), "Female"),
        ]
    )
    ctx = ValidationContext(
        rows=[
            {"apaar_id": "100000000001", "dob": "2004-06-10"},
            {"apaar_id": "100000000002", "dob": date(2005, 11, 25)},
        ],
        apaar_client=client,
    )
    rule = ApaarDobMismatchRule()
    flags = rule.check(ctx)
    assert len(flags) == 0


def test_apaar_dob_mismatch_fail() -> None:
    """Different DOB produces an ERROR flag referencing row and registry dates."""
    rec = ApaarRecord("300000000051", "Neha Sharma", date(2004, 6, 10), "Female")
    client = _create_mock_apaar_client([rec])
    # Planted messy case: registry has 2004-06-10, upload has 2004-06-11
    ctx = ValidationContext(
        rows=[
            {
                "row_number": 11,
                "apaar_id": "300000000051",
                "name": "Neha Sharma",
                "dob": "2004-06-11",
            }
        ],
        apaar_client=client,
    )
    rule = ApaarDobMismatchRule()
    flags = rule.check(ctx)

    assert len(flags) == 1
    flag = flags[0]
    assert flag.rule_code == APAAR_DOB_MISMATCH
    assert flag.level == "error"
    assert flag.row_ref == 11
    assert flag.field == "dob"
    assert "2004-06-11" in flag.message
    assert "2004-06-10" in flag.message
    assert "Update the date of birth" in flag.fix_hint
    assert flag.requires_justification is False


def test_apaar_dob_mismatch_edge_cases() -> None:
    """Invalid date strings, unregistered records, or missing APAAR IDs are safely skipped."""
    rec = ApaarRecord("111122223333", "Test", date(2004, 1, 1), "Male")
    client = _create_mock_apaar_client([rec])
    ctx = ValidationContext(
        rows=[
            {"apaar_id": "111122223333", "dob": None},  # Missing DOB
            {"apaar_id": "111122223333", "dob": "not-a-date"},  # Handled by DOB_INVALID
            {"apaar_id": "999999999999", "dob": "2004-01-01"},  # Handled by APAAR_NOT_FOUND
            {"apaar_id": "invalid", "dob": "2004-01-01"},  # Handled by APAAR_FORMAT
        ],
        apaar_client=client,
    )
    rule = ApaarDobMismatchRule()
    flags = rule.check(ctx)
    assert len(flags) == 0


# ============================================================================
# 4. Batched Lookup Execution & Pipeline Integration
# ============================================================================


def test_apaar_client_batched_lookup_called_once() -> None:
    """ApaarClient.lookup_batch is called exactly ONCE across all APAAR rules in a run."""
    spy_client = MagicMock(spec=ApaarClient)
    spy_client.lookup_batch.return_value = {
        "100000000001": ApaarRecord("100000000001", "Rahul Sharma", date(2004, 5, 15), "Male"),
        "100000000002": ApaarRecord("100000000002", "Priya Patel", date(2005, 3, 20), "Female"),
        "100000000003": None,  # Not found
    }

    ctx = ValidationContext(
        rows=[
            {
                "row_number": 1,
                "apaar_id": "100000000001",
                "name": "SHARMA RAHUL",
                "dob": "2004-05-15",
            },
            {
                "row_number": 2,
                "apaar_id": "100000000002",
                "name": "Priya Patel",
                "dob": "2005-03-21",  # DOB mismatch
            },
            {
                "row_number": 3,
                "apaar_id": "100000000003",
                "name": "Ghost Student",
                "dob": "2004-01-01",  # Not found
            },
            {
                "row_number": 4,
                "apaar_id": "100000000001",
                "name": "SHARMA RAHUL",
                "dob": "2004-05-15",  # Duplicate ID in file
            },
        ],
        apaar_client=spy_client,
    )

    # Run all three APAAR rules
    rules = [ApaarNotFoundRule(), ApaarNameMismatchRule(), ApaarDobMismatchRule()]
    result = run_rules(ctx, rules=rules)

    # Verify lookup_batch was called exactly ONCE
    assert spy_client.lookup_batch.call_count == 1
    requested_ids = spy_client.lookup_batch.call_args[0][0]
    # Check that distinct IDs were queried
    assert set(requested_ids) == {"100000000001", "100000000002", "100000000003"}

    # Verify result flags
    assert len(result) == 2
    codes = {f.rule_code for f in result}
    assert APAAR_NOT_FOUND in codes
    assert APAAR_DOB_MISMATCH in codes
    assert APAAR_NAME_MISMATCH not in codes  # "SHARMA RAHUL" matched "Rahul Sharma"
