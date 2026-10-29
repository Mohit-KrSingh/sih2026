"""Validation engine execution pipeline, scope ordering, and override handling."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import RuleConfig
from app.validation.context import RuleConfigOverride, ValidationContext, load_rule_config_overrides
from app.validation.flags import Flag, ValidationLevel, ValidationResult, ValidationScope
from app.validation.registry import BaseRule, rule_registry

# Evaluation scope order per SPEC.md Section 9.4:
# Cheap checks first: file, then field/row, then duplicates/course, then cross, then anomalies.
SCOPE_ORDER: dict[str, int] = {
    ValidationScope.FILE.value: 10,
    ValidationScope.ROW.value: 20,
    ValidationScope.COURSE.value: 30,
    ValidationScope.CROSS.value: 40,
    ValidationScope.ANOMALY.value: 50,
}


def _normalize_overrides(
    overrides: dict[str, Any] | None = None,
    db_session: Session | None = None,
    context_configs: dict[str, Any] | None = None,
) -> dict[str, RuleConfigOverride]:
    """Resolve and normalize rule overrides from DB, parameter, or context."""
    resolved: dict[str, RuleConfigOverride] = {}

    if db_session is not None:
        resolved.update(load_rule_config_overrides(db_session))

    if context_configs:
        for code, item in context_configs.items():
            if isinstance(item, RuleConfigOverride):
                resolved[code] = item
            elif isinstance(item, RuleConfig):
                resolved[code] = RuleConfigOverride.from_model(item)
            elif isinstance(item, dict):
                resolved[code] = RuleConfigOverride.from_dict({**item, "rule_code": code})

    if overrides:
        for code, item in overrides.items():
            if isinstance(item, RuleConfigOverride):
                resolved[code] = item
            elif isinstance(item, RuleConfig):
                resolved[code] = RuleConfigOverride.from_model(item)
            elif isinstance(item, dict):
                resolved[code] = RuleConfigOverride.from_dict({**item, "rule_code": code})

    return resolved


def apply_rule_override(flag: Flag, override: RuleConfigOverride) -> Flag:
    """Apply level and justification overrides to an emitted flag."""
    if override.level:
        target_level = override.level.lower()
        object.__setattr__(flag, "level", target_level)

        # Enforce SPEC.md Section 9.1 justification rules
        if target_level == ValidationLevel.EXCEPTION.value:
            object.__setattr__(flag, "requires_justification", True)
        elif target_level in (ValidationLevel.ERROR.value, ValidationLevel.INFO.value):
            object.__setattr__(flag, "requires_justification", False)

    return flag


def run_rules(
    context: ValidationContext,
    rules: list[BaseRule | str] | None = None,
    scope: ValidationScope | str | None = None,
    overrides: dict[str, Any] | None = None,
    db_session: Session | None = None,
) -> ValidationResult:
    """Execute validation rules against the context with overrides and scope handling.

    Per SPEC.md Section 9.1 & 9.2:
    - Pure check execution with no hidden side effects.
    - Evaluates registered rules or explicitly passed rules.
    - Applies policy level and parameter overrides from rule_config.
    - Skips disabled rules.
    - Returns a ValidationResult (subclass of list[Flag]).
    """
    # 1. Resolve active overrides and ensure db_session in context if supplied
    if db_session is not None and context.db_session is None:
        context.db_session = db_session

    active_overrides = _normalize_overrides(
        overrides=overrides,
        db_session=db_session,
        context_configs=context.rule_configs,
    )

    # 2. Determine rules to run
    rules_to_run: list[BaseRule] = []
    if rules is not None:
        for r in rules:
            if isinstance(r, BaseRule):
                rules_to_run.append(r)
            elif isinstance(r, str):
                registered = rule_registry.get(r)
                if registered:
                    rules_to_run.append(registered)
    else:
        # Load from registry, optionally filtered by scope
        rules_to_run = rule_registry.list_rules(scope=scope)

    # 3. Filter by scope if explicit scope filter provided on an explicit rule list
    if scope is not None and rules is not None:
        target_scope = scope.value if isinstance(scope, ValidationScope) else str(scope).lower()
        rules_to_run = [
            r
            for r in rules_to_run
            if (r.scope.value if isinstance(r.scope, ValidationScope) else str(r.scope).lower())
            == target_scope
        ]

    # 4. Sort rules by SPEC.md Section 9.4 scope ordering
    def get_sort_key(rule: BaseRule) -> int:
        s_val = (
            rule.scope.value if isinstance(rule.scope, ValidationScope) else str(rule.scope).lower()
        )
        return SCOPE_ORDER.get(s_val, 99)

    rules_to_run.sort(key=get_sort_key)

    # 5. Execute rules sequentially
    collected_flags: list[Flag] = []

    for rule in rules_to_run:
        override = active_overrides.get(rule.code)

        # Check if rule is disabled in rule_config
        if override and not override.enabled:
            continue

        # Merge parameters (default_params overridden by context/config params)
        active_params = dict(rule.default_params)
        if context.params:
            active_params.update(context.params)
        if override and override.params:
            active_params.update(override.params)

        # Build context for this rule invocation
        rule_context = context.with_params(active_params)

        # Execute pure rule check
        flags = rule.check(rule_context)

        # Apply level overrides to generated flags
        if override and override.level:
            for flag in flags:
                apply_rule_override(flag, override)

        collected_flags.extend(flags)

    return ValidationResult(collected_flags)


# Convenience alias
run_validation = run_rules


def validate_rows(*args: Any, **kwargs: Any) -> Any:
    """Validate rows entry point (delegates to app.validation.service.validate_rows)."""
    from app.validation.service import validate_rows as _validate_rows

    return _validate_rows(*args, **kwargs)


def validate_course(*args: Any, **kwargs: Any) -> Any:
    """Validate course entry point (delegates to app.validation.service.validate_course)."""
    from app.validation.service import validate_course as _validate_course

    return _validate_course(*args, **kwargs)


def validate_submission(*args: Any, **kwargs: Any) -> Any:
    """Validate submission entry point (delegates to app.validation.service.validate_submission)."""
    from app.validation.service import validate_submission as _validate_submission

    return _validate_submission(*args, **kwargs)
