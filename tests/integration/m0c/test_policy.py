from __future__ import annotations

import asyncio
from collections.abc import Sequence

import pytest

from agentsec_eval.assertions import ProgressDecision, ProgressState
from agentsec_eval.domain import CanonicalTraceEvent, validate_trace
from agentsec_eval.integrations.pyrit import (
    AttackPolicyResult,
    AttackPolicyStopReason,
    PyRITAttackPolicy,
)

from .conftest import (
    AdversarialTargetFactory,
    RecordingTargetSession,
    SequenceOracle,
    make_decision,
    make_run_spec,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.pyrit,
    pytest.mark.filterwarnings(
        "ignore:.*labels=.*deprecated and will be removed in 0.16.0.*:DeprecationWarning"
    ),
]


async def run_owned_policy(
    *,
    decisions: Sequence[ProgressDecision],
    max_turns: int,
    run_id: str = "run-1",
    target_error_on_turn: int | None = None,
    adversarial_error_on_call: int | None = None,
) -> tuple[
    AttackPolicyResult,
    RecordingTargetSession,
    SequenceOracle,
    AdversarialTargetFactory,
    list[CanonicalTraceEvent],
]:
    session = RecordingTargetSession(run_id=run_id, error_on_turn=target_error_on_turn)
    oracle = SequenceOracle(list(decisions))
    factory = AdversarialTargetFactory(
        run_id=run_id,
        error_on_call=adversarial_error_on_call,
    )
    policy = PyRITAttackPolicy(adversarial_target_factory=factory)
    trace: list[CanonicalTraceEvent] = []
    try:
        result = await policy.run(
            run_spec=make_run_spec(run_id=run_id, max_turns=max_turns),
            target_session=session,
            progress_oracle=oracle,
            trace_sink=trace,
        )
    finally:
        await session.close()
    return result, session, oracle, factory, trace


@pytest.mark.parametrize(
    ("states", "max_turns", "expected_turns", "stop_reason", "pyrit_outcome"),
    [
        (
            [ProgressState.CONTINUE, ProgressState.OBJECTIVE_ACHIEVED],
            3,
            2,
            AttackPolicyStopReason.OBJECTIVE_ACHIEVED,
            "success",
        ),
        (
            [ProgressState.TERMINAL_BLOCKED],
            3,
            1,
            AttackPolicyStopReason.TERMINAL_BLOCKED,
            "failure",
        ),
        (
            [ProgressState.INVALID_RUN],
            3,
            1,
            AttackPolicyStopReason.INVALID_RUN,
            "failure",
        ),
        (
            [ProgressState.CONTINUE, ProgressState.CONTINUE],
            2,
            2,
            AttackPolicyStopReason.BUDGET_EXHAUSTED,
            "failure",
        ),
    ],
)
def test_policy_obeys_project_stopping_and_exact_budget(
    states: list[ProgressState],
    max_turns: int,
    expected_turns: int,
    stop_reason: AttackPolicyStopReason,
    pyrit_outcome: str,
) -> None:
    decisions = [make_decision(state, turn=index) for index, state in enumerate(states, 1)]

    result, session, oracle, factory, trace = asyncio.run(
        run_owned_policy(decisions=decisions, max_turns=max_turns)
    )

    assert result.turns_executed == expected_turns
    assert result.stop_reason is stop_reason
    assert result.pyrit_outcome == pyrit_outcome
    assert len(result.turn_records) == expected_turns
    assert len(session.messages) == expected_turns
    assert len(oracle.calls) == expected_turns
    assert session.closed is True
    assert len(factory.instances) == 1
    assert result.raw_artifact["run_ids"] == ["run-1"]
    assert result.raw_artifact["score_count"] == expected_turns
    assert result.raw_artifact["attack_result_count"] == 1
    assert result.pyrit_result_ref is not None
    validate_trace(trace, expected_run_id="run-1")


def test_policy_reuses_session_and_records_complete_turn_trace() -> None:
    decisions = [
        make_decision(ProgressState.CONTINUE, turn=1),
        make_decision(ProgressState.TERMINAL_BLOCKED, turn=2),
    ]

    result, session, _, _, trace = asyncio.run(
        run_owned_policy(decisions=decisions, max_turns=3)
    )

    assert {record.target_session_id for record in result.turn_records} == {session.session_id}
    assert {record.objective_conversation_id for record in result.turn_records} == {
        result.objective_conversation_id
    }
    assert [record.target_turn for record in result.turn_records] == [1, 2]
    assert result.objective_conversation_id != result.adversarial_conversation_id
    event_types = [event.event_type for event in trace]
    assert event_types == [
        "adversarial_prompt",
        "target_request",
        "target_response",
        "progress_decision",
        "adversarial_prompt",
        "target_request",
        "target_response",
        "progress_decision",
        "policy_stopped",
    ]
    assert trace[-1].payload["stop_reason"] == "terminal_blocked"


def test_policy_forwards_only_sanitized_feedback_to_adversarial_target() -> None:
    private = "secret-canary-1 at /private/effects/run-1"
    feedback = "Try a different delivery mechanism."
    decisions = [
        make_decision(
            ProgressState.CONTINUE,
            turn=1,
            internal_rationale=private,
            policy_feedback=feedback,
        ),
        make_decision(ProgressState.TERMINAL_BLOCKED, turn=2),
    ]

    result, _, _, factory, _ = asyncio.run(
        run_owned_policy(decisions=decisions, max_turns=3)
    )

    adversarial_requests = factory.instances[0].received_requests
    assert len(adversarial_requests) == 2
    assert feedback in adversarial_requests[1]
    assert private not in adversarial_requests[1]
    assert private not in result.turn_records[0].score_rationale
    assert private in result.turn_records[0].progress_decision.internal_rationale


def test_policy_classifies_target_errors_and_preserves_cleanup() -> None:
    result, session, oracle, _, trace = asyncio.run(
        run_owned_policy(
            decisions=[],
            max_turns=3,
            target_error_on_turn=1,
        )
    )

    assert result.stop_reason is AttackPolicyStopReason.TARGET_ERROR
    assert result.pyrit_outcome == "error"
    assert result.turns_executed == 0
    assert result.final_progress_decision is None
    assert result.raw_artifact["attack_result_count"] == 1
    assert result.error_type is not None
    assert session.closed is True
    assert oracle.calls == []
    assert trace[-1].event_type == "policy_stopped"
    assert trace[-1].payload["stop_reason"] == "target_error"


def test_policy_classifies_adversarial_errors_and_preserves_cleanup() -> None:
    result, session, oracle, _, trace = asyncio.run(
        run_owned_policy(
            decisions=[],
            max_turns=3,
            adversarial_error_on_call=1,
        )
    )

    assert result.stop_reason is AttackPolicyStopReason.POLICY_ERROR
    assert result.pyrit_outcome == "error"
    assert result.turns_executed == 0
    assert result.raw_artifact["attack_result_count"] == 1
    assert session.messages == []
    assert session.closed is True
    assert oracle.calls == []
    assert trace[-1].payload["stop_reason"] == "policy_error"
