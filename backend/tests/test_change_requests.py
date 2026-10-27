"""Tests for post-lock student change requests (T26)."""

import io

import pytest
from sqlalchemy import select

from app.auth.security import decrypt_dob
from app.models import (
    AuditLog,
    ChangeRequest,
    Course,
    Institution,
    Notification,
    Student,
    Submission,
    User,
    ValidationFlag,
)
from app.validation.codes import DUP_ACTIVE_OTHER_COLLEGE


@pytest.fixture
def locked_setup(db_session):
    """Seed test institutions, users, courses, and a locked student."""
    # Institution 1
    inst1 = Institution(
        aicte_id="1-CR-1001",
        name="Institute of Technology One",
        state="Maharashtra",
        district="Pune",
        address="100 Tech Park",
        official_email="contact@tech1.edu.in",
        official_phone="9876543210",
        head_name="Dr. Director One",
        affiliating_university="Savitribai Phule Pune University",
        approval_status="active",
        account_status="active",
    )
    # Institution 2
    inst2 = Institution(
        aicte_id="1-CR-1002",
        name="Institute of Technology Two",
        state="Karnataka",
        district="Bengaluru",
        address="200 Tech Park",
        official_email="contact@tech2.edu.in",
        official_phone="9876543211",
        head_name="Dr. Director Two",
        affiliating_university="Visvesvaraya Technological University",
        approval_status="active",
        account_status="active",
    )
    db_session.add_all([inst1, inst2])
    db_session.flush()

    # Users
    user_admin1 = User(
        email="admin@tech1.edu.in",
        password_hash="mock_hash",
        role="college_admin",
        institution_id=inst1.id,
        is_active=True,
    )
    user_staff1 = User(
        email="staff@tech1.edu.in",
        password_hash="mock_hash",
        role="college_staff",
        institution_id=inst1.id,
        is_active=True,
    )
    user_viewer1 = User(
        email="viewer@tech1.edu.in",
        password_hash="mock_hash",
        role="college_viewer",
        institution_id=inst1.id,
        is_active=True,
    )
    user_admin2 = User(
        email="admin@tech2.edu.in",
        password_hash="mock_hash",
        role="college_admin",
        institution_id=inst2.id,
        is_active=True,
    )
    user_officer = User(
        email="officer@aicte-india.org",
        password_hash="mock_hash",
        role="aicte_officer",
        institution_id=None,
        is_active=True,
    )
    db_session.add_all([user_admin1, user_staff1, user_viewer1, user_admin2, user_officer])
    db_session.flush()

    # Courses
    course1a = Course(
        institution_id=inst1.id,
        name="Computer Engineering",
        level="UG",
        branch="Computer Science",
        duration_years=4,
    )
    course1b = Course(
        institution_id=inst1.id,
        name="Information Technology",
        level="UG",
        branch="Information Technology",
        duration_years=4,
    )
    course2 = Course(
        institution_id=inst2.id,
        name="Computer Science",
        level="UG",
        branch="Computer Science",
        duration_years=4,
    )
    db_session.add_all([course1a, course1b, course2])
    db_session.flush()

    # Submission & locked student for inst 1
    sub1 = Submission(
        institution_id=inst1.id,
        academic_year="2026-27",
        status="submitted",
        submitted_by=user_admin1.id,
        receipt_no="REC-2026-CR-001",
    )
    db_session.add(sub1)
    db_session.flush()

    from app.auth.security import encrypt_dob

    locked_student = Student(
        institution_id=inst1.id,
        course_id=course1a.id,
        academic_year="2026-27",
        apaar_id="998877665544",
        name="Aakash Sharma",
        dob_encrypted=encrypt_dob("2004-05-15"),
        gender="Male",
        enrolment_no="EN-2026-001",
        admission_date="2026-06-01",
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        nri="No",
        oci="No",
        foreign_national="No",
        status="submitted",
        is_locked=True,
        submission_id=sub1.id,
        source="form",
    )

    unlocked_student = Student(
        institution_id=inst1.id,
        course_id=course1a.id,
        academic_year="2026-27",
        apaar_id="998877665545",
        name="Draft Student",
        dob_encrypted=encrypt_dob("2004-08-20"),
        gender="Female",
        enrolment_no="EN-2026-002",
        admission_date="2026-06-02",
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="OBC",
        nri="No",
        oci="No",
        foreign_national="No",
        status="draft",
        is_locked=False,
        submission_id=None,
        source="form",
    )

    db_session.add_all([locked_student, unlocked_student])
    db_session.commit()

    return {
        "inst1": inst1,
        "inst2": inst2,
        "admin1": user_admin1,
        "staff1": user_staff1,
        "viewer1": user_viewer1,
        "admin2": user_admin2,
        "officer": user_officer,
        "course1a": course1a,
        "course1b": course1b,
        "course2": course2,
        "locked_student": locked_student,
        "unlocked_student": unlocked_student,
        "submission": sub1,
    }


