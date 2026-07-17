from __future__ import annotations

from typing import Literal

import pytest
from pydantic import ValidationError

from agentsec_eval.assertions import AttackStage, ProgressDecision, ProgressState
from agentsec_eval.integrations.pyrit import (
    AttackPolicyResult,
    AttackPolicyStopReason,
    AttackPolicyTurnRecord,
)

pytestmark = pytest.mark.pyrit


def make_decision(state: ProgressState = ProgressState.CONTINUE) -> ProgressDecision:
    stage_by_state = {
        ProgressState.CONTINUE: AttackStage.DELIVERED,
        ProgressState.OBJECTIVE_ACHIEVED: AttackStage.EFFECT,
        ProgressState.TERMINAL_BLOCKED: AttackStage.EXECUTED,
        ProgressState.INVALID_RUN: AttackStage.NONE,
    }
    evidence_ids = ("evidence-1",) if state is not ProgressState.CONTINUE else ()
    return ProgressDecision(
        run_id="run-1",
        state=state,
        stage_reached=stage_by_state[state],
        policy_feedback="sanitized feedback",
        evidence_ids=evidence_ids,
    )


def make_turn_record(
    *,
    turn: int = 1,
    decision: ProgressDecision | None = None,
) -> AttackPolicyTurnRecord:
    return AttackPolicyTurnRecord(
        turn=turn,
        adversarial_prompt=f"attack-{turn}",
        target_response=f"response-{turn}",
        target_session_id="session-1",
        target_turn=turn,
        objective_conversation_id="objective-conversation-1",
        score_value=False,
        score_rationale="sanitized feedback",
        progress_decision=decision or make_decision(),
    )


def make_policy_result(
    *,
    turns_executed: int = 1,
    turn_records: tuple[AttackPolicyTurnRecord, ...] | None = None,
    stop_reason: AttackPolicyStopReason = AttackPolicyStopReason.BUDGET_EXHAUSTED,
    final_decision: ProgressDecision | None = None,
    pyrit_outcome: Literal["success", "failure", "error"] = "failure",
) -> AttackPolicyResult:
    records = turn_records or (make_turn_record(),)
    return AttackPolicyResult(
        run_id="run-1",
        policy_name="pyrit_red_teaming",
        policy_version="0.14.0",
        turns_executed=turns_executed,
        stop_reason=stop_reason,
        final_progress_decision=final_decision or records[-1].progress_decision,
        objective_conversation_id="objective-conversation-1",
        adversarial_conversation_id="adversarial-conversation-1",
        turn_records=records,
        pyrit_outcome=pyrit_outcome,
        pyrit_result_ref="attack-result-1",
        raw_artifact_ref="agentsec-eval:run-1:pyrit-memory",
        raw_artifact={"run_ids": ["run-1"], "message_count": 4},
    )


def test_attack_policy_result_round_trips_without_security_verdict() -> None:
    result = make_policy_result()

    restored = AttackPolicyResult.model_validate_json(result.model_dump_json())

    assert restored == result
    assert "security_failure" not in AttackPolicyResult.model_fields
    assert restored.raw_artifact == {"run_ids": ["run-1"], "message_count": 4}


def test_attack_policy_result_requires_turn_count_to_match_records() -> None:
    with pytest.raises(ValidationError, match="turns_executed must match"):
        make_policy_result(turns_executed=2, turn_records=(make_turn_record(),))


def test_attack_policy_result_requires_sequential_logical_turns() -> None:
    with pytest.raises(ValidationError, match="turn records must be sequential"):
        make_policy_result(
            turns_executed=2,
            turn_records=(make_turn_record(turn=1), make_turn_record(turn=3)),
        )


def test_attack_policy_result_requires_final_decision_to_match_last_turn() -> None:
    with pytest.raises(ValidationError, match="final progress decision must match"):
        make_policy_result(final_decision=make_decision(ProgressState.TERMINAL_BLOCKED))


@pytest.mark.parametrize(
    ("stop_reason", "decision_state", "pyrit_outcome"),
    [
        (
            AttackPolicyStopReason.OBJECTIVE_ACHIEVED,
            ProgressState.CONTINUE,
            "success",
        ),
        (
            AttackPolicyStopReason.TERMINAL_BLOCKED,
            ProgressState.CONTINUE,
            "failure",
        ),
        (
            AttackPolicyStopReason.INVALID_RUN,
            ProgressState.CONTINUE,
            "failure",
        ),
        (
            AttackPolicyStopReason.BUDGET_EXHAUSTED,
            ProgressState.OBJECTIVE_ACHIEVED,
            "failure",
        ),
    ],
)
def test_attack_policy_result_rejects_stop_reason_decision_mismatch(
    stop_reason: AttackPolicyStopReason,
    decision_state: ProgressState,
    pyrit_outcome: Literal["success", "failure", "error"],
) -> None:
    decision = make_decision(decision_state)
    record = make_turn_record(decision=decision)

    with pytest.raises(ValidationError, match="stop reason does not match"):
        make_policy_result(
            turn_records=(record,),
            stop_reason=stop_reason,
            final_decision=decision,
            pyrit_outcome=pyrit_outcome,
        )


def test_attack_policy_result_requires_success_only_for_achieved_objective() -> None:
    decision = make_decision(ProgressState.OBJECTIVE_ACHIEVED)
    record = make_turn_record(decision=decision)

    result = make_policy_result(
        turn_records=(record,),
        stop_reason=AttackPolicyStopReason.OBJECTIVE_ACHIEVED,
        final_decision=decision,
        pyrit_outcome="success",
    )

    assert result.final_progress_decision is not None
    assert result.final_progress_decision.objective_achieved is True
    assert result.pyrit_outcome == "success"


def test_attack_policy_result_rejects_unknown_fields() -> None:
    payload = make_policy_result().model_dump(mode="json")
    payload["unexpected"] = True

    with pytest.raises(ValidationError, match="extra_forbidden"):
        AttackPolicyResult.model_validate(payload)
