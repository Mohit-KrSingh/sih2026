"""Rules documentation generator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Import rules package to ensure all rules are registered
import app.validation.rules  # noqa: F401
from app.validation.codes import RULE_CATALOGUE
from app.validation.engine import SCOPE_ORDER
from app.validation.flags import ValidationLevel, ValidationScope
from app.validation.registry import rule_registry


def format_params(params: dict[str, Any] | None) -> str:
    """Format default parameters into a clean string representation."""
    if not params:
        return "`None`"
    try:
        return f"`{json.dumps(params, ensure_ascii=False)}`"
    except Exception:
        return f"`{str(params)}`"


def generate_rules_doc(output_path: str | Path | None = None) -> str:
    """Generate Markdown documentation of all validation rules from the registry
    and metadata catalogue.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    target_path = Path(output_path) if output_path else repo_root / "docs" / "RULES.md"

    # Gather all registered rules
    registered_rules = {r.code: r for r in rule_registry.list_rules()}

    # Merge catalogue and registry
    all_codes = sorted(
        set(RULE_CATALOGUE.keys()).union(registered_rules.keys()),
        key=lambda c: (
            SCOPE_ORDER.get(
                (
                    registered_rules[c].scope.value
                    if c in registered_rules
                    and isinstance(registered_rules[c].scope, ValidationScope)
                    else str(
                        registered_rules[c].scope
                        if c in registered_rules
                        else RULE_CATALOGUE[c]["scope"]
                    ).lower()
                ),
                99,
            ),
            c,
        ),
    )

    # Calculate statistics
    total_rules = len(all_codes)
    scope_counts: dict[str, int] = {}
    level_counts: dict[str, int] = {}

    for code in all_codes:
        meta = RULE_CATALOGUE.get(code, {})
        reg = registered_rules.get(code)

        s_val = (
            reg.scope.value
            if reg and isinstance(reg.scope, ValidationScope)
            else str(reg.scope if reg else meta.get("scope", "row")).lower()
        )
        l_val = (
            reg.default_level.value
            if reg and isinstance(reg.default_level, ValidationLevel)
            else str(reg.default_level if reg else meta.get("default_level", "error")).lower()
        )

        scope_counts[s_val] = scope_counts.get(s_val, 0) + 1
        level_counts[l_val] = level_counts.get(l_val, 0) + 1

    lines: list[str] = [
        "# APAAR Validation Rules Catalogue",
        "",
        "> Automated generation from rule registry and contract specifications.",
        "> Source of truth: `SPEC.md` Section 9.3 & 9.4.",
        "",
        "## 1. Overview and Architecture",
        "",
        "The APAAR Student Data Validation Engine provides unified, automated validation",
        "across all channels (single student entry, CSV bulk upload, and automated API).",
        "",
        "### 1.1 Validation Scopes & Execution Order",
        "",
        "Per **SPEC.md Section 9.4**, rules execute following cheap-checks-first order:",
        (
            "1. **File Scope (`file`)**: Template validity, header checks, file size, empty rows, "
            "within-file duplicate APAAR and enrolment numbers."
        ),
        (
            "2. **Row Scope (`row`)**: Format checks, mandatory field presence, registry "
            "identity lookups (batched), and internal row consistency."
        ),
        (
            "3. **Course Scope (`course`)**: Approved intake quotas, supernumerary allowances, "
            "and college-declared seat counts."
        ),
        (
            "4. **Cross-College Scope (`cross`)**: Cross-institution concurrent active "
            "enrolments and identical course duplicate checks."
        ),
        (
            "5. **Anomaly Scope (`anomaly`)**: Statistical indicators, NRI/supernumerary spikes, "
            "date-of-birth clusters, sequential runs, and IsolationForest ML scoring."
        ),
        "",
        "### 1.2 Validation Levels & Submission Gate",
        "",
        "| Level | Meaning | Submission Gate Effect | Badge Presentation |",
        "|---|---|---|---|",
        (
            "| `error` | Data is wrong (typing or format mistake) | "
            "**Blocks submission** until corrected | Red filled badge |"
        ),
        (
            "| `exception` | Real-world compliance problem (e.g. over-intake) | "
            "**Permitted with written justification**; routed to AICTE review queue | "
            "Red outlined (2px) badge |"
        ),
        (
            "| `warning` | Suspicious but possibly legitimate | "
            "Permitted (justification if required) | Amber filled badge |"
        ),
        (
            "| `info` | Noteworthy observation | Informational only (no block, no justification) | "
            "Grey filled badge |"
        ),
        "",
        "### 1.3 Rule Catalogue Statistics",
        "",
        f"- **Total Rules Defined:** {total_rules}",
        f"- **Registered Active Rule Handlers:** {len(registered_rules)}",
        "- **Rules by Scope:** "
        + ", ".join(f"`{k}`: {v}" for k, v in sorted(scope_counts.items())),
        "- **Rules by Default Level:** "
        + ", ".join(f"`{k}`: {v}" for k, v in sorted(level_counts.items())),
        "",
        "---",
        "",
        "## 2. Summary Catalogue",
        "",
        (
            "| Rule Code | Scope | Default Level | Requires Justification | "
            "Meaning | Default Parameters |"
        ),
        "|---|---|---|---|---|---|",
    ]

    for code in all_codes:
        meta = RULE_CATALOGUE.get(code, {})
        reg = registered_rules.get(code)

        s_val = (
            reg.scope.value
            if reg and isinstance(reg.scope, ValidationScope)
            else str(reg.scope if reg else meta.get("scope", "row")).lower()
        )
        l_val = (
            reg.default_level.value
            if reg and isinstance(reg.default_level, ValidationLevel)
            else str(reg.default_level if reg else meta.get("default_level", "error")).lower()
        )

        requires_just = "Yes" if l_val == "exception" else "No"
        meaning = meta.get("meaning") or (reg.description if reg else "Validation rule")
        meaning = meaning.replace("\n", " ").strip()

        params = reg.default_params if reg else meta.get("default_params", {})
        param_str = format_params(params)

        lines.append(
            f"| `{code}` | `{s_val}` | `{l_val}` | {requires_just} | {meaning} | {param_str} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. Detailed Rule Specifications by Scope",
        "",
    ])

    # Group by scope
    scopes_ordered = [
        ("file", "File-Level Rules & Upload Integrity"),
        ("row", "Row-Level Format, Field & Identity Rules"),
        ("course", "Course Quotas, Intake & Seat Declarations"),
        ("cross", "Cross-College Duplicate Enrolments"),
        ("anomaly", "Intelligent Anomaly Detection & ML"),
    ]

    for scope_key, scope_title in scopes_ordered:
        scope_codes = [
            c
            for c in all_codes
            if (
                registered_rules[c].scope.value
                if c in registered_rules and isinstance(registered_rules[c].scope, ValidationScope)
                else str(
                    registered_rules[c].scope
                    if c in registered_rules
                    else RULE_CATALOGUE[c]["scope"]
                ).lower()
            )
            == scope_key
        ]
        if not scope_codes:
            continue

        lines.extend([
            f"### 3.{scopes_ordered.index((scope_key, scope_title)) + 1} {scope_title}",
            "",
        ])

        for code in scope_codes:
            meta = RULE_CATALOGUE.get(code, {})
            reg = registered_rules.get(code)
            l_val = (
                reg.default_level.value
                if reg and isinstance(reg.default_level, ValidationLevel)
                else str(reg.default_level if reg else meta.get("default_level", "error")).lower()
            )
            meaning = meta.get("meaning") or (reg.description if reg else "Validation check")
            params = reg.default_params if reg else meta.get("default_params", {})
            param_str = format_params(params)
            is_active = "Active" if reg else "Scheduled (T27)"

            req_just_str = "Yes" if l_val == "exception" else "No"
            lines.extend([
                f"#### `{code}`",
                "",
                f"- **Meaning:** {meaning}",
                f"- **Scope:** `{scope_key}`",
                f"- **Default Level:** `{l_val}`",
                f"- **Implementation Status:** {is_active}",
                f"- **Default Parameters:** {param_str}",
                f"- **Requires Justification on Exception:** {req_just_str}",
                "",
            ])

    lines.extend([
        "---",
        "",
        "## 4. Policy Configuration & Overrides",
        "",
        "Administrators (`aicte_admin`) can customize rule behavior at runtime via `rule_config`",
        "without deploying code changes:",
        (
            "- **Level Override**: Reassign a rule's severity level "
            "(e.g. promoting a `warning` to an `error`)."
        ),
        (
            "- **Parameter Customization**: Adjust numeric thresholds, admission date windows, "
            "age ranges, or fuzzy match ratios."
        ),
        "- **Enable/Disable**: Selectively disable specific rules for testing or policy shifts.",
        "",
    ])

    content = "\n".join(lines) + "\n"

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    return content


if __name__ == "__main__":
    generate_rules_doc()
    print("Successfully generated docs/RULES.md")
