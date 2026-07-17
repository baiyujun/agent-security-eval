from __future__ import annotations

from enum import StrEnum
from typing import TypeVar

import pytest
from pydantic import ValidationError

from agentsec_eval.reference_catalog.enums import (
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
from agentsec_eval.reference_catalog.models import (
    CoverageSummary,
    EmbeddedDataSource,
    PromptfooSummary,
    SaberSummary,
    SourceCoverage,
    UpstreamLedgerRecord,
)


@pytest.fixture
def record_values() -> dict[str, object]:
    return {
        "source_project": "saber",
        "source_repository": "https://github.com/ethz-spylab/saber",
        "source_commit": "a" * 40,
        "source_path": "tasks/A/info/A_info_001.json",
        "source_record_key": "A_info_001",
        "source_record_digest": "b" * 64,
        "record_role": "benchmark_scenario",
        "source_asset_kind": "saber_task",
        "asset_family": "saber",
        "scenario_class": "A",
        "category": "info",
        "attack_present": True,
        "attack_origin": "environment",
        "attack_delivery_mode": "tool_output",
        "raw_reuse_disposition": "review_required",
        "native_conversion_disposition": "eligible_for_semantic_reconstruction",
        "conversion_reason": "Reconstruct the security semantics without copying source text.",
    }


ENUM_VALUES: dict[type[StrEnum], set[str]] = {
    RecordRole: {
        "benchmark_scenario",
        "normal_task_fixture",
        "attack_taxonomy",
        "attack_generation_entry",
        "delivery_strategy_entry",
        "implementation_reference",
        "source_reference",
    },
    SourceAssetKind: {
        "saber_task",
        "codeipi_sample",
        "terminal_bench_task_directory",
        "mcp_safetybench_task",
        "mcpsecbench_structured_record",
        "mcpsecbench_taxonomy",
        "plugin",
        "plugin_collection",
        "plugin_alias",
        "strategy",
        "strategy_preset",
        "strategy_collection",
        "strategy_alias",
        "deprecated_strategy_stub",
        "source_code",
        "test_source",
        "configuration",
        "license",
        "documentation",
    },
    RawReuseDisposition: {"allowed", "review_required", "prohibited", "not_applicable"},
    NativeConversionDisposition: {
        "eligible_for_semantic_reconstruction",
        "direct_import_allowed",
        "generator_adapter_candidate",
        "policy_adapter_candidate",
        "design_reference_only",
        "unsupported",
        "duplicate",
        "intentionally_excluded",
        "malformed",
        "conversion_failed",
    },
    NativeOutputKind: {"scenario_asset", "generator_adapter", "policy_adapter", "none"},
    StateScope: {"none", "per_candidate", "per_run", "cross_run"},
    RuntimeOwnership: {"project", "promptfoo_bound"},
    GenerationDependency: {"local_only", "local_or_remote", "remote_only", "not_applicable"},
    ReuseClassification: {
        "GENERATOR_ADAPTER_REUSE",
        "POLICY_ADAPTER_CANDIDATE",
        "DESIGN_REFERENCE",
        "REJECT",
    },
}


@pytest.mark.parametrize(("enum_type", "values"), ENUM_VALUES.items())
def test_closed_enums_match_the_approved_specification(
    enum_type: type[StrEnum], values: set[str]
) -> None:
    assert {member.value for member in enum_type.__members__.values()} == values


def test_ledger_record_is_frozen_and_forbids_extra_fields(
    record_values: dict[str, object],
) -> None:
    record = UpstreamLedgerRecord.model_validate(record_values)

    with pytest.raises(ValidationError, match="frozen"):
        record.source_project = "changed"

    with pytest.raises(ValidationError, match="extra_forbidden"):
        UpstreamLedgerRecord.model_validate({**record_values, "payload": "not safe metadata"})


@pytest.mark.parametrize("field", ["source_project", "source_record_key", "conversion_reason"])
def test_required_text_fields_reject_blank_or_non_string_values(
    record_values: dict[str, object], field: str
) -> None:
    for invalid_value in ("   ", 7):
        invalid = {**record_values, field: invalid_value}
        with pytest.raises(ValidationError):
            UpstreamLedgerRecord.model_validate(invalid)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("source_commit", "a" * 39),
        ("source_commit", "A" * 40),
        ("source_commit", 1),
        ("source_record_digest", "b" * 63),
        ("source_record_digest", "B" * 64),
        ("source_record_digest", 1),
    ],
)
def test_commit_and_sha256_fields_are_strict_lowercase_hex(
    record_values: dict[str, object], field: str, invalid_value: object
) -> None:
    with pytest.raises(ValidationError):
        UpstreamLedgerRecord.model_validate({**record_values, field: invalid_value})


