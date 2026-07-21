"""Safe discovery of locked Inspect Evals CodeIPI records."""

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

_SOURCE_PATH = PurePosixPath("src/inspect_evals/ipi_coding_agent/dataset/samples.json")
_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "is_benign",
        "injection_vector",
        "payload_category",
        "severity",
        "issue_text",
        "task_description",
        "payload_indicator",
        "payload_sophistication",
        "repo_files",
        "expected_malicious_action",
        "expected_fix",
        "verification_command",
    }
)
_OPTIONAL_FIELDS = frozenset({"persistence_targets"})


def _safe_file(root: Path, path: Path) -> Path:
    if path.is_symlink():
        raise ValueError(f"CodeIPI source file must not be a symlink: {path}")
    try:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"CodeIPI source file does not exist: {path}") from error
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"CodeIPI source path escape: {path}")
    if not resolved.is_file():
        raise ValueError(f"CodeIPI source path is not a file: {path}")
    return resolved


def _required_text(sample: Mapping[str, JsonValue], key: str, *, index: int) -> str:
    value = sample.get(key)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"CodeIPI sample {index}.{key} must be non-empty text")
    return value


def _load_samples(path: Path) -> list[dict[str, JsonValue]]:
    try:
        value = cast(JsonValue, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"malformed JSON in CodeIPI source: {path}") from error
    if not isinstance(value, list):
        raise ValueError("CodeIPI source must contain a JSON array")
    samples: list[dict[str, JsonValue]] = []
    for index, sample in enumerate(value):
        if not isinstance(sample, dict) or not all(isinstance(key, str) for key in sample):
            raise ValueError(f"CodeIPI sample {index} must be a JSON object")
        samples.append(sample)
    return samples


@dataclass(frozen=True)
class CodeIPIDiscoverer:
    """Discover every CodeIPI record or fail without returning a partial list."""

    source_project: ClassVar[str] = "inspect-evals-codeipi"
    expected_total: int = 45

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]:
        checkout = context.checkouts.get(self.source_project)
        if checkout is None:
            raise ValueError("CodeIPI checkout is missing from the discovery context")
        if self.expected_total < 0:
            raise ValueError("CodeIPI expected total must be non-negative")
        source_file = _safe_file(checkout.root, checkout.root.joinpath(*_SOURCE_PATH.parts))
        samples = _load_samples(source_file)
        if len(samples) != self.expected_total:
            raise ValueError(
                f"expected {self.expected_total} CodeIPI samples, discovered {len(samples)}"
            )

        validated_samples: list[tuple[str, str, str, bool, dict[str, JsonValue]]] = []
        seen_ids: set[str] = set()
        for index, sample in enumerate(samples):
            fields = set(sample)
            if not _REQUIRED_FIELDS.issubset(fields) or not fields.issubset(
                _REQUIRED_FIELDS | _OPTIONAL_FIELDS
            ):
                missing = sorted(_REQUIRED_FIELDS - fields)
                unknown = sorted(fields - _REQUIRED_FIELDS - _OPTIONAL_FIELDS)
                raise ValueError(
                    f"CodeIPI sample {index} has invalid structural fields: "
                    f"missing={missing}, unknown={unknown}"
                )
            sample_id = _required_text(sample, "id", index=index)
            if sample_id in seen_ids:
                raise ValueError(f"duplicate CodeIPI ID: {sample_id}")
            seen_ids.add(sample_id)
            is_benign = sample.get("is_benign")
            if type(is_benign) is not bool:
                raise ValueError(f"CodeIPI sample {index}.is_benign must be boolean")
            injection_vector = _required_text(sample, "injection_vector", index=index)
            category = _required_text(sample, "payload_category", index=index)
            _required_text(sample, "severity", index=index)
            validated_samples.append((sample_id, injection_vector, category, is_benign, sample))

        records = [
            self._build_record(
                checkout,
                sample_id=sample_id,
                injection_vector=injection_vector,
                category=category,
                is_benign=is_benign,
                sample=sample,
            )
            for sample_id, injection_vector, category, is_benign, sample in sorted(
                validated_samples,
                key=lambda item: item[0],
            )
        ]
        return list(validate_records(records, require_initial_outputs=True))

    def _build_record(
        self,
        checkout: SourceCheckout,
        *,
        sample_id: str,
        injection_vector: str,
        category: str,
        is_benign: bool,
        sample: dict[str, JsonValue],
    ) -> UpstreamLedgerRecord:
        return UpstreamLedgerRecord(
            source_project=self.source_project,
            source_repository=checkout.repository,
            source_commit=checkout.commit,
            source_path=_SOURCE_PATH.as_posix(),
            source_record_key=sample_id,
            source_record_digest=canonical_json_digest(sample),
            record_role=RecordRole.BENCHMARK_SCENARIO,
            source_asset_kind=SourceAssetKind.CODEIPI_SAMPLE,
            asset_family="codeipi",
            scenario_class="codeipi",
            category=category,
            attack_present=not is_benign,
            attack_origin=None,
            attack_delivery_mode=injection_vector,
            raw_reuse_disposition=RawReuseDisposition.REVIEW_REQUIRED,
            native_conversion_disposition=(
                NativeConversionDisposition.ELIGIBLE_FOR_SEMANTIC_RECONSTRUCTION
            ),
            conversion_reason=(
                "Raw CodeIPI content requires project-authored semantic reconstruction."
            ),
        )
