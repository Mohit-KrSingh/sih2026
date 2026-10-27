"""Tests for Staff Management, Contact Changes, Role Limits, and Password Reset.

SPEC.md sections 5, 6, 11 & TASKS.md T09:
- College admin creates staff with roles.
- Role limits: staff cannot submit or manage staff (403 Forbidden).
- Contact or head change requests go to AICTE; college direct edit gets 403.
- Password reset only via OTP to on-file contacts.
- Hash-chained audit logging and IDOR prevention.
"""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import Role
from app.auth.security import create_access_token, hash_password
from app.models import AuditLog, DevOutbox, Institution, User


def _create_institution(
    db: Session,
    aicte_id: str,
    name: str,
    official_email: str = "principal@college-test.edu.in",
    official_phone: str = "+919876543210",
    head_name: str = "Dr. Test Principal",
    account_status: str = "active",
) -> Institution:
    """Helper to create test institution."""
    inst = Institution(
        aicte_id=aicte_id,
        name=name,
        state="Maharashtra",
        district="Pune",
        address="100 Knowledge Park, Pune",
        official_email=official_email,
        official_phone=official_phone,
        head_name=head_name,
        affiliating_university="Savitribai Phule Pune University",
        approval_status="active",
        account_status=account_status,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def _create_user(
    db: Session,
    email: str,
    role: str,
    institution_id: int | None = None,
    password: str = "Password@123",
    is_active: bool = True,
) -> tuple[User, str]:
    """Helper to create a user and generate bearer access token."""
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        role=role,
        institution_id=institution_id,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=institution_id,
    )
    return user, token


# =========================================================================
# 1. Staff Management CRUD Tests
# =========================================================================


def test_college_admin_can_create_and_manage_staff(client: TestClient, db_session: Session):
    """College admin creates staff with limited roles, lists, updates, and deactivates."""
    inst = _create_institution(db_session, "1-STAFF-01", "Institute of Technology")
    admin_user, admin_token = _create_user(
        db_session, "admin@tech.edu.in", Role.COLLEGE_ADMIN.value, inst.id
    )

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create a college_staff user
    create_payload = {
        "email": "admission_officer@tech.edu.in",
        "password": "SecurePassword@123",
        "role": Role.COLLEGE_STAFF.value,
    }
    resp = client.post(
        f"/api/v1/institutions/{inst.id}/staff",
        json=create_payload,
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "admission_officer@tech.edu.in"
    assert data["role"] == Role.COLLEGE_STAFF.value
    assert data["institution_id"] == inst.id
    assert data["is_active"] is True
    staff_id = data["id"]

    # Verify audit log recorded for staff.create
    audit_entry = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "staff.create",
            AuditLog.entity_id == str(staff_id),
        )
    )
    assert audit_entry is not None
    assert audit_entry.actor_id == str(admin_user.id)

    # 2. Create a college_viewer user
    create_viewer_payload = {
        "email": "viewer@tech.edu.in",
        "password": "ViewerPassword@123",
        "role": Role.COLLEGE_VIEWER.value,
    }
    resp_viewer = client.post(
        f"/api/v1/institutions/{inst.id}/staff",
        json=create_viewer_payload,
        headers=headers,
    )
    assert resp_viewer.status_code == 201
    assert resp_viewer.json()["role"] == Role.COLLEGE_VIEWER.value

    # 3. List staff accounts for institution
    resp_list = client.get(
        f"/api/v1/institutions/{inst.id}/staff",
        headers=headers,
    )
    assert resp_list.status_code == 200
    list_data = resp_list.json()
    assert list_data["total"] >= 3  # Admin + Staff + Viewer
    emails = [item["email"] for item in list_data["items"]]
    assert "admission_officer@tech.edu.in" in emails
    assert "viewer@tech.edu.in" in emails

    # 4. Get single staff detail
    resp_get = client.get(
        f"/api/v1/institutions/{inst.id}/staff/{staff_id}",
        headers=headers,
    )
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == staff_id

    # 5. Update staff role (e.g. promote to college_viewer or update active status)
    update_payload = {
        "role": Role.COLLEGE_VIEWER.value,
        "is_active": True,
    }
    resp_update = client.patch(
        f"/api/v1/institutions/{inst.id}/staff/{staff_id}",
        json=update_payload,
        headers=headers,
    )
    assert resp_update.status_code == 200
    assert resp_update.json()["role"] == Role.COLLEGE_VIEWER.value

    # 6. Deactivate staff account
    resp_delete = client.delete(
        f"/api/v1/institutions/{inst.id}/staff/{staff_id}",
        headers=headers,
    )
    assert resp_delete.status_code == 200
    assert resp_delete.json()["status"] == "success"

    # Verify user is now deactivated in database
    deactivated_staff = db_session.get(User, staff_id)
    assert deactivated_staff.is_active is False


