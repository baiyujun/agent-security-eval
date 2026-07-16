from __future__ import annotations

from pathlib import Path

import pytest
from conftest import (
    make_run_spec,
    materialize_samples,
    observe_new_resources_during,
    snapshot_resources,
    wait_for_no_new_resources,
)

from agentsec_eval.execution import run_m0a_validation


@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.timeout(180)
def test_solver_failure_closes_session_and_removes_new_resources(
    tmp_path: Path,
    resource_token: str,
) -> None:
    baseline = snapshot_resources(resource_token)

    try:
        logs, observed = observe_new_resources_during(
            resource_token,
            baseline,
            lambda: run_m0a_validation(
                [
                    make_run_spec("run-failure"),
                    make_run_spec("run-close-failure"),
                ],
                log_dir=tmp_path,
                fail_run_ids={"run-failure", "run-close-failure"},
                fail_session_close_run_ids={"run-close-failure"},
            ),
        )
    finally:
        wait_for_no_new_resources(resource_token, baseline, timeout_seconds=30)

    assert len(observed.containers) >= 4
    assert len(observed.networks) >= 2
    samples = {sample.id: sample for sample in materialize_samples(logs)}
    assert set(samples) == {"run-failure", "run-close-failure"}

    normally_closed = samples["run-failure"]
    assert normally_closed.error is not None
    normal_events = normally_closed.store["M0ARunState:events"]
    assert {event["event_type"] for event in normal_events} >= {
        "session_opened",
        "harness_error",
        "session_closed",
    }
    assert len([event for event in normal_events if event["event_type"] == "harness_error"]) == 1

    close_failed = samples["run-close-failure"]
    assert close_failed.error is not None
    assert "M0-A injected failure after session open" in close_failed.error.message
    close_failed_events = close_failed.store["M0ARunState:events"]
    harness_errors = [
        event for event in close_failed_events if event["event_type"] == "harness_error"
    ]
    assert len(harness_errors) == 2
    assert any(event["payload"].get("phase") == "session_close" for event in harness_errors)
    assert "session_closed" not in {event["event_type"] for event in close_failed_events}
