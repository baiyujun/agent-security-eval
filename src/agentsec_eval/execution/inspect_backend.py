"""Pure mappings between project run contracts and public Inspect dataset types."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from inspect_ai.dataset import Sample

from agentsec_eval.domain import ExecutionRunSpec
from agentsec_eval.scenario_assets.enums import Visibility
from agentsec_eval.scenario_assets.materialization import (
    MaterializedRunInput,
    materialized_input_digest,
)

M0A_METADATA_SCHEMA_VERSION = 1


def _sample_input(run_spec: ExecutionRunSpec) -> str:
    if not run_spec.attack_candidate.content:
        return run_spec.scenario.user_task
    return f"{run_spec.scenario.user_task}\n\n{run_spec.attack_candidate.content}"


def execution_run_spec_to_sample(
    run_spec: ExecutionRunSpec,
    *,
    peer_canaries: Sequence[str] = (),
    fail_after_session_open: bool = False,
    fail_session_close: bool = False,
) -> Sample:
    return Sample(
        id=run_spec.run_id,
        input=_sample_input(run_spec),
        metadata={
            "agentsec_eval_schema_version": M0A_METADATA_SCHEMA_VERSION,
            "execution_run_spec": run_spec.model_dump(mode="json"),
            "m0a_peer_canaries": list(peer_canaries),
            "m0a_fail_after_session_open": fail_after_session_open,
            "m0a_fail_session_close": fail_session_close,
        },
    )


def materialized_run_input_to_sample(materialized: MaterializedRunInput) -> Sample:
    """Map one fully materialized native run to one Inspect Sample."""

    if materialized.output_digest != materialized_input_digest(materialized):
        raise ValueError("materialized input digest is invalid")
    run_spec = materialized.compiled.execution_spec
    agent_files = {
        item.destination_path: item.content.decode("utf-8")
        for item in materialized.files
        if item.visibility is Visibility.AGENT_VISIBLE
    }
    private_files = [
        {
            "component_id": item.component_id,
            "destination_path": item.destination_path,
            "visibility": item.visibility.value,
            "content_digest": item.content_digest,
        }
        for item in materialized.files
        if item.visibility is not Visibility.AGENT_VISIBLE
    ]
    return Sample(
        id=run_spec.run_id,
        input=_sample_input(run_spec),
        files=agent_files,
        metadata={
            "agentsec_eval_schema_version": M0A_METADATA_SCHEMA_VERSION,
            "execution_run_spec": run_spec.model_dump(mode="json"),
            "materialization_digest": materialized.output_digest,
            "baseline_state_digest": materialized.baseline_state_digest,
            "materialized_state_digest": materialized.materialized_state_digest,
            "attack_materialized": materialized.attack_materialized,
            "placement_entry_point": (
                materialized.placement_entry_point.value
                if materialized.placement_entry_point is not None
                else None
            ),
            "channel_injections": [
                item.model_dump(mode="json") for item in materialized.channel_injections
            ],
            "private_file_manifest": private_files,
            "reset_plan": materialized.reset_plan.model_dump(mode="json"),
            "docker_environment_id": materialized.docker_environment_id,
        },
    )


def execution_run_spec_from_metadata(metadata: Mapping[str, object]) -> ExecutionRunSpec:
    schema_version = metadata.get("agentsec_eval_schema_version")
    if schema_version != M0A_METADATA_SCHEMA_VERSION:
        raise ValueError(f"unsupported metadata schema version: {schema_version!r}")
    return ExecutionRunSpec.model_validate(metadata["execution_run_spec"])