def test_staff_create_duplicate_email_rejected(client: TestClient, db_session: Session):
    """Attempting to create staff with already taken email returns 409 Conflict."""
    inst = _create_institution(db_session, "1-STAFF-02", "College Duplicate Test")
    _, admin_token = _create_user(
        db_session, "admin2@tech.edu.in", Role.COLLEGE_ADMIN.value, inst.id
    )

    headers = {"Authorization": f"Bearer {admin_token}"}

    payload = {
        "email": "existing_user@tech.edu.in",
        "password": "Password@123",
        "role": Role.COLLEGE_STAFF.value,
    }

    # First creation succeeds
    resp1 = client.post(
        f"/api/v1/institutions/{inst.id}/staff",
        json=payload,
        headers=headers,
    )
    assert resp1.status_code == 201

    # Second creation with identical email fails with 409 Conflict
    resp2 = client.post(
        f"/api/v1/institutions/{inst.id}/staff",
        json=payload,
        headers=headers,
    )
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"]


def test_admin_cannot_deactivate_or_delete_self(client: TestClient, db_session: Session):
    """Admin cannot deactivate or delete their own account."""
    inst = _create_institution(db_session, "1-STAFF-03", "College Self Lockout Test")
    admin_user, admin_token = _create_user(
        db_session, "admin3@tech.edu.in", Role.COLLEGE_ADMIN.value, inst.id
    )

    headers = {"Authorization": f"Bearer {admin_token}"}

    # Attempting to deactivate self via PATCH
    resp_patch = client.patch(
        f"/api/v1/institutions/{inst.id}/staff/{admin_user.id}",
        json={"is_active": False},
        headers=headers,
    )
    assert resp_patch.status_code == 400
    assert "Cannot deactivate your own account" in resp_patch.json()["detail"]

    # Attempting to delete self via DELETE
    resp_del = client.delete(
        f"/api/v1/institutions/{inst.id}/staff/{admin_user.id}",
        headers=headers,
    )
    assert resp_del.status_code == 400
    assert "Cannot delete or deactivate your own account" in resp_del.json()["detail"]


# =========================================================================
# 2. Role Limits Tests: Staff Cannot Manage Staff or Submit
# =========================================================================


def test_college_staff_cannot_manage_staff(client: TestClient, db_session: Session):
    """College staff (admission officer) cannot manage staff accounts (403 Forbidden).

    SPEC.md section 5: 'Cannot submit, cannot manage staff.'
    """
    inst = _create_institution(db_session, "1-LIMIT-01", "College Limits Test")
    _, staff_token = _create_user(
        db_session, "staff@tech.edu.in", Role.COLLEGE_STAFF.value, inst.id
    )

    headers = {"Authorization": f"Bearer {staff_token}"}

    # 1. Staff cannot create staff
    resp_create = client.post(
        f"/api/v1/institutions/{inst.id}/staff",
        json={
            "email": "sub_staff@tech.edu.in",
            "password": "Password@123",
            "role": Role.COLLEGE_STAFF.value,
        },
        headers=headers,
    )
    assert resp_create.status_code == 403
    assert "lacks required permissions" in resp_create.json()["detail"]

    # 2. Staff cannot list staff
    resp_list = client.get(
        f"/api/v1/institutions/{inst.id}/staff",
        headers=headers,
    )
    assert resp_list.status_code == 403

    # 3. Staff cannot get staff detail
    resp_get = client.get(
        f"/api/v1/institutions/{inst.id}/staff/1",
        headers=headers,
    )
    assert resp_get.status_code == 403

    # 4. Staff cannot update staff
    resp_update = client.patch(
        f"/api/v1/institutions/{inst.id}/staff/1",
        json={"role": Role.COLLEGE_VIEWER.value},
        headers=headers,
    )
    assert resp_update.status_code == 403

    # 5. Staff cannot delete staff
    resp_del = client.delete(
        f"/api/v1/institutions/{inst.id}/staff/1",
        headers=headers,
    )
    assert resp_del.status_code == 403


