"""Pydantic schemas for rule configuration and customization."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.validation.flags import ValidationLevel


class RuleConfigResponse(BaseModel):
    """Details and current configuration of a validation rule."""

    model_config = ConfigDict(from_attributes=True)

    rule_code: str = Field(..., description="Unique validation rule code (e.g. INTAKE_EXCEEDED)")
    scope: str = Field(..., description="Validation scope: file, row, course, cross, anomaly")
    default_level: str = Field(..., description="Catalogue default validation level")
    current_level: str = Field(..., description="Active level taking rule_config into account")
    meaning: str = Field(..., description="Plain English description of what the rule validates")
    default_params: dict[str, Any] = Field(
        default_factory=dict, description="Default parameters defined in rule catalogue"
    )
    current_params: dict[str, Any] = Field(
        default_factory=dict, description="Active parameters taking rule_config into account"
    )
    enabled: bool = Field(default=True, description="Whether the rule is currently active")
    is_overridden: bool = Field(
        default=False, description="Whether rule has custom policy overrides in rule_config"
    )
    updated_by: int | None = Field(default=None, description="User ID of last administrator")
    updated_at: datetime | None = Field(default=None, description="Timestamp of last modification")


class RuleConfigUpdateRequest(BaseModel):
    """Payload to create or update an override in rule_config."""

    level: ValidationLevel | None = Field(
        default=None, description="Override validation level: error, exception, warning, info"
    )
    params: dict[str, Any] | None = Field(
        default=None, description="Custom parameter dictionary overriding default rule params"
    )
    enabled: bool | None = Field(
        default=None, description="Toggle whether rule executes during validation"
    )


class RuleListResponse(BaseModel):
    """List response of all catalogued rules and their active configurations."""

    total: int = Field(..., description="Total rules catalogued")
    overridden_count: int = Field(..., description="Number of rules with custom overrides")
    items: list[RuleConfigResponse] = Field(..., description="Catalogued rules")
