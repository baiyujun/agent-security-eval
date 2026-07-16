"""M0-A-only Inspect harness for validating the formal execution boundary."""

from __future__ import annotations

import json
from collections.abc import Sequence, Set
from pathlib import Path
from typing import cast

from inspect_ai import Task, eval
from inspect_ai.dataset import MemoryDataset
from inspect_ai.log import EvalLog
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import StoreModel, sandbox, store_as
from pydantic import Field, JsonValue

from agentsec_eval.domain import (
    CanonicalTraceEvent,
    ExecutionRunSpec,
    ObservationStrength,
    TraceEventType,
    validate_trace,
)
from agentsec_eval.execution.inspect_backend import (
    execution_run_spec_from_metadata,
    execution_run_spec_to_sample,
)
from agentsec_eval.targets import (
    JsonHttpTargetAdapter,
    JsonRequestTransport,
    TargetSession,
    TargetTurnResult,
)

M0A_COMPOSE_FILE = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "m0a_inspect" / "compose.yaml"
)


class M0ARunState(StoreModel):
    run_id: str = ""
    session_id: str = ""
    sandbox_id: str = ""
    next_sequence: int = 1
    events: list[CanonicalTraceEvent] = Field(default_factory=list)


class InspectSandboxJsonTransport(JsonRequestTransport):
    def __init__(self, service: str = "default") -> None:
        self._service = service

    async def request(
        self,
        method: str,
        path: str,
        payload: dict[str, JsonValue],
        timeout: int,
    ) -> dict[str, JsonValue]:
        request = json.dumps(
            {
                "method": method,
                "path": path,
                "payload": payload,
                "timeout": timeout,
            },
            sort_keys=True,
        )
        result = await sandbox(self._service).exec(
            ["python", "/opt/m0a/client.py"],
            input=request,
            timeout=timeout,
        )
        if not result.success:
            raise RuntimeError(
                f"Target transport failed with exit {result.returncode}: {result.stderr.strip()}"
            )
        decoded = json.loads(result.stdout)
        if not isinstance(decoded, dict):
            raise ValueError("Target transport response must be a JSON object")
        return cast(dict[str, JsonValue], decoded)


def _append_event(
    runtime: M0ARunState,
    run_spec: ExecutionRunSpec,
    event_type: TraceEventType,
    observation_strength: ObservationStrength,
    payload: dict[str, JsonValue],
) -> None:
    sequence = runtime.next_sequence
    event = CanonicalTraceEvent(
        event_id=f"{run_spec.run_id}:{sequence}",
        run_id=run_spec.run_id,
        sequence=sequence,
        event_type=event_type,
        source="m0a_inspect_harness",
        observation_strength=observation_strength,
        payload=payload,
    )
    runtime.events = [*runtime.events, event]
    runtime.next_sequence = sequence + 1


def _record_turn(
    runtime: M0ARunState,
    run_spec: ExecutionRunSpec,
    result: TargetTurnResult,
) -> None:
    response_payload: dict[str, JsonValue] = {
        "session_id": result.session_id,
        "turn": result.turn,
        "response": result.response,
        "effect_path": result.effect_path,
        "sandbox_id": runtime.sandbox_id,
    }
    _append_event(
        runtime,
        run_spec,
        "target_response",
        "target_reported",
        response_payload,
    )
    for tool_call in result.tool_calls:
        common: dict[str, JsonValue] = {
            "call_id": tool_call.call_id,
            "session_id": result.session_id,
            "turn": result.turn,
            "sandbox_id": runtime.sandbox_id,
        }
        _append_event(
            runtime,
            run_spec,
            "tool_call",
            "target_reported",
            {**common, "name": tool_call.name, "arguments": tool_call.arguments},
        )
        _append_event(
            runtime,
            run_spec,
            "tool_result",
            "target_reported",
            {**common, "result": tool_call.result},
        )


