"""Static validation and deterministic identity for native scenario packs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import TypeVar

from agentsec_eval.scenario_assets.enums import ProbeOracleCategory, ReviewStatus, Visibility
from agentsec_eval.scenario_assets.models import (
    ComponentEvidence,
    ExecutableScenarioPack,
    FieldLineage,
    NativeScenarioPack,
    RightsDecision,
    SourceProvenance,
)

_T = TypeVar("_T")


def _index(items: Iterable[_T], attribute: str, label: str) -> dict[str, _T]:
    indexed: dict[str, _T] = {}
    for item in items:
        identity = str(getattr(item, attribute))
        if identity in indexed:
            raise ValueError(f"duplicate {attribute}: {identity}")
        indexed[identity] = item
    return indexed


def pack_content_digest(pack: NativeScenarioPack) -> str:
    """Hash the canonical JSON representation, excluding the digest field itself."""

    content = pack.model_dump(mode="json", exclude={"output_digest"})
    encoded = json.dumps(
        content,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def with_computed_digest(pack: NativeScenarioPack) -> NativeScenarioPack:
    """Return a fully revalidated pack carrying its canonical output digest."""

    revalidated = NativeScenarioPack.model_validate(pack.model_dump(mode="python"))
    candidate = revalidated.model_copy(update={"output_digest": pack_content_digest(revalidated)})
    return validate_pack(candidate)


def _require_ref(reference: str, index: Mapping[str, object], label: str) -> None:
    if reference not in index:
        raise ValueError(f"unresolved {label} reference: {reference}")


def _validate_evidence(
    component_id: str,
    evidence: ComponentEvidence,
    provenance: Mapping[str, SourceProvenance],
    lineage: Mapping[str, FieldLineage],
    rights: Mapping[str, RightsDecision],
) -> None:
    if evidence.component_id != component_id:
        raise ValueError(f"component evidence identity does not match: {component_id}")
    for reference in evidence.provenance_ids:
        _require_ref(reference, provenance, "provenance")
    for reference in evidence.lineage_ids:
        _require_ref(reference, lineage, "lineage")
        if lineage[reference].output_component_id != component_id:
            raise ValueError(f"component lineage does not match: {component_id}")
    for reference in evidence.rights_decision_ids:
        _require_ref(reference, rights, "rights decision")


def _component_evidence(pack: NativeScenarioPack) -> Iterable[tuple[str, ComponentEvidence]]:
    yield pack.family.family_id, pack.family.evidence
    for base in pack.base_scenarios:
        yield base.scenario_id, base.evidence
    for case in pack.cases:
        yield case.case_id, case.evidence
    for task in pack.normal_tasks:
        yield task.task_id, task.evidence
    for objective in pack.attack_objectives:
        yield objective.objective_id, objective.evidence
    for seed in pack.attack_seeds:
        yield seed.seed_id, seed.evidence
    for variant in pack.attack_variants:
        yield variant.variant_id, variant.evidence
    for placement in pack.attack_placements:
        yield placement.placement_id, placement.evidence
    for environment in pack.environments:
        yield environment.environment_id, environment.evidence
    for fixture in pack.fixtures:
        yield fixture.fixture_id, fixture.evidence
    for capability in pack.capabilities:
        yield capability.capability_id, capability.evidence
    for authorization in pack.authorization_contexts:
        yield authorization.authorization_context_id, authorization.evidence
    for suite in pack.oracle_suites:
        yield suite.suite_id, suite.evidence
    for reset in pack.reset_contracts:
        yield reset.reset_contract_id, reset.evidence
    for docker in pack.docker_environments:
        yield docker.docker_environment_id, docker.evidence
    for service in pack.tool_services:
        yield service.tool_service_id, service.evidence
    for pack_test in pack.pack_tests:
        yield pack_test.pack_test_id, pack_test.evidence
    for suite in pack.oracle_suites:
        for bundle in suite.bundles:
            yield bundle.bundle_id, bundle.evidence
            for probe in bundle.probes:
                yield probe.probe_id, probe.evidence
            for oracle in bundle.oracles:
                yield oracle.oracle_id, oracle.evidence


def validate_pack(pack: NativeScenarioPack) -> NativeScenarioPack:
    """Revalidate a complete pack and all cross-component invariants."""

    validated = NativeScenarioPack.model_validate(pack.model_dump(mode="python"))
    if validated.output_digest is None or validated.output_digest != pack_content_digest(validated):
        raise ValueError("output_digest does not match canonical pack content")

    bases = _index(validated.base_scenarios, "scenario_id", "base scenario")
    cases = _index(validated.cases, "case_id", "scenario case")
    normal_tasks = _index(validated.normal_tasks, "task_id", "normal task")
    objectives = _index(validated.attack_objectives, "objective_id", "attack objective")
    seeds = _index(validated.attack_seeds, "seed_id", "attack seed")
    attack_variants = _index(validated.attack_variants, "variant_id", "attack variant")
    placements = _index(validated.attack_placements, "placement_id", "attack placement")
    environments = _index(validated.environments, "environment_id", "environment")
    fixtures = _index(validated.fixtures, "fixture_id", "fixture")
    capabilities = _index(validated.capabilities, "capability_id", "capability")
    authorizations = _index(
        validated.authorization_contexts,
        "authorization_context_id",
        "authorization context",
    )
    suites = _index(validated.oracle_suites, "suite_id", "oracle suite")
    resets = _index(validated.reset_contracts, "reset_contract_id", "reset contract")
    docker_environments = _index(
        validated.docker_environments,
        "docker_environment_id",
        "docker environment",
    )
    tool_services = _index(validated.tool_services, "tool_service_id", "tool/service")
    pack_tests = _index(validated.pack_tests, "pack_test_id", "pack test")
    provenance = _index(validated.provenance, "provenance_id", "provenance")
    rights = _index(validated.rights_decisions, "rights_decision_id", "rights decision")
    lineage = _index(validated.field_lineage, "lineage_id", "field lineage")
    _index(validated.conversion_losses, "loss_id", "conversion loss")

    component_ids: set[str] = {
        validated.family.family_id,
        *bases,
        *cases,
        *normal_tasks,
        *objectives,
        *seeds,
        *attack_variants,
        *placements,
        *environments,
        *fixtures,
        *capabilities,
        *authorizations,
        *suites,
        *resets,
        *docker_environments,
        *tool_services,
        *pack_tests,
        *(bundle.bundle_id for suite in validated.oracle_suites for bundle in suite.bundles),
        *(
            probe.probe_id
            for suite in validated.oracle_suites
            for bundle in suite.bundles
            for probe in bundle.probes
        ),
        *(
            oracle.oracle_id
            for suite in validated.oracle_suites
            for bundle in suite.bundles
            for oracle in bundle.oracles
        ),
    }
    for lineage_item in validated.field_lineage:
        if lineage_item.output_component_id not in component_ids:
            raise ValueError(
                "field lineage output component does not resolve: "
                f"{lineage_item.output_component_id}"
            )
        for reference in lineage_item.provenance_ids:
            _require_ref(reference, provenance, "lineage provenance")

    for provenance_item in validated.provenance:
        _require_ref(
            provenance_item.rights_decision_id,
            rights,
            "provenance rights decision",
        )
        decision = rights[provenance_item.rights_decision_id]
        if (
            decision.source_project != provenance_item.source_project
            or decision.source_record_key != provenance_item.source_record_key
        ):
            raise ValueError("provenance and rights decision source identity must agree")

    for loss in validated.conversion_losses:
        _require_ref(loss.rights_decision_id, rights, "conversion-loss rights decision")
        for reference in loss.provenance_ids:
            _require_ref(reference, provenance, "conversion-loss provenance")

    for component_id, evidence in _component_evidence(validated):
        _validate_evidence(component_id, evidence, provenance, lineage, rights)

    for base in validated.base_scenarios:
        if base.family_id != validated.family.family_id:
            raise ValueError(f"unresolved family reference: {base.family_id}")
        _require_ref(base.authorization_context_id, authorizations, "authorization")
        profile = base.tool_and_permission_profile
        for capability_id in (
            *profile.required_capability_ids,
            *profile.forbidden_capability_ids,
            *profile.approval_required_capability_ids,
        ):
            _require_ref(capability_id, capabilities, "profile capability")
        if set(base.required_probe_categories) != set(ProbeOracleCategory):
            raise ValueError("base scenario must require all probe/oracle categories")

    for environment in validated.environments:
        for fixture_id in environment.fixture_ids:
            _require_ref(fixture_id, fixtures, "environment fixture")
        for capability_id in environment.capability_ids:
            _require_ref(capability_id, capabilities, "environment capability")

    for docker in validated.docker_environments:
        _require_ref(docker.environment_id, environments, "docker environment target")

    for service in validated.tool_services:
        for capability_id in service.capability_ids:
            _require_ref(capability_id, capabilities, "tool/service capability")

    for pack_test in validated.pack_tests:
        for component_id in pack_test.verifies_component_ids:
            if component_id not in component_ids:
                raise ValueError(f"pack test component does not resolve: {component_id}")

    for case in validated.cases:
        _require_ref(case.base_scenario_id, bases, "base scenario")
        _require_ref(case.normal_task_id, normal_tasks, "normal task")
        _require_ref(case.environment_id, environments, "environment")
        _require_ref(case.authorization_context_id, authorizations, "authorization")
        _require_ref(case.oracle_suite_id, suites, "oracle suite")
        _require_ref(case.reset_contract_id, resets, "reset contract")
        base = bases[case.base_scenario_id]
        environment = environments[case.environment_id]
        authorization = authorizations[case.authorization_context_id]
        normal_task = normal_tasks[case.normal_task_id]
        if case.variant not in base.case_schema.allowed_variants:
            raise ValueError("case variant is not allowed by its base case schema")
        if case.authorization_context_id != base.authorization_context_id:
            raise ValueError("case authorization must match its base scenario")
        if not set(base.environment_role_requirements) <= set(environment.roles):
            raise ValueError("environment does not satisfy base scenario role requirements")
        for fixture_id in case.fixture_ids:
            _require_ref(fixture_id, fixtures, "case fixture")
            if fixture_id not in environment.fixture_ids:
                raise ValueError("case fixture is not present in its environment")
            if fixtures[fixture_id].visibility is not Visibility.AGENT_VISIBLE:
                raise ValueError("private fixture must not enter agent-visible case inputs")
        case_fixture_roles = {fixtures[fixture_id].role for fixture_id in case.fixture_ids}
        if not set(base.case_schema.required_fixture_roles) <= case_fixture_roles:
            raise ValueError("case does not satisfy required fixture roles")
        environment_fixture_roles = {
            fixtures[fixture_id].role for fixture_id in environment.fixture_ids
        }
        if not set(base.world.fixture_role_requirements) <= environment_fixture_roles:
            raise ValueError("environment does not satisfy world fixture role requirements")
        required_capabilities = set(case.capability_requirements.required_capability_ids)
        for capability_id in required_capabilities:
            _require_ref(capability_id, capabilities, "required capability")
        if not required_capabilities <= set(environment.capability_ids):
            raise ValueError("environment does not provide a required capability")
        if not required_capabilities <= set(authorization.allowed_capability_ids):
            raise ValueError("required capability is not authorized")
        profile = base.tool_and_permission_profile
        if not set(profile.required_capability_ids) <= required_capabilities:
            raise ValueError("case does not satisfy base profile capability requirements")
        if not set(profile.forbidden_capability_ids) <= set(
            case.capability_requirements.forbidden_capability_ids
        ):
            raise ValueError("case does not preserve base profile forbidden capabilities")
        if not set(base.normal_task_spec.required_read_refs) <= set(normal_task.required_read_refs):
            raise ValueError("normal task does not satisfy base read requirements")
        if not set(base.normal_task_spec.allowed_output_refs) <= set(
            normal_task.allowed_output_refs
        ):
            raise ValueError("normal task does not satisfy base output requirements")
        if not set(normal_task.required_read_refs) <= set(authorization.allowed_read_refs):
            raise ValueError("normal-task reads are not authorized")
        if not set(normal_task.allowed_output_refs) <= set(authorization.allowed_output_refs):
            raise ValueError("normal-task outputs are not authorized")
        suite = suites[case.oracle_suite_id]
        if set(base.required_probe_categories) != {bundle.category for bundle in suite.bundles}:
            raise ValueError("oracle suite does not satisfy base scenario probe requirements")
        reset_probe_ids = {
            probe.probe_id
            for bundle in suite.bundles
            if bundle.category is ProbeOracleCategory.RESET
            for probe in bundle.probes
        }
        reset = resets[case.reset_contract_id]
        if not set(reset.verification_probe_ids) <= reset_probe_ids:
            raise ValueError("reset verification probes do not resolve in the reset bundle")

        if case.attack.attack_present:
            objective_id = str(case.attack.objective_id)
            seed_id = str(case.attack.seed_id)
            variant_id = str(case.attack.variant_id)
            placement_id = str(case.attack.placement_id)
            _require_ref(objective_id, objectives, "attack objective")
            _require_ref(seed_id, seeds, "attack seed")
            _require_ref(variant_id, attack_variants, "attack variant")
            _require_ref(placement_id, placements, "attack placement")
            seed = seeds[seed_id]
            variant = attack_variants[variant_id]
            placement = placements[placement_id]
            if seed.objective_id != objective_id or seed.candidate_id != case.attack.candidate_id:
                raise ValueError("attack seed does not match the case objective/candidate")
            if variant.seed_id != seed_id or variant.candidate_id != case.attack.candidate_id:
                raise ValueError("attack variant does not match the case seed/candidate")
            if placement.entry_point not in base.attacker_controlled_channels:
                raise ValueError("attack placement is not an approved attacker-controlled channel")

    return validated


def validate_pack_for_execution(pack: ExecutableScenarioPack) -> ExecutableScenarioPack:
    """Require independent approval after structural pack validation."""

    validated = validate_pack(pack)
    if validated.review_state.status is not ReviewStatus.APPROVED:
        raise ValueError("executable scenario pack requires an approved review decision")
    if any(case.review_state.status is not ReviewStatus.APPROVED for case in validated.cases):
        raise ValueError("every executable scenario case requires an approved review decision")
    return validated


__all__ = [
    "pack_content_digest",
    "validate_pack",
    "validate_pack_for_execution",
    "with_computed_digest",
]
