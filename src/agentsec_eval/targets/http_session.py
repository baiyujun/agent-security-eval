"""JSON-over-transport implementation of the project Target boundary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, JsonValue

from agentsec_eval.domain import ExecutionRunSpec
from agentsec_eval.targets.protocol import JsonRequestTransport, TargetTurnResult


class _OpenSessionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str


class JsonHttpTargetAdapter:
    def __init__(self, transport: JsonRequestTransport) -> None:
        self._transport = transport

    async def open_session(self, run_spec: ExecutionRunSpec) -> _JsonHttpTargetSession:
        payload: dict[str, JsonValue] = {
            "run_id": run_spec.run_id,
            "target_id": run_spec.target.target_id,
            "scenario_id": run_spec.scenario.scenario_id,
            "canary": run_spec.scenario.canary,
        }
        response = await self._transport.request(
            "POST",
            "/sessions",
            payload,
            run_spec.budget.timeout_seconds,
        )
        opened = _OpenSessionResult.model_validate(response)
        return _JsonHttpTargetSession(
            transport=self._transport,
            session_id=opened.session_id,
            timeout=run_spec.budget.timeout_seconds,
        )


class _JsonHttpTargetSession:
    def __init__(
        self,
        *,
        transport: JsonRequestTransport,
        session_id: str,
        timeout: int,
    ) -> None:
        self._transport = transport
        self.session_id = session_id
        self._timeout = timeout
        self._closed = False

    async def send(self, message: str) -> TargetTurnResult:
        response = await self._transport.request(
            "POST",
            f"/sessions/{self.session_id}/turns",
            {"message": message},
            self._timeout,
        )
        return TargetTurnResult.model_validate(response)

    async def close(self) -> None:
        if self._closed:
            return
        await self._transport.request(
            "POST",
            f"/sessions/{self.session_id}/close",
            {},
            self._timeout,
        )
        self._closed = True
