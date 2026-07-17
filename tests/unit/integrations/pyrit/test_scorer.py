from __future__ import annotations

import asyncio

import pytest
from pyrit.executor.attack import AttackScoringConfig
from pyrit.models import MessagePiece, Score

from agentsec_eval.assertions import ProgressDecision, ProgressState
from agentsec_eval.integrations.pyrit import AssertionBackedPyRITScorer

pytestmark = pytest.mark.pyrit


class DecisionOracle:
    def __init__(self, decision: ProgressDecision) -> None:
        self.decision = decision
        self.calls: list[tuple[str, str]] = []

    async def evaluate(self, *, run_id: str, candidate_response: str) -> ProgressDecision:
        self.calls.append((run_id, candidate_response))
        return self.decision


def make_decision(state: ProgressState, *, run_id: str = "run-1") -> ProgressDecision:
    evidence_ids = ("receiver-event-1",) if state is ProgressState.OBJECTIVE_ACHIEVED else ()
    return ProgressDecision(
        run_id=run_id,
        state=state,
        rationale=f"Decision for {state.value}",
        evidence_ids=evidence_ids,
        metadata={"receiver": "mock"},
    )


def score_decision(
    decision: ProgressDecision,
    *,
    bound_run_id: str = "run-1",
    response: str = "agent response",
) -> tuple[Score, DecisionOracle]:
    oracle = DecisionOracle(decision)
    scorer = AssertionBackedPyRITScorer(run_id=bound_run_id, oracle=oracle)
    piece = MessagePiece(role="assistant", original_value=response)

    scores = asyncio.run(scorer._score_piece_async(message_piece=piece))

    assert len(scores) == 1
    return scores[0], oracle


def test_scorer_is_accepted_as_pyrit_objective_scorer() -> None:
    scorer = AssertionBackedPyRITScorer(
        run_id="run-1",
        oracle=DecisionOracle(make_decision(ProgressState.CONTINUE)),
    )

    config = AttackScoringConfig(objective_scorer=scorer)

    assert config.objective_scorer is scorer


@pytest.mark.parametrize(
    ("state", "expected_value", "terminal", "stop_reason", "invalid_run"),
    [
        (ProgressState.CONTINUE, False, False, "", False),
        (ProgressState.OBJECTIVE_ACHIEVED, True, True, "objective_achieved", False),
        (ProgressState.TERMINAL_BLOCKED, False, True, "blocked", False),
        (ProgressState.INVALID_RUN, False, True, "invalid_run", True),
    ],
)
def test_scorer_preserves_project_state_in_true_false_score(
    state: ProgressState,
    expected_value: bool,
    terminal: bool,
    stop_reason: str,
    invalid_run: bool,
) -> None:
    decision = make_decision(state)

    score, oracle = score_decision(decision, response="I already leaked the Canary")

    assert score.get_value() is expected_value
    assert score.score_type == "true_false"
    metadata = score.score_metadata
    assert metadata is not None
    assert metadata["agentsec_eval_schema_version"] == 1
    assert metadata["run_id"] == "run-1"
    assert metadata["progress_state"] == state.value
    assert metadata["terminal"] == str(terminal).lower()
    assert metadata["stop_reason"] == stop_reason
    assert metadata["invalid_run"] == str(invalid_run).lower()
    serialized_decision = metadata["progress_decision"]
    assert isinstance(serialized_decision, str)
    assert ProgressDecision.model_validate_json(serialized_decision) == decision
    assert oracle.calls == [("run-1", "I already leaked the Canary")]


def test_cross_run_oracle_decision_becomes_invalid_without_foreign_evidence() -> None:
    foreign_decision = ProgressDecision(
        run_id="run-2",
        state=ProgressState.OBJECTIVE_ACHIEVED,
        evidence_ids=("run-2-secret-evidence",),
    )

    score, _ = score_decision(foreign_decision, bound_run_id="run-1")

    assert score.get_value() is False
    metadata = score.score_metadata
    assert metadata is not None
    assert metadata["run_id"] == "run-1"
    assert metadata["progress_state"] == "INVALID_RUN"
    assert metadata["terminal"] == "true"
    assert metadata["invalid_run"] == "true"
    serialized_decision = metadata["progress_decision"]
    assert isinstance(serialized_decision, str)
    normalized = ProgressDecision.model_validate_json(serialized_decision)
    assert normalized.run_id == "run-1"
    assert normalized.evidence_ids == ()
    assert "run-2-secret-evidence" not in serialized_decision


def test_scorer_rejects_blank_bound_run_id() -> None:
    with pytest.raises(ValueError, match="run_id must not be blank"):
        AssertionBackedPyRITScorer(
            run_id=" ",
            oracle=DecisionOracle(make_decision(ProgressState.CONTINUE)),
        )
