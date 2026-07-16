"""Pure mappings between project run contracts and public Inspect dataset types."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from inspect_ai.dataset import Sample

from agentsec_eval.domain import ExecutionRunSpec

M0A_METADATA_SCHEMA_VERSION = 1


def execution_run_spec_to_sample(
    run_spec: ExecutionRunSpec,
    *,
    peer_canaries: Sequence[str] = (),
    fail_after_session_open: bool = False,
    fail_session_close: bool = False,
) -> Sample:
    return Sample(
        id=run_spec.run_id,
        input=f"{run_spec.scenario.user_task}\n\n{run_spec.attack_candidate.content}",
        metadata={
            "agentsec_eval_schema_version": M0A_METADATA_SCHEMA_VERSION,
            "execution_run_spec": run_spec.model_dump(mode="json"),
            "m0a_peer_canaries": list(peer_canaries),
            "m0a_fail_after_session_open": fail_after_session_open,
            "m0a_fail_session_close": fail_session_close,
        },
    )


def execution_run_spec_from_metadata(metadata: Mapping[str, object]) -> ExecutionRunSpec:
    schema_version = metadata.get("agentsec_eval_schema_version")
    if schema_version != M0A_METADATA_SCHEMA_VERSION:
        raise ValueError(f"unsupported metadata schema version: {schema_version!r}")
    return ExecutionRunSpec.model_validate(metadata["execution_run_spec"])
