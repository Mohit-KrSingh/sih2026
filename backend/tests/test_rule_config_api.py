"""Integration tests for validation rule configuration API endpoints.

Spec: Section 9.2, 9.3, 12, 15:
- AICTE role access control (officer can read, admin can modify).
- College users receive 403 Forbidden.
- Parameter and level overrides persisted to rule_config.
- Audit log entry recorded on update and reset.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token
from app.models import Institution, RuleConfig, User


@pytest.fixture
def aicte_admin_token(db_session: Session) -> str:
    admin = db_session.scalar(select(User).where(User.role == "aicte_admin"))
    if not admin:
        admin = User(
            email="test_rule_admin@aicte-india.org",
            password_hash="test_hash",
            role="aicte_admin",
            is_active=True,
        )
        db_session.add(admin)
        db_session.flush()
    return create_access_token(
        user_id=admin.id,
        email=admin.email,
        role=admin.role,
        institution_id=admin.institution_id,
    )


@pytest.fixture
def aicte_officer_token(db_session: Session) -> str:
    officer = db_session.scalar(select(User).where(User.role == "aicte_officer"))
    if not officer:
        officer = User(
            email="test_rule_officer@aicte-india.org",
            password_hash="test_hash",
            role="aicte_officer",
            is_active=True,
        )
        db_session.add(officer)
        db_session.flush()
    return create_access_token(
        user_id=officer.id,
        email=officer.email,
        role=officer.role,
        institution_id=officer.institution_id,
    )


@pytest.fixture
def college_admin_token(db_session: Session) -> str:
    user = db_session.scalar(select(User).where(User.role == "college_admin"))
    if not user:
        inst = db_session.scalar(select(Institution))
        if not inst:
            inst = Institution(
                aicte_id="1-TEST-RULES-01",
                name="Test Rules College",
                state="Maharashtra",
                district="Pune",
                address="Test Campus",
                official_email="test@rules.edu",
                official_phone="9876543210",
                head_name="Dr. Principal",
                affiliating_university="Test University",
                approval_status="active",
                account_status="active",
            )
            db_session.add(inst)
            db_session.flush()
        user = User(
            email="test_college_admin_rules@example.edu.in",
            password_hash="test_hash",
            role="college_admin",
            institution_id=inst.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()
    return create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )


def test_list_rules_aicte_roles(
    client: TestClient, aicte_officer_token: str, aicte_admin_token: str
) -> None:
    """Both aicte_officer and aicte_admin can list all catalogued rules."""
    # AICTE Officer
    res = client.get(
        "/api/v1/rules",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 34
    assert len(data["items"]) == 34

    # AICTE Admin
    res_admin = client.get(
        "/api/v1/rules",
        headers={"Authorization": f"Bearer {aicte_admin_token}"},
    )
    assert res_admin.status_code == 200


def test_list_rules_rbac_enforcement(client: TestClient, college_admin_token: str) -> None:
    """College users and unauthenticated callers receive 403/401."""
    # Unauthenticated
    res = client.get("/api/v1/rules")
    assert res.status_code == 401

    # College admin
    res_college = client.get(
        "/api/v1/rules",
        headers={"Authorization": f"Bearer {college_admin_token}"},
    )
    assert res_college.status_code == 403


def test_get_single_rule(client: TestClient, aicte_officer_token: str) -> None:
    """Can retrieve a single rule by code or get 404 for unknown code."""
    res = client.get(
        "/api/v1/rules/INTAKE_EXCEEDED",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["rule_code"] == "INTAKE_EXCEEDED"
    assert data["scope"] == "course"
    assert data["default_level"] == "exception"

    res_404 = client.get(
        "/api/v1/rules/NONEXISTENT_RULE",
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert res_404.status_code == 404


def test_update_rule_aicte_admin_only(
    client: TestClient,
    aicte_officer_token: str,
    aicte_admin_token: str,
    db_session: Session,
) -> None:
    """Only aicte_admin can modify rule configuration; officer gets 403."""
    # Officer attempt blocked
    res_officer = client.put(
        "/api/v1/rules/ANOM_ENROLMENT_JUMP",
        json={"level": "error", "params": {"threshold_percent": 45.0}},
        headers={"Authorization": f"Bearer {aicte_officer_token}"},
    )
    assert res_officer.status_code == 403

    # Admin attempt succeeds
    res_admin = client.put(
        "/api/v1/rules/ANOM_ENROLMENT_JUMP",
        json={"level": "error", "params": {"threshold_percent": 45.0}, "enabled": True},
        headers={"Authorization": f"Bearer {aicte_admin_token}"},
    )
    assert res_admin.status_code == 200
    updated = res_admin.json()
    assert updated["current_level"] == "error"
    assert updated["current_params"] == {"threshold_percent": 45.0}
    assert updated["is_overridden"] is True

    # Verify DB persistence
    row = db_session.query(RuleConfig).filter(RuleConfig.rule_code == "ANOM_ENROLMENT_JUMP").first()
    assert row is not None
    assert row.level == "error"
    assert row.params_json == {"threshold_percent": 45.0}


def test_reset_rule_config(
    client: TestClient, aicte_admin_token: str, db_session: Session
) -> None:
    """aicte_admin can reset rule configuration back to catalogue defaults."""
    # First set override
    client.put(
        "/api/v1/rules/ANOM_NRI_SHARE",
        json={"level": "exception", "params": {"threshold_percent": 50.0}},
        headers={"Authorization": f"Bearer {aicte_admin_token}"},
    )

    # Now reset
    res = client.post(
        "/api/v1/rules/ANOM_NRI_SHARE/reset",
        headers={"Authorization": f"Bearer {aicte_admin_token}"},
    )
    assert res.status_code == 200
    reset_data = res.json()
    assert reset_data["current_level"] == "warning"  # default level
    assert reset_data["is_overridden"] is False

    # Verify DB row deleted
    row = db_session.query(RuleConfig).filter(RuleConfig.rule_code == "ANOM_NRI_SHARE").first()
    assert row is None