async def _confirm_environment_effect(
    runtime: M0ARunState,
    run_spec: ExecutionRunSpec,
    result: TargetTurnResult,
) -> None:
    if result.effect_path is None:
        return
    raw_effect = await sandbox("target").read_file(result.effect_path)
    if not isinstance(raw_effect, str):
        raise ValueError("M0-A effect file must be UTF-8 text")
    decoded = json.loads(raw_effect)
    expected = {
        "run_id": run_spec.run_id,
        "session_id": runtime.session_id,
        "canary": run_spec.scenario.canary,
    }
    if decoded != expected:
        raise ValueError("M0-A effect file does not match the active Run and Session")
    _append_event(
        runtime,
        run_spec,
        "environment_effect",
        "environment_confirmed",
        {
            "effect_path": result.effect_path,
            "run_id": run_spec.run_id,
            "session_id": runtime.session_id,
            "canary": run_spec.scenario.canary,
            "sandbox_id": runtime.sandbox_id,
        },
    )


@solver
def m0a_solver() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        del generate
        metadata = state.metadata or {}
        run_spec = execution_run_spec_from_metadata(metadata)
        if str(state.sample_id) != run_spec.run_id:
            raise ValueError("Sample ID must match the project Run ID")
        if run_spec.budget.max_turns < 3:
            raise ValueError("M0-A requires an execution budget of at least three turns")

        connection = await sandbox("default").connection()
        if connection.container is None:
            raise RuntimeError("Docker Sandbox did not expose a container identity")

        runtime = store_as(M0ARunState)
        runtime.run_id = run_spec.run_id
        runtime.sandbox_id = connection.container
        session: TargetSession | None = None
        try:
            transport = InspectSandboxJsonTransport("default")
            session = await JsonHttpTargetAdapter(transport).open_session(run_spec)
            runtime.session_id = session.session_id
            _append_event(
                runtime,
                run_spec,
                "session_opened",
                "harness_observed",
                {
                    "session_id": session.session_id,
                    "sandbox_id": runtime.sandbox_id,
                },
            )
            if metadata.get("m0a_fail_after_session_open") is True:
                raise RuntimeError("M0-A injected failure after session open")

            for turn in range(1, 4):
                _append_event(
                    runtime,
                    run_spec,
                    "target_request",
                    "harness_observed",
                    {
                        "session_id": session.session_id,
                        "turn": turn,
                        "message": f"turn-{turn}",
                        "sandbox_id": runtime.sandbox_id,
                    },
                )
                result = await session.send(f"turn-{turn}")
                _record_turn(runtime, run_spec, result)
                await _confirm_environment_effect(runtime, run_spec, result)
            return state
        except Exception as error:
            _append_event(
                runtime,
                run_spec,
                "harness_error",
                "harness_observed",
                {"error_type": type(error).__name__, "message": str(error)},
            )
            raise
        finally:
            if session is not None:
                await session.close()
                _append_event(
                    runtime,
                    run_spec,
                    "session_closed",
                    "harness_observed",
                    {
                        "session_id": session.session_id,
                        "sandbox_id": runtime.sandbox_id,
                    },
                )

    return solve


def _check(passed: bool, detail: str) -> dict[str, JsonValue]:
    return {"passed": passed, "detail": detail}


