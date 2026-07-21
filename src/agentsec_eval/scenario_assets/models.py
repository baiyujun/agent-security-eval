"""Immutable project-native scenario asset contracts."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints, model_validator

from agentsec_eval.scenario_assets.enums import (
    AttackDeliveryMode,
    CapabilityKind,
    CapabilityProvider,
    ConversionLossKind,
    EntryPoint,
    EnvironmentRole,
    FixtureRole,
    LineageTransformation,
    OracleExpectation,
    ProbeOracleCategory,
    ResetAction,
    ReuseMode,
    ReviewStatus,
    ScenarioDomain,
    ScenarioVariant,
    Visibility,
)


def _non_blank_untrimmed(value: str) -> str:
    if not value.strip():
        raise ValueError("text must not be blank")
    if value != value.strip():
        raise ValueError("text must not contain leading or trailing whitespace")
    return value


def _relative_posix(value: str) -> str:
    path = PurePosixPath(value)
    if (
        "\\" in value
        or "\x00" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or path.is_absolute()
        or re.match(r"^[A-Za-z]:/", value) is not None
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise ValueError("path must be a canonical relative POSIX path")
    return value


StrictText = Annotated[
    str,
    StringConstraints(strict=True, min_length=1),
    AfterValidator(_non_blank_untrimmed),
]
AssetId = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]
Sha256Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
CommitSha = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{40}$")]
SemanticVersion = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$"),
]
RelativePosixPath = Annotated[
    str,
    StringConstraints(strict=True, min_length=1),
    AfterValidator(_relative_posix),
]


def _require_unique(values: tuple[object, ...], field_name: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must not contain duplicates")


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ComponentEvidence(FrozenModel):
    component_id: AssetId
    provenance_ids: tuple[AssetId, ...]
    lineage_ids: tuple[AssetId, ...]
    rights_decision_ids: tuple[AssetId, ...]

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if not self.provenance_ids or not self.lineage_ids or not self.rights_decision_ids:
            raise ValueError("component evidence requires provenance, lineage, and rights IDs")
        _require_unique(self.provenance_ids, "provenance_ids")
        _require_unique(self.lineage_ids, "lineage_ids")
        _require_unique(self.rights_decision_ids, "rights_decision_ids")
        return self


class SourceProvenance(FrozenModel):
    provenance_id: AssetId
    source_project: AssetId
    repository: StrictText
    commit: CommitSha
    source_path: RelativePosixPath
    source_record_key: StrictText
    source_record_digest: Sha256Digest
    derivation: Literal[
        "project_authored_semantic_reconstruction",
        "approved_direct_import",
    ]
    importer_version: SemanticVersion
    deterministic_seed: int
    rights_decision_id: AssetId


class RightsDecision(FrozenModel):
    rights_decision_id: AssetId
    source_project: AssetId
    source_record_key: StrictText
    reuse_mode: ReuseMode
    raw_content_allowed: bool
    semantic_reconstruction_allowed: bool
    allowed_asset_roles: tuple[AssetId, ...]
    prohibited_content_kinds: tuple[AssetId, ...]
    license_status: StrictText
    rationale: StrictText

    @model_validator(mode="after")
    def validate_rights(self) -> Self:
        if self.reuse_mode is ReuseMode.ASSET_IMPORT and not self.raw_content_allowed:
            raise ValueError("asset_import requires raw_content_allowed")
        if self.raw_content_allowed and self.reuse_mode is ReuseMode.REFERENCE_ONLY:
            raise ValueError("reference_only cannot allow raw content")
        if not self.allowed_asset_roles:
            raise ValueError("rights decision requires at least one allowed asset role")
        _require_unique(self.allowed_asset_roles, "allowed_asset_roles")
        _require_unique(self.prohibited_content_kinds, "prohibited_content_kinds")
        return self


class FieldLineage(FrozenModel):
    lineage_id: AssetId
    output_component_id: AssetId
    output_field: StrictText
    source_fields: tuple[StrictText, ...]
    transformation: LineageTransformation
    provenance_ids: tuple[AssetId, ...]
    notes: StrictText

    @model_validator(mode="after")
    def validate_lineage(self) -> Self:
        if not self.source_fields or not self.provenance_ids:
            raise ValueError("field lineage requires source fields and provenance")
        _require_unique(self.source_fields, "source_fields")
        _require_unique(self.provenance_ids, "provenance_ids")
        return self


class ConversionLoss(FrozenModel):
    loss_id: AssetId
    source_fields: tuple[StrictText, ...]
    kind: ConversionLossKind
    handling: StrictText
    rationale: StrictText
    provenance_ids: tuple[AssetId, ...]
    rights_decision_id: AssetId

    @model_validator(mode="after")
    def validate_loss(self) -> Self:
        if not self.source_fields or not self.provenance_ids:
            raise ValueError("conversion loss requires source fields and provenance")
        _require_unique(self.source_fields, "source_fields")
        _require_unique(self.provenance_ids, "provenance_ids")
        return self


class ReviewState(FrozenModel):
    status: ReviewStatus
    reviewer: StrictText | None = None
    decision_ref: AssetId | None = None
    notes: StrictText

    @model_validator(mode="after")
    def validate_review(self) -> Self:
        if self.status in {ReviewStatus.APPROVED, ReviewStatus.REJECTED} and (
            self.reviewer is None or self.decision_ref is None
        ):
            raise ValueError("final review state requires reviewer and decision_ref")
        return self


class ScenarioFamily(FrozenModel):
    family_id: AssetId
    name: StrictText
    domain: ScenarioDomain
    description: StrictText
    evidence: ComponentEvidence


class BaseScenario(FrozenModel):
    scenario_id: AssetId
    family_id: AssetId
    title: StrictText
    legitimate_goal: StrictText
    threat_model: StrictText
    attacker_controlled_channels: tuple[EntryPoint, ...]
    authorization_context_id: AssetId
    environment_role_requirements: tuple[EnvironmentRole, ...]
    required_probe_categories: tuple[ProbeOracleCategory, ...]
    reset_required: bool
    evidence: ComponentEvidence

    @model_validator(mode="after")
    def validate_base(self) -> Self:
        if not self.environment_role_requirements or not self.required_probe_categories:
            raise ValueError("base scenario requires environment roles and probe categories")
        _require_unique(self.attacker_controlled_channels, "attacker_controlled_channels")
        _require_unique(self.environment_role_requirements, "environment_role_requirements")
        _require_unique(self.required_probe_categories, "required_probe_categories")
        return self


class NormalTask(FrozenModel):
    task_id: AssetId
    title: StrictText
    benchmark_prompt: StrictText
    user_visible_prompt: StrictText
    expected_outcome: StrictText
    required_read_refs: tuple[AssetId, ...]
    allowed_output_refs: tuple[AssetId, ...]
    evidence: ComponentEvidence

    @model_validator(mode="after")
    def validate_task(self) -> Self:
        if not self.required_read_refs or not self.allowed_output_refs:
            raise ValueError("normal task requires declared reads and outputs")
        _require_unique(self.required_read_refs, "required_read_refs")
        _require_unique(self.allowed_output_refs, "allowed_output_refs")
        return self


class AttackObjective(FrozenModel):
    objective_id: AssetId
    effect: AssetId
    description: StrictText
    protected_asset_refs: tuple[AssetId, ...]
    prohibited_effect_refs: tuple[AssetId, ...]
    evidence: ComponentEvidence

    @model_validator(mode="after")
    def validate_objective(self) -> Self:
        if not self.protected_asset_refs or not self.prohibited_effect_refs:
            raise ValueError("attack objective requires protected assets and prohibited effects")
        _require_unique(self.protected_asset_refs, "protected_asset_refs")
        _require_unique(self.prohibited_effect_refs, "prohibited_effect_refs")
        return self


class AttackSeed(FrozenModel):
    seed_id: AssetId
    candidate_id: AssetId
    objective_id: AssetId
    content: StrictText
    content_digest: Sha256Digest
    evidence: ComponentEvidence


class AttackPlacement(FrozenModel):
    placement_id: AssetId
    entry_point: EntryPoint
    delivery_mode: AttackDeliveryMode
    insertion_target: AssetId
    agent_visible: bool
    evidence: ComponentEvidence


class AttackConfiguration(FrozenModel):
    attack_present: bool
    objective_id: AssetId | None = None
    seed_id: AssetId | None = None
    candidate_id: AssetId | None = None
    placement_id: AssetId | None = None

    @model_validator(mode="after")
    def validate_attack_state(self) -> Self:
        references = (self.objective_id, self.seed_id, self.candidate_id, self.placement_id)
        if self.attack_present and any(value is None for value in references):
            raise ValueError("attacked case requires complete attack references")
        if not self.attack_present and any(value is not None for value in references):
            raise ValueError("attack-free case must not carry attack references")
        return self


class FixtureDefinition(FrozenModel):
    fixture_id: AssetId
    role: FixtureRole
    visibility: Visibility
    relative_path: RelativePosixPath
    content_digest: Sha256Digest
    project_authored: bool
    evidence: ComponentEvidence


class CapabilityDeclaration(FrozenModel):
    capability_id: AssetId
    provider: CapabilityProvider
    kind: CapabilityKind
    operations: tuple[AssetId, ...]
    local_only: bool
    evidence: ComponentEvidence

    @model_validator(mode="after")
    def validate_operations(self) -> Self:
        if not self.operations:
            raise ValueError("capability requires at least one operation")
        _require_unique(self.operations, "operations")
        return self


class EnvironmentDefinition(FrozenModel):
    environment_id: AssetId
    roles: tuple[EnvironmentRole, ...]
    fixture_ids: tuple[AssetId, ...]
    capability_ids: tuple[AssetId, ...]
    network_mode: Literal["none", "local_only"]
    evidence: ComponentEvidence

    @model_validator(mode="after")
    def validate_environment(self) -> Self:
        if not self.roles or not self.fixture_ids or not self.capability_ids:
            raise ValueError("environment requires roles, fixtures, and capabilities")
        _require_unique(self.roles, "roles")
        _require_unique(self.fixture_ids, "fixture_ids")
        _require_unique(self.capability_ids, "capability_ids")
        return self


class CapabilityRequirements(FrozenModel):
    required_capability_ids: tuple[AssetId, ...]
    forbidden_capability_ids: tuple[AssetId, ...]

    @model_validator(mode="after")
    def validate_requirements(self) -> Self:
        _require_unique(self.required_capability_ids, "required_capability_ids")
        _require_unique(self.forbidden_capability_ids, "forbidden_capability_ids")
        if set(self.required_capability_ids) & set(self.forbidden_capability_ids):
            raise ValueError("required and forbidden capabilities must be disjoint")
        return self


class AuthorizationContext(FrozenModel):
    authorization_context_id: AssetId
    protected_asset_refs: tuple[AssetId, ...]
    allowed_read_refs: tuple[AssetId, ...]
    forbidden_read_refs: tuple[AssetId, ...]
    allowed_output_refs: tuple[AssetId, ...]
    forbidden_sink_refs: tuple[AssetId, ...]
    declassification_rules: tuple[AssetId, ...]
    allowed_capability_ids: tuple[AssetId, ...]
    evidence: ComponentEvidence

    @model_validator(mode="after")
    def validate_authorization(self) -> Self:
        for field_name in (
            "protected_asset_refs",
            "allowed_read_refs",
            "forbidden_read_refs",
            "allowed_output_refs",
            "forbidden_sink_refs",
            "declassification_rules",
            "allowed_capability_ids",
        ):
            values = getattr(self, field_name)
            if not values:
                raise ValueError(f"{field_name} must not be empty")
            _require_unique(values, field_name)
        if set(self.allowed_read_refs) & set(self.forbidden_read_refs):
            raise ValueError("allowed and forbidden reads must be disjoint")
        return self


class ProbeDefinition(FrozenModel):
    probe_id: AssetId
    category: ProbeOracleCategory
    description: StrictText
    observation_key: AssetId
    visibility: Visibility
    evidence: ComponentEvidence


class OracleDefinition(FrozenModel):
    oracle_id: AssetId
    category: ProbeOracleCategory
    probe_ids: tuple[AssetId, ...]
    description: StrictText
    expectation: OracleExpectation
    expected_value: StrictText
    private_material_ref: AssetId
    authoritative: bool
    evidence: ComponentEvidence

    @model_validator(mode="after")
    def validate_oracle(self) -> Self:
        if not self.probe_ids:
            raise ValueError("oracle requires at least one probe")
        _require_unique(self.probe_ids, "probe_ids")
        return self


class ProbeOracleBundle(FrozenModel):
    bundle_id: AssetId
    category: ProbeOracleCategory
    probes: tuple[ProbeDefinition, ...]
    oracles: tuple[OracleDefinition, ...]
    evidence: ComponentEvidence

    @model_validator(mode="after")
    def validate_bundle(self) -> Self:
        if not self.probes or not self.oracles:
            raise ValueError("probe/oracle bundle requires probes and oracles")
        if any(probe.category is not self.category for probe in self.probes) or any(
            oracle.category is not self.category for oracle in self.oracles
        ):
            raise ValueError("bundle members must match the bundle category")
        probe_ids = {probe.probe_id for probe in self.probes}
        if len(probe_ids) != len(self.probes):
            raise ValueError("bundle probe IDs must be unique")
        oracle_ids = {oracle.oracle_id for oracle in self.oracles}
        if len(oracle_ids) != len(self.oracles):
            raise ValueError("bundle oracle IDs must be unique")
        if any(not set(oracle.probe_ids) <= probe_ids for oracle in self.oracles):
            raise ValueError("oracle probe references must resolve within the bundle")
        return self


class OracleSuite(FrozenModel):
    suite_id: AssetId
    bundles: tuple[ProbeOracleBundle, ...]
    evidence: ComponentEvidence

    @model_validator(mode="after")
    def validate_suite(self) -> Self:
        categories = tuple(bundle.category for bundle in self.bundles)
        if len(categories) != len(set(categories)) or set(categories) != set(ProbeOracleCategory):
            raise ValueError("oracle suite must contain every probe/oracle category exactly once")
        return self


class ResetStep(FrozenModel):
    step_id: AssetId
    action: ResetAction
    resource_id: AssetId


class ResetContract(FrozenModel):
    reset_contract_id: AssetId
    mutable_resource_ids: tuple[AssetId, ...]
    steps: tuple[ResetStep, ...]
    baseline_digest: Sha256Digest
    verification_probe_ids: tuple[AssetId, ...]
    evidence: ComponentEvidence

    @model_validator(mode="after")
    def validate_reset(self) -> Self:
        if not self.mutable_resource_ids or not self.steps or not self.verification_probe_ids:
            raise ValueError("reset contract requires resources, steps, and verification probes")
        _require_unique(self.mutable_resource_ids, "mutable_resource_ids")
        _require_unique(tuple(step.step_id for step in self.steps), "reset step IDs")
        _require_unique(self.verification_probe_ids, "verification_probe_ids")
        if any(step.resource_id not in self.mutable_resource_ids for step in self.steps):
            raise ValueError("reset steps must target declared mutable resources")
        return self


class ScenarioCase(FrozenModel):
    case_id: AssetId
    case_version: SemanticVersion
    base_scenario_id: AssetId
    variant: ScenarioVariant
    normal_task_id: AssetId
    attack: AttackConfiguration
    environment_id: AssetId
    fixture_ids: tuple[AssetId, ...]
    authorization_context_id: AssetId
    capability_requirements: CapabilityRequirements
    oracle_suite_id: AssetId
    reset_contract_id: AssetId
    evidence: ComponentEvidence
    review_state: ReviewState

    @model_validator(mode="after")
    def validate_case_state(self) -> Self:
        if not self.fixture_ids:
            raise ValueError("scenario case requires at least one agent-visible fixture")
        _require_unique(self.fixture_ids, "fixture_ids")
        if self.attack.attack_present != (self.variant is ScenarioVariant.ATTACKED):
            raise ValueError("case variant and attack presence must agree")
        return self


class NativeScenarioPack(FrozenModel):
    schema_version: SemanticVersion
    pack_id: AssetId
    pack_version: SemanticVersion
    family: ScenarioFamily
    base_scenarios: tuple[BaseScenario, ...]
    cases: tuple[ScenarioCase, ...]
    normal_tasks: tuple[NormalTask, ...]
    attack_objectives: tuple[AttackObjective, ...]
    attack_seeds: tuple[AttackSeed, ...]
    attack_placements: tuple[AttackPlacement, ...]
    environments: tuple[EnvironmentDefinition, ...]
    fixtures: tuple[FixtureDefinition, ...]
    capabilities: tuple[CapabilityDeclaration, ...]
    authorization_contexts: tuple[AuthorizationContext, ...]
    oracle_suites: tuple[OracleSuite, ...]
    reset_contracts: tuple[ResetContract, ...]
    provenance: tuple[SourceProvenance, ...]
    rights_decisions: tuple[RightsDecision, ...]
    field_lineage: tuple[FieldLineage, ...]
    conversion_losses: tuple[ConversionLoss, ...]
    review_state: ReviewState
    output_digest: Sha256Digest

    @model_validator(mode="after")
    def validate_required_collections(self) -> Self:
        required = (
            self.base_scenarios,
            self.cases,
            self.normal_tasks,
            self.environments,
            self.fixtures,
            self.capabilities,
            self.authorization_contexts,
            self.oracle_suites,
            self.reset_contracts,
            self.provenance,
            self.rights_decisions,
            self.field_lineage,
        )
        if any(not collection for collection in required):
            raise ValueError("native scenario pack is missing a required component collection")
        return self
