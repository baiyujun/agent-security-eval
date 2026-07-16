from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from conftest import materialize_samples, two_run_specs
from inspect_ai.scorer import CORRECT

from agentsec_eval.execution import run_m0a_validation


@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.timeout(180)
def test_two_samples_keep_sessions_stores_canaries_and_effects_isolated(
    tmp_path: Path,
    resource_token: str,
) -> None:
    assert resource_token

    logs = run_m0a_validation(two_run_specs(), log_dir=tmp_path)
    samples = materialize_samples(logs)

    assert len(logs) == 1
    assert logs[0].status == "success"
    assert logs[0].location
    assert {sample.id for sample in samples} == {"run-001", "run-002"}
    assert all(sample.error is None for sample in samples)
    assert all(
        sample.started_at is not None and sample.completed_at is not None for sample in samples
    )
    starts = [datetime.fromisoformat(sample.started_at) for sample in samples if sample.started_at]
    completions = [
        datetime.fromisoformat(sample.completed_at) for sample in samples if sample.completed_at
    ]
    assert max(starts) < min(completions), "Sample execution intervals must overlap"

    required_checks = {
        "run_identity",
        "single_session",
        "three_turns",
        "tool_events",
        "trace_invariants",
        "sample_sandbox",
        "confirmed_environment_evidence",
        "direct_effect_read",
        "peer_canary_absent",
    }
    for sample in samples:
        assert sample.scores is not None
        score = sample.scores["m0a_harness_validation_scorer"]
        assert score.value == CORRECT
        assert score.metadata is not None
        checks = score.metadata["checks"]
        assert set(checks) == required_checks
        assert all(check["passed"] for check in checks.values())

    assert len({sample.store["M0ARunState:session_id"] for sample in samples}) == 2
    assert len({sample.store["M0ARunState:sandbox_id"] for sample in samples}) == 2

    for sample in samples:
        events = sample.store["M0ARunState:events"]
        sandbox_id = sample.store["M0ARunState:sandbox_id"]
        sandbox_observations = sample.store["M0ARunState:sandbox_observations"]
        assert len(sandbox_observations) == 7
        assert set(sandbox_observations) == {sandbox_id}
        assert all(event["run_id"] == sample.id for event in events)
        assert len([event for event in events if event["event_type"] == "target_request"]) == 3
        assert len([event for event in events if event["event_type"] == "target_response"]) == 3
        assert {event["event_type"] for event in events} >= {
            "tool_call",
            "tool_result",
            "environment_effect",
            "session_closed",
        }
