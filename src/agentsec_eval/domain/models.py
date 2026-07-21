"""Minimal immutable contracts required by the M0-A execution boundary."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, JsonValue, PositiveInt, StringConstraints

_NonEmptyId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class FrozenModel(BaseModel):
    """Base configuration for durable immutable project contracts."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class TargetConfiguration(FrozenModel):
    target_id: _NonEmptyId
    adapter: str
    version: str


class ExecutionScenarioSpec(FrozenModel):
    """Minimal scenario projection required for one execution.

    Complete ``BaseScenario`` and ``ScenarioCase`` types belong to the future
    Benchmark/scenario-assets boundary. A separate compile or materialization
    function will later transform a ``ScenarioCase`` into an ``ExecutionRunSpec``.
    """

    scenario_id: _NonEmptyId
    user_task: str
    canary: str


class AttackCandidate(FrozenModel):
    candidate_id: _NonEmptyId
    content: str


class ExecutionBudget(FrozenModel):
    max_turns: PositiveInt
    timeout_seconds: PositiveInt


class ExecutionRunSpec(FrozenModel):
    run_id: _NonEmptyId
    target: TargetConfiguration
    scenario: ExecutionScenarioSpec
    attack_candidate: AttackCandidate
    budget: ExecutionBudget
    repetition_seed: int


TraceEventType = Literal[
    "session_opened",
    "target_request",
    "target_response",
    "tool_call",
    "tool_result",
    "environment_effect",
    "session_closed",
    "harness_error",
    "adversarial_prompt",
    "progress_decision",
    "policy_stopped",
]
ObservationStrength = Literal[
    "target_reported",
    "harness_observed",
    "environment_confirmed",
]


class CanonicalTraceEvent(FrozenModel):
    event_id: str
    run_id: str
    sequence: PositiveInt
    event_type: TraceEventType
    source: str
    observation_strength: ObservationStrength
    payload: dict[str, JsonValue]


def validate_trace(
    events: Sequence[CanonicalTraceEvent],
    *,
    expected_run_id: str,
) -> None:
    if not events:
        raise ValueError("trace must not be empty")
    if any(event.run_id != expected_run_id for event in events):
        raise ValueError("every trace event must match the expected run_id")
    event_ids = [event.event_id for event in events]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("trace event IDs must be unique")
    sequences = [event.sequence for event in events]
    if any(current >= following for current, following in pairwise(sequences)):
        raise ValueError("trace sequence must be strictly increasing")