def test_college_viewer_cannot_manage_staff(client: TestClient, db_session: Session):
    """College viewer (read-only staff) cannot manage staff (403 Forbidden)."""
    inst = _create_institution(db_session, "1-LIMIT-02", "College Viewer Test")
    _, viewer_token = _create_user(
        db_session, "viewer@tech.edu.in", Role.COLLEGE_VIEWER.value, inst.id
    )

    headers = {"Authorization": f"Bearer {viewer_token}"}

    resp = client.post(
        f"/api/v1/institutions/{inst.id}/staff",
        json={"email": "x@x.com", "password": "Password@123", "role": "college_staff"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_staff_cannot_submit_data_gate(client: TestClient, db_session: Session):
    """College staff and viewers cannot submit student data; only college_admin can.

    SPEC.md section 5 & 10:
    - 'Final submit gate (college admin only)'
    - 'Cannot submit, cannot manage staff'
    """
    inst = _create_institution(db_session, "1-SUBMIT-01", "Submit Gate Test College")
    _, admin_token = _create_user(
        db_session, "admin@submit.edu.in", Role.COLLEGE_ADMIN.value, inst.id
    )
    _, staff_token = _create_user(
        db_session, "staff@submit.edu.in", Role.COLLEGE_STAFF.value, inst.id
    )
    _, viewer_token = _create_user(
        db_session, "viewer@submit.edu.in", Role.COLLEGE_VIEWER.value, inst.id
    )

    # 1. Staff calls submit gate -> 403 Forbidden
    resp_staff = client.post(
        f"/api/v1/institutions/{inst.id}/submit",
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert resp_staff.status_code == 403
    assert "lacks required permissions" in resp_staff.json()["detail"]

    # 2. Viewer calls submit gate -> 403 Forbidden
    resp_viewer = client.post(
        f"/api/v1/institutions/{inst.id}/submit",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp_viewer.status_code == 403
    assert "lacks required permissions" in resp_viewer.json()["detail"]

    # 3. College Admin calls submit gate -> 200 OK
    resp_admin = client.post(
        f"/api/v1/institutions/{inst.id}/submit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_admin.status_code == 200
    assert resp_admin.json()["status"] == "authorized"
    assert resp_admin.json()["role"] == Role.COLLEGE_ADMIN.value


# =========================================================================
# 3. IDOR Prevention: College A Cannot Manage College B Staff
# =========================================================================


def test_college_a_admin_cannot_manage_college_b_staff(client: TestClient, db_session: Session):
    """College A admin cannot create or view staff under College B (403 Forbidden)."""
    inst_a = _create_institution(db_session, "1-IDOR-A", "College A")
    inst_b = _create_institution(db_session, "1-IDOR-B", "College B")

    _, token_a = _create_user(
        db_session, "admin_a@college-a.edu", Role.COLLEGE_ADMIN.value, inst_a.id
    )

    headers = {"Authorization": f"Bearer {token_a}"}

    # Attempting to create staff for College B
    resp_create = client.post(
        f"/api/v1/institutions/{inst_b.id}/staff",
        json={
            "email": "infiltrator@college-b.edu",
            "password": "Password@123",
            "role": Role.COLLEGE_STAFF.value,
        },
        headers=headers,
    )
    assert resp_create.status_code == 403
    assert "Cannot access another institution's data" in resp_create.json()["detail"]

    # Attempting to list staff of College B
    resp_list = client.get(
        f"/api/v1/institutions/{inst_b.id}/staff",
        headers=headers,
    )
    assert resp_list.status_code == 403
    assert "Cannot access another institution's data" in resp_list.json()["detail"]


# =========================================================================
# 4. Contact or Head Change Requests (Spec 6, 11)
# =========================================================================


def test_contact_change_request_workflow(client: TestClient, db_session: Session):
    """College admin cannot edit official contacts directly; must file a request to AICTE."""
    inst = _create_institution(
        db_session,
        "1-CONTACT-01",
        "Apex Institute of Engineering",
        official_email="old_contact@apex.edu.in",
        official_phone="+919111111111",
        head_name="Prof. Old Head",
    )
    _, college_token = _create_user(
        db_session, "admin@apex.edu.in", Role.COLLEGE_ADMIN.value, inst.id
    )
    officer_user, officer_token = _create_user(
        db_session, "officer@aicte-india.org", Role.AICTE_OFFICER.value, None
    )

    college_headers = {"Authorization": f"Bearer {college_token}"}
    officer_headers = {"Authorization": f"Bearer {officer_token}"}

    # 1. Direct edit attempt by College Admin is blocked (403 Forbidden)
    resp_direct = client.patch(
        f"/api/v1/institutions/{inst.id}",
        json={"official_email": "new_direct@apex.edu.in"},
        headers=college_headers,
    )
    assert resp_direct.status_code == 403

    # 2. College files contact change request
    change_payload = {
        "official_email": "new_principal@apex.edu.in",
        "official_phone": "+919222222222",
        "head_name": "Dr. New Principal",
        "reason": "New principal appointed following board resolution #402",
    }
    resp_request = client.post(
        f"/api/v1/institutions/{inst.id}/contact-change-requests",
        json=change_payload,
        headers=college_headers,
    )
    assert resp_request.status_code == 201
    request_data = resp_request.json()
    assert request_data["kind"] == "contact_change"
    assert request_data["status"] == "pending"
    request_id = request_data["id"]

    # 3. AICTE Officer reviews request in global queue
    resp_queue = client.get(
        "/api/v1/institutions/correction-requests",
        headers=officer_headers,
    )
    assert resp_queue.status_code == 200
    queue_ids = [item["id"] for item in resp_queue.json()]
    assert request_id in queue_ids

    # 4. AICTE Officer approves the request and applies changes
    resolve_payload = {
        "status": "approved",
        "decision_note": "Verified appointment letter; changes approved.",
        "apply_changes": True,
    }
    resp_resolve = client.patch(
        f"/api/v1/institutions/correction-requests/{request_id}/resolve",
        json=resolve_payload,
        headers=officer_headers,
    )
    assert resp_resolve.status_code == 200
    assert resp_resolve.json()["status"] == "approved"

    # 5. Verify official institution details are now updated
    db_session.refresh(inst)
    assert inst.official_email == "new_principal@apex.edu.in"
    assert inst.official_phone == "+919222222222"
    assert inst.head_name == "Dr. New Principal"


# =========================================================================
# 5. Password Reset Only via OTP to On-File Contacts (Spec 11)
# =========================================================================


def test_password_reset_only_via_otp_to_on_file_contact(client: TestClient, db_session: Session):
    """Password reset sends OTP strictly to official on-file contact, never to typed-in address.

    Spec 11: 'Password reset only via OTP to the official contacts on file.'
    """
    official_email = "principal_official@pune-tech.edu.in"
    inst = _create_institution(
        db_session,
        "1-PWD-01",
        "Pune Institute of Tech",
        official_email=official_email,
    )

    # User has personal email, but institution has official_email
    staff_user, _ = _create_user(
        db_session,
        "staff_personal@pune-tech.edu.in",
        Role.COLLEGE_STAFF.value,
        inst.id,
        password="OldPassword@123",
    )

    # 1. Request password reset using user's login email
    ip_headers = {"X-Forwarded-For": "192.168.100.50"}
    resp_req = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "staff_personal@pune-tech.edu.in"},
        headers=ip_headers,
    )
    assert resp_req.status_code == 200
    req_data = resp_req.json()
    assert req_data["status"] == "success"
    # Masked recipient points to official on-file email, NOT arbitrary address
    assert "@pune-tech.edu.in" in req_data["masked_recipient"]

    # Verify OTP was written to dev_outbox for the official_email
    outbox_entry = db_session.scalar(
        select(DevOutbox)
        .where(
            DevOutbox.recipient == official_email,
            DevOutbox.channel == "email",
        )
        .order_by(DevOutbox.id.desc())
    )
    assert outbox_entry is not None
    assert "Password reset OTP" in outbox_entry.body

    # Extract OTP code from outbox message body (e.g. "code is 123456")
    words = outbox_entry.body.split()
    otp_code = None
    for word in words:
        clean_word = word.strip(".,;:!")
        if clean_word.isdigit() and len(clean_word) == 6:
            otp_code = clean_word
            break
    assert otp_code is not None, f"Could not find 6-digit OTP code in {outbox_entry.body}"

    # 2. Test wrong OTP fails
    resp_bad_otp = client.post(
        "/api/v1/auth/password-reset/verify",
        json={
            "email": "staff_personal@pune-tech.edu.in",
            "otp_code": "000000",
        },
        headers=ip_headers,
    )
    assert resp_bad_otp.status_code == 400
    assert "Invalid OTP" in resp_bad_otp.json()["detail"]

    # 3. Verify OTP with correct code -> returns reset_token
    resp_verify = client.post(
        "/api/v1/auth/password-reset/verify",
        json={
            "email": "staff_personal@pune-tech.edu.in",
            "otp_code": otp_code,
        },
        headers=ip_headers,
    )
    assert resp_verify.status_code == 200
    verify_data = resp_verify.json()
    reset_token = verify_data["reset_token"]
    assert reset_token is not None

    # 4. Confirm new password with reset_token
    new_password = "BrandNewPassword@2026"
    resp_confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "reset_token": reset_token,
            "new_password": new_password,
        },
        headers=ip_headers,
    )
    assert resp_confirm.status_code == 200
    assert "successfully updated" in resp_confirm.json()["message"]

    # 5. Verify audit log entry exists for password reset
    reset_audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "auth.password_reset",
            AuditLog.entity_id == str(staff_user.id),
        )
    )
    assert reset_audit is not None

    # 6. Verify login with old password fails (401)
    resp_old_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "staff_personal@pune-tech.edu.in",
            "password": "OldPassword@123",
        },
    )
    assert resp_old_login.status_code == 401

    # 7. Verify login with new password succeeds (200)
    resp_new_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "staff_personal@pune-tech.edu.in",
            "password": new_password,
        },
    )
    assert resp_new_login.status_code == 200
    assert "access_token" in resp_new_login.json()