@pytest.mark.parametrize(
    "source_path",
    [
        "/etc/passwd",
        "../tasks/item.json",
        "tasks/../item.json",
        "tasks\\item.json",
        "C:/tasks/item.json",
        "tasks//item.json",
        "./tasks/item.json",
        "",
        3,
    ],
)
def test_source_path_requires_a_canonical_relative_posix_path(
    record_values: dict[str, object], source_path: object
) -> None:
    with pytest.raises(ValidationError):
        UpstreamLedgerRecord.model_validate({**record_values, "source_path": source_path})


@pytest.mark.parametrize(
    ("record_role", "source_asset_kind"),
    [
        ("benchmark_scenario", "saber_task"),
        ("benchmark_scenario", "codeipi_sample"),
        ("benchmark_scenario", "mcp_safetybench_task"),
        ("benchmark_scenario", "mcpsecbench_structured_record"),
        ("normal_task_fixture", "terminal_bench_task_directory"),
        ("attack_taxonomy", "mcpsecbench_taxonomy"),
        ("attack_generation_entry", "plugin"),
        ("attack_generation_entry", "plugin_collection"),
        ("attack_generation_entry", "plugin_alias"),
        ("delivery_strategy_entry", "strategy"),
        ("delivery_strategy_entry", "strategy_preset"),
        ("delivery_strategy_entry", "strategy_collection"),
        ("delivery_strategy_entry", "strategy_alias"),
        ("delivery_strategy_entry", "deprecated_strategy_stub"),
        ("implementation_reference", "source_code"),
        ("implementation_reference", "test_source"),
        ("implementation_reference", "configuration"),
        ("implementation_reference", "license"),
        ("implementation_reference", "documentation"),
        ("source_reference", "source_code"),
        ("source_reference", "test_source"),
        ("source_reference", "configuration"),
        ("source_reference", "license"),
        ("source_reference", "documentation"),
    ],
)
def test_role_and_source_kind_table_accepts_only_approved_pairs(
    record_values: dict[str, object], record_role: str, source_asset_kind: str
) -> None:
    values = {
        **record_values,
        "record_role": record_role,
        "source_asset_kind": source_asset_kind,
    }
    if record_role in {"attack_generation_entry", "delivery_strategy_entry"}:
        values["source_project"] = "promptfoo"
    if record_role == "delivery_strategy_entry":
        values.update(strategy_runtime_values())

    record = UpstreamLedgerRecord.model_validate(values)

    assert record.record_role.value == record_role
    assert record.source_asset_kind.value == source_asset_kind


def test_mismatched_role_and_source_kind_is_rejected(record_values: dict[str, object]) -> None:
    record_values["source_asset_kind"] = "plugin"

    with pytest.raises(ValidationError, match="record_role.*source_asset_kind"):
        UpstreamLedgerRecord.model_validate(record_values)


SELECTOR_KINDS = [
    "plugin_collection",
    "plugin_alias",
    "strategy_preset",
    "strategy_collection",
    "strategy_alias",
    "deprecated_strategy_stub",
]


@pytest.mark.parametrize("source_asset_kind", SELECTOR_KINDS)
@pytest.mark.parametrize(
    "native_conversion_disposition",
    ["generator_adapter_candidate", "policy_adapter_candidate"],
)
def test_selectors_cannot_be_adapter_candidates(
    record_values: dict[str, object],
    source_asset_kind: str,
    native_conversion_disposition: str,
) -> None:
    role = (
        "attack_generation_entry"
        if source_asset_kind.startswith("plugin")
        else "delivery_strategy_entry"
    )
    record_values.update(
        source_project="promptfoo",
        record_role=role,
        source_asset_kind=source_asset_kind,
        native_conversion_disposition=native_conversion_disposition,
    )
    if role == "delivery_strategy_entry":
        record_values.update(strategy_runtime_values())

    with pytest.raises(ValidationError, match="concrete Plugin or Strategy"):
        UpstreamLedgerRecord.model_validate(record_values)


def strategy_runtime_values(
    reuse_classification: str = "GENERATOR_ADAPTER_REUSE",
) -> dict[str, object]:
    return {
        "requires_target_feedback": False,
        "state_scope": "none",
        "remote_inference_required": False,
        "runtime_ownership": "project",
        "reuse_classification": reuse_classification,
    }


@pytest.mark.parametrize("missing_field", strategy_runtime_values())
def test_promptfoo_strategy_requires_complete_runtime_metadata(
    record_values: dict[str, object], missing_field: str
) -> None:
    record_values.update(
        source_project="promptfoo",
        record_role="delivery_strategy_entry",
        source_asset_kind="strategy",
        native_conversion_disposition="generator_adapter_candidate",
        **strategy_runtime_values(),
    )
    record_values[missing_field] = None

    with pytest.raises(ValidationError, match="Strategy runtime metadata"):
        UpstreamLedgerRecord.model_validate(record_values)


