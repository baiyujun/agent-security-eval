from __future__ import annotations

import ast
from pathlib import Path

import agentsec_eval.scenario_assets as scenario_assets
from agentsec_eval.execution import execution_run_spec_from_metadata, execution_run_spec_to_sample
from agentsec_eval.scenario_assets import RunConfiguration, compile_case, with_computed_digest

from .test_compiler import run_configuration
from .test_models import make_complete_pack


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_scenario_assets_public_api_excludes_contract_execution_harness() -> None:
    assert "execute_compiled_case" not in scenario_assets.__all__
    assert "NativeExecutionResult" not in scenario_assets.__all__
    assert not hasattr(scenario_assets, "execute_compiled_case")
    assert not hasattr(scenario_assets, "NativeExecutionResult")


def test_contract_harness_cannot_synthesize_formal_security_truth() -> None:
    runtime_source = Path("src/agentsec_eval/scenario_assets/runtime.py").read_text(
        encoding="utf-8"
    )

    assert "CONTRACT_TEST_ONLY = True" in runtime_source
    assert "attack_delivered" not in runtime_source
    assert "forbidden_effect_absent" not in runtime_source
    assert "NativeExecutionResult" not in runtime_source
    assert "RunOutcome" not in runtime_source
    assert "passed:" not in runtime_source


def test_production_execution_modules_do_not_import_offline_or_upstream_runtimes() -> None:
    roots = (
        Path("src/agentsec_eval/domain"),
        Path("src/agentsec_eval/execution"),
        Path("src/agentsec_eval/targets"),
    )
    prohibited_prefixes = (
        "agentsec_eval.reference_catalog.discovery",
        "agentsec_eval.scenario_assets.importers",
        "agentsec_eval.scenario_assets.representatives",
        "inspect_evals",
        "saber",
        "terminal_bench",
    )

    for root in roots:
        for path in root.glob("*.py"):
            for imported in imported_modules(path):
                assert not imported.startswith(prohibited_prefixes), (path, imported)


def test_compiled_case_enters_production_through_one_inspect_sample() -> None:
    pack = with_computed_digest(make_complete_pack())
    config: RunConfiguration = run_configuration()

    compiled = compile_case(pack.cases[0], pack, config)
    sample = execution_run_spec_to_sample(compiled.execution_spec)

    assert sample.id == compiled.execution_spec.run_id
    assert sample.metadata is not None
    assert execution_run_spec_from_metadata(sample.metadata) == compiled.execution_spec
