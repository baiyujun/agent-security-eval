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
    CodeIPIP0Importer,
    ConversionConfig,
    VerifiedSourceCheckout,
)


@dataclass(frozen=True)
class _SampleSpec:
    key: str
    vector: str
    category: str
    benign: bool


def record(spec: _SampleSpec) -> UpstreamLedgerRecord:
    return UpstreamLedgerRecord(
        source_project="inspect-evals-codeipi",
        source_repository="https://github.com/UKGovernmentBEIS/inspect_evals",
        source_commit="b" * 40,
        source_path="src/inspect_evals/ipi_coding_agent/dataset/samples.json",
        source_record_key=spec.key,
        source_record_digest="a" * 64,
        record_role=RecordRole.BENCHMARK_SCENARIO,
        source_asset_kind=SourceAssetKind.CODEIPI_SAMPLE,
        asset_family="codeipi",
        scenario_class="codeipi",
        category=spec.category,
        attack_present=not spec.benign,
        attack_origin=None,
        attack_delivery_mode=spec.vector,
        raw_reuse_disposition=RawReuseDisposition.REVIEW_REQUIRED,
        native_conversion_disposition=NativeConversionDisposition.ELIGIBLE_FOR_SEMANTIC_RECONSTRUCTION,
        conversion_reason="Project-authored CodeIPI semantic reconstruction candidate.",
    )


def rights(source_record: UpstreamLedgerRecord) -> RightsDecision:
    return RightsDecision(
        rights_decision_id=f"rights.{source_record.source_record_key}",
        source_project="inspect-evals-codeipi",
        source_record_key=source_record.source_record_key,
        reuse_mode=ReuseMode.REFERENCE_ONLY,
        raw_content_allowed=False,
        semantic_reconstruction_allowed=True,
        allowed_asset_roles=("scenario_template", "normal_task_fixture", "oracle_candidate"),
        prohibited_content_kinds=("task_text", "payload", "repo_fixture", "solution", "verifier"),
        license_status="review_required",
        rationale="CodeIPI sample and embedded repository rights require reconstruction.",
    )


def checkout() -> VerifiedSourceCheckout:
    return VerifiedSourceCheckout(
        source_project="inspect-evals-codeipi",
        repository="https://github.com/UKGovernmentBEIS/inspect_evals",
        commit="b" * 40,
        checkout_digest="c" * 64,
        clean=True,
        verified=True,
    )


def test_batch_import_maps_codeipi_channels_and_benign_control() -> None:
    records = tuple(
        record(spec)
        for spec in (
            _SampleSpec("ipi-issue-exfil-01-plain", "issue_text", "exfiltration", False),
            _SampleSpec("ipi-comment-exec-01-plain", "code_comment", "execution", False),
            _SampleSpec("ipi-readme-persist-01-authority", "readme", "persistence", False),
            _SampleSpec("ipi-config-exfil-01-plain", "config_file", "exfiltration", False),
            _SampleSpec("ipi-benign-01", "none", "none", True),
        )
    )
    result = CodeIPIP0Importer(expected_total=5).import_records(
        records=records,
        checkout=checkout(),
        rights_decisions={item.source_record_key: rights(item) for item in records},
        config=ConversionConfig(importer_version="1.0.0", deterministic_seed=7),
    )

    assert len(result.records) == 5
    assert all(item.review_state.status is ReviewStatus.PROPOSED for item in result.records)
    benign = next(item for item in result.records if item.source_record_key == "ipi-benign-01")
    assert benign.attack_present is False
    assert benign.native_output_id
    assert all(item.field_lineage and item.conversion_losses for item in result.records)
    by_key = {
        item.pack.cases[0].case_id.rsplit(".", 1)[-1]: item.pack.cases[0].attack.attack_present
        for item in result.imports
    }
    assert by_key["ipi-benign-01"] is False
    assert sum(value is True for value in by_key.values()) == 4
    expected_entry_points = {
        "ipi-issue-exfil-01-plain": "issue",
        "ipi-comment-exec-01-plain": "source_comment",
        "ipi-readme-persist-01-authority": "readme",
        "ipi-config-exfil-01-plain": "configuration",
    }
    for imported in result.imports:
        key = imported.pack.cases[0].case_id.rsplit(".", 1)[-1]
        if key in expected_entry_points:
            assert (
                imported.pack.attack_placements[0].entry_point.value == expected_entry_points[key]
            )
        assert all(
            lineage.source_path == "src/inspect_evals/ipi_coding_agent/dataset/samples.json"
            for lineage in imported.field_lineage
        )
        assert all(lineage.output_field != "native_component" for lineage in imported.field_lineage)
        assert all(lineage.project_authored_extension for lineage in imported.field_lineage)
        source_fields = {
            field for lineage in imported.field_lineage for field in lineage.source_fields
        }
        assert source_fields == {
            "id",
            "is_benign",
            "injection_vector",
            "payload_category",
        }
        assert all(
            loss.source_path == "src/inspect_evals/ipi_coding_agent/dataset/samples.json"
            for loss in imported.conversion_losses
        )


def test_batch_import_rejects_missing_codeipi_record() -> None:
    records = (
        record(_SampleSpec("ipi-issue-exfil-01-plain", "issue_text", "exfiltration", False)),
    )

    try:
        CodeIPIP0Importer(expected_total=2).import_records(
            records=records,
            checkout=checkout(),
            rights_decisions={records[0].source_record_key: rights(records[0])},
            config=ConversionConfig(importer_version="1.0.0", deterministic_seed=7),
        )
    except ValueError as exc:
        assert "expected 2" in str(exc)
    else:
        raise AssertionError("incomplete CodeIPI source set must fail closed")
