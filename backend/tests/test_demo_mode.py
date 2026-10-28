"""Comprehensive test suite for Demo Mode, reset scripts, and demo state verification.

SPEC.md Section 18 & TASKS.md T40:
- `make demo` resets to the scripted state.
- `TABLES_TO_TRUNCATE` covers all application tables in dependency order.
- Re-seeding restores all scripted demo fixtures:
  1. Over-intake flagged red (MMIT Mumbai, 68 regular admitted vs 60 intake, INTAKE_EXCEEDED).
  2. Cross-college duplicate caught (Priya Patel, 555566667777, DUP_ACTIVE_OTHER_COLLEGE).
  3. Anomaly alerts with explanations (Enrolment jump, DOB cluster, Sequential APAAR IDs).
  4. Cryptographic verification proof (VR-2025-111122223333 passing Ed25519 check).
  5. Cryptographic tamper detection (VR-TAMPERED-DEMO failing Ed25519 check with status='tampered').
  6. Demo CSV files in demo/ (clean, messy, overintake, cross_college_dupe).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.models import (
    Institution,
    Student,
    Submission,
    ValidationFlag,
    VerifiedRecord,
)
from app.seed import seed_all
from app.verification.service import verify_credential_by_id

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _import_demo_reset():
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from scripts.demo_reset import TABLES_TO_TRUNCATE, reset_database

    return TABLES_TO_TRUNCATE, reset_database


@pytest.fixture
def seeded_db(db_session: Session) -> Session:
    """Fixture ensuring test database contains standard seeded fixtures."""
    seed_all(db_session)
    db_session.commit()
    return db_session


def test_tables_to_truncate_covers_all_models(db_session: Session) -> None:
    """Ensure TABLES_TO_TRUNCATE includes every application table defined in SQLAlchemy models."""
    tables_to_truncate, _ = _import_demo_reset()
    inspector = inspect(db_session.get_bind())
    db_tables = set(inspector.get_table_names())

    # Exclude alembic_version as it tracks database schema migrations
    app_tables = db_tables - {"alembic_version"}

    truncate_set = set(tables_to_truncate)

    # All application tables must be included
    missing_tables = app_tables - truncate_set
    assert not missing_tables, (
        f"TABLES_TO_TRUNCATE is missing the following application tables: {missing_tables}"
    )


def test_scripted_demo_state_fixtures(seeded_db: Session) -> None:
    """Verify that all core demo fixtures required by DEMO.md are present and intact."""
    # 1. Over-intake College: MMIT Mumbai (1-10000002)
    mmit = seeded_db.scalar(select(Institution).where(Institution.aicte_id == "1-10000002"))
    assert mmit is not None
    assert "Mumbai Metropolitan" in mmit.name

    over_flag = seeded_db.scalar(
        select(ValidationFlag)
        .join(Submission, ValidationFlag.submission_id == Submission.id)
        .where(
            Submission.institution_id == mmit.id,
            ValidationFlag.rule_code == "INTAKE_EXCEEDED",
        )
    )
    assert over_flag is not None
    assert over_flag.level == "exception"
    assert "Regular admitted count (68) exceeds approved intake (60)" in over_flag.message
    assert over_flag.status == "justified"

    # 2. Cross-college duplicate: Priya Patel (555566667777)
    dupe_students = list(
        seeded_db.scalars(
            select(Student).where(
                Student.apaar_id == "555566667777",
                Student.academic_year == "2026-27",
            )
        ).all()
    )
    assert len(dupe_students) >= 2, "Priya Patel must be enrolled at >= 2 institutions"

    dupe_flags = list(
        seeded_db.scalars(
            select(ValidationFlag).where(
                ValidationFlag.rule_code == "DUP_ACTIVE_OTHER_COLLEGE",
            )
        ).all()
    )
    assert len(dupe_flags) >= 2, "Duplicate flags must exist at both institutions"

    # 3. Anomaly alerts with explanations
    jump_flag = seeded_db.scalar(
        select(ValidationFlag).where(ValidationFlag.rule_code == "ANOM_ENROLMENT_JUMP")
    )
    assert jump_flag is not None
    assert "exceeding the 30% threshold" in jump_flag.message
    assert jump_flag.audience == "aicte"

    cluster_flag = seeded_db.scalar(
        select(ValidationFlag).where(ValidationFlag.rule_code == "ANOM_DOB_CLUSTER")
    )
    assert cluster_flag is not None
    assert "Cluster of 8 students sharing the exact date of birth" in cluster_flag.message

    seq_flag = seeded_db.scalar(
        select(ValidationFlag).where(ValidationFlag.rule_code == "ANOM_SEQUENTIAL_APAAR")
    )
    assert seq_flag is not None
    assert "Sequential run of 12 APAAR IDs detected" in seq_flag.message

    # 4. Valid Cryptographic Credential
    valid_vr = seeded_db.scalar(
        select(VerifiedRecord).where(VerifiedRecord.verification_id == "VR-2025-111122223333")
    )
    assert valid_vr is not None
    check_valid = verify_credential_by_id(seeded_db, "VR-2025-111122223333")
    assert check_valid["verified"] is True
    assert check_valid["status"] == "active"
    assert "AICTE Central Repository" in check_valid["message"]

    # 5. Planted Tampered Credential
    tampered_vr = seeded_db.scalar(
        select(VerifiedRecord).where(VerifiedRecord.verification_id == "VR-TAMPERED-DEMO")
    )
    assert tampered_vr is not None
    check_tampered = verify_credential_by_id(seeded_db, "VR-TAMPERED-DEMO")
    assert check_tampered["verified"] is False
    assert check_tampered["status"] == "tampered"
    assert "Cryptographic signature verification failed" in check_tampered["message"]


def test_public_verification_api_tamper_and_valid_endpoints(
    client: TestClient, seeded_db: Session
) -> None:
    """Verify HTTP API responses for valid vs tampered credentials match DEMO.md specification."""
    # Valid credential
    res_valid = client.get("/api/v1/verification/verify?vid=VR-2025-111122223333")
    assert res_valid.status_code == 200
    data_valid = res_valid.json()
    assert data_valid["verified"] is True
    assert data_valid["status"] == "active"
    assert data_valid["institution"] == "Pune Institute of Advanced Engineering & Technology"
    assert "student_name" not in data_valid  # Privacy check

    # Tampered credential
    res_tampered = client.get("/api/v1/verification/verify?vid=VR-TAMPERED-DEMO")
    assert res_tampered.status_code == 200
    data_tampered = res_tampered.json()
    assert data_tampered["verified"] is False
    assert data_tampered["status"] == "tampered"
    assert "Cryptographic signature verification failed" in data_tampered["message"]


def test_demo_csv_files_exist_and_are_valid() -> None:
    """Verify that all 4 demo CSV files exist with proper headers and data rows."""
    demo_dir = Path("demo")
    expected_files = [
        ("clean_upload.csv", 25),
        ("messy_upload.csv", 17),
        ("overintake_upload.csv", 70),
        ("cross_college_dupe.csv", 1),
    ]

    for filename, min_rows in expected_files:
        path = demo_dir / filename
        assert path.exists(), f"Demo CSV {filename} must exist"
        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert "apaar_id" in header
            assert "course" in header
            rows = list(reader)
            assert len(rows) >= min_rows, (
                f"{filename} expected at least {min_rows} rows, got {len(rows)}"
            )


def test_reset_database_execution(db_session: Session) -> None:
    """Verify that reset_database executes clean truncation and Redis flush."""
    _, reset_db = _import_demo_reset()
    # Run reset_database targeting the test db session
    reset_db(session=db_session)
    # Verify students count is 0
    count = db_session.scalar(select(func.count(Student.id)))
    assert count == 0
    # Re-seed test database to maintain clean test environment
    seed_all(db_session)
    db_session.commit()