def _auth_headers(user: User) -> dict[str, str]:
    from app.auth.security import create_access_token

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    return {"Authorization": f"Bearer {token}"}


def test_create_change_request_unlocked_student_rejected(client, locked_setup):
    """Ensure change requests cannot be created for unlocked draft records."""
    headers = _auth_headers(locked_setup["admin1"])
    inst1 = locked_setup["inst1"]
    unlocked = locked_setup["unlocked_student"]

    response = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers,
        json={
            "student_id": unlocked.id,
            "field": "name",
            "new_value": "New Name",
            "reason": "Name correction requested",
        },
    )
    assert response.status_code == 400
    assert "not locked" in response.json()["detail"].lower()


def test_create_change_request_success_with_evidence(client, locked_setup, db_session):
    """College files a change request with reason and evidence file for a locked student."""
    headers = _auth_headers(locked_setup["staff1"])
    inst1 = locked_setup["inst1"]
    locked = locked_setup["locked_student"]

    fake_pdf = io.BytesIO(b"%PDF-1.4 Mock Legal Name Affidavit Content")

    response = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers,
        data={
            "student_id": str(locked.id),
            "field": "name",
            "new_value": "Aakash K. Sharma",
            "reason": "Court affidavit name update per Gazette notification",
        },
        files={
            "document": ("gazette_affidavit.pdf", fake_pdf, "application/pdf"),
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["field"] == "name"
    assert data["old_value"] == "Aakash Sharma"
    assert data["new_value"] == "Aakash K. Sharma"
    assert data["status"] == "pending"
    assert data["document_ref"] is not None
    assert "gazette_affidavit.pdf" in data["document_ref"]
    assert data["student"]["apaar_id"] == "998877665544"

    # Verify audit log was recorded
    audit_row = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity == "ChangeRequest",
            AuditLog.action == "change_request.created",
        )
    ).first()
    assert audit_row is not None
    assert str(audit_row.actor_id) == str(locked_setup["staff1"].id)

    # Verify notification was sent
    notif = db_session.scalars(
        select(Notification).where(
            Notification.institution_id == inst1.id,
            Notification.type == "CHANGE_REQUEST_SUBMITTED",
        )
    ).first()
    assert notif is not None


def test_create_change_request_invalid_field_and_syntax(client, locked_setup):
    """Verify validation on disallowed fields, invalid dates, and invalid enums."""
    headers = _auth_headers(locked_setup["admin1"])
    inst1 = locked_setup["inst1"]
    locked = locked_setup["locked_student"]

    # Disallowed field (apaar_id)
    r = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers,
        json={
            "student_id": locked.id,
            "field": "apaar_id",
            "new_value": "112233445566",
            "reason": "Wrong APAAR entered",
        },
    )
    assert r.status_code == 400
    assert "cannot be modified" in r.json()["detail"].lower()

    # Invalid status
    r = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers,
        json={
            "student_id": locked.id,
            "field": "status",
            "new_value": "terminated",
            "reason": "Student terminated",
        },
    )
    assert r.status_code == 400
    assert "invalid student status" in r.json()["detail"].lower()

    # Future DOB
    r = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers,
        json={
            "student_id": locked.id,
            "field": "dob",
            "new_value": "2099-01-01",
            "reason": "DOB correction",
        },
    )
    assert r.status_code == 400
    assert "future" in r.json()["detail"].lower()

    # Course from another institution
    r = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers,
        json={
            "student_id": locked.id,
            "field": "course_id",
            "new_value": str(locked_setup["course2"].id),
            "reason": "Transfer course",
        },
    )
    assert r.status_code == 400
    assert "does not belong" in r.json()["detail"].lower()


def test_duplicate_pending_change_request_conflict(client, locked_setup):
    """Verify cannot create two pending change requests for the same student and field."""
    headers = _auth_headers(locked_setup["admin1"])
    inst1 = locked_setup["inst1"]
    locked = locked_setup["locked_student"]

    # First request
    r1 = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers,
        json={
            "student_id": locked.id,
            "field": "gender",
            "new_value": "Other",
            "reason": "Gender update per identity document",
        },
    )
    assert r1.status_code == 201

    # Second duplicate request
    r2 = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers,
        json={
            "student_id": locked.id,
            "field": "gender",
            "new_value": "Female",
            "reason": "Different gender change attempt",
        },
    )
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"].lower()


