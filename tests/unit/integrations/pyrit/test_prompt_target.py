from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from pydantic import JsonValue
from pyrit.memory import CentralMemory, SQLiteMemory
from pyrit.models import Message, MessagePiece

from agentsec_eval.domain import ObservationStrength, TraceEventType
from agentsec_eval.integrations.pyrit import TargetSessionPromptTarget
from agentsec_eval.targets import TargetTurnResult

pytestmark = pytest.mark.pyrit


class _PromptTargetTestMemory(SQLiteMemory):
    pass


@pytest.fixture(autouse=True)
def isolated_central_memory() -> Iterator[None]:
    previous = CentralMemory._memory_instance
    memory = _PromptTargetTestMemory(db_path=":memory:", silent=True)
    memory.reset_database()
    CentralMemory.set_memory_instance(memory)
    try:
        yield
    finally:
        memory.reset_database()
        CentralMemory._memory_instance = previous


class RecordingTargetSession:
    def __init__(
        self,
        results: list[TargetTurnResult],
        *,
        session_id: str = "session-1",
        error: Exception | None = None,
    ) -> None:
        self.session_id = session_id
        self.results = results
        self.error = error
        self.messages: list[str] = []

    async def send(self, message: str) -> TargetTurnResult:
        self.messages.append(message)
        if self.error is not None:
            raise self.error
        return self.results.pop(0)

    async def close(self) -> None:
        return None


TraceRecord = tuple[TraceEventType, ObservationStrength, dict[str, JsonValue]]


def make_message(prompt: str, *, conversation_id: str = "objective-conversation-1") -> Message:
    piece = MessagePiece(
        role="user",
        original_value=prompt,
        conversation_id=conversation_id,
    )
    piece.labels = {"agentsec_eval.run_id": "run-1"}
    return piece.to_message()


def test_prompt_target_reuses_project_session_and_preserves_lineage() -> None:
    session = RecordingTargetSession(
        [
            TargetTurnResult(session_id="session-1", turn=1, response="first response"),
            TargetTurnResult(session_id="session-1", turn=2, response="second response"),
        ]
    )
    trace: list[TraceRecord] = []
    target = TargetSessionPromptTarget(
        run_id="run-1",
        target_session=session,
        emit_trace=lambda event_type, strength, payload: trace.append(
            (event_type, strength, payload)
        ),
    )

    first = asyncio.run(target.send_prompt_async(message=make_message("attack-1")))
    second = asyncio.run(target.send_prompt_async(message=make_message("attack-2")))

    assert session.messages == ["attack-1", "attack-2"]
    assert first[0].conversation_id == second[0].conversation_id == "objective-conversation-1"
    assert first[0].get_value() == "first response"
    assert second[0].get_value() == "second response"
    assert first[0].get_piece().labels == {"agentsec_eval.run_id": "run-1"}
    assert [record[0] for record in trace] == [
        "target_request",
        "target_response",
        "target_request",
        "target_response",
    ]
    assert all(record[2]["project_session_id"] == "session-1" for record in trace)
    assert all(
        record[2]["objective_conversation_id"] == "objective-conversation-1" for record in trace
    )


def test_prompt_target_records_tool_calls_and_results() -> None:
    session = RecordingTargetSession(
        [
            TargetTurnResult.model_validate(
                {
                    "session_id": "session-1",
                    "turn": 1,
                    "response": "read file",
                    "tool_calls": [
                        {
                            "call_id": "call-1",
                            "name": "read_file",
                            "arguments": {"path": "/secret"},
                            "result": {"content": "canary"},
                        }
                    ],
                    "effect_path": "/effects/run-1.json",
                }
            )
        ]
    )
    trace: list[TraceRecord] = []
    target = TargetSessionPromptTarget(
        run_id="run-1",
        target_session=session,
        emit_trace=lambda event_type, strength, payload: trace.append(
            (event_type, strength, payload)
        ),
    )

    asyncio.run(target.send_prompt_async(message=make_message("read it")))

    assert [record[0] for record in trace] == [
        "target_request",
        "target_response",
        "tool_call",
        "tool_result",
    ]
    assert trace[1][2]["effect_path"] == "/effects/run-1.json"
    assert trace[2][2]["call_id"] == trace[3][2]["call_id"] == "call-1"


@pytest.mark.parametrize(
    ("results", "message"),
    [
        (
            [TargetTurnResult(session_id="session-other", turn=1, response="foreign")],
            "active project Session",
        ),
        (
            [
                TargetTurnResult(session_id="session-1", turn=2, response="first"),
                TargetTurnResult(session_id="session-1", turn=2, response="duplicate"),
            ],
            "strictly increase",
        ),
    ],
)
def test_prompt_target_rejects_uncorrelated_project_results(
    results: list[TargetTurnResult],
    message: str,
) -> None:
    session = RecordingTargetSession(results)
    target = TargetSessionPromptTarget(run_id="run-1", target_session=session)

    if len(results) == 2:
        asyncio.run(target.send_prompt_async(message=make_message("first")))
    with pytest.raises(RuntimeError, match=message):
        asyncio.run(target.send_prompt_async(message=make_message("stale")))


def test_prompt_target_wraps_target_session_errors_for_policy_classification() -> None:
    session = RecordingTargetSession([], error=ConnectionError("target unavailable"))
    target = TargetSessionPromptTarget(run_id="run-1", target_session=session)

    with pytest.raises(RuntimeError, match="project Target Session failed") as caught:
        asyncio.run(target.send_prompt_async(message=make_message("attack")))

    assert isinstance(caught.value.__cause__, ConnectionError)


def test_prompt_target_rejects_blank_run_and_session_ids() -> None:
    valid_session = RecordingTargetSession([], session_id="session-1")
    blank_session = RecordingTargetSession([], session_id=" ")

    with pytest.raises(ValueError, match="run_id must not be blank"):
        TargetSessionPromptTarget(run_id=" ", target_session=valid_session)
    with pytest.raises(ValueError, match="session_id must not be blank"):
        TargetSessionPromptTarget(run_id="run-1", target_session=blank_session)
