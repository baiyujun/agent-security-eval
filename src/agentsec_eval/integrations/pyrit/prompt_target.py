"""Adapt one open project Target Session to PyRIT's PromptTarget API."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from pydantic import JsonValue
from pyrit.models import ComponentIdentifier, Message, MessagePiece
from pyrit.prompt_target import PromptTarget, TargetCapabilities
from pyrit.prompt_target.common.target_configuration import TargetConfiguration

from agentsec_eval.domain import ObservationStrength, TraceEventType
from agentsec_eval.targets import TargetSession, TargetTurnResult

TraceEmitter = Callable[
    [TraceEventType, ObservationStrength, dict[str, JsonValue]],
    None,
]

_SOURCE: Final = "target_session_prompt_target"


class _TargetSessionPromptError(RuntimeError):
    """Identify failures originating at the project Target boundary."""


class TargetSessionPromptTarget(PromptTarget):
    """Route PyRIT objective prompts through one already-open Target Session."""

    _DEFAULT_CONFIGURATION = TargetConfiguration(
        capabilities=TargetCapabilities(supports_multi_turn=True)
    )

    def __init__(
        self,
        *,
        run_id: str,
        target_session: TargetSession,
        emit_trace: TraceEmitter | None = None,
    ) -> None:
        normalized_run_id = run_id.strip()
        if not normalized_run_id:
            raise ValueError("run_id must not be blank")
        normalized_session_id = target_session.session_id.strip()
        if not normalized_session_id:
            raise ValueError("session_id must not be blank")
        self._run_id = normalized_run_id
        self._target_session = target_session
        self._session_id = normalized_session_id
        self._emit_trace = emit_trace
        self._last_turn = 0
        self._last_turn_result: TargetTurnResult | None = None
        super().__init__(model_name="agentsec-eval-target-session")

    @property
    def last_turn_result(self) -> TargetTurnResult | None:
        """Return the latest validated project Target result."""

        return self._last_turn_result

    def _build_identifier(self) -> ComponentIdentifier:
        return self._create_identifier(
            params={
                "run_id": self._run_id,
                "project_session_id": self._session_id,
                "source": _SOURCE,
            }
        )

    async def _send_prompt_to_target_async(
        self,
        *,
        normalized_conversation: list[Message],
    ) -> list[Message]:
        request = normalized_conversation[-1].get_piece()
        common: dict[str, JsonValue] = {
            "run_id": self._run_id,
            "project_session_id": self._session_id,
            "objective_conversation_id": request.conversation_id,
        }
        self._emit(
            "target_request",
            "harness_observed",
            {**common, "message": request.converted_value},
        )
        try:
            result = await self._target_session.send(request.converted_value)
        except Exception as error:
            raise _TargetSessionPromptError("project Target Session failed") from error
        self._validate_result(result)
        self._last_turn_result = result

        self._emit(
            "target_response",
            "target_reported",
            {
                **common,
                "turn": result.turn,
                "response": result.response,
                "effect_path": result.effect_path,
            },
        )
        for tool_call in result.tool_calls:
            tool_common: dict[str, JsonValue] = {
                **common,
                "turn": result.turn,
                "call_id": tool_call.call_id,
            }
            self._emit(
                "tool_call",
                "target_reported",
                {
                    **tool_common,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                },
            )
            self._emit(
                "tool_result",
                "target_reported",
                {**tool_common, "result": tool_call.result},
            )

        response_piece = MessagePiece(role="assistant", original_value=result.response)
        response_piece.copy_lineage_from(source=request)
        response_piece.prompt_metadata = {
            **response_piece.prompt_metadata,
            "agentsec_eval.run_id": self._run_id,
            "agentsec_eval.project_session_id": self._session_id,
            "agentsec_eval.target_turn": result.turn,
        }
        return [response_piece.to_message()]

    def _validate_result(self, result: TargetTurnResult) -> None:
        if result.session_id != self._session_id:
            raise _TargetSessionPromptError(
                "Target response does not match the active project Session"
            )
        if result.turn <= self._last_turn:
            raise _TargetSessionPromptError("Target response turn must strictly increase")
        self._last_turn = result.turn

    def _emit(
        self,
        event_type: TraceEventType,
        strength: ObservationStrength,
        payload: dict[str, JsonValue],
    ) -> None:
        if self._emit_trace is not None:
            self._emit_trace(event_type, strength, payload)


def caused_by_target_session(error: BaseException) -> bool:
    """Return whether an exception chain originated in the project Target adapter."""

    current: BaseException | None = error
    while current is not None:
        if isinstance(current, _TargetSessionPromptError):
            return True
        current = current.__cause__
    return False
