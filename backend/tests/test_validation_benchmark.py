"""Validation engine performance benchmark test per SPEC.md Section 9.4 and TASKS.md T18.

Spec: Section 9.4:
"Performance target: 5,000 rows validated in under 10 seconds (benchmark test)."
"""

from __future__ import annotations

import time
from datetime import date

from app.integrations.interfaces import ApaarRecord
from app.integrations.mock.apaar import MockApaarClient
from app.validation.context import ValidationContext
from app.validation.engine import run_rules
from app.validation.service import validate_rows

FIRST_NAMES = [
    "Aarav", "Aditi", "Amit", "Ananya", "Arjun", "Deepak", "Devi", "Gaurav",
    "Ishaan", "Kavya", "Manish", "Neha", "Pooja", "Pranav", "Priya", "Rahul",
    "Riya", "Rohan", "Sakshi", "Sanjay", "Shreya", "Sneha", "Varun", "Vikas"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Mehta", "Reddy", "Nair", "Iyer", "Rao",
    "Joshi", "Deshmukh", "Kulkarni", "Chauhan", "Bhat", "Singh", "Gupta"
]

APPROVED_COURSES = {
    "computer science and engineering": {
        "name": "Computer Science and Engineering",
        "branch": "Computer Science",
    },
    "mechanical engineering": {
        "name": "Mechanical Engineering",
        "branch": "Mechanical",
    },
    "electronics and communication engineering": {
        "name": "Electronics and Communication Engineering",
        "branch": "Electronics",
    },
    "electrical engineering": {
        "name": "Electrical Engineering",
        "branch": "Electrical",
    },
    "civil engineering": {
        "name": "Civil Engineering",
        "branch": "Civil",
    },
}


def generate_benchmark_rows(count: int = 5000) -> tuple[list[dict[str, str]], list[ApaarRecord]]:
    """Generate deterministic, valid student rows and matching APAAR registry records."""
    rows: list[dict[str, str]] = []
    registry_records: list[ApaarRecord] = []

    courses = [
        ("Computer Science and Engineering", "Computer Science"),
        ("Mechanical Engineering", "Mechanical"),
        ("Electronics and Communication Engineering", "Electronics"),
        ("Electrical Engineering", "Electrical"),
        ("Civil Engineering", "Civil"),
    ]

    base_apaar = 100000000000

    for i in range(count):
        apaar_id = str(base_apaar + i)
        fn = FIRST_NAMES[i % len(FIRST_NAMES)]
        ln = LAST_NAMES[(i // len(FIRST_NAMES)) % len(LAST_NAMES)]
        # Plain alphabetical name with valid spaces and hyphens, no digits
        name = f"{fn} {ln}"
        dob = date(2004, (i % 12) + 1, (i % 28) + 1)
        gender = "Male" if i % 2 == 0 else "Female"
        course_name, branch_name = courses[i % len(courses)]
        enrol_no = f"ENR-{2026}-{i:05d}"
        adm_date = f"2026-07-{(i % 25) + 1:02d}"

        rows.append({
            "apaar_id": apaar_id,
            "name": name,
            "dob": dob.isoformat(),
            "gender": gender,
            "course": course_name,
            "branch": branch_name,
            "admission_year": "2026-27",
            "enrolment_no": enrol_no,
            "admission_date": adm_date,
            "admission_mode": "JEE Main counselling",
            "seat_type": "Regular",
            "reservation_category": "General",
            "nri": "No",
            "oci": "No",
            "foreign_national": "No",
            "country": "",
            "row_number": i + 1,
        })

        registry_records.append(
            ApaarRecord(
                apaar_id=apaar_id,
                name=name,
                dob=dob,
                gender=gender,
            )
        )

    return rows, registry_records


def test_validation_benchmark_5000_rows_under_10_seconds() -> None:
    """Benchmark test: Validate 5,000 student rows in under 10 seconds."""
    row_count = 5000
    rows, registry_records = generate_benchmark_rows(row_count)
    assert len(rows) == row_count
    assert len(registry_records) == row_count

    # Set up client with in-memory records to isolate validation speed from network/disk
    client = MockApaarClient(initial_records=registry_records)

    # Context setup
    context = ValidationContext(
        rows=rows,
        institution_id=1,
        academic_year="2026-27",
        apaar_client=client,
        extra={"approved_courses": APPROVED_COURSES},
    )

    # Warm-up run with 10 rows
    warmup_ctx = ValidationContext(
        rows=rows[:10],
        institution_id=1,
        academic_year="2026-27",
        apaar_client=client,
        extra={"approved_courses": APPROVED_COURSES},
    )
    _ = run_rules(warmup_ctx)

    # Benchmark run
    start_time = time.perf_counter()
    result = run_rules(context)
    elapsed = time.perf_counter() - start_time

    # Performance assertion: under 10.0 seconds per SPEC.md Section 9.4
    speed = row_count / elapsed
    print(f"\n[BENCHMARK] Validated {row_count} rows in {elapsed:.3f}s ({speed:.1f} rows/sec)")
    assert elapsed < 10.0, f"Validation took {elapsed:.2f}s, exceeding the 10.0s requirement!"

    # Correctness check: all generated rows are valid
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_validate_rows_entry_point_performance() -> None:
    """Benchmark test: validate_rows entry point validates 5,000 rows in under 10 seconds."""
    row_count = 5000
    rows, registry_records = generate_benchmark_rows(row_count)
    client = MockApaarClient(initial_records=registry_records)

    context = ValidationContext(
        rows=rows,
        institution_id=1,
        academic_year="2026-27",
        apaar_client=client,
        extra={"approved_courses": APPROVED_COURSES},
    )

    start_time = time.perf_counter()
    result = validate_rows(
        rows=rows,
        institution_id=1,
        academic_year="2026-27",
        apaar_client=client,
        context=context,
    )
    elapsed = time.perf_counter() - start_time

    print(f"\n[BENCHMARK] validate_rows processed {row_count} rows in {elapsed:.3f}s")
    assert elapsed < 10.0
    assert result.is_valid is True
    assert len(result.errors) == 0
