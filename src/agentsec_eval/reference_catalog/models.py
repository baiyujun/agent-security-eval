"""Immutable upstream-ledger and coverage contracts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from enum import StrEnum
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Annotated, Literal, Self, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    model_validator,
)

from agentsec_eval.reference_catalog.enums import (
    BENCHMARK_KINDS,
    CONCRETE_ADAPTER_KINDS,
    FIXTURE_KINDS,
    NO_RUNTIME_OUTPUT_KINDS,
    PLUGIN_KINDS,
    REFERENCE_KINDS,
    STRATEGY_KINDS,
    TAXONOMY_KINDS,
    GenerationDependency,
    NativeConversionDisposition,
    NativeOutputKind,
    RawReuseDisposition,
    RecordRole,
    ReuseClassification,
    RuntimeOwnership,
    SourceAssetKind,
    StateScope,
)


def _validate_relative_posix_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        "\\" in value
        or "\x00" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or path.is_absolute()
        or re.match(r"^[A-Za-z]:/", value) is not None
        or any(part in {".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise ValueError("path must be a canonical relative POSIX path")
    return value


def _validate_non_empty_text(value: str) -> str:
    if not value.strip():
        raise ValueError("text must not be blank")
    if value != value.strip():
        raise ValueError("text must not contain leading or trailing whitespace")
    return value


NonEmptyText = Annotated[
    str,
    StringConstraints(strict=True, min_length=1),
    AfterValidator(_validate_non_empty_text),
]
CommitSha = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^[0-9a-f]{40}$"),
]
Sha256Digest = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$"),
]
RelativePosixPath = Annotated[
    str,
    StringConstraints(strict=True, min_length=1),
    AfterValidator(_validate_relative_posix_path),
]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]

_KeyT = TypeVar("_KeyT")


def _freeze_count_mapping(value: Mapping[_KeyT, int]) -> Mapping[_KeyT, int]:
    return MappingProxyType(dict(value))


def _serialize_count_mapping(value: Mapping[_KeyT, int]) -> dict[_KeyT, int]:
    return dict(value)


RecordRoleCounts = Annotated[
    Mapping[RecordRole, NonNegativeInt],
    AfterValidator(_freeze_count_mapping),
    PlainSerializer(_serialize_count_mapping, return_type=dict[RecordRole, int]),
]
RawReuseCounts = Annotated[
    Mapping[RawReuseDisposition, NonNegativeInt],
    AfterValidator(_freeze_count_mapping),
    PlainSerializer(_serialize_count_mapping, return_type=dict[RawReuseDisposition, int]),
]
NativeConversionCounts = Annotated[
    Mapping[NativeConversionDisposition, NonNegativeInt],
    AfterValidator(_freeze_count_mapping),
    PlainSerializer(
        _serialize_count_mapping,
        return_type=dict[NativeConversionDisposition, int],
    ),
]


class FrozenModel(BaseModel):
    """Base configuration shared by durable catalog contracts."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class EmbeddedDataSource(FrozenModel):
    repository: NonEmptyText
    commit: CommitSha
    path: RelativePosixPath
    digest: Sha256Digest
    license_disposition: RawReuseDisposition


class PromptfooEntryMetadata(FrozenModel):
    requires_target_feedback: bool | None = None
    state_scope: StateScope | None = None
    remote_inference_required: bool | None = None
    runtime_ownership: RuntimeOwnership | None = None
    reuse_classification: ReuseClassification | None = None
    plugin_collection_ids: tuple[NonEmptyText, ...] = ()
    expands_to_plugin_ids: tuple[NonEmptyText, ...] = ()
    expands_to_strategy_ids: tuple[NonEmptyText, ...] = ()
    alias_of: NonEmptyText | None = None
    generation_dependency: GenerationDependency | None = None
    repo_shell_applicable: bool | None = None
    mcp_applicable: bool | None = None
    future_domain_only: bool | None = None
    embedded_data_sources: tuple[EmbeddedDataSource, ...] = ()
    embedded_data_license_disposition: RawReuseDisposition | None = None
    grader_disposition: Literal["AUXILIARY_EVIDENCE"] | None = None


