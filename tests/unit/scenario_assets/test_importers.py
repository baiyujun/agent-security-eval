from __future__ import annotations

import pytest

from agentsec_eval.reference_catalog import (
    NativeConversionDisposition,
    RawReuseDisposition,
    RecordRole,
    SourceAssetKind,
    UpstreamLedgerRecord,
)
from agentsec_eval.scenario_assets import (
    ConversionConfig,
    ImporterRequest,
    ImportResult,
    NativeScenarioPack,
    ProjectAuthoredReconstruction,
    ReuseMode,
    RightsDecision,
    VerifiedSourceCheckout,
    build_import_result,
    with_computed_digest,
)

from .test_models import make_complete_pack

REPOSITORY = "https://github.com/sssr-lab/SABER"
COMMIT = "b" * 40
DIGEST = "a" * 64


def ledger_record() -> UpstreamLedgerRecord:
    return UpstreamLedgerRecord(
        source_project="saber",
        source_repository=REPOSITORY,
        source_commit=COMMIT,
        source_path="tasks/A/info_leak/A_info_001.json",
        source_record_key="A_info_001",
        source_record_digest=DIGEST,
        record_role=RecordRole.BENCHMARK_SCENARIO,
        source_asset_kind=SourceAssetKind.SABER_TASK,
        asset_family="coding_cli",
        scenario_class="A",
        category="info_leak",
        attack_present=True,
        attack_origin="indirect_content",
        attack_delivery_mode="indirect_context",
        raw_reuse_disposition=RawReuseDisposition.REVIEW_REQUIRED,
        native_conversion_disposition=(
            NativeConversionDisposition.ELIGIBLE_FOR_SEMANTIC_RECONSTRUCTION
        ),
        conversion_reason="Project-authored semantic reconstruction.",
    )


def rights_decision() -> RightsDecision:
    return RightsDecision(
        rights_decision_id="rights-1",
        source_project="saber",
        source_record_key="A_info_001",
        reuse_mode=ReuseMode.REFERENCE_ONLY,
        raw_content_allowed=False,
        semantic_reconstruction_allowed=True,
        allowed_asset_roles=("scenario_template", "oracle_candidate"),
        prohibited_content_kinds=("task_text", "payload", "solution"),
        license_status="review_required",
        rationale="Reconstruct semantics without copying restricted source content.",
    )


def request(
    *,
    pack: NativeScenarioPack | None = None,
    checkout: VerifiedSourceCheckout | None = None,
    rights: RightsDecision | None = None,
    source_fields: tuple[str, ...] = ("scenario", "structured_metadata", "task", "ground_truth"),
) -> ImporterRequest:
    selected_pack = with_computed_digest(make_complete_pack() if pack is None else pack)
    return ImporterRequest(
        checkout=checkout
        or VerifiedSourceCheckout(
            source_project="saber",
            repository=REPOSITORY,
            commit=COMMIT,
            checkout_digest="c" * 64,
            clean=True,
            verified=True,
        ),
        ledger_record=ledger_record(),
        rights_decision=rights or rights_decision(),
        reconstruction=ProjectAuthoredReconstruction(
            pack=selected_pack,
            source_field_inventory=source_fields,
        ),
        config=ConversionConfig(importer_version="1.0.0", deterministic_seed=7),
    )


def test_importer_contract_emits_pack_lineage_losses_digest_and_review_state() -> None:
    result = build_import_result(request())

    assert isinstance(result, ImportResult)
    assert result.pack.pack_id == "pack.saber-a"
    assert result.field_lineage == result.pack.field_lineage
    assert result.conversion_losses == result.pack.conversion_losses
    assert result.output_digest == result.pack.output_digest
    assert result.review_state == result.pack.review_state


@pytest.mark.parametrize(
    "field",
    ["source_project", "repository", "commit"],
)
def test_importer_rejects_checkout_and_ledger_identity_mismatch(field: str) -> None:
    values = request().checkout.model_dump()
    values[field] = "mismatch" if field != "commit" else "d" * 40

    with pytest.raises(ValueError, match="checkout.*ledger"):
        build_import_result(request(checkout=VerifiedSourceCheckout.model_validate(values)))


def test_importer_rejects_unverified_or_dirty_checkout() -> None:
    values = request().checkout.model_dump()
    values["verified"] = False

    with pytest.raises(ValueError, match="verified"):
        build_import_result(request(checkout=VerifiedSourceCheckout.model_validate(values)))


def test_importer_rejects_raw_reuse_without_semantic_reconstruction_approval() -> None:
    rights = rights_decision().model_copy(update={"semantic_reconstruction_allowed": False})

    with pytest.raises(ValueError, match="semantic reconstruction"):
        build_import_result(request(rights=rights))


def test_importer_rejects_silent_source_field_loss() -> None:
    with pytest.raises(ValueError, match="source field inventory"):
        build_import_result(request(source_fields=("scenario", "unmapped_field")))


def test_importer_rejects_pack_provenance_not_matching_ledger() -> None:
    pack = make_complete_pack()
    provenance = pack.provenance[0].model_copy(
        update={"source_path": "tasks/A/info_leak/different.json"}
    )
    broken = pack.model_copy(update={"provenance": (provenance,)})

    with pytest.raises(ValueError, match="provenance.*ledger"):
        build_import_result(request(pack=broken))


def test_importer_rejects_pack_rights_decision_that_differs_from_request() -> None:
    pack = make_complete_pack()
    changed_rights = pack.rights_decisions[0].model_copy(
        update={"rationale": "A materially different rights decision."}
    )
    broken = pack.model_copy(update={"rights_decisions": (changed_rights,)})

    with pytest.raises(ValueError, match="rights decision.*request"):
        build_import_result(request(pack=broken))


def test_importer_result_never_imports_upstream_runtime_objects() -> None:
    result = build_import_result(request())

    assert all(type(value).__module__.startswith("agentsec_eval") for value in result.pack.cases)
