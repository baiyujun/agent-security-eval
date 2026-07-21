"""Pure compilation from native scenario cases to project execution inputs."""

from __future__ import annotations

import hashlib
import json

from pydantic import model_validator

from agentsec_eval.domain import (
    ExecutionBudget,
    ExecutionRunSpec,
    ExecutionScenarioSpec,
    TargetConfiguration,
)
from agentsec_eval.domain.models import AttackCandidate
from agentsec_eval.scenario_assets.models import (
    AssetId,
    FrozenModel,
    NativeScenarioPack,
    ScenarioCase,
)
from agentsec_eval.scenario_assets.validation import validate_pack_for_execution


class RunConfiguration(FrozenModel):
    run_id: AssetId
    target: TargetConfiguration
    budget: ExecutionBudget
    repetition_seed: int
    granted_capability_ids: tuple[AssetId, ...]

    @model_validator(mode="after")
    def validate_capabilities(self) -> RunConfiguration:
        if len(set(self.granted_capability_ids)) != len(self.granted_capability_ids):
            raise ValueError("granted_capability_ids must not contain duplicates")
        return self


class CompiledRunInput(FrozenModel):
    pack_id: AssetId
    case_id: AssetId
    case_version: str
    normal_task_id: AssetId
    attack_objective_id: AssetId | None
    concrete_attack_candidate_id: AssetId
    agent_visible_prompt: str
    execution_spec: ExecutionRunSpec
    source_provenance_ids: tuple[AssetId, ...]
    private_oracle_material_refs: tuple[AssetId, ...]
    output_digest: str | None


def compiled_input_digest(compiled: CompiledRunInput) -> str:
    content = compiled.model_dump(mode="json", exclude={"output_digest"})
    encoded = json.dumps(
        content,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _deterministic_canary(pack_id: str, case_id: str, seed: int) -> str:
    value = f"{pack_id}:{case_id}:{seed}".encode()
    return f"run-canary-{hashlib.sha256(value).hexdigest()[:24]}"


def compile_case(
    case: ScenarioCase,
    pack: NativeScenarioPack,
    config: RunConfiguration,
) -> CompiledRunInput:
    """Compile one reviewed native case without loading an upstream package."""

    validated_pack = validate_pack_for_execution(pack)
    validated_case = ScenarioCase.model_validate(case.model_dump(mode="python"))
    case_by_id = {candidate.case_id: candidate for candidate in validated_pack.cases}
    if case_by_id.get(validated_case.case_id) != validated_case:
        raise ValueError("case is not the exact reviewed case contained in the pack")

    required = set(validated_case.capability_requirements.required_capability_ids)
    granted = set(config.granted_capability_ids)
    missing = required - granted
    if missing:
        raise ValueError(f"required capability is not granted: {sorted(missing)}")
    forbidden = set(validated_case.capability_requirements.forbidden_capability_ids) & granted
    if forbidden:
        raise ValueError(f"forbidden capability is granted: {sorted(forbidden)}")

    normal_task = next(
        task
        for task in validated_pack.normal_tasks
        if task.task_id == validated_case.normal_task_id
    )
    private_oracles: list[str] = []
    suite = next(
        suite
        for suite in validated_pack.oracle_suites
        if suite.suite_id == validated_case.oracle_suite_id
    )
    for bundle in suite.bundles:
        private_oracles.extend(oracle.private_material_ref for oracle in bundle.oracles)

    candidate_id: str
    candidate_content: str
    attack_objective_id: str | None
    if validated_case.attack.attack_present:
        assert validated_case.attack.seed_id is not None
        assert validated_case.attack.variant_id is not None
        assert validated_case.attack.candidate_id is not None
        assert validated_case.attack.objective_id is not None
        variant = next(
            variant
            for variant in validated_pack.attack_variants
            if variant.variant_id == validated_case.attack.variant_id
        )
        placement = next(
            placement
            for placement in validated_pack.attack_placements
            if placement.placement_id == validated_case.attack.placement_id
        )
        candidate_id = variant.candidate_id
        candidate_content = variant.content if placement.agent_visible else ""
        attack_objective_id = validated_case.attack.objective_id
    else:
        candidate_id = f"{validated_case.case_id}.no-attack"
        candidate_content = ""
        attack_objective_id = None

    agent_prompt = normal_task.user_visible_prompt
    if candidate_content:
        agent_prompt = f"{agent_prompt}\n\n{candidate_content}"

    execution_spec = ExecutionRunSpec(
        run_id=config.run_id,
        target=config.target,
        scenario=ExecutionScenarioSpec(
            scenario_id=validated_case.base_scenario_id,
            user_task=normal_task.user_visible_prompt,
            canary=_deterministic_canary(
                validated_pack.pack_id,
                validated_case.case_id,
                config.repetition_seed,
            ),
        ),
        attack_candidate=AttackCandidate(candidate_id=candidate_id, content=candidate_content),
        budget=config.budget,
        repetition_seed=config.repetition_seed,
    )
    candidate = CompiledRunInput(
        pack_id=validated_pack.pack_id,
        case_id=validated_case.case_id,
        case_version=validated_case.case_version,
        normal_task_id=normal_task.task_id,
        attack_objective_id=attack_objective_id,
        concrete_attack_candidate_id=candidate_id,
        agent_visible_prompt=agent_prompt,
        execution_spec=execution_spec,
        source_provenance_ids=tuple(item.provenance_id for item in validated_pack.provenance),
        private_oracle_material_refs=tuple(private_oracles),
        output_digest=None,
    )
    return candidate.model_copy(update={"output_digest": compiled_input_digest(candidate)})


__all__ = [
    "CompiledRunInput",
    "RunConfiguration",
    "compile_case",
    "compiled_input_digest",
]
