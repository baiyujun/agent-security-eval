"""Minimal immutable contracts required by the M0-A execution boundary."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue, PositiveInt


class FrozenModel(BaseModel):
    """Base configuration for durable immutable project contracts."""

    model_config = ConfigDict(frozen=True)


class TargetConfiguration(FrozenModel):
    target_id: str
    adapter: str
    version: str


class ScenarioSpec(FrozenModel):
    scenario_id: str
    user_task: str
    canary: str


class AttackCandidate(FrozenModel):
    candidate_id: str
    content: str


class ExecutionBudget(FrozenModel):
    max_turns: PositiveInt
    timeout_seconds: PositiveInt


class ExecutionRunSpec(FrozenModel):
    run_id: str
    target: TargetConfiguration
    scenario: ScenarioSpec
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
