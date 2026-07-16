from __future__ import annotations

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
    assert all(sample.scores is not None for sample in samples)
    assert all(
        sample.scores["m0a_harness_validation_scorer"].value == CORRECT
        for sample in samples
        if sample.scores is not None
    )
    assert all(
        all(
            check["passed"]
            for check in sample.scores["m0a_harness_validation_scorer"].metadata["checks"].values()
        )
        for sample in samples
        if sample.scores is not None
        and sample.scores["m0a_harness_validation_scorer"].metadata is not None
    )
    assert len({sample.store["M0ARunState:session_id"] for sample in samples}) == 2
    assert len({sample.store["M0ARunState:sandbox_id"] for sample in samples}) == 2

    for sample in samples:
        events = sample.store["M0ARunState:events"]
        assert all(event["run_id"] == sample.id for event in events)
        assert len([event for event in events if event["event_type"] == "target_request"]) == 3
        assert len([event for event in events if event["event_type"] == "target_response"]) == 3
        assert {event["event_type"] for event in events} >= {
            "tool_call",
            "tool_result",
            "environment_effect",
            "session_closed",
        }
