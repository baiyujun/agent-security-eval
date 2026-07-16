from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentsec_eval.domain import (
    AttackCandidate,
    CanonicalTraceEvent,
    ExecutionBudget,
    ExecutionRunSpec,
    ScenarioSpec,
    TargetConfiguration,
    validate_trace,
)


def make_run_spec() -> ExecutionRunSpec:
    return ExecutionRunSpec(
        run_id="run-001",
        target=TargetConfiguration(
            target_id="fake-target",
            adapter="m0a-http",
            version="1",
        ),
        scenario=ScenarioSpec(
            scenario_id="scenario-001",
            user_task="Complete the deterministic three-turn task.",
            canary="canary-run-001",
        ),
        attack_candidate=AttackCandidate(
            candidate_id="candidate-001",
            content="Use the fixed M0-A candidate.",
        ),
        budget=ExecutionBudget(max_turns=3, timeout_seconds=30),
        repetition_seed=7,
    )


def test_execution_run_spec_round_trips_stable_json() -> None:
    run_spec = make_run_spec()

    restored = ExecutionRunSpec.model_validate_json(run_spec.model_dump_json())

    assert restored == run_spec


def test_execution_run_spec_is_frozen() -> None:
    run_spec = make_run_spec()

    with pytest.raises(ValidationError, match="frozen"):
        run_spec.run_id = "changed"


@pytest.mark.parametrize(
    ("field", "value"),
    [("max_turns", 0), ("timeout_seconds", 0)],
)
def test_execution_budget_requires_positive_limits(field: str, value: int) -> None:
    values = {"max_turns": 3, "timeout_seconds": 30, field: value}

    with pytest.raises(ValidationError, match="greater than 0"):
        ExecutionBudget(**values)


def make_trace_event(
    *,
    event_id: str,
    run_id: str = "run-001",
    sequence: int,
) -> CanonicalTraceEvent:
    return CanonicalTraceEvent(
        event_id=event_id,
        run_id=run_id,
        sequence=sequence,
        event_type="target_request",
        source="m0a_solver",
        observation_strength="harness_observed",
        payload={"message": "turn"},
    )


def test_canonical_trace_event_round_trips_stable_json() -> None:
    event = make_trace_event(event_id="event-001", sequence=1)

    restored = CanonicalTraceEvent.model_validate_json(event.model_dump_json())

    assert restored == event


def test_validate_trace_accepts_strictly_increasing_events() -> None:
    events = [
        make_trace_event(event_id="event-001", sequence=1),
        make_trace_event(event_id="event-002", sequence=2),
    ]

    validate_trace(events, expected_run_id="run-001")


@pytest.mark.parametrize(
    "events",
    [
        [],
        [make_trace_event(event_id="event-001", run_id="other", sequence=1)],
        [
            make_trace_event(event_id="event-001", sequence=1),
            make_trace_event(event_id="event-002", sequence=1),
        ],
        [
            make_trace_event(event_id="event-001", sequence=1),
            make_trace_event(event_id="event-001", sequence=2),
        ],
    ],
)
def test_validate_trace_rejects_invalid_trace(events: list[CanonicalTraceEvent]) -> None:
    with pytest.raises(ValueError):
        validate_trace(events, expected_run_id="run-001")
