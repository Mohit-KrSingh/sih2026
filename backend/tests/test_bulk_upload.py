"""Comprehensive test suite for bulk student uploads (TASKS.md T21 & SPEC.md 8.2, 9.4, 13).

Test coverage:
1. Template download with required lowercase headers.
2. File rejection: unreadable files, missing columns, empty file, oversized.
3. Saving all rows as drafts without discarding data.
4. Test with demo/messy_upload.csv: every row-level rule fires at least once.
5. Error CSV file export (row, field, code, level, message, fix hint).
6. Re-upload updates matching records (same college, course, year, APAAR ID).
7. Upload history tracking and retrieval.
8. Scoping, RBAC, IDOR protection, and audit log recording.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.models import AuditLog, Course, Institution, MockApaarRegistry, Student, User
from app.validation.codes import (
    ADMISSION_DATE_WINDOW,
    ADMISSION_YEAR_MISMATCH,
    AGE_OUT_OF_RANGE,
    APAAR_DOB_MISMATCH,
    APAAR_FORMAT,
    APAAR_NAME_MISMATCH,
    APAAR_NOT_FOUND,
    APAAR_REQUIRED,
    CATEGORY_CONFLICT,
    COUNTRY_REQUIRED,
    COURSE_NOT_APPROVED,
    DOB_INVALID,
    ENUM_INVALID,
    MODE_CATEGORY_MISMATCH,
    NAME_FORMAT,
    NAME_REQUIRED,
    SEAT_TYPE_NOT_APPROVED,
)

ALL_ROW_LEVEL_RULES = [
    APAAR_REQUIRED,
    APAAR_FORMAT,
    NAME_REQUIRED,
    NAME_FORMAT,
    DOB_INVALID,
    ENUM_INVALID,
    COUNTRY_REQUIRED,
    ADMISSION_DATE_WINDOW,
    APAAR_NOT_FOUND,
    APAAR_NAME_MISMATCH,
    APAAR_DOB_MISMATCH,
    CATEGORY_CONFLICT,
    COURSE_NOT_APPROVED,
    AGE_OUT_OF_RANGE,
    SEAT_TYPE_NOT_APPROVED,
    MODE_CATEGORY_MISMATCH,
    ADMISSION_YEAR_MISMATCH,
]

EXPECTED_HEADERS = [
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


def _create_test_college_and_admin(
    db: Session,
    suffix: str = "upload1",
    approval_status: str = "active",
) -> tuple[Institution, User, Course, str]:
    """Helper to provision a college, course, and authenticated college_admin user."""
    inst = Institution(
        aicte_id=f"1-TEST-{suffix.upper()}",
        name=f"College of Engineering {suffix}",
        state="Maharashtra",
        district="Pune",
        address="University Road",
        official_email=f"admin_{suffix}@testcollege.edu",
        official_phone="9876543210",
        head_name="Principal Dr. Sharma",
        affiliating_university="Savitribai Phule Pune University",
        approval_status=approval_status,
    )
    db.add(inst)
    db.flush()

    user = User(
        email=f"admin_{suffix}@testcollege.edu",
        password_hash=hash_password("Password123!"),
        role="college_admin",
        institution_id=inst.id,
        is_active=True,
    )
    db.add(user)
    db.flush()

    course = Course(
        institution_id=inst.id,
        name="Computer Science and Engineering",
        branch="Computer Science",
        level="UG",
        duration_years=4,
        supernumerary_allowed=True,
    )
    db.add(course)

    course_nosuper = Course(
        institution_id=inst.id,
        name="Mechanical Engineering",
        branch="Mechanical",
        level="UG",
        duration_years=4,
        supernumerary_allowed=False,
    )
    db.add(course_nosuper)
    db.flush()

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    return inst, user, course, token


def test_download_template_csv(client: TestClient, db_session: Session):
    """Verify template CSV contains all expected headers in lowercase and valid structure."""
    inst, _, _, token = _create_test_college_and_admin(db_session, "tpl")

    res = client.get(
        f"/api/v1/institutions/{inst.id}/students/upload/template",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "apaar_student_upload_template.csv" in res.headers["content-disposition"]

    reader = csv.reader(io.StringIO(res.text))
    header = next(reader)
    assert header == EXPECTED_HEADERS


def test_reject_unreadable_and_malformed_files(client: TestClient, db_session: Session):
    """Verify upload rejection policy for corrupt, missing-columns, empty, or oversized files."""
    inst, _, _, token = _create_test_college_and_admin(db_session, "reject")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Binary garbage / corrupt file
    garbage_bytes = b"\x00\xff\xfe\x01\x88\x99\xaa\xbb\xcc\xdd\xee\xff"
    res = client.post(
        f"/api/v1/institutions/{inst.id}/students/upload",
        headers=headers,
        files={"file": ("corrupt.bin", garbage_bytes, "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "FILE_TEMPLATE" in res.text or "Unreadable" in res.text

    # 2. Missing required columns (FILE_TEMPLATE)
    bad_csv = "apaar_id,name,dob\n123456789012,John Doe,2004-01-01\n"
    res = client.post(
        f"/api/v1/institutions/{inst.id}/students/upload",
        headers=headers,
        files={"file": ("bad_headers.csv", bad_csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 400
    assert "FILE_TEMPLATE" in res.text

    # 3. Empty file (FILE_EMPTY)
    empty_csv = ",".join(EXPECTED_HEADERS) + "\n"
    res = client.post(
        f"/api/v1/institutions/{inst.id}/students/upload",
        headers=headers,
        files={"file": ("empty.csv", empty_csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 400
    assert "FILE_EMPTY" in res.text

    # 4. Oversized file (FILE_TOO_LARGE)
    oversized_lines = [",".join(EXPECTED_HEADERS)]
    for i in range(1, 10005):
        oversized_lines.append(
            f"9000{i:08d},Student {i},2004-05-15,Male,Computer Science and Engineering,"
            f"Computer Science,2026-27,ENR-{i:05d},2026-07-15,State counselling,"
            "Regular,General,No,No,No,"
        )
    large_csv = "\n".join(oversized_lines)
    res = client.post(
        f"/api/v1/institutions/{inst.id}/students/upload",
        headers=headers,
        files={"file": ("oversized.csv", large_csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 400
    assert "FILE_TOO_LARGE" in res.text


def test_messy_upload_csv_triggers_all_row_rules(client: TestClient, db_session: Session):
    """Upload demo/messy_upload.csv and prove every row-level rule fires at least once.

    Acceptance Criteria (TASKS.md T21):
    - Test with demo/messy_upload.csv: every row-level rule fires at least once.
    - Saves all rows as drafts without silently discarding data.
    - Returns summary plus per-row badges and fix hints.
    """
    inst, _, _, token = _create_test_college_and_admin(db_session, "messy")
    headers = {"Authorization": f"Bearer {token}"}

    # Seed mock APAAR registry records specifically expected by messy_upload.csv
    existing_50 = db_session.scalar(
        select(MockApaarRegistry).where(MockApaarRegistry.apaar_id == "300000000050")
    )
    if not existing_50:
        db_session.add(
            MockApaarRegistry(
                apaar_id="300000000050",
                name="Vikram Malhotra",
                dob=date(2004, 8, 12),
                gender="Male",
            )
        )
    existing_51 = db_session.scalar(
        select(MockApaarRegistry).where(MockApaarRegistry.apaar_id == "300000000051")
    )
    if not existing_51:
        db_session.add(
            MockApaarRegistry(
                apaar_id="300000000051",
                name="Neha Sharma",
                dob=date(2004, 6, 10),
                gender="Female",
            )
        )
    db_session.flush()

    with open("demo/messy_upload.csv", "rb") as f:
        csv_bytes = f.read()

    res = client.post(
        f"/api/v1/institutions/{inst.id}/students/upload",
        headers=headers,
        files={"file": ("messy_upload.csv", csv_bytes, "text/csv")},
    )
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["filename"] == "messy_upload.csv"
    assert data["row_count"] == 17
    summary = data["summary"]
    assert summary["total_rows"] == 17
    assert summary["error_count"] > 0
    assert summary["warning_count"] > 0
    assert summary["inserted_count"] == 17

    # Verify every row-level rule fired at least once
    all_fired_codes: set[str] = set()
    for row in data["rows"]:
        for fl in row["flags"]:
            all_fired_codes.add(fl["rule_code"])

    missing_rules = [r for r in ALL_ROW_LEVEL_RULES if r not in all_fired_codes]
    assert not missing_rules, (
        f"The following row-level rules failed to fire on demo/messy_upload.csv: {missing_rules}. "
        f"All fired rules: {sorted(all_fired_codes)}"
    )

    # Verify hard rule 3: All rows were saved in PostgreSQL as drafts (none discarded)
    saved_students = list(
        db_session.scalars(
            select(Student).where(Student.institution_id == inst.id)
        ).all()
    )
    assert len(saved_students) == 17

    # Download error file and verify contents
    upload_id = data["upload_id"]
    err_res = client.get(
        f"/api/v1/institutions/{inst.id}/students/uploads/{upload_id}/errors",
        headers=headers,
    )
    assert err_res.status_code == 200
    assert "text/csv" in err_res.headers["content-type"]
    assert f"upload_{upload_id}_errors.csv" in err_res.headers["content-disposition"]

    err_reader = csv.DictReader(io.StringIO(err_res.text))
    err_rows = list(err_reader)
    assert len(err_rows) > 0
    err_codes = {r["rule_code"] for r in err_rows}
    assert "APAAR_REQUIRED" in err_codes
    assert "APAAR_NOT_FOUND" in err_codes
    assert "COURSE_NOT_APPROVED" in err_codes
    for err in err_rows:
        assert err["row_number"]
        assert err["rule_code"]
        assert err["message"]


def test_reupload_updates_matching_records(client: TestClient, db_session: Session):
    """Verify that re-uploading updates matching records (same college, course, year, APAAR ID)."""
    inst, _, course, token = _create_test_college_and_admin(db_session, "reup")
    headers = {"Authorization": f"Bearer {token}"}

    # Initial upload
    initial_csv = (
        ",".join(EXPECTED_HEADERS) + "\n"
        "999900001111,Original Name,2004-05-15,Male,Computer Science and Engineering,"
        "Computer Science,2026-27,ENR-001,2026-07-15,State counselling,Regular,General,No,No,No,\n"
    )
    res1 = client.post(
        f"/api/v1/institutions/{inst.id}/students/upload",
        headers=headers,
        files={"file": ("batch1.csv", initial_csv.encode("utf-8"), "text/csv")},
    )
    assert res1.status_code == 201
    d1 = res1.json()
    assert d1["summary"]["inserted_count"] == 1
    assert d1["summary"]["updated_count"] == 0
    student_id = d1["rows"][0]["student_id"]

    # Re-upload with modified Name and Admission Date
    updated_csv = (
        ",".join(EXPECTED_HEADERS) + "\n"
        "999900001111,Updated Name,2004-05-15,Male,Computer Science and Engineering,"
        "Computer Science,2026-27,ENR-001-NEW,2026-07-20,State counselling,"
        "Regular,General,No,No,No,\n"
    )
    res2 = client.post(
        f"/api/v1/institutions/{inst.id}/students/upload",
        headers=headers,
        files={"file": ("batch2.csv", updated_csv.encode("utf-8"), "text/csv")},
    )
    assert res2.status_code == 201
    d2 = res2.json()
    assert d2["summary"]["inserted_count"] == 0
    assert d2["summary"]["updated_count"] == 1
    assert d2["rows"][0]["student_id"] == student_id
    assert d2["rows"][0]["name"] == "Updated Name"

    # Query DB directly to verify in-place update without record duplication
    records = list(
        db_session.scalars(
            select(Student).where(
                Student.institution_id == inst.id,
                Student.apaar_id == "999900001111",
            )
        ).all()
    )
    assert len(records) == 1
    assert records[0].name == "Updated Name"
    assert records[0].enrolment_no == "ENR-001-NEW"


def test_upload_history_and_details_endpoints(client: TestClient, db_session: Session):
    """Verify upload history retrieval and upload detail querying."""
    inst, user, _, token = _create_test_college_and_admin(db_session, "hist")
    headers = {"Authorization": f"Bearer {token}"}

    csv_data = (
        ",".join(EXPECTED_HEADERS) + "\n"
        "999911112222,Aarav Patel,2004-05-15,Male,Computer Science and Engineering,"
        "Computer Science,2026-27,ENR-H1,2026-07-15,State counselling,Regular,General,No,No,No,\n"
    )
    upload_res = client.post(
        f"/api/v1/institutions/{inst.id}/students/upload",
        headers=headers,
        files={"file": ("history_test.csv", csv_data.encode("utf-8"), "text/csv")},
    )
    assert upload_res.status_code == 201
    upload_id = upload_res.json()["upload_id"]

    # History list
    hist_res = client.get(
        f"/api/v1/institutions/{inst.id}/students/uploads",
        headers=headers,
    )
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["total"] >= 1
    assert any(h["id"] == upload_id for h in hist_data["items"])

    # Upload details
    detail_res = client.get(
        f"/api/v1/institutions/{inst.id}/students/uploads/{upload_id}",
        headers=headers,
    )
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["upload_id"] == upload_id
    assert detail_data["filename"] == "history_test.csv"
    assert len(detail_data["rows"]) == 1

    # Verify audit log entry
    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity == "upload",
            AuditLog.entity_id == str(upload_id),
            AuditLog.action == "student.bulk_upload",
        )
    )
    assert audit_log is not None
    assert audit_log.actor_id == str(user.id)


def test_blocked_upload_when_approval_suspended(client: TestClient, db_session: Session):
    """Verify upload is blocked with 403 Forbidden when institution approval is suspended."""
    inst, _, _, token = _create_test_college_and_admin(
        db_session, "susp", approval_status="suspended"
    )
    headers = {"Authorization": f"Bearer {token}"}

    sample_csv = ",".join(EXPECTED_HEADERS) + "\n" + (
        "900012345678,Rahul Sharma,2004-05-15,Male,Computer Science and Engineering,"
        "Computer Science,2026-27,ENR-01,2026-07-15,State counselling,Regular,General,No,No,No,\n"
    )

    res = client.post(
        f"/api/v1/institutions/{inst.id}/students/upload",
        headers=headers,
        files={"file": ("test.csv", sample_csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 403
    assert "suspended" in res.text.lower()


def test_idor_institution_scoping(client: TestClient, db_session: Session):
    """Verify college_admin from College A cannot upload to College B."""
    inst_a, _, _, token_a = _create_test_college_and_admin(db_session, "idora")
    inst_b, _, _, _ = _create_test_college_and_admin(db_session, "idorb")

    sample_csv = ",".join(EXPECTED_HEADERS) + "\n" + (
        "900012345678,Rahul Sharma,2004-05-15,Male,Computer Science and Engineering,"
        "Computer Science,2026-27,ENR-01,2026-07-15,State counselling,Regular,General,No,No,No,\n"
    )

    res = client.post(
        f"/api/v1/institutions/{inst_b.id}/students/upload",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("test.csv", sample_csv.encode("utf-8"), "text/csv")},
    )
    assert res.status_code == 403

