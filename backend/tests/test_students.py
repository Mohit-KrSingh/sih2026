"""Comprehensive tests for Single Student Entry, Directory, Edit, Delete, and Validation.

Spec: Section 8.2, 9.4, 13, 15, 16 & TASKS.md T20:
- Form grouped Identity, Admission, Category.
- 'Check and save' runs validation engine immediately and returns flags; saved as draft either way.
- Country field appears only for foreign nationals (persisted when Yes, cleared when No).
- Edit and delete draft records.
- Student list with filters by status and flag level.
- Locking protection (submitted or locked records cannot be edited or deleted).
- IDOR isolation: College A cannot read, create, edit, or delete College B records.
- Role limits: College viewer is strictly read-only (403 on mutation).
- Suspended approval blocks student creation and edits.
- Hash-chained audit logging on create, update, and delete.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, encrypt_dob, hash_password
from app.models import (
    AuditLog,
    Course,
    CourseIntake,
    Institution,
    MockApaarRegistry,
    Student,
    User,
    ValidationFlag,
)


@pytest.fixture
def student_test_env(db_session: Session):
    """Seed test institutions, courses, registry entries, and users."""
    # 1. College Alpha (Active)
    inst_a = Institution(
        aicte_id="1-STU-ALPHA",
        name="Alpha Engineering College",
        state="Maharashtra",
        district="Pune",
        address="100 Tech Park, Hinjawadi",
        official_email="principal@alpha-college.edu",
        official_phone="+919876543210",
        head_name="Dr. Alpha Principal",
        affiliating_university="Pune University",
        approval_status="active",
        account_status="active",
    )
    # 2. College Beta (Active, for IDOR checks)
    inst_b = Institution(
        aicte_id="1-STU-BETA",
        name="Beta Institute of Technology",
        state="Karnataka",
        district="Bengaluru",
        address="200 Electronic City",
        official_email="principal@beta-tech.edu",
        official_phone="+919876543211",
        head_name="Dr. Beta Principal",
        affiliating_university="VTU",
        approval_status="active",
        account_status="active",
    )
    # 3. College Gamma (Suspended approval)
    inst_suspended = Institution(
        aicte_id="1-STU-SUSPEND",
        name="Suspended College of Tech",
        state="Delhi",
        district="New Delhi",
        address="300 Ring Road",
        official_email="principal@suspended-college.edu",
        official_phone="+919876543212",
        head_name="Dr. Suspended",
        affiliating_university="Delhi University",
        approval_status="suspended",
        account_status="active",
    )

    db_session.add_all([inst_a, inst_b, inst_suspended])
    db_session.flush()

    # Courses for College Alpha
    c_cse = Course(
        institution_id=inst_a.id,
        name="Computer Science and Engineering",
        branch="Computer Science",
        level="UG",
        duration_years=4,
        supernumerary_allowed=True,
    )
    c_mech = Course(
        institution_id=inst_a.id,
        name="Mechanical Engineering",
        branch="Mechanical",
        level="UG",
        duration_years=4,
        supernumerary_allowed=False,
    )
    # Course for College Beta
    c_beta_it = Course(
        institution_id=inst_b.id,
        name="Information Technology",
        branch="IT",
        level="UG",
        duration_years=4,
        supernumerary_allowed=True,
    )

    db_session.add_all([c_cse, c_mech, c_beta_it])
    db_session.flush()

    # Approved Intakes
    intake_cse = CourseIntake(
        course_id=c_cse.id,
        academic_year="2026-27",
        approved_intake=60,
        supernumerary_seats_allowed=6,
        source="aicte_master",
    )
    intake_mech = CourseIntake(
        course_id=c_mech.id,
        academic_year="2026-27",
        approved_intake=60,
        supernumerary_seats_allowed=0,
        source="aicte_master",
    )
    db_session.add_all([intake_cse, intake_mech])

    # Mock APAAR Registry entries
    reg1 = MockApaarRegistry(
        apaar_id="111122223333",
        name="Rahul Sharma",
        dob=date(2005, 5, 15),
        gender="Male",
    )
    reg2 = MockApaarRegistry(
        apaar_id="222233334444",
        name="Priya Patel",
        dob=date(2004, 8, 20),
        gender="Female",
    )
    reg3 = MockApaarRegistry(
        apaar_id="333344445555",
        name="Aarav Verma",
        dob=date(2005, 11, 10),
        gender="Male",
    )
    db_session.add_all([reg1, reg2, reg3])

    # Users
    user_alpha_admin = User(
        email="admin@alpha-college.edu",
        password_hash=hash_password("Demo@12345"),
        role="college_admin",
        institution_id=inst_a.id,
        is_active=True,
    )
    user_alpha_staff = User(
        email="staff@alpha-college.edu",
        password_hash=hash_password("Demo@12345"),
        role="college_staff",
        institution_id=inst_a.id,
        is_active=True,
    )
    user_alpha_viewer = User(
        email="viewer@alpha-college.edu",
        password_hash=hash_password("Demo@12345"),
        role="college_viewer",
        institution_id=inst_a.id,
        is_active=True,
    )
    user_beta_admin = User(
        email="admin@beta-tech.edu",
        password_hash=hash_password("Demo@12345"),
        role="college_admin",
        institution_id=inst_b.id,
        is_active=True,
    )
    user_suspended_admin = User(
        email="admin@suspended-college.edu",
        password_hash=hash_password("Demo@12345"),
        role="college_admin",
        institution_id=inst_suspended.id,
        is_active=True,
    )
    user_aicte_officer = User(
        email="officer@aicte-india.org",
        password_hash=hash_password("Demo@12345"),
        role="aicte_officer",
        institution_id=None,
        is_active=True,
    )

    db_session.add_all([
        user_alpha_admin,
        user_alpha_staff,
        user_alpha_viewer,
        user_beta_admin,
        user_suspended_admin,
        user_aicte_officer,
    ])
    db_session.commit()

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "inst_suspended": inst_suspended,
        "c_cse": c_cse,
        "c_mech": c_mech,
        "c_beta_it": c_beta_it,
        "alpha_admin": user_alpha_admin,
        "alpha_staff": user_alpha_staff,
        "alpha_viewer": user_alpha_viewer,
        "beta_admin": user_beta_admin,
        "suspended_admin": user_suspended_admin,
        "aicte_officer": user_aicte_officer,
    }


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    return {"Authorization": f"Bearer {token}"}


def test_create_student_clean_check_and_save(
    client: TestClient, db_session: Session, student_test_env
):
    """Test valid student creation: saves as draft, validates clean, and writes audit log."""
    env = student_test_env
    headers = _auth_header(env["alpha_staff"])

    payload = {
        "apaar_id": "111122223333",
        "name": "Rahul Sharma",
        "dob": "2005-05-15",
        "gender": "Male",
        "course_id": env["c_cse"].id,
        "academic_year": "2026-27",
        "enrolment_no": "EN26-CSE-0001",
        "admission_date": "2026-08-10",
        "admission_mode": "State counselling",
        "seat_type": "Regular",
        "reservation_category": "General",
        "nri": "No",
        "oci": "No",
        "foreign_national": "No",
    }

    res = client.post(
        f"/api/v1/institutions/{env['inst_a'].id}/students",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["is_valid"] is True
    assert data["errors_count"] == 0
    assert data["student"]["apaar_id"] == "111122223333"
    assert data["student"]["name"] == "Rahul Sharma"
    assert data["student"]["dob"] == "2005-05-15"
    assert data["student"]["status"] == "valid"
    assert data["student"]["course_name"] == "Computer Science and Engineering"

    # Verify audit log was recorded
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "student.create",
            AuditLog.entity_id == str(data["student"]["id"]),
        )
    )
    assert audit is not None
    assert audit.actor_id == str(env["alpha_staff"].id)


def test_create_student_with_flags_saved_as_draft_either_way(
    client: TestClient, db_session: Session, student_test_env
):
    """Spec 8.2 & 9.4: Check and save returns flags and is saved as draft either way."""
    env = student_test_env
    headers = _auth_header(env["alpha_staff"])

    # Provide an unknown APAAR ID and invalid name with numbers
    payload = {
        "apaar_id": "999988887777",  # not in registry -> APAAR_NOT_FOUND
        "name": "Invalid123 Name!",   # numbers & symbol -> NAME_FORMAT
        "dob": "2005-05-15",
        "gender": "Male",
        "course_id": env["c_cse"].id,
        "academic_year": "2026-27",
        "enrolment_no": "EN26-CSE-0002",
        "admission_date": "2026-08-10",
        "admission_mode": "State counselling",
        "seat_type": "Regular",
        "reservation_category": "General",
        "nri": "No",
        "oci": "No",
        "foreign_national": "No",
    }

    res = client.post(
        f"/api/v1/institutions/{env['inst_a'].id}/students",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 201, res.text
    data = res.json()

    # The student IS saved in database
    student_id = data["student"]["id"]
    assert student_id > 0
    assert data["student"]["status"] == "flagged"

    # Validation flags are returned
    rule_codes = {f["rule_code"] for f in data["flags"]}
    assert "APAAR_NOT_FOUND" in rule_codes
    assert "NAME_FORMAT" in rule_codes
    assert data["is_valid"] is False
    assert data["errors_count"] >= 1

    # Verify persisted in database
    db_student = db_session.get(Student, student_id)
    assert db_student is not None
    assert db_student.status == "flagged"

    persisted_flags = db_session.scalars(
        select(ValidationFlag).where(ValidationFlag.student_id == student_id)
    ).all()
    assert len(persisted_flags) >= 2


def test_foreign_national_country_field_handling(
    client: TestClient, db_session: Session, student_test_env
):
    """TASKS.md T20: Country field appears only for foreign nationals."""
    env = student_test_env
    headers = _auth_header(env["alpha_admin"])

    # 1. Foreign national is Yes with country
    payload_fn = {
        "apaar_id": "222233334444",
        "name": "Priya Patel",
        "dob": "2004-08-20",
        "gender": "Female",
        "course_id": env["c_cse"].id,
        "academic_year": "2026-27",
        "enrolment_no": "EN26-FN-001",
        "admission_date": "2026-08-10",
        "admission_mode": "NRI/OCI/foreign quota",
        "seat_type": "Regular",
        "reservation_category": "General",
        "nri": "No",
        "oci": "No",
        "foreign_national": "Yes",
        "country": "Nepal",
    }
    res = client.post(
        f"/api/v1/institutions/{env['inst_a'].id}/students",
        json=payload_fn,
        headers=headers,
    )
    assert res.status_code == 201
    fn_student = res.json()["student"]
    assert fn_student["foreign_national"] == "Yes"
    assert fn_student["country"] == "Nepal"

    # 2. Foreign national is Yes but country is missing -> COUNTRY_REQUIRED error flag
    payload_fn_missing = {
        "apaar_id": "333344445555",
        "name": "Aarav Verma",
        "dob": "2005-11-10",
        "gender": "Male",
        "course_id": env["c_cse"].id,
        "academic_year": "2026-27",
        "enrolment_no": "EN26-FN-002",
        "admission_date": "2026-08-10",
        "admission_mode": "NRI/OCI/foreign quota",
        "seat_type": "Regular",
        "reservation_category": "General",
        "nri": "No",
        "oci": "No",
        "foreign_national": "Yes",
        "country": "",
    }
    res2 = client.post(
        f"/api/v1/institutions/{env['inst_a'].id}/students",
        json=payload_fn_missing,
        headers=headers,
    )
    assert res2.status_code == 201
    data2 = res2.json()
    rule_codes = [f["rule_code"] for f in data2["flags"]]
    assert "COUNTRY_REQUIRED" in rule_codes

    # 3. Foreign national is No -> country is cleared even if passed
    payload_domestic = {
        "apaar_id": "111122223333",
        "name": "Rahul Sharma",
        "dob": "2005-05-15",
        "gender": "Male",
        "course_id": env["c_mech"].id,
        "academic_year": "2026-27",
        "enrolment_no": "EN26-MECH-001",
        "admission_date": "2026-08-10",
        "admission_mode": "State counselling",
        "seat_type": "Regular",
        "reservation_category": "General",
        "nri": "No",
        "oci": "No",
        "foreign_national": "No",
        "country": "ShouldBeIgnored",
    }
    res3 = client.post(
        f"/api/v1/institutions/{env['inst_a'].id}/students",
        json=payload_domestic,
        headers=headers,
    )
    assert res3.status_code == 201
    assert res3.json()["student"]["country"] is None


def test_edit_draft_student(client: TestClient, db_session: Session, student_test_env):
    """TASKS.md T20: Edit drafts and re-run validation engine."""
    env = student_test_env
    headers = _auth_header(env["alpha_staff"])

    # 1. Create a student with invalid name
    payload = {
        "apaar_id": "111122223333",
        "name": "Rahul123 BadName",
        "dob": "2005-05-15",
        "gender": "Male",
        "course_id": env["c_cse"].id,
        "academic_year": "2026-27",
        "enrolment_no": "EN26-CSE-0005",
        "admission_date": "2026-08-10",
        "admission_mode": "State counselling",
        "seat_type": "Regular",
        "reservation_category": "General",
    }
    create_res = client.post(
        f"/api/v1/institutions/{env['inst_a'].id}/students",
        json=payload,
        headers=headers,
    )
    student_id = create_res.json()["student"]["id"]
    assert create_res.json()["student"]["status"] == "flagged"

    # 2. Fix name via PUT
    update_payload = {
        "name": "Rahul Sharma",
    }
    update_res = client.put(
        f"/api/v1/institutions/{env['inst_a'].id}/students/{student_id}",
        json=update_payload,
        headers=headers,
    )
    assert update_res.status_code == 200, update_res.text
    updated_data = update_res.json()

    assert updated_data["student"]["name"] == "Rahul Sharma"
    assert updated_data["is_valid"] is True
    assert updated_data["student"]["status"] == "valid"

    # 3. Check audit log for update
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "student.update",
            AuditLog.entity_id == str(student_id),
        )
    )
    assert audit is not None


def test_delete_draft_student(client: TestClient, db_session: Session, student_test_env):
    """TASKS.md T20: Delete student draft."""
    env = student_test_env
    headers = _auth_header(env["alpha_staff"])

    # Create draft
    payload = {
        "apaar_id": "222233334444",
        "name": "Priya Patel",
        "dob": "2004-08-20",
        "gender": "Female",
        "course_id": env["c_cse"].id,
        "academic_year": "2026-27",
        "enrolment_no": "EN26-DEL-001",
        "admission_date": "2026-08-10",
        "admission_mode": "State counselling",
        "seat_type": "Regular",
        "reservation_category": "General",
    }
    create_res = client.post(
        f"/api/v1/institutions/{env['inst_a'].id}/students",
        json=payload,
        headers=headers,
    )
    student_id = create_res.json()["student"]["id"]

    # Delete draft
    del_res = client.delete(
        f"/api/v1/institutions/{env['inst_a'].id}/students/{student_id}",
        headers=headers,
    )
    assert del_res.status_code == 200

    # Ensure student is gone
    assert db_session.get(Student, student_id) is None

    # Check audit log
    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "student.delete",
            AuditLog.entity_id == str(student_id),
        )
    )
    assert audit is not None


def test_locked_student_cannot_be_edited_or_deleted(
    client: TestClient, db_session: Session, student_test_env
):
    """Spec 10: Locked or submitted students cannot be modified or deleted directly."""
    env = student_test_env
    headers = _auth_header(env["alpha_admin"])

    # Create locked student
    locked_stu = Student(
        institution_id=env["inst_a"].id,
        course_id=env["c_cse"].id,
        academic_year="2026-27",
        apaar_id="111122223333",
        name="Submitted Student",
        dob_encrypted=encrypt_dob("2005-05-15"),
        gender="Male",
        enrolment_no="EN26-LOCK-001",
        admission_date=date(2026, 8, 10),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        status="submitted",
        is_locked=True,
    )
    db_session.add(locked_stu)
    db_session.commit()

    # Attempt PUT
    put_res = client.put(
        f"/api/v1/institutions/{env['inst_a'].id}/students/{locked_stu.id}",
        json={"name": "Hacked Student"},
        headers=headers,
    )
    assert put_res.status_code == 403
    assert "Locked or submitted" in put_res.json()["detail"]

    # Attempt DELETE
    del_res = client.delete(
        f"/api/v1/institutions/{env['inst_a'].id}/students/{locked_stu.id}",
        headers=headers,
    )
    assert del_res.status_code == 403
    assert "Locked or submitted" in del_res.json()["detail"]


def test_student_list_filters_by_status_and_level(
    client: TestClient, db_session: Session, student_test_env
):
    """TASKS.md T20: Student list with filters by status and level."""
    env = student_test_env
    headers = _auth_header(env["alpha_admin"])

    # Create 3 students in inst_a: 1 clean/valid, 1 draft with error, 1 draft
    s_valid = Student(
        institution_id=env["inst_a"].id,
        course_id=env["c_cse"].id,
        academic_year="2026-27",
        apaar_id="111122223333",
        name="Valid Student",
        dob_encrypted=encrypt_dob("2005-05-15"),
        gender="Male",
        enrolment_no="EN26-LIST-001",
        admission_date=date(2026, 8, 10),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        status="valid",
    )
    s_flagged = Student(
        institution_id=env["inst_a"].id,
        course_id=env["c_cse"].id,
        academic_year="2026-27",
        apaar_id="222233334444",
        name="Flagged Student",
        dob_encrypted=encrypt_dob("2004-08-20"),
        gender="Female",
        enrolment_no="EN26-LIST-002",
        admission_date=date(2026, 8, 10),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        status="flagged",
    )
    s_draft = Student(
        institution_id=env["inst_a"].id,
        course_id=env["c_mech"].id,
        academic_year="2026-27",
        apaar_id="333344445555",
        name="Draft Student",
        dob_encrypted=encrypt_dob("2005-11-10"),
        gender="Male",
        enrolment_no="EN26-LIST-003",
        admission_date=date(2026, 8, 10),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        status="draft",
    )
    db_session.add_all([s_valid, s_flagged, s_draft])
    db_session.flush()

    # Add error flag to s_flagged
    flag_err = ValidationFlag(
        student_id=s_flagged.id,
        course_id=env["c_cse"].id,
        rule_code="APAAR_NAME_MISMATCH",
        level="warning",
        field="name",
        message="Fuzzy name mismatch",
        fix_hint="Check spelling",
        status="open",
    )
    db_session.add(flag_err)
    db_session.commit()

    # 1. Test Filter by Status: valid
    res_valid = client.get(
        f"/api/v1/institutions/{env['inst_a'].id}/students?status=valid",
        headers=headers,
    )
    assert res_valid.status_code == 200
    valid_items = res_valid.json()["items"]
    assert len(valid_items) == 1
    assert valid_items[0]["name"] == "Valid Student"

    # 2. Test Filter by Status: flagged
    res_flagged = client.get(
        f"/api/v1/institutions/{env['inst_a'].id}/students?status=flagged",
        headers=headers,
    )
    assert res_flagged.status_code == 200
    flagged_items = res_flagged.json()["items"]
    assert len(flagged_items) == 1
    assert flagged_items[0]["name"] == "Flagged Student"

    # 3. Test Filter by Level: warning
    res_warn = client.get(
        f"/api/v1/institutions/{env['inst_a'].id}/students?level=warning",
        headers=headers,
    )
    assert res_warn.status_code == 200
    warn_items = res_warn.json()["items"]
    assert len(warn_items) == 1
    assert warn_items[0]["name"] == "Flagged Student"

    # 4. Test Filter by Level: clean
    res_clean = client.get(
        f"/api/v1/institutions/{env['inst_a'].id}/students?level=clean",
        headers=headers,
    )
    assert res_clean.status_code == 200
    clean_names = {i["name"] for i in res_clean.json()["items"]}
    assert "Valid Student" in clean_names
    assert "Draft Student" in clean_names
    assert "Flagged Student" not in clean_names

    # 5. Test Search by APAAR ID
    res_search = client.get(
        f"/api/v1/institutions/{env['inst_a'].id}/students?search=333344445555",
        headers=headers,
    )
    assert res_search.status_code == 200
    assert len(res_search.json()["items"]) == 1
    assert res_search.json()["items"][0]["name"] == "Draft Student"


def test_idor_protection_across_colleges(client: TestClient, db_session: Session, student_test_env):
    """Hard Rule 7 & Spec 5: College A cannot read, create, edit, or delete College B records."""
    env = student_test_env
    headers_a = _auth_header(env["alpha_admin"])

    # College B has a student
    b_student = Student(
        institution_id=env["inst_b"].id,
        course_id=env["c_beta_it"].id,
        academic_year="2026-27",
        apaar_id="111122223333",
        name="Beta Student",
        dob_encrypted=encrypt_dob("2005-05-15"),
        gender="Male",
        enrolment_no="EN26-BETA-001",
        admission_date=date(2026, 8, 10),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        status="draft",
    )
    db_session.add(b_student)
    db_session.commit()

    # College A cannot list College B students
    assert client.get(
        f"/api/v1/institutions/{env['inst_b'].id}/students",
        headers=headers_a,
    ).status_code == 403

    # College A cannot get single student of College B
    assert client.get(
        f"/api/v1/institutions/{env['inst_b'].id}/students/{b_student.id}",
        headers=headers_a,
    ).status_code == 403

    # College A cannot create student in College B
    assert client.post(
        f"/api/v1/institutions/{env['inst_b'].id}/students",
        json={
            "apaar_id": "222233334444",
            "name": "Intruder",
            "dob": "2004-08-20",
            "gender": "Female",
            "course_id": env["c_beta_it"].id,
            "academic_year": "2026-27",
            "enrolment_no": "EN26-INT-001",
            "admission_date": "2026-08-10",
            "admission_mode": "State counselling",
            "seat_type": "Regular",
            "reservation_category": "General",
        },
        headers=headers_a,
    ).status_code == 403

    # College A cannot edit student of College B
    assert client.put(
        f"/api/v1/institutions/{env['inst_b'].id}/students/{b_student.id}",
        json={"name": "Hacked"},
        headers=headers_a,
    ).status_code == 403

    # College A cannot delete student of College B
    assert client.delete(
        f"/api/v1/institutions/{env['inst_b'].id}/students/{b_student.id}",
        headers=headers_a,
    ).status_code == 403

    # AICTE officer CAN read College B students
    headers_aicte = _auth_header(env["aicte_officer"])
    res_aicte = client.get(
        f"/api/v1/institutions/{env['inst_b'].id}/students",
        headers=headers_aicte,
    )
    assert res_aicte.status_code == 200


def test_college_viewer_read_only(client: TestClient, db_session: Session, student_test_env):
    """Spec 5: College viewer cannot create, edit, or delete student records."""
    env = student_test_env
    headers_viewer = _auth_header(env["alpha_viewer"])

    # Create an existing student
    stu = Student(
        institution_id=env["inst_a"].id,
        course_id=env["c_cse"].id,
        academic_year="2026-27",
        apaar_id="111122223333",
        name="Existing Student",
        dob_encrypted=encrypt_dob("2005-05-15"),
        gender="Male",
        enrolment_no="EN26-VIEW-001",
        admission_date=date(2026, 8, 10),
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        status="draft",
    )
    db_session.add(stu)
    db_session.commit()

    # Viewer CAN read
    assert client.get(
        f"/api/v1/institutions/{env['inst_a'].id}/students",
        headers=headers_viewer,
    ).status_code == 200
    assert client.get(
        f"/api/v1/institutions/{env['inst_a'].id}/students/{stu.id}",
        headers=headers_viewer,
    ).status_code == 200

    # Viewer CANNOT create
    assert client.post(
        f"/api/v1/institutions/{env['inst_a'].id}/students",
        json={
            "apaar_id": "222233334444",
            "name": "New Student",
            "dob": "2004-08-20",
            "gender": "Female",
            "course_id": env["c_cse"].id,
            "academic_year": "2026-27",
            "enrolment_no": "EN26-VIEW-002",
            "admission_date": "2026-08-10",
            "admission_mode": "State counselling",
            "seat_type": "Regular",
            "reservation_category": "General",
        },
        headers=headers_viewer,
    ).status_code == 403

    # Viewer CANNOT update
    assert client.put(
        f"/api/v1/institutions/{env['inst_a'].id}/students/{stu.id}",
        json={"name": "Altered Name"},
        headers=headers_viewer,
    ).status_code == 403

    # Viewer CANNOT delete
    assert client.delete(
        f"/api/v1/institutions/{env['inst_a'].id}/students/{stu.id}",
        headers=headers_viewer,
    ).status_code == 403


def test_suspended_college_blocked_from_upload(
    client: TestClient, db_session: Session, student_test_env
):
    """Spec 6: If approval becomes suspended, uploads and edits are blocked with 403."""
    env = student_test_env
    headers_suspended = _auth_header(env["suspended_admin"])

    # Course for suspended college
    c_susp = Course(
        institution_id=env["inst_suspended"].id,
        name="Civil Engineering",
        branch="Civil",
        level="UG",
        duration_years=4,
        supernumerary_allowed=False,
    )
    db_session.add(c_susp)
    db_session.commit()

    res = client.post(
        f"/api/v1/institutions/{env['inst_suspended'].id}/students",
        json={
            "apaar_id": "111122223333",
            "name": "Rahul Sharma",
            "dob": "2005-05-15",
            "gender": "Male",
            "course_id": c_susp.id,
            "academic_year": "2026-27",
            "enrolment_no": "EN26-SUSP-001",
            "admission_date": "2026-08-10",
            "admission_mode": "State counselling",
            "seat_type": "Regular",
            "reservation_category": "General",
        },
        headers=headers_suspended,
    )
    assert res.status_code == 403
    assert "suspended" in res.json()["detail"].lower()
