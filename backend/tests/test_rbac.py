"""Tests for Role-Based Access Control (RBAC), Route Protection, and IDOR prevention."""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.allowlist import PUBLIC_ALLOWLIST
from app.auth.dependencies import (
    get_current_user,
    get_institution_scope,
    oauth2_scheme,
    require_aicte_admin,
    require_aicte_officer,
    require_college_admin,
    require_college_staff,
    require_college_user,
    verify_api_key,
    verify_institution_access,
)
from app.auth.schemas import Role
from app.auth.security import create_access_token
from app.main import app
from app.models import Institution, User


def _create_test_institution(db: Session, aicte_id: str, name: str) -> Institution:
    inst = Institution(
        aicte_id=aicte_id,
        name=name,
        state="Maharashtra",
        district="Pune",
        address="123 Test Street",
        official_email=f"contact_{aicte_id.lower()}@example.edu",
        official_phone="+919876543210",
        head_name="Principal Test",
        affiliating_university="State Tech University",
        approval_status="active",
        account_status="active",
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def _has_auth_dependency(dependant) -> bool:
    """Recursively inspect a FastAPI Dependant for authentication or role dependencies."""
    auth_callables = {
        get_current_user,
        oauth2_scheme,
        verify_institution_access,
        get_institution_scope,
        verify_api_key,
    }

    if dependant.call in auth_callables:
        return True

    # Check if the callable is a closure created by require_roles or require_api_key_scope
    qualname = getattr(dependant.call, "__qualname__", "")
    if "require_roles.<locals>.role_checker" in qualname:
        return True
    if "require_api_key_scope.<locals>.scope_checker" in qualname:
        return True

    for sub_dep in dependant.dependencies:
        if _has_auth_dependency(sub_dep):
            return True

    return False


def test_route_protection_deny_by_default():
    """Verify that every route in the application has an explicit role requirement

    unless it is present on the explicit PUBLIC_ALLOWLIST.
    Hard Rule 7: Deny by default: every route has an explicit role requirement.
    A test fails if a route is unprotected and not on the public allowlist.
    """
    unprotected_routes: list[tuple[str, str]] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue

            endpoint_key = (route.path, method)
            if endpoint_key in PUBLIC_ALLOWLIST:
                continue

            # Route is not on allowlist - verify it enforces authentication/roles
            is_protected = _has_auth_dependency(route.dependant)
            if not is_protected:
                unprotected_routes.append(endpoint_key)

    assert not unprotected_routes, (
        f"Security violation! Found {len(unprotected_routes)} unprotected route(s) "
        f"not on the public allowlist: {unprotected_routes}"
    )


def test_idor_college_a_cannot_access_college_b_data(client: TestClient, db_session: Session):
    """IDOR test: College A cannot read or write College B's data.

    SPEC.md section 5: 'A college user can only ever access their own institution's data
    (test for this explicitly: college A must not read college B's students).'
    """
    inst_a = _create_test_institution(db_session, "IDOR-INST-A", "College A")
    inst_b = _create_test_institution(db_session, "IDOR-INST-B", "College B")

    # Create College A Admin
    user_college_a = User(
        email="admin_a@college-a.edu",
        password_hash="fake_hash",
        role=Role.COLLEGE_ADMIN.value,
        institution_id=inst_a.id,
        is_active=True,
    )
    # Create College B Admin
    user_college_b = User(
        email="admin_b@college-b.edu",
        password_hash="fake_hash",
        role=Role.COLLEGE_ADMIN.value,
        institution_id=inst_b.id,
        is_active=True,
    )
    # Create AICTE Admin (institution_id=None, supervisory role)
    user_aicte_admin = User(
        email="admin@aicte-india.org",
        password_hash="fake_hash",
        role=Role.AICTE_ADMIN.value,
        institution_id=None,
        is_active=True,
    )
    # Create Verifier (institution_id=None, restricted to verification only)
    user_verifier = User(
        email="verifier@company.org",
        password_hash="fake_hash",
        role=Role.VERIFIER.value,
        institution_id=None,
        is_active=True,
    )

    db_session.add_all([user_college_a, user_college_b, user_aicte_admin, user_verifier])
    db_session.commit()
    for u in [user_college_a, user_college_b, user_aicte_admin, user_verifier]:
        db_session.refresh(u)

    token_a = create_access_token(
        user_college_a.id, user_college_a.email, user_college_a.role, inst_a.id
    )
    token_b = create_access_token(
        user_college_b.id, user_college_b.email, user_college_b.role, inst_b.id
    )
    token_aicte = create_access_token(
        user_aicte_admin.id, user_aicte_admin.email, user_aicte_admin.role, None
    )
    token_verifier = create_access_token(
        user_verifier.id, user_verifier.email, user_verifier.role, None
    )

    # 1. College A accessing College A: ALLOWED (200)
    resp = client.get(
        f"/api/v1/auth/institutions/{inst_a.id}/access-check",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "granted"
    assert resp.json()["institution_id"] == inst_a.id

    # 2. College A attempting to access College B: FORBIDDEN (403 - IDOR prevented!)
    resp_idor = client.get(
        f"/api/v1/auth/institutions/{inst_b.id}/access-check",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_idor.status_code == 403
    assert "Cannot access another institution's data" in resp_idor.json()["detail"]

    # 3. College B accessing College B: ALLOWED (200)
    resp = client.get(
        f"/api/v1/auth/institutions/{inst_b.id}/access-check",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 200
    assert resp.json()["institution_id"] == inst_b.id

    # 4. College B attempting to access College A: FORBIDDEN (403 - IDOR prevented!)
    resp_idor_b = client.get(
        f"/api/v1/auth/institutions/{inst_a.id}/access-check",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_idor_b.status_code == 403
    assert "Cannot access another institution's data" in resp_idor_b.json()["detail"]

    # 5. AICTE Admin can supervise both Institution A and Institution B
    resp_aicte_1 = client.get(
        f"/api/v1/auth/institutions/{inst_a.id}/access-check",
        headers={"Authorization": f"Bearer {token_aicte}"},
    )
    assert resp_aicte_1.status_code == 200

    resp_aicte_2 = client.get(
        f"/api/v1/auth/institutions/{inst_b.id}/access-check",
        headers={"Authorization": f"Bearer {token_aicte}"},
    )
    assert resp_aicte_2.status_code == 200

    # 6. Verifier cannot access college endpoints
    resp_verifier = client.get(
        f"/api/v1/auth/institutions/{inst_a.id}/access-check",
        headers={"Authorization": f"Bearer {token_verifier}"},
    )
    assert resp_verifier.status_code == 403


def test_role_dependency_helpers():
    """Test RBAC role enforcement across user roles."""
    test_app = FastAPI()

    @test_app.get("/admin-only")
    def admin_endpoint(_: None = require_aicte_admin):
        return {"access": "granted"}

    @test_app.get("/officer-or-admin")
    def officer_endpoint(_: None = require_aicte_officer):
        return {"access": "granted"}

    @test_app.get("/college-admin-only")
    def college_admin_endpoint(_: None = require_college_admin):
        return {"access": "granted"}

    @test_app.get("/college-staff-or-admin")
    def college_staff_endpoint(_: None = require_college_staff):
        return {"access": "granted"}

    @test_app.get("/college-any")
    def college_user_endpoint(_: None = require_college_user):
        return {"access": "granted"}

    # Mock dependency override for fast unit checking
    def make_user(role: str, inst_id: int | None = 1) -> User:
        return User(
            id=1,
            email=f"{role}@example.com",
            role=role,
            institution_id=inst_id,
            is_active=True,
        )

    t_client = TestClient(test_app)

    # 1. AICTE Admin on admin-only: OK
    test_app.dependency_overrides[get_current_user] = lambda: make_user(Role.AICTE_ADMIN.value)
    assert t_client.get("/admin-only").status_code == 200

    # 2. AICTE Officer on admin-only: 403
    test_app.dependency_overrides[get_current_user] = lambda: make_user(Role.AICTE_OFFICER.value)
    assert t_client.get("/admin-only").status_code == 403

    # 3. AICTE Officer on officer-or-admin: 200
    assert t_client.get("/officer-or-admin").status_code == 200

    # 4. College Admin on college-admin-only: 200
    test_app.dependency_overrides[get_current_user] = lambda: make_user(Role.COLLEGE_ADMIN.value)
    assert t_client.get("/college-admin-only").status_code == 200

    # 5. College Staff on college-admin-only: 403 (cannot manage staff or submit)
    test_app.dependency_overrides[get_current_user] = lambda: make_user(Role.COLLEGE_STAFF.value)
    assert t_client.get("/college-admin-only").status_code == 403

    # 6. College Staff on college-staff-or-admin: 200
    assert t_client.get("/college-staff-or-admin").status_code == 200

    # 7. College Viewer on college-staff-or-admin: 403
    test_app.dependency_overrides[get_current_user] = lambda: make_user(Role.COLLEGE_VIEWER.value)
    assert t_client.get("/college-staff-or-admin").status_code == 403

    # 8. College Viewer on college-any: 200
    assert t_client.get("/college-any").status_code == 200

    # Clean up overrides
    test_app.dependency_overrides.clear()


def test_get_institution_scope_helper():
    """Test get_institution_scope behavior for college, AICTE, and invalid users."""
    college_user = User(
        id=1, email="c@c.edu", role=Role.COLLEGE_ADMIN.value, institution_id=5, is_active=True
    )
    assert get_institution_scope(college_user) == 5

    aicte_user = User(
        id=2,
        email="a@aicte.org",
        role=Role.AICTE_OFFICER.value,
        institution_id=None,
        is_active=True,
    )
    assert get_institution_scope(aicte_user) is None

    unaffiliated_college_user = User(
        id=3, email="bad@c.edu", role=Role.COLLEGE_ADMIN.value, institution_id=None, is_active=True
    )
    with pytest.raises(HTTPException) as exc_info:
        get_institution_scope(unaffiliated_college_user)
    assert exc_info.value.status_code == 403

    verifier_user = User(
        id=4, email="v@v.com", role=Role.VERIFIER.value, institution_id=None, is_active=True
    )
    with pytest.raises(HTTPException) as exc_info:
        get_institution_scope(verifier_user)
    assert exc_info.value.status_code == 403
