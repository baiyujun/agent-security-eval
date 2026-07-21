"""Offline Benchmark Importer protocol and request/result validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Annotated, Protocol, Self, runtime_checkable

from pydantic import AfterValidator, PlainSerializer, model_validator

from agentsec_eval.reference_catalog import (
    RecordRole,
    SourceAssetKind,
    UpstreamLedgerRecord,
    validate_records,
)
from agentsec_eval.scenario_assets.enums import (
    ReuseMode,
    ReviewStatus,
    SaberConversionDisposition,
)
from agentsec_eval.scenario_assets.models import (
    AssetId,
    CommitSha,
    ConversionLoss,
    FieldLineage,
    FrozenModel,
    NativeScenarioPack,
    RelativePosixPath,
    ReviewState,
    RightsDecision,
    SemanticVersion,
    Sha256Digest,
    SourceProvenance,
    StrictText,
)
from agentsec_eval.scenario_assets.validation import pack_content_digest, validate_pack


def _freeze_counts(value: Mapping[str, int]) -> Mapping[str, int]:
    return MappingProxyType(dict(value))


def _serialize_counts(value: Mapping[str, int]) -> dict[str, int]:
    return dict(value)


ScenarioCounts = Annotated[
    Mapping[str, int],
    AfterValidator(_freeze_counts),
    PlainSerializer(_serialize_counts, return_type=dict[str, int]),
]


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


class SaberConversionRecord(FrozenModel):
    """One complete, reviewable SABER conversion disposition."""

    source_project: AssetId
    source_repository: StrictText
    source_commit: CommitSha
    source_path: RelativePosixPath
    source_record_key: StrictText
    source_record_digest: Sha256Digest
    record_role: RecordRole
    source_asset_kind: SourceAssetKind
    scenario_class: StrictText
    category: StrictText
    attack_present: bool | None
    attack_origin: StrictText | None
    attack_delivery_mode: StrictText | None
    source_provenance: SourceProvenance
    asset_roles: tuple[StrictText, ...]
    reuse_mode: ReuseMode
    rights_decision: RightsDecision
    field_lineage: tuple[FieldLineage, ...]
    conversion_losses: tuple[ConversionLoss, ...]
    native_output_id: AssetId | None
    review_state: ReviewState
    disposition: SaberConversionDisposition
    output_digest: Sha256Digest

    @model_validator(mode="after")
    def validate_disposition(self) -> Self:
        provenance = self.source_provenance
        expected_kind = {
            "saber": SourceAssetKind.SABER_TASK,
            "inspect-evals-codeipi": SourceAssetKind.CODEIPI_SAMPLE,
            "terminal-bench-2": SourceAssetKind.TERMINAL_BENCH_TASK_DIRECTORY,
        }.get(self.source_project)
        expected_role = (
            RecordRole.NORMAL_TASK_FIXTURE
            if self.source_project == "terminal-bench-2"
            else RecordRole.BENCHMARK_SCENARIO
        )
        if (
            expected_kind is None
            or self.record_role is not expected_role
            or self.source_asset_kind is not expected_kind
        ):
            raise ValueError("SABER conversion records require SABER task source records")
        if (
            provenance.source_project != self.source_project
            or provenance.repository != self.source_repository
            or provenance.commit != self.source_commit
            or provenance.source_path != self.source_path
            or provenance.source_record_key != self.source_record_key
            or provenance.source_record_digest != self.source_record_digest
        ):
            raise ValueError("SABER conversion provenance does not match source record")
        if (
            self.rights_decision.source_project != self.source_project
            or self.rights_decision.source_record_key != self.source_record_key
        ):
            raise ValueError("SABER rights decision does not match source record")
        if not self.asset_roles:
            raise ValueError("SABER conversion requires asset roles")
        if self.disposition is SaberConversionDisposition.CONVERTED_CANDIDATE:
            if self.native_output_id is None or (
                self.review_state.status is not ReviewStatus.PROPOSED
            ):
                raise ValueError("converted candidate requires a proposed native output")
        if self.disposition is SaberConversionDisposition.NORMAL_TASK_ASSET:
            if (
                self.native_output_id is None
                or self.review_state.status is not ReviewStatus.PROPOSED
            ):
                raise ValueError("normal task asset requires a proposed native output")
        return self


class SaberBatchImportResult(FrozenModel):
    """Atomic result for a complete SABER source set."""

    records: tuple[SaberConversionRecord, ...]
    imports: tuple[ImportResult, ...]
    scenario_counts: ScenarioCounts

    @model_validator(mode="after")
    def validate_batch(self) -> Self:
        if len(self.records) != len(self.imports):
            raise ValueError("SABER conversion records and imports must be aligned")
        if len(self.records) != sum(self.scenario_counts.values()):
            raise ValueError("SABER scenario counts must sum to the record count")
        keys = tuple(record.source_record_key for record in self.records)
        if len(keys) != len(set(keys)):
            raise ValueError("SABER conversion record keys must be unique")
        return self


@runtime_checkable
class OfflineBenchmarkImporter(Protocol):
    def import_record(self, request: ImporterRequest) -> ImportResult:
        """Convert one verified source record without entering a source runtime."""


class SaberOfflineImporter:
    """Convert one arbitrary SABER record through the project-owned importer contract."""

    def import_record(self, request: ImporterRequest) -> ImportResult:
        if request.ledger_record.source_project != "saber":
            raise ValueError("SABER importer requires source_project='saber'")
        return build_import_result(request)


class CodeIPIOfflineImporter:
    """Convert one arbitrary CodeIPI record through the project-owned contract."""

    def import_record(self, request: ImporterRequest) -> ImportResult:
        if request.ledger_record.source_project != "inspect-evals-codeipi":
            raise ValueError("CodeIPI importer requires the Inspect Evals source project")
        return build_import_result(request)


class TerminalBenchOfflineImporter:
    """Convert one Terminal-Bench task directory without running its contents."""

    def import_record(self, request: ImporterRequest) -> ImportResult:
        if request.ledger_record.source_project != "terminal-bench-2":
            raise ValueError("Terminal-Bench importer requires the locked source project")
        return build_import_result(request)


class SaberP0Importer:
    """Convert and account for the complete locked SABER P0 source set."""

    def __init__(
        self,
        *,
        expected_total: int = 716,
        expected_scenario_counts: Mapping[str, int] | None = None,
    ) -> None:
        self.expected_total = expected_total
        self.expected_scenario_counts = dict(
            expected_scenario_counts or {"A": 289, "B": 186, "C": 241}
        )

    def import_records(
        self,
        *,
        records: Sequence[UpstreamLedgerRecord],
        checkout: VerifiedSourceCheckout,
        rights_decisions: Mapping[str, RightsDecision],
        config: ConversionConfig,
    ) -> SaberBatchImportResult:
        validated_records = validate_records(records, require_initial_outputs=True)
        if len(validated_records) != self.expected_total:
            raise ValueError(
                f"expected {self.expected_total} SABER records, got {len(validated_records)}"
            )
        if set(rights_decisions) != {record.source_record_key for record in validated_records}:
            raise ValueError("SABER rights decisions must cover exactly the source record set")
        scenario_counts = {
            scenario: sum(record.scenario_class == scenario for record in validated_records)
            for scenario in ("A", "B", "C")
        }
        if scenario_counts != self.expected_scenario_counts:
            raise ValueError(
                f"SABER scenario counts disagree: expected={self.expected_scenario_counts}, "
                f"actual={scenario_counts}"
            )
        if checkout.source_project != "saber":
            raise ValueError("SABER checkout marker has the wrong source project")
        importer = SaberOfflineImporter()
        ordered_records = tuple(
            sorted(
                validated_records,
                key=lambda item: (
                    item.source_path,
                    item.source_record_key,
                ),
            )
        )
        imports: list[ImportResult] = []
        dispositions: list[SaberConversionRecord] = []
        for source_record in ordered_records:
            rights = rights_decisions[source_record.source_record_key]
            request = self._request(
                source_record,
                checkout=checkout,
                rights=rights,
                config=config,
            )
            imported = importer.import_record(request)
            imports.append(imported)
            provenance = imported.pack.provenance[0]
            asset_roles = ["scenario_template", "normal_task_fixture", "oracle_candidate"]
            if source_record.attack_present:
                asset_roles.append("attack_seed")
            dispositions.append(
                SaberConversionRecord(
                    source_project=source_record.source_project,
                    source_repository=source_record.source_repository,
                    source_commit=source_record.source_commit,
                    source_path=source_record.source_path,
                    source_record_key=source_record.source_record_key,
                    source_record_digest=source_record.source_record_digest,
                    record_role=source_record.record_role,
                    source_asset_kind=source_record.source_asset_kind,
                    scenario_class=source_record.scenario_class,
                    category=source_record.category,
                    attack_present=source_record.attack_present,
                    attack_origin=source_record.attack_origin,
                    attack_delivery_mode=source_record.attack_delivery_mode,
                    source_provenance=provenance,
                    asset_roles=tuple(asset_roles),
                    reuse_mode=rights.reuse_mode,
                    rights_decision=rights,
                    field_lineage=imported.field_lineage,
                    conversion_losses=imported.conversion_losses,
                    native_output_id=imported.pack.pack_id,
                    review_state=imported.review_state,
                    disposition=SaberConversionDisposition.CONVERTED_CANDIDATE,
                    output_digest=imported.output_digest,
                )
            )
        return SaberBatchImportResult(
            records=tuple(dispositions),
            imports=tuple(imports),
            scenario_counts=scenario_counts,
        )

    @staticmethod
    def _request(
        source_record: UpstreamLedgerRecord,
        *,
        checkout: VerifiedSourceCheckout,
        rights: RightsDecision,
        config: ConversionConfig,
    ) -> ImporterRequest:
        from agentsec_eval.scenario_assets.representatives import make_representative_request

        return make_representative_request(
            source_record,
            checkout=checkout,
            rights_decision=rights,
            config=config,
        )


class CodeIPIP0Importer(SaberP0Importer):
    """Convert and account for the complete locked CodeIPI P0 source set."""

    def __init__(self, *, expected_total: int = 45) -> None:
        super().__init__(
            expected_total=expected_total,
            expected_scenario_counts={"codeipi": expected_total},
        )

    def import_records(
        self,
        *,
        records: Sequence[UpstreamLedgerRecord],
        checkout: VerifiedSourceCheckout,
        rights_decisions: Mapping[str, RightsDecision],
        config: ConversionConfig,
    ) -> SaberBatchImportResult:
        validated_records = validate_records(records, require_initial_outputs=True)
        if len(validated_records) != self.expected_total:
            raise ValueError(
                f"expected {self.expected_total} CodeIPI records, got {len(validated_records)}"
            )
        if set(rights_decisions) != {record.source_record_key for record in validated_records}:
            raise ValueError("CodeIPI rights decisions must cover exactly the source record set")
        if any(
            record.source_project != "inspect-evals-codeipi"
            or record.source_asset_kind is not SourceAssetKind.CODEIPI_SAMPLE
            or record.record_role is not RecordRole.BENCHMARK_SCENARIO
            for record in validated_records
        ):
            raise ValueError("CodeIPI batch contains a record from another source family")
        scenario_counts = {"codeipi": len(validated_records)}
        if checkout.source_project != "inspect-evals-codeipi":
            raise ValueError("CodeIPI checkout marker has the wrong source project")
        importer = CodeIPIOfflineImporter()
        ordered_records = tuple(
            sorted(
                validated_records,
                key=lambda item: (item.source_path, item.source_record_key),
            )
        )
        imports: list[ImportResult] = []
        dispositions: list[SaberConversionRecord] = []
        for source_record in ordered_records:
            rights = rights_decisions[source_record.source_record_key]
            imported = importer.import_record(
                self._request(
                    source_record,
                    checkout=checkout,
                    rights=rights,
                    config=config,
                )
            )
            imports.append(imported)
            asset_roles = ["scenario_template", "normal_task_fixture", "oracle_candidate"]
            if source_record.attack_present:
                asset_roles.append("attack_seed")
            dispositions.append(
                SaberConversionRecord(
                    source_project=source_record.source_project,
                    source_repository=source_record.source_repository,
                    source_commit=source_record.source_commit,
                    source_path=source_record.source_path,
                    source_record_key=source_record.source_record_key,
                    source_record_digest=source_record.source_record_digest,
                    record_role=source_record.record_role,
                    source_asset_kind=source_record.source_asset_kind,
                    scenario_class=source_record.scenario_class,
                    category=source_record.category,
                    attack_present=source_record.attack_present,
                    attack_origin=source_record.attack_origin,
                    attack_delivery_mode=source_record.attack_delivery_mode,
                    source_provenance=imported.pack.provenance[0],
                    asset_roles=tuple(asset_roles),
                    reuse_mode=rights.reuse_mode,
                    rights_decision=rights,
                    field_lineage=imported.field_lineage,
                    conversion_losses=imported.conversion_losses,
                    native_output_id=imported.pack.pack_id,
                    review_state=imported.review_state,
                    disposition=SaberConversionDisposition.CONVERTED_CANDIDATE,
                    output_digest=imported.output_digest,
                )
            )
        return SaberBatchImportResult(
            records=tuple(dispositions),
            imports=tuple(imports),
            scenario_counts=scenario_counts,
        )


class TerminalBenchP0Importer(SaberP0Importer):
    """Convert and account for the complete locked Terminal-Bench P0 task set."""

    def __init__(self, *, expected_total: int = 89) -> None:
        super().__init__(
            expected_total=expected_total,
            expected_scenario_counts={"normal_task": expected_total},
        )

    def import_records(
        self,
        *,
        records: Sequence[UpstreamLedgerRecord],
        checkout: VerifiedSourceCheckout,
        rights_decisions: Mapping[str, RightsDecision],
        config: ConversionConfig,
    ) -> SaberBatchImportResult:
        validated_records = validate_records(records, require_initial_outputs=True)
        if len(validated_records) != self.expected_total:
            raise ValueError(
                f"expected {self.expected_total} Terminal-Bench records, "
                f"got {len(validated_records)}"
            )
        if set(rights_decisions) != {record.source_record_key for record in validated_records}:
            raise ValueError(
                "Terminal-Bench rights decisions must cover exactly the source record set"
            )
        if any(
            record.source_project != "terminal-bench-2"
            or record.source_asset_kind is not SourceAssetKind.TERMINAL_BENCH_TASK_DIRECTORY
            or record.record_role is not RecordRole.NORMAL_TASK_FIXTURE
            for record in validated_records
        ):
            raise ValueError("Terminal-Bench batch contains a record from another source family")
        if checkout.source_project != "terminal-bench-2":
            raise ValueError("Terminal-Bench checkout marker has the wrong source project")
        importer = TerminalBenchOfflineImporter()
        ordered_records = tuple(
            sorted(validated_records, key=lambda item: (item.source_path, item.source_record_key))
        )
        imports: list[ImportResult] = []
        dispositions: list[SaberConversionRecord] = []
        for source_record in ordered_records:
            rights = rights_decisions[source_record.source_record_key]
            imported = importer.import_record(
                self._request(
                    source_record,
                    checkout=checkout,
                    rights=rights,
                    config=config,
                )
            )
            imports.append(imported)
            dispositions.append(
                SaberConversionRecord(
                    source_project=source_record.source_project,
                    source_repository=source_record.source_repository,
                    source_commit=source_record.source_commit,
                    source_path=source_record.source_path,
                    source_record_key=source_record.source_record_key,
                    source_record_digest=source_record.source_record_digest,
                    record_role=source_record.record_role,
                    source_asset_kind=source_record.source_asset_kind,
                    scenario_class=source_record.scenario_class,
                    category=source_record.category,
                    attack_present=False,
                    attack_origin=None,
                    attack_delivery_mode=None,
                    source_provenance=imported.pack.provenance[0],
                    asset_roles=("normal_task_fixture", "environment_fixture", "oracle_candidate"),
                    reuse_mode=rights.reuse_mode,
                    rights_decision=rights,
                    field_lineage=imported.field_lineage,
                    conversion_losses=imported.conversion_losses,
                    native_output_id=imported.pack.pack_id,
                    review_state=imported.review_state,
                    disposition=SaberConversionDisposition.NORMAL_TASK_ASSET,
                    output_digest=imported.output_digest,
                )
            )
        return SaberBatchImportResult(
            records=tuple(dispositions),
            imports=tuple(imports),
            scenario_counts={"normal_task": len(ordered_records)},
        )


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
    "SaberBatchImportResult",
    "SaberConversionRecord",
    "SaberOfflineImporter",
    "SaberP0Importer",
    "CodeIPIOfflineImporter",
    "CodeIPIP0Importer",
    "TerminalBenchOfflineImporter",
    "TerminalBenchP0Importer",
    "CodeIPIBatchImportResult",
    "CodeIPIConversionRecord",
    "VerifiedSourceCheckout",
    "build_import_result",
]


CodeIPIConversionRecord = SaberConversionRecord
CodeIPIBatchImportResult = SaberBatchImportResult
