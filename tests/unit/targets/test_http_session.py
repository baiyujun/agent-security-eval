from __future__ import annotations

import asyncio

import pytest
from pydantic import JsonValue, ValidationError

from agentsec_eval.domain import (
    AttackCandidate,
    ExecutionBudget,
    ExecutionRunSpec,
    ExecutionScenarioSpec,
    TargetConfiguration,
)
from agentsec_eval.targets import JsonHttpTargetAdapter, TargetToolCall, TargetTurnResult


class RecordingTransport:
    def __init__(self, responses: list[dict[str, JsonValue]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, JsonValue], int]] = []

    async def request(
        self,
        method: str,
        path: str,
        payload: dict[str, JsonValue],
        timeout: int,
    ) -> dict[str, JsonValue]:
        self.calls.append((method, path, payload, timeout))
        return self.responses.pop(0)


def make_run_spec() -> ExecutionRunSpec:
    return ExecutionRunSpec(
        run_id="run-001",
        target=TargetConfiguration(
            target_id="fake-target",
            adapter="m0a-http",
            version="1",
        ),
        scenario=ExecutionScenarioSpec(
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


def test_target_session_reuses_session_id() -> None:
    transport = RecordingTransport(
        [
            {"session_id": "session-001"},
            {"session_id": "session-001", "turn": 1, "response": "first"},
            {"session_id": "session-001", "turn": 2, "response": "second"},
        ]
    )

    session = asyncio.run(JsonHttpTargetAdapter(transport).open_session(make_run_spec()))
    first = asyncio.run(session.send("one"))
    second = asyncio.run(session.send("two"))

    assert first.session_id == second.session_id == session.session_id == "session-001"
    assert [call[1] for call in transport.calls] == [
        "/sessions",
        "/sessions/session-001/turns",
        "/sessions/session-001/turns",
    ]


def test_target_session_normalizes_tool_call_and_result() -> None:
    transport = RecordingTransport(
        [
            {"session_id": "session-001"},
            {
                "session_id": "session-001",
                "turn": 2,
                "response": "read fixture",
                "tool_calls": [
                    {
                        "call_id": "tool-001",
                        "name": "read_file",
                        "arguments": {"path": "/fixture.txt"},
                        "result": {"content": "fixture contents"},
                    }
                ],
            },
        ]
    )

    session = asyncio.run(JsonHttpTargetAdapter(transport).open_session(make_run_spec()))
    result = asyncio.run(session.send("two"))

    assert result.tool_calls == (
        TargetToolCall(
            call_id="tool-001",
            name="read_file",
            arguments={"path": "/fixture.txt"},
            result={"content": "fixture contents"},
        ),
    )


def test_target_session_close_is_idempotent() -> None:
    transport = RecordingTransport(
        [
            {"session_id": "session-001"},
            {"session_id": "session-001", "closed": True},
        ]
    )
    session = asyncio.run(JsonHttpTargetAdapter(transport).open_session(make_run_spec()))

    asyncio.run(session.close())
    asyncio.run(session.close())

    assert transport.calls[-1] == (
        "POST",
        "/sessions/session-001/close",
        {},
        30,
    )
    assert len(transport.calls) == 2


def test_target_session_preserves_reported_effect_path() -> None:
    transport = RecordingTransport(
        [
            {"session_id": "session-001"},
            {
                "session_id": "session-001",
                "turn": 3,
                "response": "environment effect written",
                "effect_path": "/effects/session-001.json",
            },
        ]
    )

    session = asyncio.run(JsonHttpTargetAdapter(transport).open_session(make_run_spec()))
    result = asyncio.run(session.send("three"))

    assert result.effect_path == "/effects/session-001.json"


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            TargetToolCall,
            {
                "call_id": "tool-001",
                "name": "read_file",
                "arguments": {},
                "result": None,
                "unexpected": True,
            },
        ),
        (
            TargetTurnResult,
            {
                "session_id": "session-001",
                "turn": 1,
                "response": "response",
                "unexpected": True,
            },
        ),
    ],
)
def test_target_results_forbid_unknown_fields(
    model: type[TargetToolCall] | type[TargetTurnResult],
    payload: dict[str, JsonValue],
) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        model.model_validate(payload)


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            TargetToolCall,
            {"call_id": " ", "name": "read_file", "arguments": {}, "result": None},
        ),
        (
            TargetToolCall,
            {"call_id": "tool-001", "name": " ", "arguments": {}, "result": None},
        ),
        (
            TargetTurnResult,
            {"session_id": " ", "turn": 1, "response": "response"},
        ),
    ],
)
def test_target_results_reject_blank_identifiers(
    model: type[TargetToolCall] | type[TargetTurnResult],
    payload: dict[str, JsonValue],
) -> None:
    with pytest.raises(ValidationError, match="string_too_short"):
        model.model_validate(payload)


def test_target_adapter_rejects_unknown_and_blank_open_session_fields() -> None:
    extra_transport = RecordingTransport([{"session_id": "session-001", "unexpected": True}])
    blank_transport = RecordingTransport([{"session_id": " "}])

    with pytest.raises(ValidationError, match="extra_forbidden"):
        asyncio.run(JsonHttpTargetAdapter(extra_transport).open_session(make_run_spec()))
    with pytest.raises(ValidationError, match="string_too_short"):
        asyncio.run(JsonHttpTargetAdapter(blank_transport).open_session(make_run_spec()))


def test_target_session_rejects_response_for_another_session() -> None:
    transport = RecordingTransport(
        [
            {"session_id": "session-001"},
            {"session_id": "session-other", "turn": 1, "response": "stale response"},
        ]
    )
    session = asyncio.run(JsonHttpTargetAdapter(transport).open_session(make_run_spec()))

    with pytest.raises(ValueError, match="active Session"):
        asyncio.run(session.send("one"))


@pytest.mark.parametrize("turns", [(1, 1), (2, 1)])
def test_target_session_rejects_non_increasing_turns(turns: tuple[int, int]) -> None:
    transport = RecordingTransport(
        [
            {"session_id": "session-001"},
            {"session_id": "session-001", "turn": turns[0], "response": "first"},
            {"session_id": "session-001", "turn": turns[1], "response": "stale"},
        ]
    )
    session = asyncio.run(JsonHttpTargetAdapter(transport).open_session(make_run_spec()))
    asyncio.run(session.send("one"))

    with pytest.raises(ValueError, match="strictly increase"):
        asyncio.run(session.send("two"))
