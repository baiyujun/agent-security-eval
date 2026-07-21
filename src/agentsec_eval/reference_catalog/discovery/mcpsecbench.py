"""Safe discovery of locked MCPSecBench records and taxonomy headers."""

from __future__ import annotations

import csv
import hashlib
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

_STRUCTURED_PATH = PurePosixPath("data/data.json")
_TAXONOMY_PATH = PurePosixPath("data/experiments.csv")
_STRUCTURED_FIELDS = frozenset({"attack", "prompt", "result"})
_QUOTE_TRANSLATION = str.maketrans({"“": "", "”": "", "‘": "", "’": "", '"': "", "'": ""})


def _safe_file(root: Path, relative_path: PurePosixPath) -> Path:
    path = root.joinpath(*relative_path.parts)
    if path.is_symlink():
        raise ValueError(f"MCPSecBench source file must not be a symlink: {relative_path}")
    try:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"MCPSecBench source file does not exist: {relative_path}") from error
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"MCPSecBench source path escape: {relative_path}")
    if not resolved.is_file():
        raise ValueError(f"MCPSecBench source path is not a file: {relative_path}")
    return resolved


def _required_text(values: Mapping[str, JsonValue], key: str, *, index: int) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"MCPSecBench structured record {index}.{key} must be non-empty text")
    return value


def _normalize_category(value: str) -> str:
    return " ".join(value.translate(_QUOTE_TRANSLATION).casefold().split())


def _load_structured(path: Path) -> list[dict[str, JsonValue]]:
    try:
        value = cast(JsonValue, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"malformed JSON in MCPSecBench structured source: {path}") from error
    if not isinstance(value, list):
        raise ValueError("MCPSecBench structured source must contain a JSON array")
    records: list[dict[str, JsonValue]] = []
    for index, record in enumerate(value):
        if not isinstance(record, dict) or not all(isinstance(key, str) for key in record):
            raise ValueError(f"MCPSecBench structured record {index} must be a JSON object")
        records.append(record)
    return records


def _read_taxonomy_header(path: Path) -> tuple[str, ...]:
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            header_line = stream.readline()
    except (OSError, UnicodeError) as error:
        raise ValueError(f"cannot read MCPSecBench taxonomy header: {path}") from error
    if not header_line:
        raise ValueError("MCPSecBench taxonomy CSV must contain a header")
    try:
        header = next(csv.reader([header_line]))
    except (csv.Error, StopIteration) as error:
        raise ValueError("malformed MCPSecBench taxonomy CSV header") from error
    if not header or _normalize_category(header[0]) != "mcp provider":
        raise ValueError("MCPSecBench taxonomy CSV header must begin with MCP Provider")
    declared = tuple(category.strip() for category in header[1:])
    if not declared or any(not category for category in declared):
        raise ValueError("MCPSecBench taxonomy categories must be non-empty")
    return declared


