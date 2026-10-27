"""Unit and integration tests for validation engine core (TASKS.md T12 & SPEC.md 9.1, 9.2).

Acceptance criteria:
- Flag, rule interface, registry, level handling, rule_config overrides, context objects, run_rules.
- Tests: registry lists rules, level override changes the output, disabled rules are skipped.
"""

from sqlalchemy.orm import Session

from app.models import RuleConfig
from app.validation import (
    BaseRule,
    Flag,
    RuleConfigOverride,
    RuleRegistry,
    ValidationAudience,
    ValidationContext,
    ValidationLevel,
    ValidationResult,
    ValidationScope,
    load_rule_config_overrides,
    run_rules,
)


class DummyApaarRequiredRule(BaseRule):
    """Test rule that checks for apaar_id presence."""

    code = "APAAR_REQUIRED"
    scope = ValidationScope.ROW
    default_level = ValidationLevel.ERROR
    default_params = {"allow_empty": False}
    description = "APAAR ID missing"

    def check(self, context: ValidationContext) -> list[Flag]:
        flags: list[Flag] = []
        allow_empty = context.get_param("allow_empty", False)
        for idx, row in enumerate(context.get_all_rows(), start=1):
            apaar = context.get_field_value(row, "apaar_id")
            if not apaar and not allow_empty:
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=context.get_field_value(row, "row_number", idx),
                        field="apaar_id",
                        message="APAAR ID missing",
                        fix_hint="Enter a valid 12-digit APAAR ID",
                        audience=ValidationAudience.COLLEGE.value,
                    )
                )
        return flags


class DummyFileTemplateRule(BaseRule):
    """Test rule for file scope."""

    code = "FILE_TEMPLATE"
    scope = ValidationScope.FILE
    default_level = ValidationLevel.ERROR
    default_params = {"required_columns": ["apaar_id", "name"]}
    description = "Wrong or missing columns"

    def check(self, context: ValidationContext) -> list[Flag]:
        headers = context.file_metadata.get("headers", [])
        required = context.get_param("required_columns", ["apaar_id", "name"])
        missing = [c for c in required if c not in headers]
        if missing:
            return [
                Flag(
                    rule_code=self.code,
                    level=self.default_level,
                    field=None,
                    message=f"Missing required columns: {', '.join(missing)}",
                    fix_hint="Download the standard CSV template and re-upload",
                    audience=ValidationAudience.COLLEGE.value,
                )
            ]
        return []


class DummyIntakeExceededRule(BaseRule):
    """Test rule for course scope emitting exceptions."""

    code = "INTAKE_EXCEEDED"
    scope = ValidationScope.COURSE
    default_level = ValidationLevel.EXCEPTION
    default_params = {}
    description = "Regular admitted is above approved intake"

    def check(self, context: ValidationContext) -> list[Flag]:
        approved = context.approved_intake or 0
        regular_count = sum(
            1
            for r in context.get_all_rows()
            if context.get_field_value(r, "seat_type", "Regular") == "Regular"
        )
        if regular_count > approved:
            overshoot = regular_count - approved
            return [
                Flag(
                    rule_code=self.code,
                    level=self.default_level,
                    field="approved_intake",
                    message=(
                        f"Admitted regular students ({regular_count}) exceeds "
                        f"approved intake ({approved}) by {overshoot}"
                    ),
                    fix_hint="Submit justification or file an intake correction request",
                    audience=ValidationAudience.BOTH.value,
                    requires_justification=True,
                )
            ]
        return []


class DummyFuzzyNameRule(BaseRule):
    """Test rule with configurable threshold parameter."""

    code = "APAAR_NAME_MISMATCH"
    scope = ValidationScope.ROW
    default_level = ValidationLevel.WARNING
    default_params = {"threshold": 85}
    description = "Fuzzy name match below threshold"

    def check(self, context: ValidationContext) -> list[Flag]:
        threshold = context.get_param("threshold", 85)
        flags: list[Flag] = []
        for idx, row in enumerate(context.get_all_rows(), start=1):
            score = context.get_field_value(row, "score", 100)
            if score < threshold:
                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=context.get_field_value(row, "row_number", idx),
                        field="name",
                        message=f"Name similarity score {score} is below threshold {threshold}",
                        fix_hint="Verify spelling against student's official APAAR card",
                        audience=ValidationAudience.BOTH.value,
                        requires_justification=False,
                    )
                )
        return flags


