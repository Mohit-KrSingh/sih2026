"""Validation rule: ANOM_MODEL_SCORE."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models import AnomalyScore
from app.validation.codes import ANOM_MODEL_SCORE
from app.validation.context import ValidationContext
from app.validation.flags import Flag, ValidationAudience, ValidationLevel, ValidationScope
from app.validation.registry import BaseRule, register_rule
from app.validation.rules.anomaly_helpers import extract_course_anomaly_features
from app.validation.rules.course_helpers import get_course_student_counts


@register_rule
class AnomModelScoreRule(BaseRule):
    """Flags when an IsolationForest model detects unusual multi-dimensional course deviations."""

    code: str = ANOM_MODEL_SCORE
    scope: ValidationScope = ValidationScope.ANOMALY
    default_level: ValidationLevel = ValidationLevel.WARNING
    default_params: dict[str, Any] = {"threshold_score": -0.05, "contamination": 0.08}
    description: str = (
        "IsolationForest score on college-course features flags this as unusual. Audience: aicte"
    )

    def check(self, context: ValidationContext) -> list[Flag]:
        from app.analytics.anomaly_service import (
            evaluate_course_features,
            feature_dict_to_vector,
            fit_isolation_forest,
        )

        flags: list[Flag] = []
        course_groups = get_course_student_counts(context)
        threshold_score = float(context.get_param("threshold_score", -0.05))
        contamination = float(context.get_param("contamination", 0.08))

        # Check for precomputed anomaly scores passed in context.extra
        precomputed_scores: dict[int, Any] = context.extra.get("anomaly_scores", {})

        for _group_key, counts in course_groups.items():
            active_rows = counts.active_rows
            if not active_rows:
                continue

            course_id = counts.course_id
            academic_year = context.academic_year

            score_val: float | None = None
            is_flagged: bool = False
            summary_msg: str | None = None

            # 1. Check precomputed in context.extra
            if course_id is not None and course_id in precomputed_scores:
                item = precomputed_scores[course_id]
                score_raw = getattr(item, "score", None)
                if score_raw is None and isinstance(item, dict):
                    score_raw = item.get("score", 0.0)
                score_val = float(score_raw or 0.0)

                flagged_raw = getattr(item, "flagged", None)
                if flagged_raw is None and isinstance(item, dict):
                    flagged_raw = item.get("flagged", False)
                is_flagged = bool(flagged_raw)

                feats_raw = getattr(item, "features_json", None)
                if feats_raw is None and isinstance(item, dict):
                    feats_raw = item.get("features_json", {})
                feats = feats_raw or {}
                summary_msg = feats.get("summary") if isinstance(feats, dict) else None

            # 2. Check precomputed in database
            elif context.db_session is not None and course_id is not None and academic_year:
                db_anom = context.db_session.scalar(
                    select(AnomalyScore).where(
                        AnomalyScore.course_id == course_id,
                        AnomalyScore.academic_year == academic_year,
                    )
                )
                if db_anom:
                    score_val = float(db_anom.score)
                    is_flagged = bool(db_anom.flagged)
                    feats = db_anom.features_json or {}
                    summary_msg = feats.get("summary")

            # 3. Dynamic evaluation on the fly (requires at least 5 active students)
            if score_val is None:
                if len(active_rows) < 5:
                    continue
                feats = extract_course_anomaly_features(counts, context)
                vec = feature_dict_to_vector(feats)
                model = fit_isolation_forest([vec], contamination=contamination)
                score_val, is_flagged, summary_msg = evaluate_course_features(
                    model=model,
                    feature_dict=feats,
                    threshold_score=threshold_score,
                )

            if is_flagged:
                course_desc = (
                    f" for course '{counts.course_name}'" if counts.course_name else ""
                )
                msg = summary_msg or (
                    f"IsolationForest anomaly model flagged unusual profile{course_desc} "
                    f"(score: {score_val:.3f})."
                )
                fix_hint = (
                    "Conduct holistic institutional review regarding multi-dimensional "
                    "admission deviations."
                )

                row_ref: int | str | None = None
                if counts.course_id is not None:
                    row_ref = counts.course_id
                elif counts.course_name is not None:
                    row_ref = counts.course_name

                flags.append(
                    Flag(
                        rule_code=self.code,
                        level=self.default_level,
                        row_ref=row_ref,
                        field="model_score",
                        message=msg,
                        fix_hint=fix_hint,
                        audience=ValidationAudience.AICTE.value,
                        requires_justification=False,
                    )
                )

        return flags


rule = AnomModelScoreRule()
code = rule.code
scope = rule.scope
default_level = rule.default_level
default_params = rule.default_params
check = rule.check
