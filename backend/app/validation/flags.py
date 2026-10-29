"""Validation engine data structures: Flag, Level, Scope, and Result."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ValidationLevel(StrEnum):
    """Validation severity levels per SPEC.md Section 9.1."""

    ERROR = "error"
    EXCEPTION = "exception"
    WARNING = "warning"
    INFO = "info"


class ValidationScope(StrEnum):
    """Validation rule evaluation scopes per SPEC.md Section 9.2 & 9.3."""

    FILE = "file"
    ROW = "row"
    COURSE = "course"
    CROSS = "cross"
    ANOMALY = "anomaly"


class ValidationAudience(StrEnum):
    """Target audience for validation flags per SPEC.md Section 9.2."""

    COLLEGE = "college"
    AICTE = "aicte"
    BOTH = "both"


@dataclass(slots=True)
class Flag:
    """A single validation flag emitted by a validation rule.

    Per SPEC.md Section 9.2:
    - rule_code: string code (e.g. 'APAAR_REQUIRED')
    - level: error | exception | warning | info
    - row_ref: optional row number (for uploads) or student_id (for persisted records)
    - field: optional field name (e.g. 'apaar_id', 'dob')
    - message: plain English explanation of what is wrong
    - fix_hint: plain English advice on how to fix
    - audience: college | aicte | both
    - requires_justification: whether submission can only proceed with written justification
    """

    rule_code: str
    level: str  # error | exception | warning | info
    message: str
    fix_hint: str | None = None
    field: str | None = None
    row_ref: int | str | None = None
    audience: str = "both"  # college | aicte | both
    requires_justification: bool = False

    def __post_init__(self) -> None:
        # Normalize level string
        if isinstance(self.level, ValidationLevel):
            object.__setattr__(self, "level", self.level.value)
        elif isinstance(self.level, str):
            object.__setattr__(self, "level", self.level.lower())

        # Normalize audience string
        if isinstance(self.audience, ValidationAudience):
            object.__setattr__(self, "audience", self.audience.value)
        elif isinstance(self.audience, str):
            object.__setattr__(self, "audience", self.audience.lower())

        # Enforce SPEC.md Section 9.1 justification defaults:
        # Exceptions always require justification.
        # Errors block submit and cannot be justified.
        # Infos are purely informational.
        if self.level == ValidationLevel.EXCEPTION.value and not self.requires_justification:
            object.__setattr__(self, "requires_justification", True)
        elif self.level in (ValidationLevel.ERROR.value, ValidationLevel.INFO.value):
            object.__setattr__(self, "requires_justification", False)

    def to_dict(self) -> dict[str, Any]:
        """Convert flag to dictionary suitable for JSON serialization and DB storage."""
        return {
            "rule_code": self.rule_code,
            "level": self.level,
            "row_ref": self.row_ref,
            "field": self.field,
            "message": self.message,
            "fix_hint": self.fix_hint,
            "audience": self.audience,
            "requires_justification": self.requires_justification,
        }


class ValidationResult(list[Flag]):
    """Ordered collection of flags emitted by validation engine with convenience helpers.

    Subclasses list[Flag] to ensure total backward compatibility with any
    consumer expecting a standard Python list.
    """

    def __init__(self, flags: list[Flag] | None = None) -> None:
        super().__init__(flags or [])

    @property
    def flags(self) -> list[Flag]:
        """Return raw list of flags."""
        return list(self)

    @property
    def errors(self) -> list[Flag]:
        """All error-level flags (data is wrong, blocks submit)."""
        return [f for f in self if f.level == ValidationLevel.ERROR.value]

    @property
    def exceptions(self) -> list[Flag]:
        """All exception-level flags (compliance issue, allowed with justification)."""
        return [f for f in self if f.level == ValidationLevel.EXCEPTION.value]

    @property
    def warnings(self) -> list[Flag]:
        """All warning-level flags (suspicious, allowed with optional justification)."""
        return [f for f in self if f.level == ValidationLevel.WARNING.value]

    @property
    def infos(self) -> list[Flag]:
        """All info-level flags (informational, no effect on submission)."""
        return [f for f in self if f.level == ValidationLevel.INFO.value]

    @property
    def is_valid(self) -> bool:
        """True if there are no error-level flags."""
        return len(self.errors) == 0

    @property
    def has_errors(self) -> bool:
        """True if any error-level flag exists."""
        return len(self.errors) > 0

    @property
    def has_exceptions(self) -> bool:
        """True if any exception-level flag exists."""
        return len(self.exceptions) > 0

    @property
    def has_warnings(self) -> bool:
        """True if any warning-level flag exists."""
        return len(self.warnings) > 0

    @property
    def can_submit(self) -> bool:
        """Per SPEC.md Section 9.1 & 10: submissions can proceed if there are zero errors.

        Exceptions require written justifications to be accepted by the gate.
        """
        return len(self.errors) == 0

    def by_level(self) -> dict[str, list[Flag]]:
        """Group flags by level name."""
        return {
            "error": self.errors,
            "exception": self.exceptions,
            "warning": self.warnings,
            "info": self.infos,
        }

    def by_row(self) -> dict[int | str, list[Flag]]:
        """Group flags by row reference."""
        grouped: dict[int | str, list[Flag]] = {}
        for f in self:
            if f.row_ref is not None:
                grouped.setdefault(f.row_ref, []).append(f)
        return grouped

    def by_rule(self) -> dict[str, list[Flag]]:
        """Group flags by rule code."""
        grouped: dict[str, list[Flag]] = {}
        for f in self:
            grouped.setdefault(f.rule_code, []).append(f)
        return grouped

    def to_dict(self) -> dict[str, Any]:
        """Serialize validation result with aggregate counts and flag payload."""
        return {
            "is_valid": self.is_valid,
            "can_submit": self.can_submit,
            "counts": {
                "error": len(self.errors),
                "exception": len(self.exceptions),
                "warning": len(self.warnings),
                "info": len(self.infos),
                "total": len(self),
            },
            "flags": [f.to_dict() for f in self],
        }
