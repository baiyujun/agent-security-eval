from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from agentsec_eval.domain import ExecutionBudget, TargetConfiguration
from agentsec_eval.scenario_assets import (
    CompiledRunInput,
    RunConfiguration,
    compile_case,
    compiled_input_digest,
    with_computed_digest,
)

from .test_models import make_complete_pack


def run_configuration(
    *, granted_capabilities: tuple[str, ...] = ("cap.filesystem-read",)
) -> RunConfiguration:
    return RunConfiguration(
        run_id="run.saber-a.001",
        target=TargetConfiguration(target_id="target.local", adapter="fixture", version="1.0"),
        budget=ExecutionBudget(max_turns=4, timeout_seconds=30),
        repetition_seed=7,
        granted_capability_ids=granted_capabilities,
    )


def test_compile_case_keeps_task_attack_and_private_oracles_separate() -> None:
    pack = with_computed_digest(make_complete_pack())

    compiled = compile_case(pack.cases[0], pack, run_configuration())

    assert isinstance(compiled, CompiledRunInput)
    assert compiled.execution_spec.scenario.user_task == pack.normal_tasks[0].user_visible_prompt
    assert compiled.execution_spec.attack_candidate.candidate_id == "candidate.synthetic"
    assert compiled.execution_spec.attack_candidate.content == ""
    assert pack.attack_variants[0].content not in compiled.agent_visible_prompt
    assert compiled.attack_objective_id == "objective.exfiltration"
    assert compiled.private_oracle_material_refs
    assert "private.security_effect" in compiled.private_oracle_material_refs
    assert all(
        private_ref not in compiled.agent_visible_prompt
        for private_ref in compiled.private_oracle_material_refs
    )
    assert all(
        private_ref not in compiled.execution_spec.model_dump_json()
        for private_ref in compiled.private_oracle_material_refs
    )


def test_compile_case_is_deterministic_and_round_trips_existing_runtime_contract() -> None:
    pack = with_computed_digest(make_complete_pack())
    config = run_configuration()

    first = compile_case(pack.cases[0], pack, config)
    second = compile_case(pack.cases[0], pack, config)

    assert first == second
    assert first.output_digest == second.output_digest == compiled_input_digest(first)
    assert first.execution_spec.run_id == config.run_id
    assert first.execution_spec.repetition_seed == config.repetition_seed
    assert set(first.source_provenance_ids) == {"prov-1"}


def test_compile_case_fails_closed_when_required_capability_is_missing() -> None:
    pack = with_computed_digest(make_complete_pack())

    with pytest.raises(ValueError, match="required capability"):
        compile_case(pack.cases[0], pack, run_configuration(granted_capabilities=()))


def test_compile_case_fails_closed_when_forbidden_capability_is_granted() -> None:
    pack = with_computed_digest(make_complete_pack())

    with pytest.raises(ValueError, match="forbidden capability"):
        compile_case(
            pack.cases[0],
            pack,
            run_configuration(granted_capabilities=("cap.filesystem-read", "cap.network")),
        )


def test_compile_case_revalidates_model_copy_bypass() -> None:
    pack = with_computed_digest(make_complete_pack())
    broken_attack = pack.cases[0].attack.model_copy(update={"candidate_id": None})
    broken_case = pack.cases[0].model_copy(update={"attack": broken_attack})

    with pytest.raises((ValidationError, ValueError), match="attack"):
        compile_case(broken_case, pack, run_configuration())


def test_compiler_seals_digest_without_placeholder_hashes() -> None:
    source = Path("src/agentsec_eval/scenario_assets/compiler.py").read_text(encoding="utf-8")
    pack = with_computed_digest(make_complete_pack())

    compiled = compile_case(pack.cases[0], pack, run_configuration())

    assert '"0" * 64' not in source
    assert compiled.output_digest == compiled_input_digest(compiled)
