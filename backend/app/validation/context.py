"""Validation context objects and rule configuration overrides."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RuleConfig


@dataclass(slots=True)
class RuleConfigOverride:
    """Override configuration for a validation rule per SPEC.md Section 9.2."""

    rule_code: str
    level: str | None = None  # error | exception | warning | info
    params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    @classmethod
    def from_model(cls, model: RuleConfig) -> RuleConfigOverride:
        """Construct from SQLAlchemy RuleConfig model."""
        return cls(
            rule_code=model.rule_code,
            level=model.level,
            params=model.params_json or {},
            enabled=model.enabled,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleConfigOverride:
        """Construct from dictionary."""
        return cls(
            rule_code=data.get("rule_code", ""),
            level=data.get("level"),
            params=data.get("params", data.get("params_json", {})),
            enabled=data.get("enabled", True),
        )


def load_rule_config_overrides(db: Session) -> dict[str, RuleConfigOverride]:
    """Query rule_config table from database and return rule_code -> RuleConfigOverride map."""
    records = db.scalars(select(RuleConfig)).all()
    return {rec.rule_code: RuleConfigOverride.from_model(rec) for rec in records}


@dataclass
class ValidationContext:
    """Carries rows, course, approved intake, config, and lookup clients passed in explicitly.

    Per SPEC.md Section 9.2:
    Pure, no hidden side effects. All required state is held within this context object.
    """

    rows: list[dict[str, Any]] = field(default_factory=list)
    single_row: dict[str, Any] | None = None
    course: Any | None = None
    course_id: int | None = None
    submission_id: int | None = None
    approved_intake: int | None = None
    approved_supernumerary: int | None = None
    institution_id: int | None = None
    academic_year: str | None = None
    declared_seats: dict[str, int] | None = None
    history_students: list[Any] = field(default_factory=list)
    all_college_students: list[Any] = field(default_factory=list)
    other_college_students: list[Any] = field(default_factory=list)
    file_metadata: dict[str, Any] = field(default_factory=dict)
    apaar_client: Any | None = None
    aicte_client: Any | None = None
    db_session: Session | None = None
    rule_configs: dict[str, RuleConfigOverride] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    apaar_cache: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def get_param(self, key: str, default: Any = None) -> Any:
        """Get parameter value merged for the currently active rule."""
        return self.params.get(key, default)

    def get_all_rows(self) -> list[Any]:
        """Return all rows in this context, falling back to single_row if rows is empty."""
        if self.rows:
            return self.rows
        if self.single_row is not None:
            return [self.single_row]
        return []

    @staticmethod
    def get_field_value(row: Any, field_name: str, default: Any = None) -> Any:
        """Extract a field from a row whether row is a dict or an object."""
        if isinstance(row, dict):
            return row.get(field_name, default)
        return getattr(row, field_name, default)

    def with_params(self, params: dict[str, Any]) -> ValidationContext:
        """Return a shallow copy of this context with active rule params set."""
        return ValidationContext(
            rows=self.rows,
            single_row=self.single_row,
            course=self.course,
            course_id=self.course_id,
            submission_id=self.submission_id,
            approved_intake=self.approved_intake,
            approved_supernumerary=self.approved_supernumerary,
            institution_id=self.institution_id,
            academic_year=self.academic_year,
            declared_seats=self.declared_seats,
            history_students=self.history_students,
            all_college_students=self.all_college_students,
            other_college_students=self.other_college_students,
            file_metadata=self.file_metadata,
            apaar_client=self.apaar_client,
            aicte_client=self.aicte_client,
            db_session=self.db_session,
            rule_configs=self.rule_configs,
            params=params,
            apaar_cache=self.apaar_cache,
            extra=self.extra,
        )
