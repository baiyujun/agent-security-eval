from __future__ import annotations

import sys

import pytest

from agentsec_eval.domain import ExecutionBudget, ExecutionRunSpec, TargetConfiguration
from agentsec_eval.execution.inspect_backend import (
    execution_run_spec_from_metadata,
    execution_run_spec_to_sample,
)
from agentsec_eval.reference_catalog import (
    NativeConversionDisposition,
    RawReuseDisposition,
    RecordRole,
    SourceAssetKind,
    UpstreamLedgerRecord,
)
from agentsec_eval.scenario_assets import (
    CodeIPIRepresentativeImporter,
    ConversionConfig,
    ReuseMode,
    RightsDecision,
    RunConfiguration,
    SaberRepresentativeImporter,
    VerifiedSourceCheckout,
    compile_case,
    make_representative_request,
    validate_pack,
)

COMMIT = "b" * 40
REPOSITORIES = {
    "saber": "https://github.com/sssr-lab/SABER",
    "inspect-evals-codeipi": "https://github.com/UKGovernmentBEIS/inspect_evals",
}


def record(
    *,
    project: str,
    key: str,
    path: str,
    scenario_class: str,
    category: str,
    attack_present: bool,
    attack_origin: str | None,
    delivery: str | None,
) -> UpstreamLedgerRecord:
    return UpstreamLedgerRecord(
        source_project=project,
        source_repository=REPOSITORIES[project],
        source_commit=COMMIT,
        source_path=path,
        source_record_key=key,
        source_record_digest="a" * 64,
        record_role=RecordRole.BENCHMARK_SCENARIO,
        source_asset_kind=(
            SourceAssetKind.SABER_TASK if project == "saber" else SourceAssetKind.CODEIPI_SAMPLE
        ),
        asset_family="coding_cli",
        scenario_class=scenario_class,
        category=category,
        attack_present=attack_present,
        attack_origin=attack_origin,
        attack_delivery_mode=delivery,
        raw_reuse_disposition=RawReuseDisposition.REVIEW_REQUIRED,
        native_conversion_disposition=(
            NativeConversionDisposition.ELIGIBLE_FOR_SEMANTIC_RECONSTRUCTION
        ),
        conversion_reason="Project-authored semantic reconstruction without raw reuse.",
    )


def checkout(project: str) -> VerifiedSourceCheckout:
    return VerifiedSourceCheckout(
        source_project=project,
        repository=REPOSITORIES[project],
        commit=COMMIT,
        checkout_digest="c" * 64,
        clean=True,
        verified=True,
    )


def rights(record: UpstreamLedgerRecord) -> RightsDecision:
    return RightsDecision(
        rights_decision_id=f"rights.{record.source_project}.{record.source_record_key}",
        source_project=record.source_project,
        source_record_key=record.source_record_key,
        reuse_mode=ReuseMode.REFERENCE_ONLY,
        raw_content_allowed=False,
        semantic_reconstruction_allowed=True,
        allowed_asset_roles=("scenario_template", "attack_seed", "oracle_candidate"),
        prohibited_content_kinds=("task_text", "payload", "fixture", "solution", "verifier"),
        license_status="review_required",
        rationale="Only project-authored semantic reconstruction is approved.",
    )


def representative_records() -> tuple[UpstreamLedgerRecord, ...]:
    return (
        record(
            project="saber",
            key="A_info_001",
            path="tasks/A/info_leak/A_info_001.json",
            scenario_class="A",
            category="info_leak",
            attack_present=True,
            attack_origin=None,
            delivery="tool_output",
        ),
        record(
            project="saber",
            key="B_info_001",
            path="tasks/B/info_leak/B_info_001.json",
            scenario_class="B",
            category="info_leak",
            attack_present=False,
            attack_origin=None,
            delivery=None,
        ),
        record(
            project="saber",
            key="C_info_001",
            path="tasks/C/info_leak/C_info_001.json",
            scenario_class="C",
            category="info_leak",
            attack_present=True,
            attack_origin="user",
            delivery="direct_user_request",
        ),
        record(
            project="inspect-evals-codeipi",
            key="ipi-issue-exfil-01-plain",
            path="src/inspect_evals/ipi_coding_agent/dataset/samples.json",
            scenario_class="codeipi",
            category="issue_exfiltration",
            attack_present=True,
            attack_origin=None,
            delivery="issue_text",
        ),
        record(
            project="inspect-evals-codeipi",
            key="ipi-benign-02-suspicious",
            path="src/inspect_evals/ipi_coding_agent/dataset/samples.json",
            scenario_class="codeipi",
            category="none",
            attack_present=False,
            attack_origin=None,
            delivery="none",
        ),
    )


@pytest.mark.parametrize(
    "source_record",
    representative_records(),
    ids=lambda item: item.source_record_key,
)
def test_representative_records_convert_end_to_end_without_upstream_packages(
    source_record: UpstreamLedgerRecord,
) -> None:
    request = make_representative_request(
        source_record,
        checkout=checkout(source_record.source_project),
        rights_decision=rights(source_record),
        config=ConversionConfig(importer_version="1.0.0", deterministic_seed=7),
    )
    importer = (
        SaberRepresentativeImporter()
        if source_record.source_project == "saber"
        else CodeIPIRepresentativeImporter()
    )

    result = importer.import_record(request)
    pack = validate_pack(result.pack)
    compiled = compile_case(
        pack.cases[0],
        pack,
        RunConfiguration(
            run_id=f"run.{pack.cases[0].case_id}",
            target=TargetConfiguration(
                target_id="target.fixture",
                adapter="fixture",
                version="1.0",
            ),
            budget=ExecutionBudget(max_turns=4, timeout_seconds=30),
            repetition_seed=7,
            granted_capability_ids=("cap.filesystem-read", "cap.filesystem-write"),
        ),
    )
    sample = execution_run_spec_to_sample(compiled.execution_spec)
    metadata = sample.metadata
    assert metadata is not None
    restored = execution_run_spec_from_metadata(metadata)

    assert result.output_digest == pack.output_digest
    expected_case_id = f"case.{source_record.source_project}.{source_record.source_record_key}"
    assert compiled.case_id == expected_case_id
    assert isinstance(restored, ExecutionRunSpec)
    assert restored == compiled.execution_spec
    assert "inspect_evals" not in sys.modules
    assert "saber" not in sys.modules


def test_representative_attack_semantics_are_not_guessed_from_text() -> None:
    records = {record.source_record_key: record for record in representative_records()}
    requests = [
        make_representative_request(
            source_record,
            checkout=checkout(source_record.source_project),
            rights_decision=rights(source_record),
            config=ConversionConfig(importer_version="1.0.0", deterministic_seed=7),
        )
        for source_record in representative_records()
    ]

    by_key = {
        request.ledger_record.source_record_key: request.reconstruction.pack.cases[0]
        for request in requests
    }
    assert by_key["A_info_001"].attack.attack_present is True
    assert by_key["B_info_001"].attack.attack_present is False
    assert by_key["B_info_001"].attack.objective_id is None
    assert by_key["C_info_001"].attack.attack_present is True
    assert by_key["C_info_001"].attack.objective_id is not None
    assert records["C_info_001"].attack_origin == "user"
    assert records["C_info_001"].attack_delivery_mode == "direct_user_request"
