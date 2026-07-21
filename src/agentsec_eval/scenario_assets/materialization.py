"""Placement-aware materialization of compiled scenario cases."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Self

from pydantic import model_validator

from agentsec_eval.scenario_assets.compiler import CompiledRunInput, compiled_input_digest
from agentsec_eval.scenario_assets.enums import AttackDeliveryMode, EntryPoint, Visibility
from agentsec_eval.scenario_assets.models import (
    AssetId,
    FixtureDefinition,
    FrozenModel,
    ResetStep,
    Sha256Digest,
)
from agentsec_eval.scenario_assets.storage import (
    LoadedExecutableScenarioPack,
    LoadedPackFile,
)
from agentsec_eval.scenario_assets.validation import validate_pack_for_execution


class MaterializedFile(FrozenModel):
    component_id: AssetId
    source_path: str
    destination_path: str
    visibility: Visibility
    baseline_content_digest: Sha256Digest
    content_digest: Sha256Digest
    baseline_content: bytes
    content: bytes

    @model_validator(mode="after")
    def validate_content_digests(self) -> Self:
        if _digest(self.baseline_content) != self.baseline_content_digest:
            raise ValueError("baseline_content_digest does not match materialized file")
        if _digest(self.content) != self.content_digest:
            raise ValueError("content_digest does not match materialized file")
        return self


class MaterializedChannelInjection(FrozenModel):
    injection_id: AssetId
    entry_point: EntryPoint
    target_id: AssetId
    content_digest: Sha256Digest
    content: str

    @model_validator(mode="after")
    def validate_content_digest(self) -> Self:
        if _digest(self.content.encode("utf-8")) != self.content_digest:
            raise ValueError("content_digest does not match channel injection")
        return self


class MaterializedResetPlan(FrozenModel):
    reset_contract_id: AssetId
    baseline_state_digest: Sha256Digest
    mutable_resource_ids: tuple[AssetId, ...]
    steps: tuple[ResetStep, ...]
    verification_probe_ids: tuple[AssetId, ...]


class MaterializedRunInput(FrozenModel):
    compiled: CompiledRunInput
    files: tuple[MaterializedFile, ...]
    channel_injections: tuple[MaterializedChannelInjection, ...]
    placement_entry_point: EntryPoint | None
    attack_materialized: bool
    baseline_state_digest: Sha256Digest
    materialized_state_digest: Sha256Digest
    reset_plan: MaterializedResetPlan
    docker_environment_id: AssetId
    output_digest: Sha256Digest | None


class MaterializedEnvironmentState(FrozenModel):
    state_digest: Sha256Digest
    file_paths: tuple[str, ...]


class EnvironmentResetResult(FrozenModel):
    state_digest: Sha256Digest
    baseline_restored: bool
    file_paths: tuple[str, ...]


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _digest(encoded)


def environment_baseline_digest(fixtures: Iterable[FixtureDefinition]) -> str:
    """Digest the declared pre-injection fixture state and visibility boundaries."""

    entries = sorted(
        (
            {
                "component_id": fixture.fixture_id,
                "destination_path": fixture.materialization_path,
                "visibility": fixture.visibility.value,
                "content_digest": fixture.content_digest,
            }
            for fixture in fixtures
        ),
        key=lambda item: (item["visibility"], item["destination_path"], item["component_id"]),
    )
    return _canonical_digest(entries)


def materialized_state_digest(files: Iterable[MaterializedFile]) -> str:
    entries = sorted(
        (
            {
                "component_id": item.component_id,
                "destination_path": item.destination_path,
                "visibility": item.visibility.value,
                "content_digest": item.content_digest,
            }
            for item in files
            if item.source_path.startswith("fixtures/")
        ),
        key=lambda item: (item["visibility"], item["destination_path"], item["component_id"]),
    )
    return _canonical_digest(entries)


def materialized_input_digest(materialized: MaterializedRunInput) -> str:
    return _canonical_digest(materialized.model_dump(mode="json", exclude={"output_digest"}))


def _loaded_file_by_component(
    loaded: LoadedExecutableScenarioPack,
) -> dict[str, LoadedPackFile]:
    indexed: dict[str, LoadedPackFile] = {}
    for item in loaded.files:
        if item.component_id in indexed:
            raise ValueError(f"component has multiple physical files: {item.component_id}")
        indexed[item.component_id] = item
    return indexed


def _materialized_files(
    loaded: LoadedExecutableScenarioPack,
) -> list[MaterializedFile]:
    source_files = _loaded_file_by_component(loaded)
    files: list[MaterializedFile] = []
    for fixture in loaded.pack.fixtures:
        source = source_files[fixture.fixture_id]
        files.append(
            MaterializedFile(
                component_id=fixture.fixture_id,
                source_path=source.relative_path,
                destination_path=fixture.materialization_path,
                visibility=fixture.visibility,
                baseline_content_digest=source.content_digest,
                content_digest=source.content_digest,
                baseline_content=source.content,
                content=source.content,
            )
        )
    for service in loaded.pack.tool_services:
        source = source_files[service.tool_service_id]
        files.append(
            MaterializedFile(
                component_id=service.tool_service_id,
                source_path=source.relative_path,
                destination_path=service.materialization_path,
                visibility=service.visibility,
                baseline_content_digest=source.content_digest,
                content_digest=source.content_digest,
                baseline_content=source.content,
                content=source.content,
            )
        )
    destinations = [(item.visibility, item.destination_path) for item in files]
    if len(destinations) != len(set(destinations)):
        raise ValueError("materialized destination paths must be unique within a visibility plane")
    return files


def _replace_file(
    files: list[MaterializedFile],
    component_id: str,
    content: bytes,
) -> None:
    for index, item in enumerate(files):
        if item.component_id == component_id:
            files[index] = item.model_copy(
                update={"content": content, "content_digest": _digest(content)}
            )
            return
    raise ValueError(f"attack insertion target does not resolve: {component_id}")


def _json_document(item: MaterializedFile) -> dict[str, object]:
    try:
        value = json.loads(item.content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"attack target must contain valid JSON: {item.component_id}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"attack target JSON must be an object: {item.component_id}")
    return value


def _inject_file_placement(
    files: list[MaterializedFile],
    *,
    entry_point: EntryPoint,
    target_id: str,
    content: str,
    source_comment_prefix: str | None,
) -> None:
    target = next((item for item in files if item.component_id == target_id), None)
    if target is None:
        raise ValueError(f"attack insertion target does not resolve: {target_id}")
    if entry_point is EntryPoint.ISSUE:
        document = _json_document(target)
        issue = document.setdefault("issue", {})
        if not isinstance(issue, dict):
            raise ValueError("issue fixture field must be an object")
        issue["body"] = content
        rendered = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()
    elif entry_point is EntryPoint.README:
        existing = target.content.decode("utf-8").rstrip("\n")
        rendered = f"{existing}\n\n{content}\n".encode()
    elif entry_point is EntryPoint.SOURCE_COMMENT:
        if source_comment_prefix is None:
            raise ValueError("source-comment placement requires a declared comment prefix")
        comment = "\n".join(f"{source_comment_prefix}{line}" for line in content.splitlines())
        rendered = f"{comment}\n{target.content.decode('utf-8')}".encode()
    else:
        raise ValueError(f"entry point is not a file placement: {entry_point.value}")
    _replace_file(files, target_id, rendered)


def materialize_case(
    compiled: CompiledRunInput,
    loaded: LoadedExecutableScenarioPack,
) -> MaterializedRunInput:
    """Place one reviewed attack into its declared environment channel."""

    pack = validate_pack_for_execution(loaded.pack)
    if compiled.output_digest != compiled_input_digest(compiled):
        raise ValueError("compiled input digest is invalid")
    if compiled.pack_id != pack.pack_id:
        raise ValueError("compiled input and loaded pack identities do not match")
    case = next((item for item in pack.cases if item.case_id == compiled.case_id), None)
    if case is None:
        raise ValueError("compiled case does not resolve in the loaded pack")

    reset = next(
        item for item in pack.reset_contracts if item.reset_contract_id == case.reset_contract_id
    )
    baseline_digest = environment_baseline_digest(pack.fixtures)
    if reset.baseline_digest != baseline_digest:
        raise ValueError("reset baseline digest does not match declared fixture state")

    files = _materialized_files(loaded)
    channel_injections: list[MaterializedChannelInjection] = []
    entry_point: EntryPoint | None = None
    attack_materialized = False
    if case.attack.attack_present:
        variant = next(
            item for item in pack.attack_variants if item.variant_id == case.attack.variant_id
        )
        placement = next(
            item for item in pack.attack_placements if item.placement_id == case.attack.placement_id
        )
        entry_point = placement.entry_point
        if entry_point is EntryPoint.USER_REQUEST:
            if placement.delivery_mode is not AttackDeliveryMode.DIRECT_USER_REQUEST:
                raise ValueError("user-request placement requires direct delivery mode")
            if compiled.execution_spec.attack_candidate.content != variant.content:
                raise ValueError("direct attack content is missing from execution input")
            attack_materialized = True
        elif entry_point in {EntryPoint.ISSUE, EntryPoint.README, EntryPoint.SOURCE_COMMENT}:
            fixture = next(
                (item for item in pack.fixtures if item.fixture_id == placement.insertion_target),
                None,
            )
            if fixture is None:
                raise ValueError("file placement must target a fixture")
            _inject_file_placement(
                files,
                entry_point=entry_point,
                target_id=placement.insertion_target,
                content=variant.content,
                source_comment_prefix=fixture.source_comment_prefix,
            )
            attack_materialized = True
        elif entry_point in {EntryPoint.BUILD_LOG, EntryPoint.TOOL_RESULT}:
            channel_injections.append(
                MaterializedChannelInjection(
                    injection_id=f"injection.{case.case_id}.{entry_point.value}",
                    entry_point=entry_point,
                    target_id=placement.insertion_target,
                    content_digest=variant.content_digest,
                    content=variant.content,
                )
            )
            attack_materialized = True
        elif entry_point is EntryPoint.MCP_TOOL_DEFINITION:
            target = next(
                (item for item in files if item.component_id == placement.insertion_target),
                None,
            )
            if target is None:
                raise ValueError("MCP placement must target a tool/service definition")
            document = _json_document(target)
            document["description"] = variant.content
            rendered = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()
            _replace_file(files, placement.insertion_target, rendered)
            attack_materialized = True
        else:
            raise ValueError(f"unsupported attack entry point: {entry_point.value}")

    materialized_files = tuple(
        sorted(files, key=lambda item: (item.visibility.value, item.destination_path))
    )
    candidate = MaterializedRunInput(
        compiled=compiled,
        files=materialized_files,
        channel_injections=tuple(channel_injections),
        placement_entry_point=entry_point,
        attack_materialized=attack_materialized,
        baseline_state_digest=baseline_digest,
        materialized_state_digest=materialized_state_digest(materialized_files),
        reset_plan=MaterializedResetPlan(
            reset_contract_id=reset.reset_contract_id,
            baseline_state_digest=reset.baseline_digest,
            mutable_resource_ids=reset.mutable_resource_ids,
            steps=reset.steps,
            verification_probe_ids=reset.verification_probe_ids,
        ),
        docker_environment_id=pack.docker_environments[0].docker_environment_id,
        output_digest=None,
    )
    return candidate.model_copy(update={"output_digest": materialized_input_digest(candidate)})


def _visibility_plane(visibility: Visibility) -> str:
    return {
        Visibility.AGENT_VISIBLE: "agent",
        Visibility.VERIFIER_PRIVATE: "verifier",
        Visibility.HARNESS_INTERNAL: "harness",
    }[visibility]


def _environment_path(root: Path, item: MaterializedFile) -> Path:
    relative = PurePosixPath(item.destination_path)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError(f"invalid materialization destination: {item.destination_path}")
    return root / _visibility_plane(item.visibility) / Path(*relative.parts)


def _write_environment_tree(
    materialized: MaterializedRunInput,
    root: Path,
    *,
    baseline: bool,
) -> None:
    for item in materialized.files:
        path = _environment_path(root, item)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(item.baseline_content if baseline else item.content)


def _environment_fixture_digest(materialized: MaterializedRunInput, root: Path) -> str:
    entries: list[dict[str, str]] = []
    for item in materialized.files:
        if not item.source_path.startswith("fixtures/"):
            continue
        path = _environment_path(root, item)
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"materialized fixture is missing or unsafe: {item.destination_path}")
        entries.append(
            {
                "component_id": item.component_id,
                "destination_path": item.destination_path,
                "visibility": item.visibility.value,
                "content_digest": _digest(path.read_bytes()),
            }
        )
    return _canonical_digest(
        sorted(
            entries,
            key=lambda item: (item["visibility"], item["destination_path"], item["component_id"]),
        )
    )


def _environment_file_paths(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    )


def write_materialized_environment(
    materialized: MaterializedRunInput,
    destination: Path,
) -> MaterializedEnvironmentState:
    """Atomically write one materialized environment with separated visibility planes."""

    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"materialized environment already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent))
    try:
        _write_environment_tree(materialized, staging, baseline=False)
        state_digest = _environment_fixture_digest(materialized, staging)
        if state_digest != materialized.materialized_state_digest:
            raise ValueError("written environment state digest does not match materialization")
        os.replace(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return MaterializedEnvironmentState(
        state_digest=state_digest,
        file_paths=_environment_file_paths(destination),
    )


def reset_materialized_environment(
    materialized: MaterializedRunInput,
    destination: Path,
) -> EnvironmentResetResult:
    """Remove all run artifacts and rebuild the declared pre-injection baseline."""

    if not destination.is_dir() or destination.is_symlink():
        raise ValueError("materialized environment root is missing or unsafe")
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.reset-", dir=destination.parent))
    try:
        _write_environment_tree(materialized, staging, baseline=True)
        state_digest = _environment_fixture_digest(materialized, staging)
        shutil.rmtree(destination)
        os.replace(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return EnvironmentResetResult(
        state_digest=state_digest,
        baseline_restored=state_digest == materialized.reset_plan.baseline_state_digest,
        file_paths=_environment_file_paths(destination),
    )


__all__ = [
    "MaterializedChannelInjection",
    "MaterializedEnvironmentState",
    "MaterializedFile",
    "MaterializedResetPlan",
    "MaterializedRunInput",
    "EnvironmentResetResult",
    "environment_baseline_digest",
    "materialize_case",
    "materialized_input_digest",
    "materialized_state_digest",
    "reset_materialized_environment",
    "write_materialized_environment",
]
