"""PyRIT-independent runtime progress decisions."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    model_validator,
)

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProgressState(StrEnum):
    """Runtime progress states preserved across external scorer boundaries."""

    CONTINUE = "CONTINUE"
    OBJECTIVE_ACHIEVED = "OBJECTIVE_ACHIEVED"
    TERMINAL_BLOCKED = "TERMINAL_BLOCKED"
    INVALID_RUN = "INVALID_RUN"


class AttackStage(StrEnum):
    """Furthest security-relevant stage confirmed for one Run."""

    NONE = "NONE"
    DELIVERED = "DELIVERED"
    INFLUENCED = "INFLUENCED"
    ATTEMPTED = "ATTEMPTED"
    EXECUTED = "EXECUTED"
    EFFECT = "EFFECT"


class ProgressDecision(BaseModel):
    """One project-owned progress decision for an explicitly identified Run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: NonEmptyText
    state: ProgressState
    stage_reached: AttackStage
    progress_features: dict[str, JsonValue] = Field(default_factory=dict)
    internal_rationale: str = ""
    policy_feedback: str = ""
    evidence_ids: tuple[NonEmptyText, ...] = ()
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_state_invariants(self) -> ProgressDecision:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence IDs must be unique")
        if self.state is ProgressState.OBJECTIVE_ACHIEVED:
            if self.stage_reached is not AttackStage.EFFECT:
                raise ValueError("OBJECTIVE_ACHIEVED requires EFFECT")
            if not self.evidence_ids:
                raise ValueError("OBJECTIVE_ACHIEVED requires at least one evidence ID")
        if self.state is ProgressState.CONTINUE and self.stage_reached is AttackStage.EFFECT:
            raise ValueError("CONTINUE cannot use EFFECT")
        if self.state is ProgressState.INVALID_RUN and self.stage_reached is not AttackStage.NONE:
            raise ValueError("INVALID_RUN requires NONE")
        if (
            self.state is ProgressState.TERMINAL_BLOCKED
            and self.stage_reached is AttackStage.EFFECT
        ):
            raise ValueError("TERMINAL_BLOCKED cannot use EFFECT")
        return self

    @property
    def is_terminal(self) -> bool:
        return self.state is not ProgressState.CONTINUE

    @property
    def objective_achieved(self) -> bool:
        return self.state is ProgressState.OBJECTIVE_ACHIEVED

    @property
    def invalid_run(self) -> bool:
        return self.state is ProgressState.INVALID_RUN


class ProgressOracle(Protocol):
    """Resolve progress for a caller-supplied Run without inferring its identity."""

    async def evaluate(
        self,
        *,
        run_id: str,
        candidate_response: str,
    ) -> ProgressDecision: ...