def test_non_strategy_rejects_strategy_runtime_metadata(record_values: dict[str, object]) -> None:
    record_values["state_scope"] = "none"

    with pytest.raises(ValidationError, match="non-Strategy"):
        UpstreamLedgerRecord.model_validate(record_values)


def test_non_promptfoo_record_rejects_promptfoo_specific_metadata(
    record_values: dict[str, object],
) -> None:
    record_values["plugin_collection_ids"] = ["harmful"]

    with pytest.raises(ValidationError, match="non-Promptfoo"):
        UpstreamLedgerRecord.model_validate(record_values)


def test_embedded_data_source_uses_only_strict_safe_metadata() -> None:
    source = EmbeddedDataSource(
        repository="https://example.invalid/source",
        commit="c" * 40,
        path="datasets/prompts.json",
        digest="d" * 64,
        license_disposition=RawReuseDisposition.REVIEW_REQUIRED,
    )

    assert source.path == "datasets/prompts.json"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        EmbeddedDataSource.model_validate({**source.model_dump(), "content": "forbidden"})


def test_initial_native_output_fields_are_paired(record_values: dict[str, object]) -> None:
    record_values["native_output_kind"] = "scenario_asset"

    with pytest.raises(ValidationError, match="native_output"):
        UpstreamLedgerRecord.model_validate(record_values)


def test_native_output_id_without_kind_is_rejected(record_values: dict[str, object]) -> None:
    record_values["native_output_id"] = "scenario/A_info_001"

    with pytest.raises(ValidationError, match="native_output"):
        UpstreamLedgerRecord.model_validate(record_values)


@pytest.mark.parametrize(
    (
        "record_role",
        "source_asset_kind",
        "native_conversion_disposition",
        "native_output_kind",
    ),
    [
        (
            "benchmark_scenario",
            "saber_task",
            "eligible_for_semantic_reconstruction",
            "scenario_asset",
        ),
        (
            "normal_task_fixture",
            "terminal_bench_task_directory",
            "eligible_for_semantic_reconstruction",
            "scenario_asset",
        ),
        ("attack_taxonomy", "mcpsecbench_taxonomy", "design_reference_only", "none"),
        ("attack_generation_entry", "plugin_collection", "design_reference_only", "none"),
        ("delivery_strategy_entry", "strategy_alias", "design_reference_only", "none"),
        ("implementation_reference", "source_code", "design_reference_only", "none"),
        ("source_reference", "documentation", "design_reference_only", "none"),
        (
            "attack_generation_entry",
            "plugin",
            "generator_adapter_candidate",
            "generator_adapter",
        ),
        (
            "attack_generation_entry",
            "plugin",
            "policy_adapter_candidate",
            "policy_adapter",
        ),
        (
            "delivery_strategy_entry",
            "strategy",
            "generator_adapter_candidate",
            "generator_adapter",
        ),
        (
            "delivery_strategy_entry",
            "strategy",
            "policy_adapter_candidate",
            "policy_adapter",
        ),
    ],
)
def test_non_initial_native_outputs_follow_the_role_kind_table(
    record_values: dict[str, object],
    record_role: str,
    source_asset_kind: str,
    native_conversion_disposition: str,
    native_output_kind: str,
) -> None:
    record_values.update(
        record_role=record_role,
        source_asset_kind=source_asset_kind,
        native_conversion_disposition=native_conversion_disposition,
        native_output_kind=native_output_kind,
        native_output_id="native/output-001",
    )
    if record_role in {"attack_generation_entry", "delivery_strategy_entry"}:
        record_values["source_project"] = "promptfoo"
    if record_role == "delivery_strategy_entry":
        reuse_classification = {
            "generator_adapter_candidate": "GENERATOR_ADAPTER_REUSE",
            "policy_adapter_candidate": "POLICY_ADAPTER_CANDIDATE",
            "design_reference_only": "DESIGN_REFERENCE",
        }.get(native_conversion_disposition, "GENERATOR_ADAPTER_REUSE")
        record_values.update(strategy_runtime_values(reuse_classification))

    record = UpstreamLedgerRecord.model_validate(record_values)

    assert record.native_output_kind is NativeOutputKind(native_output_kind)