@scorer(metrics=[])
def m0a_harness_validation_scorer() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        del target
        metadata = state.metadata or {}
        run_spec = execution_run_spec_from_metadata(metadata)
        runtime = store_as(M0ARunState)
        events = runtime.events

        checks: dict[str, dict[str, JsonValue]] = {}
        identity_matches = str(state.sample_id) == run_spec.run_id == runtime.run_id and all(
            event.run_id == run_spec.run_id for event in events
        )
        checks["run_identity"] = _check(
            identity_matches,
            "Sample, metadata, Store, and Trace Run IDs",
        )

        session_ids = {
            session_id
            for event in events
            if isinstance((session_id := event.payload.get("session_id")), str)
        }
        checks["single_session"] = _check(
            session_ids == {runtime.session_id},
            f"observed Session IDs: {sorted(session_ids)}",
        )

        requests = [event for event in events if event.event_type == "target_request"]
        responses = [event for event in events if event.event_type == "target_response"]
        checks["three_turns"] = _check(
            len(requests) >= 3 and len(responses) >= 3,
            f"requests={len(requests)}, responses={len(responses)}",
        )
        event_types = {event.event_type for event in events}
        checks["tool_events"] = _check(
            {"tool_call", "tool_result"}.issubset(event_types),
            "tool_call and tool_result must both be present",
        )

        try:
            validate_trace(events, expected_run_id=run_spec.run_id)
        except ValueError as error:
            checks["trace_invariants"] = _check(False, str(error))
        else:
            checks["trace_invariants"] = _check(True, "unique IDs and strictly increasing sequence")

        turn_sandbox_ids = {event.payload.get("sandbox_id") for event in [*requests, *responses]}
        checks["sample_sandbox"] = _check(
            turn_sandbox_ids == {runtime.sandbox_id},
            f"turn Sandbox IDs: {sorted(str(value) for value in turn_sandbox_ids)}",
        )

        environment_events = [event for event in events if event.event_type == "environment_effect"]
        checks["confirmed_environment_evidence"] = _check(
            len(environment_events) == 1
            and environment_events[0].observation_strength == "environment_confirmed",
            f"confirmed environment events: {len(environment_events)}",
        )

        effect_matches = False
        effect_detail = "no confirmed effect path"
        if environment_events:
            effect_path = environment_events[0].payload.get("effect_path")
            if isinstance(effect_path, str):
                raw_effect = await sandbox("target").read_file(effect_path)
                if isinstance(raw_effect, str):
                    effect = json.loads(raw_effect)
                    expected_effect = {
                        "run_id": run_spec.run_id,
                        "session_id": runtime.session_id,
                        "canary": run_spec.scenario.canary,
                    }
                    effect_matches = effect == expected_effect
                    effect_detail = f"effect file {effect_path} matches active identity"
        checks["direct_effect_read"] = _check(effect_matches, effect_detail)

        scan = await sandbox("target").exec(
            [
                "python",
                "-c",
                (
                    "from pathlib import Path; "
                    "print('\\n'.join(p.read_text() for p in Path('/effects').glob('*.json')))"
                ),
            ],
            timeout=10,
        )
        peer_canaries = metadata.get("m0a_peer_canaries", [])
        if not isinstance(peer_canaries, list) or not all(
            isinstance(canary, str) for canary in peer_canaries
        ):
            raise ValueError("m0a_peer_canaries must be a list of strings")
        peer_absent = scan.success and all(canary not in scan.stdout for canary in peer_canaries)
        checks["peer_canary_absent"] = _check(
            peer_absent,
            "direct scan of every target effect file excludes peer canaries",
        )

        passed = all(bool(check["passed"]) for check in checks.values())
        return Score(
            value=CORRECT if passed else INCORRECT,
            explanation="M0-A execution harness checks passed" if passed else "M0-A checks failed",
            metadata={"checks": checks},
        )

    return score


def build_m0a_task(
    run_specs: Sequence[ExecutionRunSpec],
    *,
    fail_run_ids: Set[str] = frozenset(),
) -> Task:
    if not run_specs:
        raise ValueError("M0-A requires at least one Run Spec")
    canaries = [run_spec.scenario.canary for run_spec in run_specs]
    samples = [
        execution_run_spec_to_sample(
            run_spec,
            peer_canaries=[canary for canary in canaries if canary != run_spec.scenario.canary],
            fail_after_session_open=run_spec.run_id in fail_run_ids,
        )
        for run_spec in run_specs
    ]
    return Task(
        dataset=MemoryDataset(samples=samples, name="m0a-inspect-execution-validation"),
        solver=m0a_solver(),
        scorer=m0a_harness_validation_scorer(),
        sandbox=("docker", str(M0A_COMPOSE_FILE)),
        name="m0a_inspect_execution_validation",
    )


def run_m0a_validation(
    run_specs: Sequence[ExecutionRunSpec],
    *,
    log_dir: str | Path,
    fail_run_ids: Set[str] = frozenset(),
) -> list[EvalLog]:
    task = build_m0a_task(run_specs, fail_run_ids=fail_run_ids)
    return eval(
        task,
        model="mockllm/model",
        max_samples=min(2, len(run_specs)),
        max_sandboxes=min(2, len(run_specs)),
        log_dir=str(log_dir),
        display="none",
        sandbox_cleanup=True,
        fail_on_error=False,
    )