@dataclass(frozen=True)
class MCPSecBenchDiscoverer:
    """Discover all structured and taxonomy-only MCPSecBench records."""

    CATEGORY_ALIASES: ClassVar[dict[str, str]] = {
        "tool/service misuse via confused ai": "tool misuse via confused ai",
        "package name squatting(tools name)": "package name squatting(tool name)",
        "package name squatting(server name)": "package name squatting(server name)",
        "rug pull attack": "rug pull",
    }
    source_project: ClassVar[str] = "mcpsecbench"
    expected_structured_total: int = 11
    expected_taxonomy_total: int = 6

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]:
        checkout = context.checkouts.get(self.source_project)
        if checkout is None:
            raise ValueError("MCPSecBench checkout is missing from the discovery context")
        if self.expected_structured_total < 0 or self.expected_taxonomy_total < 0:
            raise ValueError("MCPSecBench expected totals must be non-negative")

        structured = _load_structured(_safe_file(checkout.root, _STRUCTURED_PATH))
        if len(structured) != self.expected_structured_total:
            raise ValueError(
                f"expected {self.expected_structured_total} MCPSecBench structured records, "
                f"discovered {len(structured)}"
            )
        parsed_structured: list[tuple[str, str, dict[str, JsonValue]]] = []
        structured_categories: set[str] = set()
        for index, record in enumerate(structured):
            if set(record) != _STRUCTURED_FIELDS:
                raise ValueError(
                    f"MCPSecBench structured record {index} must contain attack, prompt, and result"
                )
            declared_category = _required_text(record, "attack", index=index)
            normalized_category = self._canonical_category(declared_category)
            if normalized_category in structured_categories:
                raise ValueError(f"duplicate structured MCPSecBench category: {declared_category}")
            structured_categories.add(normalized_category)
            parsed_structured.append((declared_category, normalized_category, record))

        taxonomy_header = _read_taxonomy_header(_safe_file(checkout.root, _TAXONOMY_PATH))
        parsed_taxonomy: list[tuple[str, str]] = []
        taxonomy_categories: set[str] = set()
        for declared_category in taxonomy_header:
            normalized_category = self._canonical_category(declared_category)
            if normalized_category in taxonomy_categories:
                raise ValueError(f"duplicate taxonomy MCPSecBench category: {declared_category}")
            taxonomy_categories.add(normalized_category)
            if normalized_category not in structured_categories:
                parsed_taxonomy.append((declared_category, normalized_category))

        if len(parsed_taxonomy) != self.expected_taxonomy_total:
            raise ValueError(
                f"expected {self.expected_taxonomy_total} MCPSecBench taxonomy records, "
                f"discovered {len(parsed_taxonomy)}"
            )

        records = [
            self._build_structured_record(
                checkout,
                declared_category=declared_category,
                normalized_category=normalized_category,
                source_record=source_record,
            )
            for declared_category, normalized_category, source_record in parsed_structured
        ]
        records.extend(
            self._build_taxonomy_record(
                checkout,
                declared_category=declared_category,
                normalized_category=normalized_category,
            )
            for declared_category, normalized_category in parsed_taxonomy
        )
        return list(validate_records(records, require_initial_outputs=True))

    def _canonical_category(self, value: str) -> str:
        normalized = _normalize_category(value)
        return self.CATEGORY_ALIASES.get(normalized, normalized)

    def _build_structured_record(
        self,
        checkout: SourceCheckout,
        *,
        declared_category: str,
        normalized_category: str,
        source_record: dict[str, JsonValue],
    ) -> UpstreamLedgerRecord:
        return UpstreamLedgerRecord(
            source_project=self.source_project,
            source_repository=checkout.repository,
            source_commit=checkout.commit,
            source_path=_STRUCTURED_PATH.as_posix(),
            source_record_key=normalized_category,
            source_record_digest=canonical_json_digest(source_record),
            record_role=RecordRole.BENCHMARK_SCENARIO,
            source_asset_kind=SourceAssetKind.MCPSECBENCH_STRUCTURED_RECORD,
            asset_family="mcpsecbench",
            scenario_class="mcpsecbench_structured",
            category=declared_category,
            attack_present=True,
            attack_origin=None,
            attack_delivery_mode=None,
            raw_reuse_disposition=RawReuseDisposition.REVIEW_REQUIRED,
            native_conversion_disposition=(
                NativeConversionDisposition.ELIGIBLE_FOR_SEMANTIC_RECONSTRUCTION
            ),
            conversion_reason=(
                "Raw MCPSecBench content requires project-authored semantic reconstruction."
            ),
        )

    def _build_taxonomy_record(
        self,
        checkout: SourceCheckout,
        *,
        declared_category: str,
        normalized_category: str,
    ) -> UpstreamLedgerRecord:
        digest_input = (
            f"{_TAXONOMY_PATH.as_posix()}\n{normalized_category}\n{declared_category}"
        ).encode()
        return UpstreamLedgerRecord(
            source_project=self.source_project,
            source_repository=checkout.repository,
            source_commit=checkout.commit,
            source_path=_TAXONOMY_PATH.as_posix(),
            source_record_key=normalized_category,
            source_record_digest=hashlib.sha256(digest_input).hexdigest(),
            record_role=RecordRole.ATTACK_TAXONOMY,
            source_asset_kind=SourceAssetKind.MCPSECBENCH_TAXONOMY,
            asset_family="mcpsecbench",
            scenario_class="attack_taxonomy",
            category=declared_category,
            attack_present=None,
            attack_origin=None,
            attack_delivery_mode=None,
            raw_reuse_disposition=RawReuseDisposition.REVIEW_REQUIRED,
            native_conversion_disposition=NativeConversionDisposition.DESIGN_REFERENCE_ONLY,
            conversion_reason=(
                "MCPSecBench taxonomy metadata is retained as a design and generation reference."
            ),
        )
