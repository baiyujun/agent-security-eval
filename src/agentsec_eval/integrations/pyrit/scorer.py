"""Translate project progress decisions into PyRIT true/false scores."""

from __future__ import annotations

from typing import Final

from pyrit.models import ComponentIdentifier, MessagePiece, Score
from pyrit.score import ScorerPromptValidator, TrueFalseScorer

from agentsec_eval.assertions import ProgressDecision, ProgressOracle, ProgressState

_SCORE_METADATA_SCHEMA_VERSION: Final = 1
_STOP_REASON_BY_STATE: Final[dict[ProgressState, str]] = {
    ProgressState.CONTINUE: "",
    ProgressState.OBJECTIVE_ACHIEVED: "objective_achieved",
    ProgressState.TERMINAL_BLOCKED: "blocked",
    ProgressState.INVALID_RUN: "invalid_run",
}


class AssertionBackedPyRITScorer(TrueFalseScorer):
    """Expose one Run-bound Progress Oracle through PyRIT's objective scorer API."""

    def __init__(self, *, run_id: str, oracle: ProgressOracle) -> None:
        normalized_run_id = run_id.strip()
        if not normalized_run_id:
            raise ValueError("run_id must not be blank")
        self._run_id = normalized_run_id
        self._oracle = oracle
        super().__init__(
            validator=ScorerPromptValidator(
                supported_data_types=["text"],
                max_pieces_in_response=1,
            )
        )

    def _build_identifier(self) -> ComponentIdentifier:
        oracle_type = f"{type(self._oracle).__module__}.{type(self._oracle).__qualname__}"
        return self._create_identifier(
            params={
                "run_id": self._run_id,
                "oracle_type": oracle_type,
                "metadata_schema_version": _SCORE_METADATA_SCHEMA_VERSION,
            }
        )

    async def _score_piece_async(
        self,
        message_piece: MessagePiece,
        *,
        objective: str | None = None,
    ) -> list[Score]:
        decision = await self._oracle.evaluate(
            run_id=self._run_id,
            candidate_response=message_piece.converted_value,
        )
        decision = self._normalize_for_bound_run(decision)
        return [
            Score(
                score_value=str(decision.objective_achieved).lower(),
                score_value_description=f"Project progress state: {decision.state.value}",
                score_type="true_false",
                score_category=["agent_security_eval"],
                score_metadata=self._score_metadata(decision),
                score_rationale=decision.rationale,
                scorer_class_identifier=self.get_identifier(),
                message_piece_id=message_piece.id,
                objective=objective,
            )
        ]

    def _normalize_for_bound_run(self, decision: ProgressDecision) -> ProgressDecision:
        if decision.run_id == self._run_id:
            return decision
        return ProgressDecision(
            run_id=self._run_id,
            state=ProgressState.INVALID_RUN,
            rationale=(
                "Progress Oracle returned a decision for an unexpected Run; "
                "foreign evidence was discarded."
            ),
            metadata={"reported_run_id": decision.run_id},
        )

    @staticmethod
    def _score_metadata(decision: ProgressDecision) -> dict[str, str | int | float]:
        return {
            "agentsec_eval_schema_version": _SCORE_METADATA_SCHEMA_VERSION,
            "run_id": decision.run_id,
            "progress_state": decision.state.value,
            "terminal": str(decision.is_terminal).lower(),
            "stop_reason": _STOP_REASON_BY_STATE[decision.state],
            "invalid_run": str(decision.invalid_run).lower(),
            "progress_decision": decision.model_dump_json(),
        }
