"""FastAPI router for Validation Rule Configuration and Customization."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.auth.dependencies import require_aicte_admin, require_aicte_user
from app.db import get_db
from app.models import RuleConfig, User
from app.validation.codes import RULE_CATALOGUE
from app.validation.schemas import (
    RuleConfigResponse,
    RuleConfigUpdateRequest,
    RuleListResponse,
)

router = APIRouter(prefix="/rules", tags=["Validation Rules & Configuration"])


def _build_rule_response(rule_code: str, override: RuleConfig | None) -> RuleConfigResponse:
    cat = RULE_CATALOGUE[rule_code]
    scope_val = cat["scope"].value if hasattr(cat["scope"], "value") else str(cat["scope"])
    default_lvl = (
        cat["default_level"].value
        if hasattr(cat["default_level"], "value")
        else str(cat["default_level"])
    )
    default_p = cat.get("default_params") or {}

    if override is not None:
        return RuleConfigResponse(
            rule_code=rule_code,
            scope=scope_val,
            default_level=default_lvl,
            current_level=override.level,
            meaning=cat.get("meaning", ""),
            default_params=default_p,
            current_params=override.params_json if override.params_json is not None else default_p,
            enabled=override.enabled,
            is_overridden=True,
            updated_by=override.updated_by,
            updated_at=override.updated_at,
        )

    return RuleConfigResponse(
        rule_code=rule_code,
        scope=scope_val,
        default_level=default_lvl,
        current_level=default_lvl,
        meaning=cat.get("meaning", ""),
        default_params=default_p,
        current_params=default_p,
        enabled=True,
        is_overridden=False,
        updated_by=None,
        updated_at=None,
    )


@router.get(
    "",
    response_model=RuleListResponse,
    summary="List all validation rules and active configurations (AICTE only)",
)
def list_rules(
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
) -> RuleListResponse:
    """Retrieve all 34 catalogued rules merged with database policy overrides."""
    overrides_stmt = select(RuleConfig)
    overrides = {rc.rule_code: rc for rc in db.scalars(overrides_stmt).all()}

    items: list[RuleConfigResponse] = []
    overridden_count = 0

    for code in RULE_CATALOGUE:
        override = overrides.get(code)
        if override is not None:
            overridden_count += 1
        items.append(_build_rule_response(code, override))

    return RuleListResponse(
        total=len(items),
        overridden_count=overridden_count,
        items=items,
    )


@router.get(
    "/{rule_code}",
    response_model=RuleConfigResponse,
    summary="Get configuration of a specific rule (AICTE only)",
)
def get_rule(
    rule_code: str,
    current_user: Annotated[User, require_aicte_user],
    db: Annotated[Session, Depends(get_db)],
) -> RuleConfigResponse:
    """Retrieve rule catalogue metadata and current active configuration."""
    if rule_code not in RULE_CATALOGUE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule code '{rule_code}' not found in registry catalogue",
        )

    override = db.scalar(select(RuleConfig).where(RuleConfig.rule_code == rule_code))
    return _build_rule_response(rule_code, override)


@router.put(
    "/{rule_code}",
    response_model=RuleConfigResponse,
    summary="Update validation rule policy override (AICTE admin only)",
)
def update_rule_config(
    rule_code: str,
    payload: RuleConfigUpdateRequest,
    current_user: Annotated[User, require_aicte_admin],
    db: Annotated[Session, Depends(get_db)],
    request: Request,
) -> RuleConfigResponse:
    """Customize rule severity level, parameters, or toggle enabled status."""
    if rule_code not in RULE_CATALOGUE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule code '{rule_code}' not found in registry catalogue",
        )

    cat = RULE_CATALOGUE[rule_code]
    override = db.scalar(select(RuleConfig).where(RuleConfig.rule_code == rule_code))

    default_lvl = (
        cat["default_level"].value
        if hasattr(cat["default_level"], "value")
        else str(cat["default_level"])
    )
    default_p = cat.get("default_params") or {}

    before_state = None
    if override is not None:
        before_state = {
            "level": override.level,
            "params_json": override.params_json,
            "enabled": override.enabled,
        }
    else:
        override = RuleConfig(
            rule_code=rule_code,
            level=default_lvl,
            params_json=default_p,
            enabled=True,
            updated_by=current_user.id,
        )
        db.add(override)

    if payload.level is not None:
        lvl_val = (
            payload.level.value
            if hasattr(payload.level, "value")
            else str(payload.level)
        )
        override.level = lvl_val
    if payload.params is not None:
        override.params_json = payload.params
    if payload.enabled is not None:
        override.enabled = payload.enabled

    override.updated_by = current_user.id
    db.commit()
    db.refresh(override)

    after_state = {
        "level": override.level,
        "params_json": override.params_json,
        "enabled": override.enabled,
    }

    client_ip = request.client.host if request.client else None
    audit.record(
        db=db,
        action="rule_config.update",
        actor_id=str(current_user.id),
        actor_role=current_user.role,
        entity="rule_config",
        entity_id=str(override.id),
        before_json=before_state,
        after_json=after_state,
        ip=client_ip,
        commit=True,
    )

    return _build_rule_response(rule_code, override)


@router.post(
    "/{rule_code}/reset",
    response_model=RuleConfigResponse,
    summary="Reset rule configuration to catalogue defaults (AICTE admin only)",
)
def reset_rule_config(
    rule_code: str,
    current_user: Annotated[User, require_aicte_admin],
    db: Annotated[Session, Depends(get_db)],
    request: Request,
) -> RuleConfigResponse:
    """Remove custom overrides and restore catalogue default level and parameters."""
    if rule_code not in RULE_CATALOGUE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule code '{rule_code}' not found in registry catalogue",
        )

    override = db.scalar(select(RuleConfig).where(RuleConfig.rule_code == rule_code))
    if override is not None:
        before_state = {
            "level": override.level,
            "params_json": override.params_json,
            "enabled": override.enabled,
        }
        override_id = override.id
        db.delete(override)
        db.commit()

        client_ip = request.client.host if request.client else None
        audit.record(
            db=db,
            action="rule_config.reset",
            actor_id=str(current_user.id),
            actor_role=current_user.role,
            entity="rule_config",
            entity_id=str(override_id),
            before_json=before_state,
            after_json=None,
            ip=client_ip,
            commit=True,
        )

    return _build_rule_response(rule_code, None)