_ROLE_KINDS: dict[RecordRole, frozenset[SourceAssetKind]] = {
    RecordRole.BENCHMARK_SCENARIO: BENCHMARK_KINDS,
    RecordRole.NORMAL_TASK_FIXTURE: FIXTURE_KINDS,
    RecordRole.ATTACK_TAXONOMY: TAXONOMY_KINDS,
    RecordRole.ATTACK_GENERATION_ENTRY: PLUGIN_KINDS,
    RecordRole.DELIVERY_STRATEGY_ENTRY: STRATEGY_KINDS,
    RecordRole.IMPLEMENTATION_REFERENCE: REFERENCE_KINDS,
    RecordRole.SOURCE_REFERENCE: REFERENCE_KINDS,
}
_ADAPTER_DISPOSITIONS = frozenset(
    {
        NativeConversionDisposition.GENERATOR_ADAPTER_CANDIDATE,
        NativeConversionDisposition.POLICY_ADAPTER_CANDIDATE,
    }
)
_STRATEGY_RUNTIME_FIELDS = (
    "requires_target_feedback",
    "state_scope",
    "remote_inference_required",
    "runtime_ownership",
    "reuse_classification",
)
_PROMPTFOO_SCALAR_FIELDS = (
    *_STRATEGY_RUNTIME_FIELDS,
    "alias_of",
    "generation_dependency",
    "repo_shell_applicable",
    "mcp_applicable",
    "future_domain_only",
    "embedded_data_license_disposition",
    "grader_disposition",
)
_PROMPTFOO_COLLECTION_FIELDS = (
    "plugin_collection_ids",
    "expands_to_plugin_ids",
    "expands_to_strategy_ids",
    "embedded_data_sources",
)
_PROMPTFOO_ROLES = frozenset(
    {RecordRole.ATTACK_GENERATION_ENTRY, RecordRole.DELIVERY_STRATEGY_ENTRY}
)


class UpstreamLedgerRecord(PromptfooEntryMetadata):
    source_project: NonEmptyText
    source_repository: NonEmptyText
    source_commit: CommitSha
    source_path: RelativePosixPath
    source_record_key: NonEmptyText
    source_record_digest: Sha256Digest
    record_role: RecordRole
    source_asset_kind: SourceAssetKind
    asset_family: NonEmptyText
    scenario_class: NonEmptyText
    category: NonEmptyText
    attack_present: bool | None
    attack_origin: NonEmptyText | None
    attack_delivery_mode: NonEmptyText | None
    raw_reuse_disposition: RawReuseDisposition
    native_conversion_disposition: NativeConversionDisposition
    conversion_reason: NonEmptyText
    native_output_kind: NativeOutputKind | None = None
    native_output_id: NonEmptyText | None = None

    @model_validator(mode="after")
    def validate_record_invariants(self) -> Self:
        self._validate_role_and_kind()
        self._validate_adapter_disposition()
        self._validate_promptfoo_metadata()
        self._validate_native_output()
        return self

    def _validate_role_and_kind(self) -> None:
        if self.source_asset_kind not in _ROLE_KINDS[self.record_role]:
            raise ValueError("record_role and source_asset_kind are not an approved pair")
        if self.record_role in _PROMPTFOO_ROLES and self.source_project != "promptfoo":
            raise ValueError("Promptfoo entry roles require source_project='promptfoo'")
        if self.source_project == "promptfoo" and self.record_role not in _PROMPTFOO_ROLES:
            raise ValueError("Promptfoo records require a Promptfoo entry role")

    def _validate_adapter_disposition(self) -> None:
        if (
            self.native_conversion_disposition in _ADAPTER_DISPOSITIONS
            and self.source_asset_kind not in CONCRETE_ADAPTER_KINDS
        ):
            raise ValueError("Adapter candidates require a concrete Plugin or Strategy")

    def _validate_promptfoo_metadata(self) -> None:
        if self.record_role in _PROMPTFOO_ROLES and (
            self.generation_dependency is None or self.embedded_data_license_disposition is None
        ):
            raise ValueError(
                "Promptfoo Entry metadata requires generation_dependency and "
                "embedded_data_license_disposition"
            )

        runtime_values = tuple(getattr(self, field) for field in _STRATEGY_RUNTIME_FIELDS)
        if self.source_asset_kind in STRATEGY_KINDS:
            if any(value is None for value in runtime_values):
                raise ValueError("Promptfoo Strategy runtime metadata must be complete")
            self._validate_strategy_reuse_classification()
        elif any(value is not None for value in runtime_values):
            raise ValueError("non-Strategy rows must not contain Strategy runtime metadata")

        if self.source_project != "promptfoo":
            has_scalar_metadata = any(
                getattr(self, field) is not None for field in _PROMPTFOO_SCALAR_FIELDS
            )
            has_collection_metadata = any(
                bool(getattr(self, field)) for field in _PROMPTFOO_COLLECTION_FIELDS
            )
            if has_scalar_metadata or has_collection_metadata:
                raise ValueError("non-Promptfoo rows must not contain Promptfoo-specific metadata")

    def _validate_strategy_reuse_classification(self) -> None:
        expected_by_disposition = {
            NativeConversionDisposition.GENERATOR_ADAPTER_CANDIDATE: (
                ReuseClassification.GENERATOR_ADAPTER_REUSE
            ),
            NativeConversionDisposition.POLICY_ADAPTER_CANDIDATE: (
                ReuseClassification.POLICY_ADAPTER_CANDIDATE
            ),
            NativeConversionDisposition.DESIGN_REFERENCE_ONLY: ReuseClassification.DESIGN_REFERENCE,
            NativeConversionDisposition.DUPLICATE: ReuseClassification.DESIGN_REFERENCE,
            NativeConversionDisposition.UNSUPPORTED: ReuseClassification.REJECT,
        }
        expected = expected_by_disposition.get(self.native_conversion_disposition)
        if expected is not None and self.reuse_classification is not expected:
            raise ValueError("Strategy reuse_classification must match its conversion disposition")

    def _validate_native_output(self) -> None:
        if self.native_output_kind is None:
            if self.native_output_id is not None:
                raise ValueError("native_output_id requires a concrete native_output_kind")
            return
        if self.native_output_kind is NativeOutputKind.NONE:
            if self.native_output_id is not None:
                raise ValueError("none native output must have a null native_output_id")
        elif self.native_output_id is None:
            raise ValueError("concrete native_output_kind requires a native_output_id")

        allowed_kind = self._allowed_native_output_kind()
        if self.native_output_kind is not allowed_kind:
            raise ValueError(
                f"native output for {self.record_role.value}/{self.source_asset_kind.value} "
                f"must be {allowed_kind.value}"
            )

    def _allowed_native_output_kind(self) -> NativeOutputKind:
        if self.record_role in {
            RecordRole.BENCHMARK_SCENARIO,
            RecordRole.NORMAL_TASK_FIXTURE,
        }:
            return NativeOutputKind.SCENARIO_ASSET
        if self.source_asset_kind in NO_RUNTIME_OUTPUT_KINDS or self.record_role in {
            RecordRole.ATTACK_TAXONOMY,
            RecordRole.IMPLEMENTATION_REFERENCE,
            RecordRole.SOURCE_REFERENCE,
        }:
            return NativeOutputKind.NONE
        if (
            self.native_conversion_disposition
            is NativeConversionDisposition.GENERATOR_ADAPTER_CANDIDATE
        ):
            return NativeOutputKind.GENERATOR_ADAPTER
        if (
            self.native_conversion_disposition
            is NativeConversionDisposition.POLICY_ADAPTER_CANDIDATE
        ):
            return NativeOutputKind.POLICY_ADAPTER
        return NativeOutputKind.NONE


