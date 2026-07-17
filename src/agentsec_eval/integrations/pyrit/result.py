"""Project-owned result contracts for one PyRIT Attack Policy execution."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    JsonValue,
    NonNegativeInt,
    PositiveInt,
    StringConstraints,
    model_validator,
)

from agentsec_eval.assertions import ProgressDecision, ProgressState

_NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PyRITOutcome = Literal["success", "failure", "error"]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AttackPolicyStopReason(StrEnum):
    """Why one bounded Attack Policy stopped."""

    OBJECTIVE_ACHIEVED = "objective_achieved"
    TERMINAL_BLOCKED = "terminal_blocked"
    INVALID_RUN = "invalid_run"
    BUDGET_EXHAUSTED = "budget_exhausted"
    TARGET_ERROR = "target_error"
    POLICY_ERROR = "policy_error"
    CANCELLED = "cancelled"


class AttackPolicyTurnRecord(_FrozenModel):
    """Trusted record of one completed project-controlled attack turn."""

    turn: PositiveInt
    adversarial_prompt: str
    target_response: str
    target_session_id: _NonEmptyText
    target_turn: PositiveInt
    objective_conversation_id: _NonEmptyText
    score_value: bool
    score_rationale: str
    progress_decision: ProgressDecision


class AttackPolicyResult(_FrozenModel):
    """Non-authoritative result of one Attack Policy execution."""

    run_id: _NonEmptyText
    policy_name: _NonEmptyText
    policy_version: _NonEmptyText
    turns_executed: NonNegativeInt
    stop_reason: AttackPolicyStopReason
    final_progress_decision: ProgressDecision | None
    objective_conversation_id: _NonEmptyText | None
    adversarial_conversation_id: _NonEmptyText | None
    turn_records: tuple[AttackPolicyTurnRecord, ...] = ()
    pyrit_outcome: PyRITOutcome
    pyrit_result_ref: _NonEmptyText | None
    raw_artifact_ref: _NonEmptyText
    raw_artifact: dict[str, JsonValue]
    error_type: _NonEmptyText | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_result_invariants(self) -> AttackPolicyResult:
        if self.turns_executed != len(self.turn_records):
            raise ValueError("turns_executed must match the number of turn records")
        expected_turns = tuple(range(1, self.turns_executed + 1))
        actual_turns = tuple(record.turn for record in self.turn_records)
        if actual_turns != expected_turns:
            raise ValueError("turn records must be sequential from one")
        if self.turn_records:
            if self.final_progress_decision != self.turn_records[-1].progress_decision:
                raise ValueError("final progress decision must match the last turn")
        elif self.final_progress_decision is not None:
            raise ValueError("a final progress decision requires at least one turn")
        if any(record.progress_decision.run_id != self.run_id for record in self.turn_records):
            raise ValueError("every turn decision must match the result run_id")
        if self.final_progress_decision is not None:
            self._validate_stop_reason(self.final_progress_decision)
        self._validate_outcome()
        return self

    def _validate_stop_reason(self, decision: ProgressDecision) -> None:
        expected_state = {
            AttackPolicyStopReason.OBJECTIVE_ACHIEVED: ProgressState.OBJECTIVE_ACHIEVED,
            AttackPolicyStopReason.TERMINAL_BLOCKED: ProgressState.TERMINAL_BLOCKED,
            AttackPolicyStopReason.INVALID_RUN: ProgressState.INVALID_RUN,
            AttackPolicyStopReason.BUDGET_EXHAUSTED: ProgressState.CONTINUE,
        }.get(self.stop_reason)
        if expected_state is not None and decision.state is not expected_state:
            raise ValueError("stop reason does not match the final progress decision")

    def _validate_outcome(self) -> None:
        if self.stop_reason is AttackPolicyStopReason.OBJECTIVE_ACHIEVED:
            expected_outcome: PyRITOutcome = "success"
        elif self.stop_reason in {
            AttackPolicyStopReason.TARGET_ERROR,
            AttackPolicyStopReason.POLICY_ERROR,
            AttackPolicyStopReason.CANCELLED,
        }:
            expected_outcome = "error"
        else:
            expected_outcome = "failure"
        if self.pyrit_outcome != expected_outcome:
            raise ValueError("PyRIT outcome does not match the policy stop reason")
