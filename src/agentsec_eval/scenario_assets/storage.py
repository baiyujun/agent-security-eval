"""Deterministic physical storage for executable scenario packs."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Literal, Self, cast

import yaml
from pydantic import model_validator

from agentsec_eval.scenario_assets.enums import Visibility
from agentsec_eval.scenario_assets.models import (
    AssetId,
    ExecutableScenarioPack,
    FrozenModel,
    RelativePosixPath,
    Sha256Digest,
)
from agentsec_eval.scenario_assets.validation import validate_pack

PACK_STORAGE_SCHEMA_VERSION: Literal[1] = 1

_LAYOUT_DIRECTORIES = (
    "cases",
    "fixtures",
    "docker",
    "tools",
    "oracles",
    "assertions",
    "reset",
    "tests",
)
_FIXED_METADATA_PATHS = frozenset(
    {
        "scenario.yaml",
        "fixtures/manifest.yaml",
        "docker/manifest.yaml",
        "tools/manifest.yaml",
        "oracles/suites.yaml",
        "assertions/contexts.yaml",
        "provenance.yaml",
        "reset/contracts.yaml",
        "tests/manifest.yaml",
    }
)

PackFileKind = Literal["fixture", "docker", "tool_service", "pack_test"]


class PackFileManifestEntry(FrozenModel):
    relative_path: RelativePosixPath
    component_id: AssetId
    file_kind: PackFileKind
    visibility: Visibility
    content_digest: Sha256Digest
    size_bytes: int

    @model_validator(mode="after")
    def validate_size(self) -> Self:
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")
        return self


class PackStorageManifest(FrozenModel):
    storage_schema_version: Literal[1]
    pack_id: AssetId
    pack_content_digest: Sha256Digest
    files: tuple[PackFileManifestEntry, ...]


class LoadedPackFile(FrozenModel):
    relative_path: RelativePosixPath
    component_id: AssetId
    file_kind: PackFileKind
    visibility: Visibility
    content_digest: Sha256Digest
    content: bytes


class LoadedExecutableScenarioPack(FrozenModel):
    pack: ExecutableScenarioPack
    storage_manifest: PackStorageManifest
    files: tuple[LoadedPackFile, ...]

    def files_for_visibility(self, visibility: Visibility) -> tuple[LoadedPackFile, ...]:
        return tuple(item for item in self.files if item.visibility is visibility)


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _yaml_bytes(value: object) -> bytes:
    return yaml.safe_dump(
        value,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=True,
    ).encode("utf-8")


def _safe_path(root: Path, relative_path: str) -> Path:
    pure = PurePosixPath(relative_path)
    if (
        not relative_path
        or "\\" in relative_path
        or pure.is_absolute()
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != relative_path
    ):
        raise ValueError(f"invalid relative pack path: {relative_path}")
    path = root.joinpath(*pure.parts)
    if root not in path.parents:
        raise ValueError(f"pack path escapes destination: {relative_path}")
    return path


def _fixture_prefix(visibility: Visibility) -> str:
    partition = {
        Visibility.AGENT_VISIBLE: "agent-visible",
        Visibility.VERIFIER_PRIVATE: "verifier-private",
        Visibility.HARNESS_INTERNAL: "harness-internal",
    }[visibility]
    return f"fixtures/{partition}/"


def _declared_files(pack: ExecutableScenarioPack) -> tuple[PackFileManifestEntry, ...]:
    declarations: list[PackFileManifestEntry] = []
    for fixture in pack.fixtures:
        if not fixture.relative_path.startswith(_fixture_prefix(fixture.visibility)):
            raise ValueError(
                "fixture path must match its visibility partition: "
                f"{fixture.fixture_id} -> {fixture.relative_path}"
            )
        declarations.append(
            PackFileManifestEntry(
                relative_path=fixture.relative_path,
                component_id=fixture.fixture_id,
                file_kind="fixture",
                visibility=fixture.visibility,
                content_digest=fixture.content_digest,
                size_bytes=0,
            )
        )
    for docker in pack.docker_environments:
        declarations.append(
            PackFileManifestEntry(
                relative_path=docker.dockerfile_path,
                component_id=docker.docker_environment_id,
                file_kind="docker",
                visibility=Visibility.HARNESS_INTERNAL,
                content_digest=docker.dockerfile_digest,
                size_bytes=0,
            )
        )
        if docker.compose_path is not None and docker.compose_digest is not None:
            declarations.append(
                PackFileManifestEntry(
                    relative_path=docker.compose_path,
                    component_id=docker.docker_environment_id,
                    file_kind="docker",
                    visibility=Visibility.HARNESS_INTERNAL,
                    content_digest=docker.compose_digest,
                    size_bytes=0,
                )
            )
    for service in pack.tool_services:
        declarations.append(
            PackFileManifestEntry(
                relative_path=service.interface_path,
                component_id=service.tool_service_id,
                file_kind="tool_service",
                visibility=service.visibility,
                content_digest=service.content_digest,
                size_bytes=0,
            )
        )
    for pack_test in pack.pack_tests:
        declarations.append(
            PackFileManifestEntry(
                relative_path=pack_test.test_path,
                component_id=pack_test.pack_test_id,
                file_kind="pack_test",
                visibility=Visibility.HARNESS_INTERNAL,
                content_digest=pack_test.content_digest,
                size_bytes=0,
            )
        )
    paths = [item.relative_path for item in declarations]
    if len(paths) != len(set(paths)):
        raise ValueError("physical pack asset paths must be unique")
    if set(paths) & _FIXED_METADATA_PATHS:
        raise ValueError("physical pack asset path collides with pack metadata")
    return tuple(sorted(declarations, key=lambda item: item.relative_path))


def _metadata_documents(
    pack: ExecutableScenarioPack,
    manifest: PackStorageManifest,
) -> dict[str, bytes]:
    pack_data = pack.model_dump(mode="json")
    cases = cast(list[dict[str, object]], pack_data.pop("cases"))
    fixtures = pack_data.pop("fixtures")
    docker_environments = pack_data.pop("docker_environments")
    capabilities = pack_data.pop("capabilities")
    tool_services = pack_data.pop("tool_services")
    oracle_suites = pack_data.pop("oracle_suites")
    authorization_contexts = pack_data.pop("authorization_contexts")
    provenance = pack_data.pop("provenance")
    rights_decisions = pack_data.pop("rights_decisions")
    field_lineage = pack_data.pop("field_lineage")
    conversion_losses = pack_data.pop("conversion_losses")
    reset_contracts = pack_data.pop("reset_contracts")
    pack_tests = pack_data.pop("pack_tests")

    documents = {
        "scenario.yaml": _yaml_bytes(
            {
                "storage_schema_version": PACK_STORAGE_SCHEMA_VERSION,
                "pack": pack_data,
                "file_manifest": manifest.model_dump(mode="json"),
            }
        ),
        "fixtures/manifest.yaml": _yaml_bytes({"fixtures": fixtures}),
        "docker/manifest.yaml": _yaml_bytes({"docker_environments": docker_environments}),
        "tools/manifest.yaml": _yaml_bytes(
            {"capabilities": capabilities, "tool_services": tool_services}
        ),
        "oracles/suites.yaml": _yaml_bytes({"oracle_suites": oracle_suites}),
        "assertions/contexts.yaml": _yaml_bytes({"authorization_contexts": authorization_contexts}),
        "provenance.yaml": _yaml_bytes(
            {
                "provenance": provenance,
                "rights_decisions": rights_decisions,
                "field_lineage": field_lineage,
                "conversion_losses": conversion_losses,
            }
        ),
        "reset/contracts.yaml": _yaml_bytes({"reset_contracts": reset_contracts}),
        "tests/manifest.yaml": _yaml_bytes({"pack_tests": pack_tests}),
    }
    for case in cases:
        case_id = cast(str, case["case_id"])
        documents[f"cases/{case_id}.yaml"] = _yaml_bytes(case)
    return documents


def _write_file(root: Path, relative_path: str, content: bytes) -> None:
    path = _safe_path(root, relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def serialize_executable_pack(
    pack: ExecutableScenarioPack,
    destination: Path,
    asset_contents: Mapping[str, bytes],
) -> PackStorageManifest:
    """Atomically create a complete pack directory from declared native assets."""

    validated = validate_pack(pack)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"pack destination already exists: {destination}")
    declared = _declared_files(validated)
    expected_paths = {item.relative_path for item in declared}
    supplied_paths = set(asset_contents)
    if supplied_paths != expected_paths:
        missing = sorted(expected_paths - supplied_paths)
        undeclared = sorted(supplied_paths - expected_paths)
        raise ValueError(f"asset contents mismatch; missing={missing}, undeclared={undeclared}")

    manifest_entries: list[PackFileManifestEntry] = []
    for item in declared:
        content = asset_contents[item.relative_path]
        if not isinstance(content, bytes):
            raise TypeError(f"asset content must be bytes: {item.relative_path}")
        actual_digest = _digest(content)
        if actual_digest != item.content_digest:
            raise ValueError(f"asset content digest mismatch: {item.relative_path}")
        manifest_entries.append(item.model_copy(update={"size_bytes": len(content)}))
    manifest = PackStorageManifest(
        storage_schema_version=PACK_STORAGE_SCHEMA_VERSION,
        pack_id=validated.pack_id,
        pack_content_digest=cast(str, validated.output_digest),
        files=tuple(manifest_entries),
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent))
    try:
        for directory in _LAYOUT_DIRECTORIES:
            (staging / directory).mkdir()
        for relative_path, content in _metadata_documents(validated, manifest).items():
            _write_file(staging, relative_path, content)
        for item in manifest.files:
            _write_file(staging, item.relative_path, asset_contents[item.relative_path])
        os.replace(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def _load_yaml(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"pack metadata must be a mapping: {path}")
    return cast(dict[str, object], loaded)


def _required(document: Mapping[str, object], key: str) -> object:
    if key not in document:
        raise ValueError(f"pack metadata is missing {key}")
    return document[key]


def load_executable_pack(root: Path) -> LoadedExecutableScenarioPack:
    """Load and fully verify a physical executable scenario pack."""

    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"pack root must be a real directory: {root}")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"pack must not contain symlinks: {path.relative_to(root)}")

    scenario = _load_yaml(root / "scenario.yaml")
    if scenario.get("storage_schema_version") != PACK_STORAGE_SCHEMA_VERSION:
        raise ValueError("unsupported pack storage schema version")
    pack_data = _required(scenario, "pack")
    if not isinstance(pack_data, dict):
        raise ValueError("scenario.yaml pack must be a mapping")
    assembled = cast(dict[str, object], dict(pack_data))

    assembled["cases"] = [
        _load_yaml(path)
        for path in sorted((root / "cases").glob("*.yaml"), key=lambda item: item.name)
    ]
    documents = (
        (_load_yaml(root / "fixtures" / "manifest.yaml"), ("fixtures",)),
        (_load_yaml(root / "docker" / "manifest.yaml"), ("docker_environments",)),
        (
            _load_yaml(root / "tools" / "manifest.yaml"),
            ("capabilities", "tool_services"),
        ),
        (_load_yaml(root / "oracles" / "suites.yaml"), ("oracle_suites",)),
        (
            _load_yaml(root / "assertions" / "contexts.yaml"),
            ("authorization_contexts",),
        ),
        (
            _load_yaml(root / "provenance.yaml"),
            ("provenance", "rights_decisions", "field_lineage", "conversion_losses"),
        ),
        (_load_yaml(root / "reset" / "contracts.yaml"), ("reset_contracts",)),
        (_load_yaml(root / "tests" / "manifest.yaml"), ("pack_tests",)),
    )
    for document, keys in documents:
        for key in keys:
            assembled[key] = _required(document, key)

    pack = validate_pack(ExecutableScenarioPack.model_validate(assembled))
    manifest = PackStorageManifest.model_validate(_required(scenario, "file_manifest"))
    if manifest.pack_id != pack.pack_id or manifest.pack_content_digest != pack.output_digest:
        raise ValueError("storage manifest does not match pack identity or content digest")

    declared = _declared_files(pack)
    if len(declared) != len(manifest.files):
        raise ValueError("storage manifest does not match declared pack assets")
    declared_shape = tuple(
        item.model_copy(update={"size_bytes": stored.size_bytes})
        for item, stored in zip(declared, manifest.files, strict=True)
    )
    if declared_shape != manifest.files:
        raise ValueError("storage manifest does not match declared pack assets")

    metadata_paths = set(_FIXED_METADATA_PATHS) | {
        f"cases/{case.case_id}.yaml" for case in pack.cases
    }
    expected_paths = metadata_paths | {item.relative_path for item in manifest.files}
    actual_paths = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual_paths != expected_paths:
        missing = sorted(expected_paths - actual_paths)
        undeclared = sorted(actual_paths - expected_paths)
        raise ValueError(f"pack files mismatch; missing={missing}, undeclared={undeclared}")

    loaded_files: list[LoadedPackFile] = []
    for item in manifest.files:
        content = _safe_path(root, item.relative_path).read_bytes()
        if len(content) != item.size_bytes or _digest(content) != item.content_digest:
            raise ValueError(f"asset file digest or size mismatch: {item.relative_path}")
        loaded_files.append(
            LoadedPackFile(
                relative_path=item.relative_path,
                component_id=item.component_id,
                file_kind=item.file_kind,
                visibility=item.visibility,
                content_digest=item.content_digest,
                content=content,
            )
        )
    return LoadedExecutableScenarioPack(
        pack=pack,
        storage_manifest=manifest,
        files=tuple(loaded_files),
    )


__all__ = [
    "PACK_STORAGE_SCHEMA_VERSION",
    "LoadedExecutableScenarioPack",
    "LoadedPackFile",
    "PackFileManifestEntry",
    "PackStorageManifest",
    "load_executable_pack",
    "serialize_executable_pack",
]
