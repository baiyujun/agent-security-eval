"""Project-owned Target interfaces and normalized result contracts."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, JsonValue, PositiveInt

from agentsec_eval.domain import ExecutionRunSpec


class TargetToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    call_id: str
    name: str
    arguments: dict[str, JsonValue]
    result: JsonValue


class TargetTurnResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    turn: PositiveInt
    response: str
    tool_calls: tuple[TargetToolCall, ...] = ()
    effect_path: str | None = None


class TargetSession(Protocol):
    session_id: str

    async def send(self, message: str) -> TargetTurnResult: ...

    async def close(self) -> None: ...


class TargetAdapter(Protocol):
    async def open_session(self, run_spec: ExecutionRunSpec) -> TargetSession: ...


class JsonRequestTransport(Protocol):
    async def request(
        self,
        method: str,
        path: str,
        payload: dict[str, JsonValue],
        timeout: int,
    ) -> dict[str, JsonValue]: ...
