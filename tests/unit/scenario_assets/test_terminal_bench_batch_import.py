from __future__ import annotations

from dataclasses import dataclass

from agentsec_eval.reference_catalog import (
    NativeConversionDisposition,
    RawReuseDisposition,
    RecordRole,
    SourceAssetKind,
    UpstreamLedgerRecord,
)
from agentsec_eval.scenario_assets import ReuseMode, ReviewStatus, RightsDecision
from agentsec_eval.scenario_assets.importers import (
    ConversionConfig,
    TerminalBenchP0Importer,
    VerifiedSourceCheckout,
)


@dataclass(frozen=True)
class _TaskSpec:
    key: str


def record(spec: _TaskSpec) -> UpstreamLedgerRecord:
    return UpstreamLedgerRecord(
        source_project="terminal-bench-2",
        source_repository="https://github.com/harbor-framework/terminal-bench-2",
        source_commit="c" * 40,
        source_path=spec.key,
        source_record_key=spec.key,
        source_record_digest="a" * 64,
        record_role=RecordRole.NORMAL_TASK_FIXTURE,
        source_asset_kind=SourceAssetKind.TERMINAL_BENCH_TASK_DIRECTORY,
        asset_family="terminal_bench_2",
        scenario_class="normal_task",
        category="normal_task",
        attack_present=False,
        attack_origin=None,
        attack_delivery_mode=None,
        raw_reuse_disposition=RawReuseDisposition.REVIEW_REQUIRED,
        native_conversion_disposition=NativeConversionDisposition.ELIGIBLE_FOR_SEMANTIC_RECONSTRUCTION,
        conversion_reason="Project-authored normal task and environment reconstruction candidate.",
    )


def rights(source_record: UpstreamLedgerRecord) -> RightsDecision:
    return RightsDecision(
        rights_decision_id=f"rights.{source_record.source_record_key}",
        source_project="terminal-bench-2",
        source_record_key=source_record.source_record_key,
        reuse_mode=ReuseMode.REFERENCE_ONLY,
        raw_content_allowed=False,
        semantic_reconstruction_allowed=True,
        allowed_asset_roles=("normal_task_fixture", "environment_fixture", "oracle_candidate"),
        prohibited_content_kinds=("instruction", "environment", "solution", "verifier", "docker"),
        license_status="review_required",
        rationale="Terminal-Bench task and environment rights require reconstruction.",
    )


def checkout() -> VerifiedSourceCheckout:
    return VerifiedSourceCheckout(
        source_project="terminal-bench-2",
        repository="https://github.com/harbor-framework/terminal-bench-2",
        commit="c" * 40,
        checkout_digest="d" * 64,
        clean=True,
        verified=True,
    )


def test_batch_import_emits_normal_task_environment_candidates() -> None:
    records = tuple(record(_TaskSpec(key)) for key in ("regex-log", "sqlite-with-gcov"))
    result = TerminalBenchP0Importer(expected_total=2).import_records(
        records=records,
        checkout=checkout(),
        rights_decisions={item.source_record_key: rights(item) for item in records},
        config=ConversionConfig(importer_version="1.0.0", deterministic_seed=7),
    )

    assert len(result.records) == 2
    assert all(item.review_state.status is ReviewStatus.PROPOSED for item in result.records)
    assert all(item.disposition.value == "normal_task_asset" for item in result.records)
    assert all(item.attack_present is False for item in result.records)
    assert all("normal_task_fixture" in item.asset_roles for item in result.records)
    assert all("environment_fixture" in item.asset_roles for item in result.records)
    assert all("attack_seed" not in item.asset_roles for item in result.records)
    assert all(item.pack.cases[0].attack.attack_present is False for item in result.imports)
    assert all(item.pack.normal_tasks and item.pack.environments for item in result.imports)


def test_batch_import_rejects_incomplete_terminal_bench_set() -> None:
    records = (record(_TaskSpec("regex-log")),)
    try:
        TerminalBenchP0Importer(expected_total=2).import_records(
            records=records,
            checkout=checkout(),
            rights_decisions={records[0].source_record_key: rights(records[0])},
            config=ConversionConfig(importer_version="1.0.0", deterministic_seed=7),
        )
    except ValueError as exc:
        assert "expected 2" in str(exc)
    else:
        raise AssertionError("incomplete Terminal-Bench source set must fail closed")