_EnumT = TypeVar("_EnumT", bound=StrEnum)


def _require_all_enum_keys(
    counts: Mapping[_EnumT, NonNegativeInt],
    enum_type: type[_EnumT],
    field_name: str,
) -> None:
    if set(counts) != set(enum_type.__members__.values()):
        raise ValueError(f"{field_name} must contain every {enum_type.__name__} key")


class PromptfooSummary(FrozenModel):
    concrete_plugin_ids: NonNegativeInt
    plugin_collection_ids: NonNegativeInt
    alias_only_plugin_selectors: NonNegativeInt
    unique_plugin_entries: NonNegativeInt
    accepted_strategy_ids: NonNegativeInt
    registry_only_strategy_stubs: NonNegativeInt
    strategy_entries: NonNegativeInt

    @model_validator(mode="after")
    def validate_totals(self) -> Self:
        plugin_total = (
            self.concrete_plugin_ids + self.plugin_collection_ids + self.alias_only_plugin_selectors
        )
        if self.unique_plugin_entries != plugin_total:
            raise ValueError("unique_plugin_entries must equal all Plugin entry counts")
        if self.strategy_entries != (
            self.accepted_strategy_ids + self.registry_only_strategy_stubs
        ):
            raise ValueError("strategy_entries must equal all Strategy entry counts")
        return self


class SaberSummary(FrozenModel):
    expected_upstream_total: NonNegativeInt
    discovered_total: NonNegativeInt
    indexed_total: NonNegativeInt
    scenario_a_count: NonNegativeInt
    scenario_b_count: NonNegativeInt
    scenario_c_count: NonNegativeInt

    @model_validator(mode="after")
    def validate_totals(self) -> Self:
        if not (
            self.expected_upstream_total == self.discovered_total == self.indexed_total
        ) or self.expected_upstream_total != (
            self.scenario_a_count + self.scenario_b_count + self.scenario_c_count
        ):
            raise ValueError("SABER expected, discovered, indexed, and A/B/C totals must agree")
        return self


