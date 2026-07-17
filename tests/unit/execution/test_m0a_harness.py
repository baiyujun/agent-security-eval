from __future__ import annotations

import asyncio

import pytest

from agentsec_eval.domain import (
    AttackCandidate,
    ExecutionBudget,
    ExecutionRunSpec,
    ExecutionScenarioSpec,
    TargetConfiguration,
)
from agentsec_eval.execution import build_m0a_task
from agentsec_eval.execution.m0a_harness import (
    _attempt_session_close,
    _effect_evidence_check,
    _peer_canary_evidence_check,
)
from agentsec_eval.targets import TargetTurnResult


class FailingCloseSession:
    session_id = "session-close-failure"

    async def send(self, message: str) -> TargetTurnResult:
        raise AssertionError(f"send must not be called: {message}")

    async def close(self) -> None:
        raise RuntimeError("close failed")


def make_run_spec(run_id: str, canary: str) -> ExecutionRunSpec:
    return ExecutionRunSpec(
        run_id=run_id,
        target=TargetConfiguration(
            target_id="fake-target",
            adapter="m0a-http",
            version="1",
        ),
        scenario=ExecutionScenarioSpec(
            scenario_id=f"scenario-{run_id}",
            user_task="Complete the deterministic three-turn task.",
            canary=canary,
        ),
        attack_candidate=AttackCandidate(
            candidate_id=f"candidate-{run_id}",
            content="Use the fixed M0-A candidate.",
        ),
        budget=ExecutionBudget(max_turns=3, timeout_seconds=30),
        repetition_seed=7,
    )


def test_build_m0a_task_rejects_duplicate_run_ids() -> None:
    run_specs = [
        make_run_spec("duplicate", "canary-001"),
        make_run_spec("duplicate", "canary-002"),
    ]

    with pytest.raises(ValueError, match="M0-A Run IDs must be unique"):
        build_m0a_task(run_specs)


def test_build_m0a_task_rejects_duplicate_canaries() -> None:
    run_specs = [
        make_run_spec("run-001", "duplicate-canary"),
        make_run_spec("run-002", "duplicate-canary"),
    ]

    with pytest.raises(ValueError, match="M0-A Canaries must be unique"):
        build_m0a_task(run_specs)


def test_attempt_session_close_returns_failure_for_solver_adjudication() -> None:
    error = asyncio.run(_attempt_session_close(FailingCloseSession()))

    assert isinstance(error, RuntimeError)
    assert str(error) == "close failed"


def test_effect_evidence_check_reports_invalid_json() -> None:
    check = _effect_evidence_check(
        "not-json",
        expected={"run_id": "run-001", "session_id": "session-001", "canary": "canary-001"},
        effect_path="/effects/session-001.json",
    )

    assert check["passed"] is False
    assert "invalid JSON" in str(check["detail"])


def test_peer_canary_evidence_check_rejects_invalid_metadata() -> None:
    check = _peer_canary_evidence_check(
        scan_success=True,
        scan_output="current-canary",
        peer_canaries="not-a-list",
    )

    assert check["passed"] is False
    assert "list of strings" in str(check["detail"])
