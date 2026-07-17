"""Project-controlled stopping for one pinned PyRIT red-teaming attack."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, MutableSequence
from typing import Any, Final, Literal, cast

from pyrit.executor.attack import AttackAdversarialConfig, AttackScoringConfig
from pyrit.executor.attack.multi_turn.multi_turn_attack_strategy import MultiTurnAttackContext
from pyrit.executor.attack.multi_turn.red_teaming import RedTeamingAttack
from pyrit.models import (
    AttackOutcome,
    AttackResult,
    Score,
    build_atomic_attack_identifier,
)
from pyrit.prompt_target import PromptTarget

from agentsec_eval.assertions import ProgressDecision, ProgressOracle, ProgressState
from agentsec_eval.domain import (
    CanonicalTraceEvent,
    ExecutionRunSpec,
    ObservationStrength,
    TraceEventType,
    validate_trace,
)
from agentsec_eval.integrations.pyrit.memory import PyRITMemoryScope
from agentsec_eval.integrations.pyrit.prompt_target import (
    TargetSessionPromptTarget,
    caused_by_target_session,
)
from agentsec_eval.integrations.pyrit.result import (
    AttackPolicyResult,
    AttackPolicyStopReason,
    AttackPolicyTurnRecord,
)
from agentsec_eval.integrations.pyrit.scorer import AssertionBackedPyRITScorer
from agentsec_eval.targets import TargetSession

_POLICY_NAME: Final = "pyrit_red_teaming"
_POLICY_VERSION: Final = "0.14.0"

_STOP_REASON_BY_STATE: Final[dict[ProgressState, AttackPolicyStopReason]] = {
    ProgressState.OBJECTIVE_ACHIEVED: AttackPolicyStopReason.OBJECTIVE_ACHIEVED,
    ProgressState.TERMINAL_BLOCKED: AttackPolicyStopReason.TERMINAL_BLOCKED,
    ProgressState.INVALID_RUN: AttackPolicyStopReason.INVALID_RUN,
}


class _CanonicalTraceEmitter:
    def __init__(
        self,
        *,
        run_id: str,
        sink: MutableSequence[CanonicalTraceEvent],
    ) -> None:
        if sink:
            validate_trace(sink, expected_run_id=run_id)
            next_sequence = sink[-1].sequence + 1
        else:
            next_sequence = 1
        self._run_id = run_id
        self._sink = sink
        self._next_sequence = next_sequence
        self._event_ids = {event.event_id for event in sink}

    def emit(
        self,
        *,
        source: str,
        event_type: TraceEventType,
        strength: ObservationStrength,
        payload: dict[str, Any],
    ) -> None:
        sequence = self._next_sequence
        event_id = f"{self._run_id}:m0c:{sequence}"
        if event_id in self._event_ids:
            raise ValueError("M0-C trace event ID collides with an existing event")
        event = CanonicalTraceEvent(
            event_id=event_id,
            run_id=self._run_id,
            sequence=sequence,
            event_type=event_type,
            source=source,
            observation_strength=strength,
            payload=payload,
        )
        self._sink.append(event)
        self._event_ids.add(event_id)
        self._next_sequence += 1


class _ProjectControlledRedTeamingAttack(RedTeamingAttack):
    def __init__(
        self,
        *,
        objective_target: TargetSessionPromptTarget,
        attack_adversarial_config: AttackAdversarialConfig,
        attack_scoring_config: AttackScoringConfig,
        max_turns: int,
        trace_emitter: _CanonicalTraceEmitter,
    ) -> None:
        self._project_target = objective_target
        self._trace_emitter = trace_emitter
        self._turn_records: list[AttackPolicyTurnRecord] = []
        self._final_decision: ProgressDecision | None = None
        self._policy_stop_reason: AttackPolicyStopReason | None = None
        self._active_context: MultiTurnAttackContext[Any] | None = None
        super().__init__(
            objective_target=objective_target,
            attack_adversarial_config=attack_adversarial_config,
            attack_scoring_config=attack_scoring_config,
            max_turns=max_turns,
        )

    @property
    def turn_records(self) -> tuple[AttackPolicyTurnRecord, ...]:
        return tuple(self._turn_records)

    @property
    def final_decision(self) -> ProgressDecision | None:
        return self._final_decision

    @property
    def policy_stop_reason(self) -> AttackPolicyStopReason | None:
        return self._policy_stop_reason

    @property
    def objective_conversation_id(self) -> str | None:
        if self._active_context is None:
            return None
        return self._active_context.session.conversation_id

    @property
    def adversarial_conversation_id(self) -> str | None:
        if self._active_context is None:
            return None
        return self._active_context.session.adversarial_chat_conversation_id

    async def _setup_async(self, *, context: MultiTurnAttackContext[Any]) -> None:
        self._active_context = context
        await super()._setup_async(context=context)

    async def _perform_async(self, *, context: MultiTurnAttackContext[Any]) -> AttackResult:
        while context.executed_turns < self._max_turns:
            message = await self._generate_next_prompt_async(context=context)
            logical_turn = context.executed_turns + 1
            self._trace_emitter.emit(
                source="pyrit_attack_policy",
                event_type="adversarial_prompt",
                strength="harness_observed",
                payload={
                    "turn": logical_turn,
                    "adversarial_prompt": message.get_value(),
                    "objective_conversation_id": context.session.conversation_id,
                    "adversarial_conversation_id": (
                        context.session.adversarial_chat_conversation_id
                    ),
                },
            )
            response = await self._send_prompt_to_objective_target_async(
                context=context,
                message=message,
            )
            context.last_response = response
            score = await self._score_response_async(context=context)
            if score is None:
                raise RuntimeError("project scorer returned no score")
            context.last_score = score
            decision = self._progress_decision_from_score(score)
            target_result = self._project_target.last_turn_result
            if target_result is None:
                raise RuntimeError("project Target adapter did not retain its turn result")

            context.executed_turns = logical_turn
            record = AttackPolicyTurnRecord(
                turn=logical_turn,
                adversarial_prompt=message.get_value(),
                target_response=response.get_value(),
                target_session_id=target_result.session_id,
                target_turn=target_result.turn,
                objective_conversation_id=context.session.conversation_id,
                score_value=bool(score.get_value()),
                score_rationale=score.score_rationale or "",
                progress_decision=decision,
            )
            self._turn_records.append(record)
            self._final_decision = decision
            self._trace_emitter.emit(
                source="pyrit_attack_policy",
                event_type="progress_decision",
                strength="harness_observed",
                payload={
                    "turn": logical_turn,
                    "score_value": record.score_value,
                    "score_rationale": record.score_rationale,
                    "progress_decision": decision.model_dump(mode="json"),
                },
            )
            if decision.is_terminal:
                self._policy_stop_reason = _STOP_REASON_BY_STATE[decision.state]
                break

        if self._policy_stop_reason is None:
            self._policy_stop_reason = AttackPolicyStopReason.BUDGET_EXHAUSTED
        achieved = self._policy_stop_reason is AttackPolicyStopReason.OBJECTIVE_ACHIEVED
        return AttackResult(
            atomic_attack_identifier=build_atomic_attack_identifier(
                attack_identifier=self.get_identifier()
            ),
            conversation_id=context.session.conversation_id,
            objective=context.objective,
            outcome=AttackOutcome.SUCCESS if achieved else AttackOutcome.FAILURE,
            outcome_reason=self._policy_stop_reason.value,
            executed_turns=context.executed_turns,
            last_response=context.last_response.get_piece() if context.last_response else None,
            last_score=context.last_score,
            related_conversations=context.related_conversations,
            labels=context.memory_labels,
        )

    @staticmethod
    def _progress_decision_from_score(score: Score) -> ProgressDecision:
        metadata = score.score_metadata or {}
        serialized = metadata.get("progress_decision")
        if not isinstance(serialized, str):
            raise RuntimeError("project Score is missing its ProgressDecision metadata")
        decision = ProgressDecision.model_validate_json(serialized)
        if bool(score.get_value()) is not decision.objective_achieved:
            raise RuntimeError("project Score boolean contradicts its ProgressDecision")
        return decision


class PyRITAttackPolicy:
    """Execute one Run with an explicit attacker objective distinct from task and seed."""

    def __init__(
        self,
        *,
        adversarial_target_factory: Callable[[], PromptTarget],
    ) -> None:
        self._adversarial_target_factory = adversarial_target_factory

    async def run(
        self,
        *,
        run_spec: ExecutionRunSpec,
        attack_objective: str,
        target_session: TargetSession,
        progress_oracle: ProgressOracle,
        trace_sink: MutableSequence[CanonicalTraceEvent],
    ) -> AttackPolicyResult:
        normalized_attack_objective = attack_objective.strip()
        if not normalized_attack_objective:
            raise ValueError("attack_objective must not be blank")
        trace = _CanonicalTraceEmitter(run_id=run_spec.run_id, sink=trace_sink)
        scope = PyRITMemoryScope(run_id=run_spec.run_id)
        attack: _ProjectControlledRedTeamingAttack | None = None
        pyrit_result: AttackResult | None = None
        stop_reason: AttackPolicyStopReason | None = None
        policy_error: Exception | None = None

        async with scope:
            try:
                objective_target = TargetSessionPromptTarget(
                    run_id=run_spec.run_id,
                    target_session=target_session,
                    emit_trace=lambda event_type, strength, payload: trace.emit(
                        source="target_session_prompt_target",
                        event_type=event_type,
                        strength=strength,
                        payload=payload,
                    ),
                )
                scorer = AssertionBackedPyRITScorer(
                    run_id=run_spec.run_id,
                    oracle=progress_oracle,
                )
                adversarial_target = self._adversarial_target_factory()
                if adversarial_target._memory is not scope.memory:
                    raise RuntimeError(
                        "adversarial target must be created inside the active PyRITMemoryScope"
                    )
                attack = _ProjectControlledRedTeamingAttack(
                    objective_target=objective_target,
                    attack_adversarial_config=AttackAdversarialConfig(
                        target=adversarial_target,
                        seed_prompt=run_spec.attack_candidate.content,
                    ),
                    attack_scoring_config=AttackScoringConfig(
                        objective_scorer=scorer,
                        use_score_as_feedback=True,
                    ),
                    max_turns=run_spec.budget.max_turns,
                    trace_emitter=trace,
                )
                pyrit_result = await attack.execute_async(
                    objective=normalized_attack_objective,
                    memory_labels=scope.labels,
                )
                stop_reason = attack.policy_stop_reason
            except asyncio.CancelledError:
                trace.emit(
                    source="pyrit_attack_policy",
                    event_type="policy_stopped",
                    strength="harness_observed",
                    payload={"stop_reason": AttackPolicyStopReason.CANCELLED.value},
                )
                raise
            except Exception as error:
                policy_error = error
                stop_reason = (
                    AttackPolicyStopReason.TARGET_ERROR
                    if caused_by_target_session(error)
                    else AttackPolicyStopReason.POLICY_ERROR
                )
                persisted_results = scope.attack_results
                if persisted_results:
                    pyrit_result = persisted_results[-1]

            if stop_reason is None:
                raise RuntimeError("PyRIT policy completed without a stop reason")
            trace.emit(
                source="pyrit_attack_policy",
                event_type="policy_stopped",
                strength="harness_observed",
                payload={
                    "stop_reason": stop_reason.value,
                    "turns_executed": len(attack.turn_records) if attack else 0,
                },
            )

        if stop_reason is None:
            raise RuntimeError("PyRIT policy exited its memory scope without a stop reason")
        pyrit_outcome_value = "error" if pyrit_result is None else pyrit_result.outcome.value
        if pyrit_outcome_value not in {"success", "failure", "error"}:
            raise RuntimeError(f"unsupported PyRIT outcome: {pyrit_outcome_value}")
        pyrit_outcome = cast(
            Literal["success", "failure", "error"],
            pyrit_outcome_value,
        )
        turn_records = attack.turn_records if attack else ()
        return AttackPolicyResult(
            run_id=run_spec.run_id,
            policy_name=_POLICY_NAME,
            policy_version=_POLICY_VERSION,
            turns_executed=len(turn_records),
            stop_reason=stop_reason,
            final_progress_decision=attack.final_decision if attack else None,
            objective_conversation_id=attack.objective_conversation_id if attack else None,
            adversarial_conversation_id=(attack.adversarial_conversation_id if attack else None),
            turn_records=turn_records,
            pyrit_outcome=pyrit_outcome,
            pyrit_result_ref=(pyrit_result.attack_result_id if pyrit_result else None),
            raw_artifact_ref=scope.raw_artifact_ref,
            raw_artifact=scope.artifact,
            error_type=type(policy_error).__name__ if policy_error else None,
            error_message=str(policy_error) if policy_error else None,
        )
