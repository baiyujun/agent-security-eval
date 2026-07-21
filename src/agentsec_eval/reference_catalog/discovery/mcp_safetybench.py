"""Safe discovery of locked MCP-SafetyBench attack tasks."""

from __future__ import annotations

import json
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

_CONFIG_ROOT = PurePosixPath("mcpuniverse/benchmark/configs/test")
_REQUIRED_FIELDS = frozenset({"category", "attack_category", "question", "evaluators"})


def _safe_directory(root: Path, path: Path) -> Path:
    if path.is_symlink():
        raise ValueError(f"MCP-SafetyBench directory must not be a symlink: {path}")
    try:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"MCP-SafetyBench directory does not exist: {path}") from error
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"MCP-SafetyBench directory path escape: {path}")
    if not resolved.is_dir():
        raise ValueError(f"MCP-SafetyBench source path is not a directory: {path}")
    return resolved


def _safe_file(root: Path, path: Path) -> Path:
    if path.is_symlink():
        raise ValueError(f"MCP-SafetyBench source file must not be a symlink: {path}")
    try:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"MCP-SafetyBench source file does not exist: {path}") from error
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"MCP-SafetyBench source path escape: {path}")
    if not resolved.is_file():
        raise ValueError(f"MCP-SafetyBench source path is not a file: {path}")
    return resolved


def _load_json_object(path: Path, *, source_path: PurePosixPath) -> dict[str, JsonValue]:
    try:
        value = cast(JsonValue, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"malformed JSON in MCP-SafetyBench task: {source_path}") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"MCP-SafetyBench task must be a JSON object: {source_path}")
    return value


def _required_text(task: Mapping[str, JsonValue], key: str, *, source_path: PurePosixPath) -> str:
    value = task.get(key)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"MCP-SafetyBench {source_path}.{key} must be non-empty text")
    return value


@dataclass(frozen=True)
class MCPSafetyBenchDiscoverer:
    """Discover all MCP-SafetyBench tasks or return no records on any failure."""

    source_project: ClassVar[str] = "mcp-safetybench"
    expected_total: int = 245

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]:
        checkout = context.checkouts.get(self.source_project)
        if checkout is None:
            raise ValueError("MCP-SafetyBench checkout is missing from the discovery context")
        if self.expected_total < 0:
            raise ValueError("MCP-SafetyBench expected total must be non-negative")
        source_paths = self._approved_task_paths(checkout.root)
        if len(source_paths) != self.expected_total:
            raise ValueError(
                f"expected {self.expected_total} MCP-SafetyBench tasks, "
                f"discovered {len(source_paths)}"
            )

        parsed: list[tuple[str, PurePosixPath, str, dict[str, JsonValue]]] = []
        seen_keys: set[str] = set()
        for source_path in source_paths:
            relative_task_path = source_path.relative_to(_CONFIG_ROOT)
            record_key = f"{relative_task_path.parts[0]}/{relative_task_path.stem}"
            if record_key in seen_keys:
                raise ValueError(f"duplicate MCP-SafetyBench record key: {record_key}")
            seen_keys.add(record_key)
            task = _load_json_object(
                _safe_file(checkout.root, checkout.root.joinpath(*source_path.parts)),
                source_path=source_path,
            )
            missing_fields = _REQUIRED_FIELDS - set(task)
            if missing_fields:
                raise ValueError(
                    f"MCP-SafetyBench task lacks structural fields {sorted(missing_fields)}: "
                    f"{source_path}"
                )
            category = _required_text(task, "attack_category", source_path=source_path)
            _required_text(task, "category", source_path=source_path)
            parsed.append((record_key, source_path, category, task))

        records = [
            self._build_record(
                checkout,
                record_key=record_key,
                source_path=source_path,
                category=category,
                task=task,
            )
            for record_key, source_path, category, task in parsed
        ]
        return list(validate_records(records, require_initial_outputs=True))

    def _approved_task_paths(self, checkout_root: Path) -> tuple[PurePosixPath, ...]:
        config_root = _safe_directory(
            checkout_root,
            checkout_root.joinpath(*_CONFIG_ROOT.parts),
        )
        approved: list[PurePosixPath] = []
        for candidate in config_root.rglob("*.json"):
            relative_path = PurePosixPath(candidate.relative_to(config_root).as_posix())
            if candidate.is_symlink():
                raise ValueError(
                    f"MCP-SafetyBench source path must not be symlink: {relative_path}"
                )
            if candidate.is_dir():
                continue
            if (
                not candidate.is_file()
                or len(relative_path.parts) != 2
                or not relative_path.name.endswith(".json")
                or not relative_path.stem
            ):
                raise ValueError(
                    f"MCP-SafetyBench task path must use two-level JSON shape: {relative_path}"
                )
            approved.append(_CONFIG_ROOT.joinpath(relative_path))
        return tuple(sorted(approved, key=PurePosixPath.as_posix))

    def _build_record(
        self,
        checkout: SourceCheckout,
        *,
        record_key: str,
        source_path: PurePosixPath,
        category: str,
        task: dict[str, JsonValue],
    ) -> UpstreamLedgerRecord:
        return UpstreamLedgerRecord(
            source_project=self.source_project,
            source_repository=checkout.repository,
            source_commit=checkout.commit,
            source_path=source_path.as_posix(),
            source_record_key=record_key,
            source_record_digest=canonical_json_digest(task),
            record_role=RecordRole.BENCHMARK_SCENARIO,
            source_asset_kind=SourceAssetKind.MCP_SAFETYBENCH_TASK,
            asset_family="mcp_safetybench",
            scenario_class="mcp_attack",
            category=category,
            attack_present=True,
            attack_origin=None,
            attack_delivery_mode=None,
            raw_reuse_disposition=RawReuseDisposition.REVIEW_REQUIRED,
            native_conversion_disposition=(
                NativeConversionDisposition.ELIGIBLE_FOR_SEMANTIC_RECONSTRUCTION
            ),
            conversion_reason=(
                "Raw MCP-SafetyBench content requires project-authored semantic reconstruction."
            ),
        )