@pytest.mark.parametrize(
    ("record_role", "source_asset_kind", "native_output_kind"),
    [
        ("benchmark_scenario", "saber_task", "none"),
        ("normal_task_fixture", "terminal_bench_task_directory", "generator_adapter"),
        ("attack_taxonomy", "mcpsecbench_taxonomy", "scenario_asset"),
        ("attack_generation_entry", "plugin_collection", "generator_adapter"),
        ("implementation_reference", "source_code", "scenario_asset"),
    ],
)
def test_non_initial_native_outputs_reject_prohibited_mappings(
    record_values: dict[str, object],
    record_role: str,
    source_asset_kind: str,
    native_output_kind: str,
) -> None:
    record_values.update(
        record_role=record_role,
        source_asset_kind=source_asset_kind,
        native_output_kind=native_output_kind,
        native_output_id="native/output-001",
    )
    if record_role == "attack_generation_entry":
        record_values["source_project"] = "promptfoo"

    with pytest.raises(ValidationError, match="native output"):
        UpstreamLedgerRecord.model_validate(record_values)


_EnumT = TypeVar("_EnumT", bound=StrEnum)


def all_counts(enum_type: type[_EnumT], **nonzero: int) -> dict[_EnumT, int]:
    return {member: nonzero.get(member.value, 0) for member in enum_type.__members__.values()}


def valid_source_coverage() -> SourceCoverage:
    return SourceCoverage(
        source_project="saber",
        discovered_total=1,
        indexed_total=1,
        record_role_counts=all_counts(RecordRole, benchmark_scenario=1),
        raw_reuse_counts=all_counts(RawReuseDisposition, review_required=1),
        native_conversion_counts=all_counts(
            NativeConversionDisposition,
            eligible_for_semantic_reconstruction=1,
        ),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("indexed_total", 0),
        ("record_role_counts", all_counts(RecordRole)),
        ("raw_reuse_counts", all_counts(RawReuseDisposition)),
        ("native_conversion_counts", all_counts(NativeConversionDisposition)),
    ],
)
def test_source_coverage_enforces_index_and_conservation(field: str, value: object) -> None:
    values = valid_source_coverage().model_dump()
    values[field] = value

    with pytest.raises(ValidationError, match="conservation|indexed_total"):
        SourceCoverage.model_validate(values)


def test_source_coverage_requires_every_enum_count_key() -> None:
    values = valid_source_coverage().model_dump()
    record_role_counts = values["record_role_counts"]
    assert isinstance(record_role_counts, dict)
    record_role_counts.pop(RecordRole.SOURCE_REFERENCE)

    with pytest.raises(ValidationError, match="every RecordRole"):
        SourceCoverage.model_validate(values)


def valid_coverage_summary() -> CoverageSummary:
    source = valid_source_coverage()
    return CoverageSummary(
        source_order=("saber",),
        sources=(source,),
        role_counts=all_counts(RecordRole, benchmark_scenario=1),
        raw_reuse_counts=all_counts(RawReuseDisposition, review_required=1),
        native_conversion_counts=all_counts(
            NativeConversionDisposition,
            eligible_for_semantic_reconstruction=1,
        ),
        promptfoo_summary=PromptfooSummary(
            concrete_plugin_ids=0,
            plugin_collection_ids=0,
            alias_only_plugin_selectors=0,
            unique_plugin_entries=0,
            accepted_strategy_ids=0,
            registry_only_strategy_stubs=0,
            strategy_entries=0,
        ),
        saber_summary=SaberSummary(
            expected_upstream_total=1,
            discovered_total=1,
            indexed_total=1,
            scenario_a_count=1,
            scenario_b_count=0,
            scenario_c_count=0,
        ),
        ledger_total=1,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ledger_total", 2),
        ("source_order", ("other",)),
        ("role_counts", all_counts(RecordRole)),
        ("raw_reuse_counts", all_counts(RawReuseDisposition)),
        ("native_conversion_counts", all_counts(NativeConversionDisposition)),
    ],
)
def test_coverage_summary_enforces_source_order_and_global_conservation(
    field: str, value: object
) -> None:
    values = valid_coverage_summary().model_dump()
    values[field] = value

    with pytest.raises(ValidationError, match="ledger_total|source_order|conservation"):
        CoverageSummary.model_validate(values)


def test_promptfoo_and_saber_summaries_enforce_internal_totals() -> None:
    with pytest.raises(ValidationError, match="unique_plugin_entries"):
        PromptfooSummary(
            concrete_plugin_ids=1,
            plugin_collection_ids=1,
            alias_only_plugin_selectors=1,
            unique_plugin_entries=2,
            accepted_strategy_ids=0,
            registry_only_strategy_stubs=0,
            strategy_entries=0,
        )

    with pytest.raises(ValidationError, match="SABER"):
        SaberSummary(
            expected_upstream_total=2,
            discovered_total=2,
            indexed_total=2,
            scenario_a_count=1,
            scenario_b_count=0,
            scenario_c_count=0,
        )