def test_college_idor_protection(client, locked_setup):
    """Verify College A cannot create or inspect change requests of College B."""
    headers_col2 = _auth_headers(locked_setup["admin2"])
    inst1 = locked_setup["inst1"]
    locked1 = locked_setup["locked_student"]

    # College 2 tries to file change request for College 1's student
    r = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers_col2,
        json={
            "student_id": locked1.id,
            "field": "name",
            "new_value": "Hacked Name",
            "reason": "Unauthorized attempt",
        },
    )
    assert r.status_code == 403


def test_aicte_approve_change_request_and_history(client, locked_setup, db_session):
    """AICTE approves a change request; verifies student is updated,
    history preserved, and DOB encrypted."""
    headers_staff = _auth_headers(locked_setup["staff1"])
    headers_officer = _auth_headers(locked_setup["officer"])
    inst1 = locked_setup["inst1"]
    locked = locked_setup["locked_student"]

    # College files DOB correction request
    r_create = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers_staff,
        json={
            "student_id": locked.id,
            "field": "dob",
            "new_value": "2004-06-25",
            "reason": "Birth certificate verification corrected date",
        },
    )
    assert r_create.status_code == 201
    cr_id = r_create.json()["id"]
    assert r_create.json()["old_value"] == "2004-05-15"

    # AICTE lists queue and verifies item is present
    r_queue = client.get(
        "/api/v1/change-requests",
        headers=headers_officer,
        params={"status": "pending"},
    )
    assert r_queue.status_code == 200
    items = r_queue.json()["items"]
    assert any(item["id"] == cr_id for item in items)

    # AICTE officer approves request
    r_decide = client.post(
        f"/api/v1/change-requests/{cr_id}/decision",
        headers=headers_officer,
        json={
            "decision": "approve",
            "decision_note": "Verified with original birth certificate copy. Approved.",
        },
    )
    assert r_decide.status_code == 200
    res_data = r_decide.json()
    assert res_data["status"] == "approved"
    assert res_data["decided_by"] == locked_setup["officer"].id
    assert res_data["decided_at"] is not None
    assert "Verified with original" in res_data["decision_note"]

    # Verify student record was updated and Fernet encrypted
    db_session.expire_all()
    updated_student = db_session.get(Student, locked.id)
    decrypted_dob = decrypt_dob(updated_student.dob_encrypted)
    assert str(decrypted_dob) == "2004-06-25"

    # Verify history is preserved in change_requests table
    cr_db = db_session.get(ChangeRequest, cr_id)
    assert cr_db.old_value == "2004-05-15"
    assert cr_db.new_value == "2004-06-25"
    assert cr_db.status == "approved"

    # Verify audit log recorded before and after states
    audit_approval = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity == "ChangeRequest",
            AuditLog.action == "change_request.approved",
            AuditLog.entity_id == str(cr_id),
        )
    ).first()
    assert audit_approval is not None
    assert audit_approval.before_json["value"] == "2004-05-15"
    assert audit_approval.after_json["value"] == "2004-06-25"


def test_withdrawn_or_transferred_status_resolves_duplicates(client, locked_setup, db_session):
    """Approving a status change to 'withdrawn' or 'transferred' auto-resolves
    cross-college duplicate flags."""
    headers_admin1 = _auth_headers(locked_setup["admin1"])
    headers_officer = _auth_headers(locked_setup["officer"])
    inst1 = locked_setup["inst1"]
    inst2 = locked_setup["inst2"]
    locked1 = locked_setup["locked_student"]

    from app.auth.security import encrypt_dob

    # Add a duplicate student at College 2
    student2 = Student(
        institution_id=inst2.id,
        course_id=locked_setup["course2"].id,
        academic_year="2026-27",
        apaar_id=locked1.apaar_id,  # SAME APAAR ID
        name=locked1.name,
        dob_encrypted=encrypt_dob("2004-05-15"),
        gender="Male",
        enrolment_no="EN-2026-999",
        admission_date="2026-06-05",
        admission_mode="State counselling",
        seat_type="Regular",
        reservation_category="General",
        nri="No",
        oci="No",
        foreign_national="No",
        status="submitted",
        is_locked=True,
        source="form",
    )
    db_session.add(student2)
    db_session.flush()

    # Plant active duplicate flags on both students
    flag1 = ValidationFlag(
        student_id=locked1.id,
        rule_code=DUP_ACTIVE_OTHER_COLLEGE,
        level="warning",
        field="apaar_id",
        message="Active at College 2",
        status="open",
        audience="both",
    )
    flag2 = ValidationFlag(
        student_id=student2.id,
        rule_code=DUP_ACTIVE_OTHER_COLLEGE,
        level="warning",
        field="apaar_id",
        message="Active at College 1",
        status="open",
        audience="both",
    )
    db_session.add_all([flag1, flag2])
    db_session.commit()

    # College 1 files change request to mark student as 'withdrawn'
    r_create = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers_admin1,
        json={
            "student_id": locked1.id,
            "field": "status",
            "new_value": "withdrawn",
            "reason": "Student formally withdrew admission to pursue other career",
        },
    )
    assert r_create.status_code == 201
    cr_id = r_create.json()["id"]

    # AICTE officer approves withdrawal
    r_decide = client.post(
        f"/api/v1/change-requests/{cr_id}/decision",
        headers=headers_officer,
        json={
            "decision": "approve",
            "decision_note": "Withdrawal letter and fee refund receipt verified.",
        },
    )
    assert r_decide.status_code == 200

    # Verify student1 status is now withdrawn
    db_session.expire_all()
    s1 = db_session.get(Student, locked1.id)
    assert s1.status == "withdrawn"

    # Verify both duplicate flags are now marked resolved
    db_session.refresh(flag1)
    db_session.refresh(flag2)
    assert flag1.status == "resolved"
    assert flag2.status == "resolved"

    # Verify resolution notifications sent to both institutions
    notif_inst1 = db_session.scalars(
        select(Notification).where(
            Notification.institution_id == inst1.id,
            Notification.type == "DUPLICATE_ENROLMENT_RESOLVED",
        )
    ).first()
    assert notif_inst1 is not None

    notif_inst2 = db_session.scalars(
        select(Notification).where(
            Notification.institution_id == inst2.id,
            Notification.type == "DUPLICATE_ENROLMENT_RESOLVED",
        )
    ).first()
    assert notif_inst2 is not None