def test_flag_data_structure_and_serialization() -> None:
    """Test Flag attributes, normalization, and dictionary serialization."""
    flag = Flag(
        rule_code="APAAR_REQUIRED",
        level="error",
        message="APAAR ID is missing",
        fix_hint="Enter a 12-digit number",
        field="apaar_id",
        row_ref=5,
        audience="college",
    )

    assert flag.rule_code == "APAAR_REQUIRED"
    assert flag.level == "error"
    assert flag.requires_justification is False
    assert flag.audience == "college"

    payload = flag.to_dict()
    assert payload["rule_code"] == "APAAR_REQUIRED"
    assert payload["level"] == "error"
    assert payload["row_ref"] == 5
    assert payload["field"] == "apaar_id"
    assert payload["message"] == "APAAR ID is missing"
    assert payload["fix_hint"] == "Enter a 12-digit number"
    assert payload["audience"] == "college"
    assert payload["requires_justification"] is False


def test_flag_justification_rules_per_spec() -> None:
    """Test that SPEC.md Section 9.1 justification defaults are enforced."""
    # Exception defaults to requires_justification=True
    exc_flag = Flag(
        rule_code="INTAKE_EXCEEDED",
        level=ValidationLevel.EXCEPTION,
        message="Over intake",
    )
    assert exc_flag.level == "exception"
    assert exc_flag.requires_justification is True

    # Error defaults to requires_justification=False (must be fixed, cannot be justified)
    err_flag = Flag(
        rule_code="APAAR_FORMAT",
        level=ValidationLevel.ERROR,
        message="Invalid format",
        requires_justification=True,  # Should be normalized to False
    )
    assert err_flag.requires_justification is False

    # Warning respects explicit justification requirement
    warn_flag = Flag(
        rule_code="APAAR_NAME_MISMATCH",
        level=ValidationLevel.WARNING,
        message="Minor mismatch",
        requires_justification=True,
    )
    assert warn_flag.requires_justification is True


def test_rule_registry_registration_and_listing() -> None:
    """Test that registry properly registers, lists, gets, and filters rules by scope."""
    registry = RuleRegistry()

    rule1 = DummyApaarRequiredRule()
    rule2 = DummyFileTemplateRule()
    rule3 = DummyIntakeExceededRule()

    registry.register(rule1)
    registry.register(rule2)
    registry.register(rule3)

    # 1. Test listing all rules
    all_rules = registry.list_rules()
    assert len(all_rules) == 3
    assert set(registry.list_codes()) == {"APAAR_REQUIRED", "FILE_TEMPLATE", "INTAKE_EXCEEDED"}

    # 2. Test get by code
    fetched = registry.get("APAAR_REQUIRED")
    assert fetched is not None
    assert fetched.code == "APAAR_REQUIRED"
    assert fetched.scope == ValidationScope.ROW

    assert registry.get("NON_EXISTENT") is None

    # 3. Test filtering by scope
    row_rules = registry.list_rules(scope=ValidationScope.ROW)
    assert len(row_rules) == 1
    assert row_rules[0].code == "APAAR_REQUIRED"

    file_rules = registry.list_rules(scope="file")
    assert len(file_rules) == 1
    assert file_rules[0].code == "FILE_TEMPLATE"

    # 4. Test clearing registry
    registry.clear()
    assert len(registry.list_rules()) == 0


def test_functional_rule_registration() -> None:
    """Test registering pure function check with decorator."""
    registry = RuleRegistry()

    @registry.register(
        code="CUSTOM_CHECK",
        scope=ValidationScope.ROW,
        default_level=ValidationLevel.WARNING,
        default_params={"max_len": 50},
    )
    def my_check(ctx: ValidationContext) -> list[Flag]:
        """Custom check docstring."""
        return [
            Flag(
                rule_code="CUSTOM_CHECK",
                level="warning",
                message="Custom warning",
            )
        ]

    rule = registry.get("CUSTOM_CHECK")
    assert rule is not None
    assert rule.code == "CUSTOM_CHECK"
    assert rule.scope == "row"
    assert rule.default_level == "warning"
    assert rule.default_params == {"max_len": 50}
    assert "Custom check docstring" in rule.description

    ctx = ValidationContext()
    flags = rule.check(ctx)
    assert len(flags) == 1
    assert flags[0].rule_code == "CUSTOM_CHECK"


def test_run_rules_basic_execution() -> None:
    """Test running rules against a context with valid and invalid rows."""
    rules = [DummyApaarRequiredRule(), DummyIntakeExceededRule()]

    ctx = ValidationContext(
        rows=[
            {"row_number": 1, "apaar_id": "123456789012", "seat_type": "Regular"},
            {"row_number": 2, "apaar_id": "", "seat_type": "Regular"},
        ],
        approved_intake=5,
    )

    result = run_rules(ctx, rules=rules)
    assert isinstance(result, list)
    assert isinstance(result, ValidationResult)
    assert len(result) == 1
    assert result[0].rule_code == "APAAR_REQUIRED"
    assert result[0].row_ref == 2
    assert result[0].level == "error"
    assert result.has_errors is True
    assert result.is_valid is False
    assert result.can_submit is False


