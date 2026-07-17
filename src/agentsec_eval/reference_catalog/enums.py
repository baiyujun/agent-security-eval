"""Closed vocabularies for the upstream reference catalog."""

from __future__ import annotations

from enum import StrEnum


class RecordRole(StrEnum):
    BENCHMARK_SCENARIO = "benchmark_scenario"
    NORMAL_TASK_FIXTURE = "normal_task_fixture"
    ATTACK_TAXONOMY = "attack_taxonomy"
    ATTACK_GENERATION_ENTRY = "attack_generation_entry"
    DELIVERY_STRATEGY_ENTRY = "delivery_strategy_entry"
    IMPLEMENTATION_REFERENCE = "implementation_reference"
    SOURCE_REFERENCE = "source_reference"


class SourceAssetKind(StrEnum):
    SABER_TASK = "saber_task"
    CODEIPI_SAMPLE = "codeipi_sample"
    TERMINAL_BENCH_TASK_DIRECTORY = "terminal_bench_task_directory"
    MCP_SAFETYBENCH_TASK = "mcp_safetybench_task"
    MCPSECBENCH_STRUCTURED_RECORD = "mcpsecbench_structured_record"
    MCPSECBENCH_TAXONOMY = "mcpsecbench_taxonomy"
    PLUGIN = "plugin"
    PLUGIN_COLLECTION = "plugin_collection"
    PLUGIN_ALIAS = "plugin_alias"
    STRATEGY = "strategy"
    STRATEGY_PRESET = "strategy_preset"
    STRATEGY_COLLECTION = "strategy_collection"
    STRATEGY_ALIAS = "strategy_alias"
    DEPRECATED_STRATEGY_STUB = "deprecated_strategy_stub"
    SOURCE_CODE = "source_code"
    TEST_SOURCE = "test_source"
    CONFIGURATION = "configuration"
    LICENSE = "license"
    DOCUMENTATION = "documentation"


class RawReuseDisposition(StrEnum):
    ALLOWED = "allowed"
    REVIEW_REQUIRED = "review_required"
    PROHIBITED = "prohibited"
    NOT_APPLICABLE = "not_applicable"


class NativeConversionDisposition(StrEnum):
    ELIGIBLE_FOR_SEMANTIC_RECONSTRUCTION = "eligible_for_semantic_reconstruction"
    DIRECT_IMPORT_ALLOWED = "direct_import_allowed"
    GENERATOR_ADAPTER_CANDIDATE = "generator_adapter_candidate"
    POLICY_ADAPTER_CANDIDATE = "policy_adapter_candidate"
    DESIGN_REFERENCE_ONLY = "design_reference_only"
    UNSUPPORTED = "unsupported"
    DUPLICATE = "duplicate"
    INTENTIONALLY_EXCLUDED = "intentionally_excluded"
    MALFORMED = "malformed"
    CONVERSION_FAILED = "conversion_failed"


class NativeOutputKind(StrEnum):
    SCENARIO_ASSET = "scenario_asset"
    GENERATOR_ADAPTER = "generator_adapter"
    POLICY_ADAPTER = "policy_adapter"
    NONE = "none"


class StateScope(StrEnum):
    NONE = "none"
    PER_CANDIDATE = "per_candidate"
    PER_RUN = "per_run"
    CROSS_RUN = "cross_run"


class RuntimeOwnership(StrEnum):
    PROJECT = "project"
    PROMPTFOO_BOUND = "promptfoo_bound"


class GenerationDependency(StrEnum):
    LOCAL_ONLY = "local_only"
    LOCAL_OR_REMOTE = "local_or_remote"
    REMOTE_ONLY = "remote_only"
    NOT_APPLICABLE = "not_applicable"


class ReuseClassification(StrEnum):
    GENERATOR_ADAPTER_REUSE = "GENERATOR_ADAPTER_REUSE"
    POLICY_ADAPTER_CANDIDATE = "POLICY_ADAPTER_CANDIDATE"
    DESIGN_REFERENCE = "DESIGN_REFERENCE"
    REJECT = "REJECT"


BENCHMARK_KINDS = frozenset(
    {
        SourceAssetKind.SABER_TASK,
        SourceAssetKind.CODEIPI_SAMPLE,
        SourceAssetKind.MCP_SAFETYBENCH_TASK,
        SourceAssetKind.MCPSECBENCH_STRUCTURED_RECORD,
    }
)
FIXTURE_KINDS = frozenset({SourceAssetKind.TERMINAL_BENCH_TASK_DIRECTORY})
TAXONOMY_KINDS = frozenset({SourceAssetKind.MCPSECBENCH_TAXONOMY})
PLUGIN_KINDS = frozenset(
    {
        SourceAssetKind.PLUGIN,
        SourceAssetKind.PLUGIN_COLLECTION,
        SourceAssetKind.PLUGIN_ALIAS,
    }
)
STRATEGY_KINDS = frozenset(
    {
        SourceAssetKind.STRATEGY,
        SourceAssetKind.STRATEGY_PRESET,
        SourceAssetKind.STRATEGY_COLLECTION,
        SourceAssetKind.STRATEGY_ALIAS,
        SourceAssetKind.DEPRECATED_STRATEGY_STUB,
    }
)
REFERENCE_KINDS = frozenset(
    {
        SourceAssetKind.SOURCE_CODE,
        SourceAssetKind.TEST_SOURCE,
        SourceAssetKind.CONFIGURATION,
        SourceAssetKind.LICENSE,
        SourceAssetKind.DOCUMENTATION,
    }
)
CONCRETE_ADAPTER_KINDS = frozenset(
    {
        SourceAssetKind.PLUGIN,
        SourceAssetKind.STRATEGY,
    }
)
NO_RUNTIME_OUTPUT_KINDS = frozenset(
    {
        SourceAssetKind.PLUGIN_COLLECTION,
        SourceAssetKind.PLUGIN_ALIAS,
        SourceAssetKind.STRATEGY_PRESET,
        SourceAssetKind.STRATEGY_COLLECTION,
        SourceAssetKind.STRATEGY_ALIAS,
        SourceAssetKind.DEPRECATED_STRATEGY_STUB,
        *REFERENCE_KINDS,
    }
)