def test_aicte_reject_change_request(client, locked_setup, db_session):
    """AICTE rejects a change request; verifies student record is unchanged and reason recorded."""
    headers_staff = _auth_headers(locked_setup["staff1"])
    headers_officer = _auth_headers(locked_setup["officer"])
    inst1 = locked_setup["inst1"]
    locked = locked_setup["locked_student"]
    original_enrol = locked.enrolment_no

    r_create = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers_staff,
        json={
            "student_id": locked.id,
            "field": "enrolment_no",
            "new_value": "EN-NEW-9999",
            "reason": "Typo in enrolment number",
        },
    )
    assert r_create.status_code == 201
    cr_id = r_create.json()["id"]

    r_decide = client.post(
        f"/api/v1/change-requests/{cr_id}/decision",
        headers=headers_officer,
        json={
            "decision": "reject",
            "decision_note": "Insufficient proof of enrolment number discrepancy.",
        },
    )
    assert r_decide.status_code == 200
    assert r_decide.json()["status"] == "rejected"

    # Verify student was NOT modified
    db_session.expire_all()
    s = db_session.get(Student, locked.id)
    assert s.enrolment_no == original_enrol

    # Verify rejection audit log
    audit_rej = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity == "ChangeRequest",
            AuditLog.action == "change_request.rejected",
            AuditLog.entity_id == str(cr_id),
        )
    ).first()
    assert audit_rej is not None


def test_evidence_download_and_permissions(client, locked_setup):
    """Verify evidence document can be downloaded by college and AICTE,
    but blocked for College B."""
    headers_admin1 = _auth_headers(locked_setup["admin1"])
    headers_admin2 = _auth_headers(locked_setup["admin2"])
    headers_officer = _auth_headers(locked_setup["officer"])
    inst1 = locked_setup["inst1"]
    locked = locked_setup["locked_student"]

    pdf_content = b"%PDF-1.4 Transfer Certificate Proof"
    r_create = client.post(
        f"/api/v1/institutions/{inst1.id}/change-requests",
        headers=headers_admin1,
        data={
            "student_id": str(locked.id),
            "field": "status",
            "new_value": "transferred",
            "reason": "Transferred to another university",
        },
        files={
            "document": ("transfer_certificate.pdf", io.BytesIO(pdf_content), "application/pdf"),
        },
    )
    assert r_create.status_code == 201
    cr_id = r_create.json()["id"]

    # College 1 downloads evidence
    r_col1 = client.get(
        f"/api/v1/institutions/{inst1.id}/change-requests/{cr_id}/evidence",
        headers=headers_admin1,
    )
    assert r_col1.status_code == 200
    assert r_col1.content == pdf_content

    # AICTE downloads evidence
    r_aicte = client.get(
        f"/api/v1/change-requests/{cr_id}/evidence",
        headers=headers_officer,
    )
    assert r_aicte.status_code == 200
    assert r_aicte.content == pdf_content

    # College 2 tries to download College 1's evidence -> 403 Forbidden
    r_col2 = client.get(
        f"/api/v1/institutions/{inst1.id}/change-requests/{cr_id}/evidence",
        headers=headers_admin2,
    )
    assert r_col2.status_code == 403