def test_level_override_changes_output() -> None:
    """Acceptance criteria: level override changes the output."""
    rules = [DummyApaarRequiredRule()]

    ctx = ValidationContext(rows=[{"row_number": 1, "apaar_id": ""}])

    # Default level is 'error'
    default_result = run_rules(ctx, rules=rules)
    assert len(default_result) == 1
    assert default_result[0].level == "error"
    assert default_result[0].requires_justification is False
    assert default_result.can_submit is False

    # Override level to 'exception'
    # Per SPEC.md Section 9.1: exception goes to review queue and requires justification
    override_result = run_rules(
        ctx,
        rules=rules,
        overrides={"APAAR_REQUIRED": {"level": "exception"}},
    )
    assert len(override_result) == 1
    assert override_result[0].level == "exception"
    assert override_result[0].requires_justification is True
    assert override_result.has_exceptions is True
    assert override_result.has_errors is False
    assert override_result.can_submit is True  # Allowed with justification

    # Override level to 'warning'
    warn_result = run_rules(
        ctx,
        rules=rules,
        overrides={
            "APAAR_REQUIRED": RuleConfigOverride(rule_code="APAAR_REQUIRED", level="warning")
        },
    )
    assert len(warn_result) == 1
    assert warn_result[0].level == "warning"


def test_disabled_rules_are_skipped() -> None:
    """Acceptance criteria: disabled rules are skipped."""
    rules = [DummyApaarRequiredRule(), DummyFileTemplateRule()]

    ctx = ValidationContext(
        rows=[{"row_number": 1, "apaar_id": ""}],  # violates APAAR_REQUIRED
        file_metadata={"headers": ["extra"]},  # violates FILE_TEMPLATE
    )

    # Both fire by default
    both_result = run_rules(ctx, rules=rules)
    assert len(both_result) == 2
    rule_codes = {f.rule_code for f in both_result}
    assert rule_codes == {"APAAR_REQUIRED", "FILE_TEMPLATE"}

    # Disable APAAR_REQUIRED
    skipped_result = run_rules(
        ctx,
        rules=rules,
        overrides={"APAAR_REQUIRED": {"enabled": False}},
    )
    assert len(skipped_result) == 1
    assert skipped_result[0].rule_code == "FILE_TEMPLATE"

    # Disable both
    all_disabled_result = run_rules(
        ctx,
        rules=rules,
        overrides={
            "APAAR_REQUIRED": RuleConfigOverride(rule_code="APAAR_REQUIRED", enabled=False),
            "FILE_TEMPLATE": RuleConfigOverride(rule_code="FILE_TEMPLATE", enabled=False),
        },
    )
    assert len(all_disabled_result) == 0


def test_parameter_override_modifies_rule_behaviour() -> None:
    """Test that policy parameter overrides change rule thresholds."""
    rules = [DummyFuzzyNameRule()]

    # Student has similarity score of 80 (below default threshold 85, above lowered threshold 75)
    ctx = ValidationContext(rows=[{"row_number": 1, "score": 80}])

    # Under default threshold 85 -> triggers warning
    res_default = run_rules(ctx, rules=rules)
    assert len(res_default) == 1
    assert res_default[0].rule_code == "APAAR_NAME_MISMATCH"

    # Override threshold to 75 -> passes without flags
    res_lowered = run_rules(
        ctx,
        rules=rules,
        overrides={"APAAR_NAME_MISMATCH": {"params": {"threshold": 75}}},
    )
    assert len(res_lowered) == 0

    # Override threshold to 90 -> fails with updated message
    res_raised = run_rules(
        ctx,
        rules=rules,
        overrides={"APAAR_NAME_MISMATCH": {"params": {"threshold": 90}}},
    )
    assert len(res_raised) == 1
    assert "below threshold 90" in res_raised[0].message


def test_validation_context_helpers() -> None:
    """Test ValidationContext accessor methods and immutable copying."""
    ctx = ValidationContext(
        rows=[{"apaar_id": "111122223333", "name": "Rahul"}],
        course={"id": 1, "name": "Computer Science"},
        approved_intake=60,
        approved_supernumerary=6,
        institution_id=10,
        academic_year="2026-27",
        declared_seats={"regular": 60, "supernumerary": 6},
        extra={"custom_key": "custom_val"},
    )

    assert len(ctx.get_all_rows()) == 1
    assert ctx.get_field_value(ctx.rows[0], "apaar_id") == "111122223333"
    assert ctx.approved_intake == 60
    assert ctx.academic_year == "2026-27"
    assert ctx.extra["custom_key"] == "custom_val"

    # Test single_row fallback
    single_ctx = ValidationContext(single_row={"apaar_id": "999988887777"})
    assert len(single_ctx.get_all_rows()) == 1
    assert single_ctx.get_all_rows()[0]["apaar_id"] == "999988887777"

    # Test with_params shallow copy
    updated = ctx.with_params({"threshold": 95})
    assert updated.params["threshold"] == 95
    assert ctx.params == {}  # Original untouched


