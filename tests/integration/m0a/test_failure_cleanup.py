from __future__ import annotations

from pathlib import Path

import pytest
from conftest import (
    make_run_spec,
    materialize_samples,
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
        logs = run_m0a_validation(
            [make_run_spec("run-failure")],
            log_dir=tmp_path,
            fail_run_ids={"run-failure"},
        )
    finally:
        wait_for_no_new_resources(resource_token, baseline, timeout_seconds=30)

    samples = materialize_samples(logs)
    assert len(samples) == 1
    assert samples[0].error is not None
    events = samples[0].store["M0ARunState:events"]
    assert {event["event_type"] for event in events} >= {
        "session_opened",
        "harness_error",
        "session_closed",
    }
