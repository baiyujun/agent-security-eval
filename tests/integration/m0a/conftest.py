from __future__ import annotations

import os
import subprocess
import time
import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

import pytest
from inspect_ai.log import EvalLog, EvalSample

from agentsec_eval.domain import (
    AttackCandidate,
    ExecutionBudget,
    ExecutionRunSpec,
    ScenarioSpec,
    TargetConfiguration,
)


def make_run_spec(run_id: str) -> ExecutionRunSpec:
    return ExecutionRunSpec(
        run_id=run_id,
        target=TargetConfiguration(
            target_id="fake-target",
            adapter="m0a-http",
            version="1",
        ),
        scenario=ScenarioSpec(
            scenario_id=f"scenario-{run_id}",
            user_task="Complete the deterministic three-turn task.",
            canary=f"canary-{run_id}",
        ),
        attack_candidate=AttackCandidate(
            candidate_id=f"candidate-{run_id}",
            content="Use the fixed M0-A candidate.",
        ),
        budget=ExecutionBudget(max_turns=3, timeout_seconds=30),
        repetition_seed=7,
    )


def two_run_specs() -> list[ExecutionRunSpec]:
    return [make_run_spec("run-001"), make_run_spec("run-002")]


def materialize_samples(logs: Sequence[EvalLog]) -> list[EvalSample]:
    return [sample for log in logs for sample in (log.samples or [])]


@dataclass(frozen=True)
class DockerResources:
    containers: frozenset[str]
    networks: frozenset[str]


def _docker_ids(command: list[str]) -> frozenset[str]:
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return frozenset(line for line in result.stdout.splitlines() if line)


def snapshot_resources(resource_token: str) -> DockerResources:
    label = f"agentsec_eval.m0a.token={resource_token}"
    return DockerResources(
        containers=_docker_ids(["docker", "ps", "-aq", "--filter", f"label={label}"]),
        networks=_docker_ids(["docker", "network", "ls", "-q", "--filter", f"label={label}"]),
    )


def wait_for_no_new_resources(
    resource_token: str,
    baseline: DockerResources,
    *,
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        current = snapshot_resources(resource_token)
        new_containers = current.containers - baseline.containers
        new_networks = current.networks - baseline.networks
        if not new_containers and not new_networks:
            return
        if time.monotonic() >= deadline:
            pytest.fail(
                f"M0-A Docker resources leaked: containers={sorted(new_containers)}, "
                f"networks={sorted(new_networks)}"
            )
        time.sleep(0.25)


def _docker_unavailable_reason() -> str | None:
    for command in (["docker", "version"], ["docker", "compose", "version"]):
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return f"{' '.join(command)} failed: {error}"
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            return f"{' '.join(command)} exited {result.returncode}: {detail}"
    return None


@pytest.fixture(autouse=True)
def require_docker(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("docker") is None:
        return
    reason = _docker_unavailable_reason()
    if reason is None:
        return
    if os.environ.get("CI"):
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture
def resource_token(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    token = f"pytest-{uuid.uuid4().hex}"
    monkeypatch.setenv("M0A_RESOURCE_TOKEN", token)
    yield token
