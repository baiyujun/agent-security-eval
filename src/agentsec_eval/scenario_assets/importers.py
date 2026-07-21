"""Offline Benchmark Importer protocol and request/result validation."""

from __future__ import annotations

from typing import Protocol, Self, runtime_checkable

from pydantic import model_validator

from agentsec_eval.reference_catalog import UpstreamLedgerRecord
from agentsec_eval.scenario_assets.models import (
    AssetId,
    CommitSha,
    ConversionLoss,
    FieldLineage,
    FrozenModel,
    NativeScenarioPack,
    ReviewState,
    RightsDecision,
    SemanticVersion,
    Sha256Digest,
    SourceProvenance,
    StrictText,
)
from agentsec_eval.scenario_assets.validation import pack_content_digest, validate_pack


class VerifiedSourceCheckout(FrozenModel):
    source_project: AssetId
    repository: StrictText
    commit: CommitSha
    checkout_digest: Sha256Digest
    clean: bool
    verified: bool

    @model_validator(mode="after")
    def validate_checkout(self) -> Self:
        if not self.clean or not self.verified:
            raise ValueError("source checkout must be clean and verified")
        return self


class ConversionConfig(FrozenModel):
    importer_version: SemanticVersion
    deterministic_seed: int


class ProjectAuthoredReconstruction(FrozenModel):
    pack: NativeScenarioPack
    source_field_inventory: tuple[StrictText, ...]

    @model_validator(mode="after")
    def validate_inventory(self) -> Self:
        if not self.source_field_inventory:
            raise ValueError("source field inventory must not be empty")
        if len(set(self.source_field_inventory)) != len(self.source_field_inventory):
            raise ValueError("source field inventory must not contain duplicates")
        return self


class ImporterRequest(FrozenModel):
    checkout: VerifiedSourceCheckout
    ledger_record: UpstreamLedgerRecord
    rights_decision: RightsDecision
    reconstruction: ProjectAuthoredReconstruction
    config: ConversionConfig


class ImportResult(FrozenModel):
    pack: NativeScenarioPack
    field_lineage: tuple[FieldLineage, ...]
    conversion_losses: tuple[ConversionLoss, ...]
    output_digest: Sha256Digest
    review_state: ReviewState


@runtime_checkable
class OfflineBenchmarkImporter(Protocol):
    def import_record(self, request: ImporterRequest) -> ImportResult:
        """Convert one verified source record without entering a source runtime."""


def _source_tuple_matches(
    provenance: SourceProvenance,
    request: ImporterRequest,
) -> bool:
    return (
        provenance.source_project == request.ledger_record.source_project
        and provenance.repository == request.ledger_record.source_repository
        and provenance.commit == request.ledger_record.source_commit
        and provenance.source_path == request.ledger_record.source_path
        and provenance.source_record_key == request.ledger_record.source_record_key
        and provenance.source_record_digest == request.ledger_record.source_record_digest
        and provenance.rights_decision_id == request.rights_decision.rights_decision_id
    )


def build_import_result(request: ImporterRequest) -> ImportResult:
    """Validate an authored reconstruction and emit a complete immutable result."""

    validated_request = ImporterRequest.model_validate(request.model_dump(mode="python"))
    ledger = validated_request.ledger_record
    checkout = validated_request.checkout
    if (
        checkout.source_project != ledger.source_project
        or checkout.repository != ledger.source_repository
        or checkout.commit != ledger.source_commit
    ):
        raise ValueError("verified checkout identity does not match ledger")
    rights = validated_request.rights_decision
    if (
        rights.source_project != ledger.source_project
        or rights.source_record_key != ledger.source_record_key
    ):
        raise ValueError("rights decision identity does not match ledger")
    if not rights.semantic_reconstruction_allowed:
        raise ValueError("semantic reconstruction is not approved by the rights decision")

    pack = validate_pack(validated_request.reconstruction.pack)
    pack_rights = {decision.rights_decision_id: decision for decision in pack.rights_decisions}
    if pack_rights.get(rights.rights_decision_id) != rights:
        raise ValueError("pack rights decision does not match importer request")
    for provenance in pack.provenance:
        if not _source_tuple_matches(provenance, validated_request):
            raise ValueError("pack provenance does not match ledger")
        if (
            provenance.importer_version != validated_request.config.importer_version
            or provenance.deterministic_seed != validated_request.config.deterministic_seed
        ):
            raise ValueError("pack provenance does not match conversion configuration")

    lineage_fields = {
        source_field for lineage in pack.field_lineage for source_field in lineage.source_fields
    }
    loss_fields = {
        source_field for loss in pack.conversion_losses for source_field in loss.source_fields
    }
    accounted_fields = lineage_fields | loss_fields
    inventory = set(validated_request.reconstruction.source_field_inventory)
    if accounted_fields != inventory:
        missing = sorted(inventory - accounted_fields)
        unexpected = sorted(accounted_fields - inventory)
        raise ValueError(
            "source field inventory is not fully accounted for: "
            f"missing={missing}, unexpected={unexpected}"
        )

    output_digest = pack_content_digest(pack)
    if pack.output_digest != output_digest:
        raise ValueError("pack output digest is invalid")
    return ImportResult(
        pack=pack,
        field_lineage=pack.field_lineage,
        conversion_losses=pack.conversion_losses,
        output_digest=output_digest,
        review_state=pack.review_state,
    )


__all__ = [
    "ConversionConfig",
    "ImportResult",
    "ImporterRequest",
    "OfflineBenchmarkImporter",
    "ProjectAuthoredReconstruction",
    "VerifiedSourceCheckout",
    "build_import_result",
]
