from __future__ import annotations

import pytest

from agentsec_eval.domain import (
    AttackCandidate,
    ExecutionBudget,
    ExecutionRunSpec,
    ExecutionScenarioSpec,
    TargetConfiguration,
)
from agentsec_eval.execution import (
    execution_run_spec_from_metadata,
    execution_run_spec_to_sample,
)


def make_run_spec() -> ExecutionRunSpec:
    return ExecutionRunSpec(
        run_id="run-001",
        target=TargetConfiguration(
            target_id="fake-target",
            adapter="m0a-http",
            version="1",
        ),
        scenario=ExecutionScenarioSpec(
            scenario_id="scenario-001",
            user_task="Complete the deterministic three-turn task.",
            canary="canary-run-001",
        ),
        attack_candidate=AttackCandidate(
            candidate_id="candidate-001",
            content="Use the fixed M0-A candidate.",
        ),
        budget=ExecutionBudget(max_turns=3, timeout_seconds=30),
        repetition_seed=7,
    )


def test_run_spec_maps_to_one_sample_with_recoverable_metadata() -> None:
    run_spec = make_run_spec()

    sample = execution_run_spec_to_sample(
        run_spec,
        peer_canaries=("canary-run-002",),
        fail_after_session_open=True,
    )

    assert sample.id == run_spec.run_id
    assert sample.input == (
        "Complete the deterministic three-turn task.\n\nUse the fixed M0-A candidate."
    )
    assert sample.metadata is not None
    assert sample.metadata["agentsec_eval_schema_version"] == 1
    assert sample.metadata["m0a_peer_canaries"] == ["canary-run-002"]
    assert sample.metadata["m0a_fail_after_session_open"] is True
    assert execution_run_spec_from_metadata(sample.metadata) == run_spec


@pytest.mark.parametrize("schema_version", [None, 2])
def test_metadata_recovery_rejects_unknown_schema(schema_version: int | None) -> None:
    metadata: dict[str, object] = {
        "execution_run_spec": make_run_spec().model_dump(mode="json"),
    }
    if schema_version is not None:
        metadata["agentsec_eval_schema_version"] = schema_version

    with pytest.raises(ValueError, match="metadata schema version"):
        execution_run_spec_from_metadata(metadata)
