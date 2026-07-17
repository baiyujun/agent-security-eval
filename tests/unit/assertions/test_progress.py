from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentsec_eval.assertions import ProgressDecision, ProgressState


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
    decision = ProgressDecision(run_id="run-1", state=state, evidence_ids=evidence_ids)

    assert decision.is_terminal is is_terminal
    assert decision.objective_achieved is objective_achieved
    assert decision.invalid_run is invalid_run


def test_objective_achieved_requires_environment_evidence() -> None:
    with pytest.raises(ValidationError, match="requires at least one evidence ID"):
        ProgressDecision(run_id="run-1", state=ProgressState.OBJECTIVE_ACHIEVED)


def test_progress_decision_round_trips_complete_project_state() -> None:
    decision = ProgressDecision(
        run_id="run-1",
        state=ProgressState.OBJECTIVE_ACHIEVED,
        rationale="Receiver observed this Run's Canary.",
        evidence_ids=("receiver-event-1",),
        metadata={"receiver": "mock", "canary_count": 1},
    )

    restored = ProgressDecision.model_validate_json(decision.model_dump_json())

    assert restored == decision


def test_progress_decision_rejects_blank_run_id_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ProgressDecision(run_id=" ", state=ProgressState.CONTINUE)

    with pytest.raises(ValidationError, match="extra_forbidden"):
        ProgressDecision.model_validate(
            {"run_id": "run-1", "state": "CONTINUE", "unexpected": True}
        )