class SourceCoverage(FrozenModel):
    source_project: NonEmptyText
    discovered_total: NonNegativeInt
    indexed_total: NonNegativeInt
    record_role_counts: RecordRoleCounts
    raw_reuse_counts: RawReuseCounts
    native_conversion_counts: NativeConversionCounts

    @model_validator(mode="after")
    def validate_conservation(self) -> Self:
        _require_all_enum_keys(self.record_role_counts, RecordRole, "record_role_counts")
        _require_all_enum_keys(self.raw_reuse_counts, RawReuseDisposition, "raw_reuse_counts")
        _require_all_enum_keys(
            self.native_conversion_counts,
            NativeConversionDisposition,
            "native_conversion_counts",
        )
        if self.indexed_total != self.discovered_total:
            raise ValueError("indexed_total must equal discovered_total")
        if sum(self.record_role_counts.values()) != self.discovered_total:
            raise ValueError("record role conservation must equal discovered_total")
        if sum(self.raw_reuse_counts.values()) != self.discovered_total:
            raise ValueError("raw reuse conservation must equal discovered_total")
        if sum(self.native_conversion_counts.values()) != self.discovered_total:
            raise ValueError("native conversion conservation must equal discovered_total")
        return self


class CoverageSummary(FrozenModel):
    source_order: tuple[NonEmptyText, ...]
    sources: tuple[SourceCoverage, ...]
    role_counts: RecordRoleCounts
    raw_reuse_counts: RawReuseCounts
    native_conversion_counts: NativeConversionCounts
    promptfoo_summary: PromptfooSummary
    saber_summary: SaberSummary
    ledger_total: NonNegativeInt

    @model_validator(mode="after")
    def validate_conservation(self) -> Self:
        _require_all_enum_keys(self.role_counts, RecordRole, "role_counts")
        _require_all_enum_keys(self.raw_reuse_counts, RawReuseDisposition, "raw_reuse_counts")
        _require_all_enum_keys(
            self.native_conversion_counts,
            NativeConversionDisposition,
            "native_conversion_counts",
        )
        source_projects = tuple(source.source_project for source in self.sources)
        if len(set(source_projects)) != len(source_projects):
            raise ValueError("sources must not contain a duplicate source_project")
        if self.source_order != source_projects:
            raise ValueError("source_order must match sources in order")
        if sum(source.indexed_total for source in self.sources) != self.ledger_total:
            raise ValueError("source totals must equal ledger_total")
        if sum(self.role_counts.values()) != self.ledger_total:
            raise ValueError("role conservation must equal ledger_total")
        if sum(self.raw_reuse_counts.values()) != self.ledger_total:
            raise ValueError("raw reuse conservation must equal ledger_total")
        if sum(self.native_conversion_counts.values()) != self.ledger_total:
            raise ValueError("native conversion conservation must equal ledger_total")
        self._validate_aggregate_counts()
        self._validate_source_summaries()
        return self

    def _validate_aggregate_counts(self) -> None:
        expected_roles = {role: 0 for role in RecordRole}
        expected_raw_reuse = {raw_disposition: 0 for raw_disposition in RawReuseDisposition}
        expected_native_conversion = {
            native_disposition: 0 for native_disposition in NativeConversionDisposition
        }
        for source in self.sources:
            for role, count in source.record_role_counts.items():
                expected_roles[role] += count
            for raw_disposition, count in source.raw_reuse_counts.items():
                expected_raw_reuse[raw_disposition] += count
            for native_disposition, count in source.native_conversion_counts.items():
                expected_native_conversion[native_disposition] += count
        if expected_roles != self.role_counts:
            raise ValueError("role conservation must match source counts")
        if expected_raw_reuse != self.raw_reuse_counts:
            raise ValueError("raw reuse conservation must match source counts")
        if expected_native_conversion != self.native_conversion_counts:
            raise ValueError("native conversion conservation must match source counts")

    def _validate_source_summaries(self) -> None:
        sources_by_project = {source.source_project: source for source in self.sources}
        promptfoo_source = sources_by_project.get("promptfoo")
        plugin_entries = self.promptfoo_summary.unique_plugin_entries
        strategy_entries = self.promptfoo_summary.strategy_entries
        if plugin_entries != self.role_counts[RecordRole.ATTACK_GENERATION_ENTRY]:
            raise ValueError("Promptfoo Plugin summary must match its RecordRole count")
        if strategy_entries != self.role_counts[RecordRole.DELIVERY_STRATEGY_ENTRY]:
            raise ValueError("Promptfoo Strategy summary must match its RecordRole count")
        promptfoo_total = 0 if promptfoo_source is None else promptfoo_source.indexed_total
        if plugin_entries + strategy_entries != promptfoo_total:
            raise ValueError("Promptfoo summary must match the Promptfoo source total")

        saber_source = sources_by_project.get("saber")
        saber_discovered = 0 if saber_source is None else saber_source.discovered_total
        saber_indexed = 0 if saber_source is None else saber_source.indexed_total
        if (
            self.saber_summary.discovered_total != saber_discovered
            or self.saber_summary.indexed_total != saber_indexed
        ):
            raise ValueError("SABER summary must match the SABER source totals")