def test_validation_result_aggregates_and_serialization() -> None:
    """Test ValidationResult classification and summary dict."""
    flags = [
        Flag("APAAR_REQUIRED", "error", "Missing APAAR", row_ref=1),
        Flag("INTAKE_EXCEEDED", "exception", "Intake exceeded by 2", field="intake"),
        Flag("APAAR_NAME_MISMATCH", "warning", "Spelling variant", row_ref=2),
        Flag("ANOM_SAME_ADMISSION_DAY", "info", "Cluster of dates"),
    ]

    result = ValidationResult(flags)
    assert len(result) == 4
    assert len(result.errors) == 1
    assert len(result.exceptions) == 1
    assert len(result.warnings) == 1
    assert len(result.infos) == 1

    assert result.has_errors is True
    assert result.has_exceptions is True
    assert result.has_warnings is True
    assert result.is_valid is False
    assert result.can_submit is False

    by_level = result.by_level()
    assert len(by_level["error"]) == 1
    assert len(by_level["exception"]) == 1

    by_row = result.by_row()
    assert 1 in by_row
    assert 2 in by_row

    summary = result.to_dict()
    assert summary["counts"]["total"] == 4
    assert summary["counts"]["error"] == 1
    assert summary["counts"]["exception"] == 1
    assert summary["is_valid"] is False
    assert len(summary["flags"]) == 4


def test_scope_ordering_execution() -> None:
    """Test that rules execute in SPEC.md Section 9.4 cheap-checks-first order."""
    execution_order: list[str] = []

    class OrderFileRule(BaseRule):
        code = "ORDER_FILE"
        scope = ValidationScope.FILE
        default_level = ValidationLevel.ERROR

        def check(self, ctx: ValidationContext) -> list[Flag]:
            execution_order.append("file")
            return []

    class OrderRowRule(BaseRule):
        code = "ORDER_ROW"
        scope = ValidationScope.ROW
        default_level = ValidationLevel.ERROR

        def check(self, ctx: ValidationContext) -> list[Flag]:
            execution_order.append("row")
            return []

    class OrderCourseRule(BaseRule):
        code = "ORDER_COURSE"
        scope = ValidationScope.COURSE
        default_level = ValidationLevel.EXCEPTION

        def check(self, ctx: ValidationContext) -> list[Flag]:
            execution_order.append("course")
            return []

    class OrderAnomalyRule(BaseRule):
        code = "ORDER_ANOMALY"
        scope = ValidationScope.ANOMALY
        default_level = ValidationLevel.WARNING

        def check(self, ctx: ValidationContext) -> list[Flag]:
            execution_order.append("anomaly")
            return []

    # Provide rules in reverse order
    reversed_rules = [OrderAnomalyRule(), OrderCourseRule(), OrderRowRule(), OrderFileRule()]
    run_rules(ValidationContext(), rules=reversed_rules)

    # Order must be file -> row -> course -> anomaly
    assert execution_order == ["file", "row", "course", "anomaly"]


def test_db_rule_config_overrides(db_session: Session) -> None:
    """Test loading and applying RuleConfig records directly from PostgreSQL."""
    # Clean any prior override for APAAR_REQUIRED
    db_session.query(RuleConfig).filter(RuleConfig.rule_code == "APAAR_REQUIRED").delete()
    db_session.flush()

    override_record = RuleConfig(
        rule_code="APAAR_REQUIRED",
        level="warning",  # overridden from error to warning
        params_json={"allow_empty": True},  # overridden to allow empty
        enabled=True,
    )
    db_session.add(override_record)
    db_session.commit()

    # Verify load_rule_config_overrides helper
    overrides_map = load_rule_config_overrides(db_session)
    assert "APAAR_REQUIRED" in overrides_map
    loaded_override = overrides_map["APAAR_REQUIRED"]
    assert loaded_override.level == "warning"
    assert loaded_override.params == {"allow_empty": True}
    assert loaded_override.enabled is True

    # Test run_rules with db_session parameter
    ctx = ValidationContext(rows=[{"row_number": 1, "apaar_id": ""}])
    result = run_rules(ctx, rules=[DummyApaarRequiredRule()], db_session=db_session)

    # Since allow_empty is overridden to True in DB, zero flags should be emitted!
    assert len(result) == 0

    # Now change DB config to disabled
    override_record.enabled = False
    override_record.params_json = {"allow_empty": False}
    db_session.commit()

    result_disabled = run_rules(ctx, rules=[DummyApaarRequiredRule()], db_session=db_session)
    assert len(result_disabled) == 0  # Skipped because enabled is False

    # Clean up test row
    db_session.delete(override_record)
    db_session.commit()
