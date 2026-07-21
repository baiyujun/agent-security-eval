from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentsec_eval.assertions import AttackStage, ProgressDecision, ProgressState


def test_attack_stage_has_stable_progression_vocabulary() -> None:
    assert tuple(stage.value for stage in AttackStage) == (
        "NONE",
        "DELIVERED",
        "INFLUENCED",
        "ATTEMPTED",
        "EXECUTED",
        "EFFECT",
    )


@pytest.mark.parametrize(
    ("state", "is_terminal", "objective_achieved", "invalid_run"),
    [
        (ProgressState.CONTINUE, False, False, False),
        (ProgressState.OBJECTIVE_ACHIEVED, True, True, False),
        (ProgressState.TERMINAL_BLOCKED, True, False, False),
        (ProgressState.INVALID_RUN, True, False, True),
    ],
)
def test_progress_decision_exposes_unambiguous_control_state(
    state: ProgressState,
    is_terminal: bool,
    objective_achieved: bool,
    invalid_run: bool,
) -> None:
    evidence_ids = ("receiver-event-1",) if state is ProgressState.OBJECTIVE_ACHIEVED else ()
    stage_reached = (
        AttackStage.EFFECT if state is ProgressState.OBJECTIVE_ACHIEVED else AttackStage.NONE
    )
    decision = ProgressDecision(
        run_id="run-1",
        state=state,
        stage_reached=stage_reached,
        evidence_ids=evidence_ids,
    )

    assert decision.is_terminal is is_terminal
    assert decision.objective_achieved is objective_achieved
    assert decision.invalid_run is invalid_run


def test_objective_achieved_requires_environment_evidence() -> None:
    with pytest.raises(ValidationError, match="requires at least one evidence ID"):
        ProgressDecision(
            run_id="run-1",
            state=ProgressState.OBJECTIVE_ACHIEVED,
            stage_reached=AttackStage.EFFECT,
        )


@pytest.mark.parametrize(
    ("state", "stage", "evidence_ids", "message"),
    [
        (
            ProgressState.OBJECTIVE_ACHIEVED,
            AttackStage.EXECUTED,
            ("receiver-event-1",),
            "OBJECTIVE_ACHIEVED requires EFFECT",
        ),
        (
            ProgressState.CONTINUE,
            AttackStage.EFFECT,
            (),
            "CONTINUE cannot use EFFECT",
        ),
        (
            ProgressState.INVALID_RUN,
            AttackStage.DELIVERED,
            (),
            "INVALID_RUN requires NONE",
        ),
        (
            ProgressState.TERMINAL_BLOCKED,
            AttackStage.EFFECT,
            (),
            "TERMINAL_BLOCKED cannot use EFFECT",
        ),
        (
            ProgressState.CONTINUE,
            AttackStage.DELIVERED,
            ("event-1", "event-1"),
            "evidence IDs must be unique",
        ),
    ],
)
def test_progress_decision_rejects_inconsistent_state(
    state: ProgressState,
    stage: AttackStage,
    evidence_ids: tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        ProgressDecision(
            run_id="run-1",
            state=state,
            stage_reached=stage,
            evidence_ids=evidence_ids,
        )


def test_terminal_blocked_allows_late_block_after_execution() -> None:
    decision = ProgressDecision(
        run_id="run-1",
        state=ProgressState.TERMINAL_BLOCKED,
        stage_reached=AttackStage.EXECUTED,
        evidence_ids=("file-read-event-1",),
    )

    assert decision.stage_reached is AttackStage.EXECUTED


def test_progress_decision_round_trips_complete_project_state() -> None:
    decision = ProgressDecision(
        run_id="run-1",
        state=ProgressState.OBJECTIVE_ACHIEVED,
        stage_reached=AttackStage.EFFECT,
        progress_features={"receiver_confirmed": True, "tool_calls": 2},
        internal_rationale="Receiver observed this Run's Canary.",
        policy_feedback="The objective was confirmed.",
        evidence_ids=("receiver-event-1",),
        metadata={"receiver": "mock", "canary_count": 1},
    )

    restored = ProgressDecision.model_validate_json(decision.model_dump_json())

    assert restored == decision
    assert restored.stage_reached is AttackStage.EFFECT
    assert restored.progress_features == {"receiver_confirmed": True, "tool_calls": 2}
    assert restored.internal_rationale == "Receiver observed this Run's Canary."
    assert restored.policy_feedback == "The objective was confirmed."


def test_progress_decision_rejects_blank_run_id_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ProgressDecision(
            run_id=" ",
            state=ProgressState.CONTINUE,
            stage_reached=AttackStage.NONE,
        )

    with pytest.raises(ValidationError, match="extra_forbidden"):
        ProgressDecision.model_validate(
            {
                "run_id": "run-1",
                "state": "CONTINUE",
                "stage_reached": "NONE",
                "unexpected": True,
            }
        )
