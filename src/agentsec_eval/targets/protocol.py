"""Project-owned Target interfaces and normalized result contracts."""

from __future__ import annotations

from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, JsonValue, PositiveInt, StringConstraints

from agentsec_eval.domain import ExecutionRunSpec

_NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TargetToolCall(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    call_id: _NonEmptyText
    name: _NonEmptyText
    arguments: dict[str, JsonValue]
    result: JsonValue


class TargetTurnResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: _NonEmptyText
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
