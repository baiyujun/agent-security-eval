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
    SaberP0Importer,
    VerifiedSourceCheckout,
)


@dataclass(frozen=True)
class _RecordSpec:
    scenario: str
    category: str
    key: str
    delivery: str | None
    attack_present: bool
    attack_origin: str | None


def record(spec: _RecordSpec) -> UpstreamLedgerRecord:
    return UpstreamLedgerRecord(
        source_project="saber",
        source_repository="https://github.com/sssr-lab/SABER",
        source_commit="b" * 40,
        source_path=f"tasks/{spec.scenario}/{spec.category}/{spec.key}.json",
        source_record_key=spec.key,
        source_record_digest="a" * 64,
        record_role=RecordRole.BENCHMARK_SCENARIO,
        source_asset_kind=SourceAssetKind.SABER_TASK,
        asset_family="saber",
        scenario_class=spec.scenario,
        category=spec.category,
        attack_present=spec.attack_present,
        attack_origin=spec.attack_origin,
        attack_delivery_mode=spec.delivery,
        raw_reuse_disposition=RawReuseDisposition.REVIEW_REQUIRED,
        native_conversion_disposition=NativeConversionDisposition.ELIGIBLE_FOR_SEMANTIC_RECONSTRUCTION,
        conversion_reason="Project-authored semantic reconstruction candidate.",
    )


def rights(source_record: UpstreamLedgerRecord) -> RightsDecision:
    return RightsDecision(
        rights_decision_id=f"rights.{source_record.source_record_key}",
        source_project="saber",
        source_record_key=source_record.source_record_key,
        reuse_mode=ReuseMode.REFERENCE_ONLY,
        raw_content_allowed=False,
        semantic_reconstruction_allowed=True,
        allowed_asset_roles=("scenario_template", "normal_task_fixture", "oracle_candidate"),
        prohibited_content_kinds=("task_text", "payload", "fixture", "solution", "verifier"),
        license_status="review_required",
        rationale="SABER task/data license conflict requires semantic reconstruction only.",
    )


def checkout() -> VerifiedSourceCheckout:
    return VerifiedSourceCheckout(
        source_project="saber",
        repository="https://github.com/sssr-lab/SABER",
        commit="b" * 40,
        checkout_digest="c" * 64,
        clean=True,
        verified=True,
    )


def test_batch_import_emits_complete_candidate_records_for_all_scenarios() -> None:
    records = (
        record(_RecordSpec("A", "info_leak", "A_info_001", "tool_output", True, None)),
        record(_RecordSpec("B", "info_leak", "B_info_001", None, False, None)),
        record(_RecordSpec("C", "info_leak", "C_info_001", "direct_user_request", True, "user")),
    )
    importer = SaberP0Importer(
        expected_total=3,
        expected_scenario_counts={"A": 1, "B": 1, "C": 1},
    )
    result = importer.import_records(
        records=records,
        checkout=checkout(),
        rights_decisions={item.source_record_key: rights(item) for item in records},
        config=ConversionConfig(importer_version="1.0.0", deterministic_seed=7),
    )

    assert len(result.records) == 3
    assert [item.source_record_key for item in result.records] == [
        "A_info_001",
        "B_info_001",
        "C_info_001",
    ]
    assert all(item.disposition.value == "converted_candidate" for item in result.records)
    assert all(item.review_state.status is ReviewStatus.PROPOSED for item in result.records)
    assert all(item.native_output_id for item in result.records)
    assert all(item.field_lineage and item.conversion_losses for item in result.records)
    assert all(item.record_role is RecordRole.BENCHMARK_SCENARIO for item in result.records)
    assert all(item.source_asset_kind is SourceAssetKind.SABER_TASK for item in result.records)
    for imported in result.imports:
        assert all(lineage.output_field != "native_component" for lineage in imported.field_lineage)
        assert all(lineage.source_path.startswith("tasks/") for lineage in imported.field_lineage)
        assert {field for lineage in imported.field_lineage for field in lineage.source_fields} == {
            "id",
            "scenario",
            "category",
            "injection.enabled",
            "injection.method",
        }
    assert result.scenario_counts == {"A": 1, "B": 1, "C": 1}
    try:
        result.scenario_counts["A"] = 2  # type: ignore[index]
    except TypeError:
        pass
    else:
        raise AssertionError("scenario counts must be deeply immutable")
    assert result.model_dump(mode="json")["scenario_counts"] == {"A": 1, "B": 1, "C": 1}


def test_batch_import_rejects_incomplete_source_set_without_partial_result() -> None:
    records = (
        record(_RecordSpec("A", "info_leak", "A_info_001", "tool_output", True, None)),
        record(_RecordSpec("B", "info_leak", "B_info_001", None, False, None)),
    )

    try:
        importer = SaberP0Importer(
            expected_total=3,
            expected_scenario_counts={"A": 1, "B": 1, "C": 1},
        )
        importer.import_records(
            records=records,
            checkout=checkout(),
            rights_decisions={item.source_record_key: rights(item) for item in records},
            config=ConversionConfig(importer_version="1.0.0", deterministic_seed=7),
        )
    except ValueError as exc:
        assert "expected 3" in str(exc)
    else:
        raise AssertionError("incomplete SABER source set must fail closed")


def test_batch_import_preserves_structured_saber_attack_placements() -> None:
    methods = (
        ("tool_output", "tool_result"),
        ("file_content", "file_content"),
        ("config_inject", "configuration"),
        ("error_message", "error_message"),
        ("multi_step", "delayed_context"),
    )
    records = tuple(
        record(
            _RecordSpec(
                "A",
                "info_leak",
                f"A_info_{index:03d}",
                method,
                True,
                None,
            )
        )
        for index, (method, _entry_point) in enumerate(methods, start=1)
    )
    result = SaberP0Importer(
        expected_total=len(records),
        expected_scenario_counts={"A": len(records), "B": 0, "C": 0},
    ).import_records(
        records=records,
        checkout=checkout(),
        rights_decisions={item.source_record_key: rights(item) for item in records},
        config=ConversionConfig(importer_version="1.0.0", deterministic_seed=7),
    )

    placements = [item.pack.cases[0].attack.placement_id for item in result.imports]
    entry_points = [
        next(
            placement.entry_point.value
            for placement in item.pack.attack_placements
            if placement.placement_id == placement_id
        )
        for item, placement_id in zip(result.imports, placements, strict=True)
    ]
    assert entry_points == [expected for _method, expected in methods]


def test_batch_import_is_deterministic_for_same_records_and_configuration() -> None:
    records = (
        record(_RecordSpec("A", "info_leak", "A_info_001", "tool_output", True, None)),
        record(_RecordSpec("B", "info_leak", "B_info_001", None, False, None)),
        record(_RecordSpec("C", "info_leak", "C_info_001", "direct_user_request", True, "user")),
    )
    rights_decisions = {item.source_record_key: rights(item) for item in records}
    source_checkout = checkout()
    config = ConversionConfig(importer_version="1.0.0", deterministic_seed=7)
    importer = SaberP0Importer(
        expected_total=3,
        expected_scenario_counts={"A": 1, "B": 1, "C": 1},
    )

    first = importer.import_records(
        records=records,
        checkout=source_checkout,
        rights_decisions=rights_decisions,
        config=config,
    )
    second = importer.import_records(
        records=records,
        checkout=source_checkout,
        rights_decisions=rights_decisions,
        config=config,
    )

    assert first.model_dump_json() == second.model_dump_json()
