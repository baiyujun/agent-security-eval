"""Safe discovery and exact reconciliation of locked SABER tasks."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar, cast

from pydantic import JsonValue

from agentsec_eval.reference_catalog.digest import canonical_json_digest
from agentsec_eval.reference_catalog.discovery.base import DiscoveryContext, SourceCheckout
from agentsec_eval.reference_catalog.enums import (
    NativeConversionDisposition,
    RawReuseDisposition,
    RecordRole,
    SourceAssetKind,
)
from agentsec_eval.reference_catalog.models import UpstreamLedgerRecord
from agentsec_eval.reference_catalog.validation import validate_records

_SCENARIOS = ("A", "B", "C")
_PRODUCTION_SCENARIO_COUNTS = {"A": 289, "B": 186, "C": 241}
_PILOT_PATH = PurePosixPath("pilot_tasks.json")


@dataclass(frozen=True)
class _ParsedTask:
    source_path: PurePosixPath
    task_id: str
    scenario: str
    category: str
    task: dict[str, JsonValue]
    attack_delivery_mode: str | None


def _load_json_object(path: Path, *, context: str) -> dict[str, JsonValue]:
    try:
        value = cast(JsonValue, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"malformed JSON in {context}: {path}") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{context} must contain a JSON object")
    return value


def _required_text(values: Mapping[str, JsonValue], key: str, *, context: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{context}.{key} must be non-empty text")
    return value


def _required_mapping(
    values: Mapping[str, JsonValue], key: str, *, context: str
) -> Mapping[str, JsonValue]:
    value = values.get(key)
    if not isinstance(value, dict) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{context}.{key} must be an object")
    return value


def _safe_file(root: Path, path: Path) -> Path:
    if path.is_symlink():
        raise ValueError(f"SABER source file must not be a symlink: {path}")
    try:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"SABER source file does not exist: {path}") from error
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"SABER source path escape: {path}")
    if not resolved.is_file():
        raise ValueError(f"SABER source path is not a file: {path}")
    return resolved


def _safe_directory(root: Path, path: Path) -> Path:
    if path.is_symlink():
        raise ValueError(f"SABER source directory must not be a symlink: {path}")
    try:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"SABER source directory does not exist: {path}") from error
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"SABER source directory path escape: {path}")
    if not resolved.is_dir():
        raise ValueError(f"SABER source path is not a directory: {path}")
    return resolved


@dataclass(frozen=True)
class SaberDiscoverer:
    """Discover all SABER task metadata or fail before emitting any record."""

    source_project: ClassVar[str] = "saber"
    expected_total: int = 716

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]:
        checkout = context.checkouts.get(self.source_project)
        if checkout is None:
            raise ValueError("SABER checkout is missing from the discovery context")
        if self.expected_total < 0:
            raise ValueError("SABER expected total must be non-negative")

        manifest = _load_json_object(
            _safe_file(checkout.root, checkout.root / "dataset/manifest.json"),
            context="SABER manifest",
        )
        manifest_ids, manifest_scenario_counts = self._validate_manifest(manifest)
        parsed = self._parse_tasks(checkout)

        if len(parsed) != self.expected_total:
            raise ValueError(
                f"expected {self.expected_total} SABER task files, discovered {len(parsed)}"
            )
        parsed_ids = tuple(task.task_id for task in parsed)
        if len(set(parsed_ids)) != len(parsed_ids):
            raise ValueError("duplicate parsed task ID in SABER task files")
        if set(parsed_ids) != set(manifest_ids):
            missing = sorted(set(manifest_ids) - set(parsed_ids))
            extra = sorted(set(parsed_ids) - set(manifest_ids))
            raise ValueError(f"SABER manifest/task ID mismatch: missing={missing}, extra={extra}")

        parsed_scenario_counts = Counter(task.scenario for task in parsed)
        if dict(parsed_scenario_counts) != manifest_scenario_counts:
            raise ValueError("SABER parsed scenario counts do not match manifest scenario counts")

        records = [self._build_record(checkout, parsed_task) for parsed_task in parsed]
        return list(validate_records(records, require_initial_outputs=True))

    def _validate_manifest(
        self, manifest: Mapping[str, JsonValue]
    ) -> tuple[tuple[str, ...], dict[str, int]]:
        counts = _required_mapping(manifest, "counts", context="SABER manifest")
        declared_total = counts.get("tasks")
        if type(declared_total) is not int or declared_total < 0:
            raise ValueError("SABER manifest count must be a non-negative integer")
        if declared_total != self.expected_total:
            raise ValueError(
                f"SABER manifest count {declared_total} does not match expected total "
                f"{self.expected_total}"
            )

        raw_ids = manifest.get("task_ids")
        if not isinstance(raw_ids, list):
            raise ValueError("SABER manifest task_ids must be an array")
        if not all(
            isinstance(task_id, str) and task_id and task_id == task_id.strip()
            for task_id in raw_ids
        ):
            raise ValueError("SABER manifest task IDs must be non-empty text")
        manifest_ids = tuple(cast(str, task_id) for task_id in raw_ids)
        if len(set(manifest_ids)) != len(manifest_ids):
            raise ValueError("duplicate manifest task ID in SABER manifest")
        if len(manifest_ids) != self.expected_total:
            raise ValueError(
                f"SABER manifest ID count {len(manifest_ids)} does not match expected total "
                f"{self.expected_total}"
            )

        raw_scenario_counts = _required_mapping(
            counts,
            "by_scenario",
            context="SABER manifest counts",
        )
        if set(raw_scenario_counts) != set(_SCENARIOS):
            raise ValueError("SABER manifest scenario counts must contain exactly A, B, and C")
        if not all(type(value) is int and value >= 0 for value in raw_scenario_counts.values()):
            raise ValueError("SABER manifest scenario counts must be non-negative integers")
        scenario_counts = {
            scenario: cast(int, raw_scenario_counts[scenario]) for scenario in _SCENARIOS
        }
        if sum(scenario_counts.values()) != self.expected_total:
            raise ValueError("SABER manifest scenario counts do not sum to expected total")
        if self.expected_total == 716 and scenario_counts != _PRODUCTION_SCENARIO_COUNTS:
            raise ValueError("SABER production scenario counts must be A=289, B=186, C=241")
        return manifest_ids, scenario_counts

    def _parse_tasks(self, checkout: SourceCheckout) -> list[_ParsedTask]:
        parsed: list[_ParsedTask] = []
        for source_path, resolved_path in self._approved_task_files(checkout.root):
            scenario = source_path.parts[1]
            category = source_path.parts[2]
            task = _load_json_object(
                resolved_path,
                context=f"SABER task {source_path}",
            )
            task_id, attack_delivery_mode = self._validate_task(
                task,
                source_path,
                scenario,
                category,
            )
            parsed.append(
                _ParsedTask(
                    source_path=source_path,
                    task_id=task_id,
                    scenario=scenario,
                    category=category,
                    task=task,
                    attack_delivery_mode=attack_delivery_mode,
                )
            )
        return parsed

    def _approved_task_files(self, checkout_root: Path) -> list[tuple[PurePosixPath, Path]]:
        tasks_root = _safe_directory(checkout_root, checkout_root / "tasks")
        approved: list[tuple[PurePosixPath, Path]] = []
        for candidate in tasks_root.rglob("*"):
            relative_path = PurePosixPath(candidate.relative_to(tasks_root).as_posix())
            if candidate.is_symlink():
                raise ValueError(f"unapproved SABER task path: {relative_path}")
            if candidate.is_dir():
                continue
            if not candidate.is_file():
                raise ValueError(f"unapproved SABER task path: {relative_path}")
            if relative_path == _PILOT_PATH:
                continue
            if (
                len(relative_path.parts) != 3
                or relative_path.parts[0] not in _SCENARIOS
                or not relative_path.parts[1]
                or not relative_path.name.endswith(".json")
                or not relative_path.stem
            ):
                raise ValueError(f"unapproved SABER task path: {relative_path}")
            source_path = PurePosixPath("tasks").joinpath(relative_path)
            approved.append((source_path, _safe_file(checkout_root, candidate)))
        return sorted(approved, key=lambda item: item[0].as_posix())

    def _validate_task(
        self,
        task: Mapping[str, JsonValue],
        source_path: PurePosixPath,
        path_scenario: str,
        path_category: str,
    ) -> tuple[str, str | None]:
        scenario = _required_text(task, "scenario", context=str(source_path))
        if scenario not in _SCENARIOS:
            raise ValueError(f"unknown scenario in SABER task {source_path}: {scenario}")
        if scenario != path_scenario:
            raise ValueError(f"SABER task scenario does not match source path: {source_path}")

        category = _required_text(task, "category", context=str(source_path))
        if category != path_category:
            raise ValueError(f"SABER task category does not match source path: {source_path}")

        task_id = _required_text(task, "id", context=str(source_path))
        if not task_id.startswith(f"{scenario}_") or task_id != source_path.stem:
            raise ValueError(
                f"SABER task ID does not match scenario and source path: {source_path}"
            )

        injection = _required_mapping(task, "injection", context=str(source_path))
        enabled = injection.get("enabled")
        if enabled not in (True, False):
            raise ValueError(f"SABER injection.enabled must be boolean: {source_path}")
        attack_delivery_mode: str | None = None
        if scenario == "A":
            method = injection.get("method")
            if enabled is True and method is not None:
                if not isinstance(method, str) or not method or method != method.strip():
                    raise ValueError(
                        f"{source_path}.injection.method must be non-empty text when present"
                    )
                attack_delivery_mode = method
        elif scenario == "B" and enabled is not False:
            raise ValueError(f"SABER Scenario B requires disabled injection: {source_path}")
        elif scenario == "C" and enabled is True:
            _required_text(injection, "method", context=f"{source_path}.injection")
        return task_id, attack_delivery_mode

    def _build_record(
        self,
        checkout: SourceCheckout,
        parsed_task: _ParsedTask,
    ) -> UpstreamLedgerRecord:
        attack_present: bool
        attack_origin: str | None = None
        attack_delivery_mode: str | None = None
        if parsed_task.scenario == "A":
            attack_present = True
            attack_delivery_mode = parsed_task.attack_delivery_mode
        elif parsed_task.scenario == "B":
            attack_present = False
        else:
            attack_present = True
            attack_origin = "user"
            attack_delivery_mode = "direct_user_request"

        return UpstreamLedgerRecord(
            source_project=self.source_project,
            source_repository=checkout.repository,
            source_commit=checkout.commit,
            source_path=parsed_task.source_path.as_posix(),
            source_record_key=parsed_task.task_id,
            source_record_digest=canonical_json_digest(parsed_task.task),
            record_role=RecordRole.BENCHMARK_SCENARIO,
            source_asset_kind=SourceAssetKind.SABER_TASK,
            asset_family="saber",
            scenario_class=parsed_task.scenario,
            category=parsed_task.category,
            attack_present=attack_present,
            attack_origin=attack_origin,
            attack_delivery_mode=attack_delivery_mode,
            raw_reuse_disposition=RawReuseDisposition.REVIEW_REQUIRED,
            native_conversion_disposition=(
                NativeConversionDisposition.ELIGIBLE_FOR_SEMANTIC_RECONSTRUCTION
            ),
            conversion_reason=(
                "Raw SABER task content requires project-authored semantic reconstruction."
            ),
        )
