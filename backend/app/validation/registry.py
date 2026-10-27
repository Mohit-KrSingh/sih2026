"""Rule interface, registry, and rule registration decorator."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationLevel, ValidationScope


class BaseRule(ABC):
    """Abstract base class for all validation rules per SPEC.md Section 9.2.

    Each rule exposes:
    - code (string constant)
    - scope (file | row | course | cross | anomaly)
    - default_level (error | exception | warning | info)
    - default_params (dict of parameters)
    - check(context) -> list[Flag]: pure, no hidden side effects
    """

    code: str
    scope: ValidationScope | str
    default_level: ValidationLevel | str
    default_params: dict[str, Any] = {}
    description: str = ""

    @abstractmethod
    def check(self, context: ValidationContext) -> list[Flag]:
        """Execute pure validation logic on the given context and return emitted flags."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Rule {self.code} [{self.scope}] default={self.default_level}>"


class FunctionalRule(BaseRule):
    """Wraps a pure function check(context) -> list[Flag] as a Rule instance."""

    def __init__(
        self,
        check_func: Callable[[ValidationContext], list[Flag]],
        code: str,
        scope: ValidationScope | str,
        default_level: ValidationLevel | str,
        default_params: dict[str, Any] | None = None,
        description: str = "",
    ) -> None:
        self._check_func = check_func
        self.code = code
        self.scope = scope if isinstance(scope, str) else scope.value
        self.default_level = (
            default_level if isinstance(default_level, str) else default_level.value
        )
        self.default_params = default_params or {}
        self.description = description or getattr(check_func, "__doc__", "") or ""

    def check(self, context: ValidationContext) -> list[Flag]:
        return self._check_func(context)


class RuleRegistry:
    """Registry maintaining all available validation rules."""

    def __init__(self) -> None:
        self._rules: dict[str, BaseRule] = {}

    def register(
        self,
        rule_or_cls: Any = None,
        *,
        code: str | None = None,
        scope: ValidationScope | str | None = None,
        default_level: ValidationLevel | str | None = None,
        default_params: dict[str, Any] | None = None,
        description: str = "",
    ) -> Any:
        """Register a rule instance, rule class, or rule function.

        Can be used as:
        1. Direct registration: `registry.register(MyRule())`
        2. Class decorator:
           @registry.register
           class MyRule(BaseRule): ...
        3. Function decorator:
           @registry.register(code="CODE", scope="row", default_level="error")
           def check_something(context: ValidationContext) -> list[Flag]: ...
        """

        def decorator(target: Any) -> Any:
            # If target is a class inheriting from BaseRule
            if inspect.isclass(target) and issubclass(target, BaseRule):
                instance = target()
                self._rules[instance.code] = instance
                return target

            # If target is a pure function
            if callable(target):
                if not code or not scope or not default_level:
                    raise ValueError(
                        "code, scope, and default_level are required when registering a function"
                    )
                rule_instance = FunctionalRule(
                    check_func=target,
                    code=code,
                    scope=scope,
                    default_level=default_level,
                    default_params=default_params or {},
                    description=description or target.__doc__ or "",
                )
                self._rules[code] = rule_instance
                return target

            raise TypeError(f"Cannot register target of type {type(target)}")

        # Handle direct registration of an instance
        if rule_or_cls is not None:
            if isinstance(rule_or_cls, BaseRule):
                self._rules[rule_or_cls.code] = rule_or_cls
                return rule_or_cls
            if inspect.isclass(rule_or_cls) and issubclass(rule_or_cls, BaseRule):
                instance = rule_or_cls()
                self._rules[instance.code] = instance
                return rule_or_cls
            # Direct functional target without parens (not typical if kwargs missing)
            return decorator(rule_or_cls)

        # Invoked with decorator arguments @registry.register(...)
        return decorator

    def get(self, code: str) -> BaseRule | None:
        """Retrieve a registered rule by its unique code."""
        return self._rules.get(code)

    def list_rules(self, scope: ValidationScope | str | None = None) -> list[BaseRule]:
        """List registered rules, optionally filtered by scope."""
        if scope is None:
            return list(self._rules.values())

        scope_val = scope.value if isinstance(scope, ValidationScope) else str(scope).lower()
        return [
            r
            for r in self._rules.values()
            if (r.scope.value if isinstance(r.scope, ValidationScope) else str(r.scope).lower())
            == scope_val
        ]

    def list_codes(self) -> list[str]:
        """Return list of all registered rule codes."""
        return list(self._rules.keys())

    def clear(self) -> None:
        """Clear all registered rules."""
        self._rules.clear()

    def auto_discover(self, package_name: str = "app.validation.rules") -> None:
        """Discover and import all rule modules from the specified package."""
        try:
            package = importlib.import_module(package_name)
        except ModuleNotFoundError:
            return

        if not hasattr(package, "__path__"):
            return

        for _, modname, _ in pkgutil.iter_modules(package.__path__):
            full_name = f"{package_name}.{modname}"
            importlib.import_module(full_name)


# Global singleton registry instance
rule_registry = RuleRegistry()


def register_rule(
    rule_or_cls: Any = None,
    *,
    code: str | None = None,
    scope: ValidationScope | str | None = None,
    default_level: ValidationLevel | str | None = None,
    default_params: dict[str, Any] | None = None,
    description: str = "",
) -> Any:
    """Convenience alias for rule_registry.register."""
    return rule_registry.register(
        rule_or_cls,
        code=code,
        scope=scope,
        default_level=default_level,
        default_params=default_params,
        description=description,
    )
