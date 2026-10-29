"""Submission lifecycle state machine and submit gate transition logic.

SPEC.md Section 10:
- Submission states (per college per academic year):
  draft -> submitted or submitted_with_exceptions -> under_review (only when exceptions
  or review-worthy warnings exist) -> accepted, query_raised, or escalated.
  After query_raised the college responds and it returns to under_review.

Final submit gate (college admin only):
- Any error flag open: Blocked, with the exact rows and fields to fix
- exception or justification-required warning flags without a justification: Blocked
- Only justified exceptions or warnings: Allowed. State: submitted_with_exceptions
- Nothing open: Allowed. State: submitted
- Declared seat counts differ from uploaded students: Blocked (SEAT_DECLARATION_MISMATCH)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SubmissionState(StrEnum):
    """Allowed submission lifecycle states."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    SUBMITTED_WITH_EXCEPTIONS = "submitted_with_exceptions"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    QUERY_RAISED = "query_raised"
    ESCALATED = "escalated"


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal lifecycle transition is attempted."""

    def __init__(self, from_state: str, to_state: str, reason: str | None = None) -> None:
        msg = f"Invalid submission state transition from '{from_state}' to '{to_state}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason


@dataclass(frozen=True)
class GateEvaluationResult:
    """Outcome of evaluating final submit gate criteria."""

    can_submit: bool
    target_state: SubmissionState | None
    situation: str
    reason: str
    blocker_reasons: list[str] = field(default_factory=list)


class SubmissionStateMachine:
    """Manages legal transitions and gate checks for institutional submissions."""

    # Explicit transition graph per SPEC.md Section 10
    TRANSITIONS: dict[SubmissionState, set[SubmissionState]] = {
        SubmissionState.DRAFT: {
            SubmissionState.SUBMITTED,
            SubmissionState.SUBMITTED_WITH_EXCEPTIONS,
        },
        SubmissionState.SUBMITTED_WITH_EXCEPTIONS: {
            SubmissionState.UNDER_REVIEW,
        },
        SubmissionState.SUBMITTED: {
            SubmissionState.ACCEPTED,
            SubmissionState.UNDER_REVIEW,
            SubmissionState.SUBMITTED_WITH_EXCEPTIONS,
        },
        SubmissionState.UNDER_REVIEW: {
            SubmissionState.ACCEPTED,
            SubmissionState.QUERY_RAISED,
            SubmissionState.ESCALATED,
        },
        SubmissionState.QUERY_RAISED: {
            SubmissionState.UNDER_REVIEW,
        },
        SubmissionState.ESCALATED: {
            SubmissionState.UNDER_REVIEW,
            SubmissionState.ACCEPTED,
        },
        SubmissionState.ACCEPTED: set(),  # Terminal state (revisions require change requests)
    }

    @classmethod
    def can_transition(
        cls,
        from_state: str | SubmissionState,
        to_state: str | SubmissionState,
    ) -> bool:
        """Check whether a transition between two states is permitted."""
        try:
            curr = SubmissionState(str(from_state).lower())
            target = SubmissionState(str(to_state).lower())
        except ValueError:
            return False

        allowed = cls.TRANSITIONS.get(curr, set())
        return target in allowed

    @classmethod
    def validate_transition(
        cls,
        from_state: str | SubmissionState,
        to_state: str | SubmissionState,
    ) -> None:
        """Enforce transition rules, raising InvalidStateTransitionError on violation."""
        curr_str = str(from_state).lower()
        target_str = str(to_state).lower()

        try:
            curr = SubmissionState(curr_str)
        except ValueError:
            raise InvalidStateTransitionError(
                from_state=curr_str,
                to_state=target_str,
                reason=f"'{curr_str}' is not a recognised submission state.",
            ) from None

        try:
            target = SubmissionState(target_str)
        except ValueError:
            raise InvalidStateTransitionError(
                from_state=curr_str,
                to_state=target_str,
                reason=f"'{target_str}' is not a recognised submission state.",
            ) from None

        allowed = cls.TRANSITIONS.get(curr, set())
        if target not in allowed:
            raise InvalidStateTransitionError(
                from_state=curr.value,
                to_state=target.value,
                reason=f"Legal transitions from '{curr.value}' are: {[s.value for s in allowed]}",
            )

    @classmethod
    def evaluate_gate(
        cls,
        *,
        open_error_count: int,
        unjustified_exception_count: int,
        unjustified_warning_count: int,
        seat_declaration_mismatch: bool,
        justified_exception_count: int = 0,
        justified_warning_count: int = 0,
        total_students: int = 0,
    ) -> GateEvaluationResult:
        """Evaluate the final submit gate according to SPEC.md Section 10 rules.

        Rules in priority order:
        1. Any open error flag -> Blocked.
        2. Seat declaration mismatch -> Blocked.
        3. Any unjustified exception -> Blocked.
        4. Any unjustified warning that requires justification -> Blocked.
        5. Justified exceptions or warnings exist -> Allowed, target is `submitted_with_exceptions`.
        6. Clean (no blockers, no exceptions) -> Allowed, target is `submitted`.
        """
        blockers: list[str] = []

        if open_error_count > 0:
            blockers.append(
                f"{open_error_count} data error(s) must be resolved in student or course records."
            )

        if seat_declaration_mismatch:
            blockers.append(
                "Declared seat counts differ from uploaded student records "
                "(SEAT_DECLARATION_MISMATCH)."
            )

        if unjustified_exception_count > 0:
            blockers.append(
                f"{unjustified_exception_count} compliance exception(s) "
                "require written justification."
            )

        if unjustified_warning_count > 0:
            blockers.append(
                f"{unjustified_warning_count} warning(s) require written justification."
            )

        if blockers:
            primary_reason = blockers[0]
            situation = "BLOCKED"
            if open_error_count > 0:
                situation = "OPEN_ERRORS"
            elif seat_declaration_mismatch:
                situation = "SEAT_DECLARATION_MISMATCH"
            elif unjustified_exception_count > 0:
                situation = "UNJUSTIFIED_EXCEPTIONS"
            elif unjustified_warning_count > 0:
                situation = "UNJUSTIFIED_WARNINGS"

            return GateEvaluationResult(
                can_submit=False,
                target_state=None,
                situation=situation,
                reason=primary_reason,
                blocker_reasons=blockers,
            )

        # Gate is passed: determine whether submitted clean or with exceptions
        has_exceptions = justified_exception_count > 0 or justified_warning_count > 0

        if has_exceptions:
            return GateEvaluationResult(
                can_submit=True,
                target_state=SubmissionState.SUBMITTED_WITH_EXCEPTIONS,
                situation="JUSTIFIED_EXCEPTIONS",
                reason=(
                    "All errors resolved and exceptions justified. "
                    "Ready for submission with exceptions."
                ),
                blocker_reasons=[],
            )

        return GateEvaluationResult(
            can_submit=True,
            target_state=SubmissionState.SUBMITTED,
            situation="CLEAN",
            reason="All student data and seat declarations valid. Ready for clean submission.",
            blocker_reasons=[],
        )
