from __future__ import annotations

import json
from pathlib import Path

import agentsec_eval.execution as execution
import agentsec_eval.scenario_assets as scenario_assets
from agentsec_eval.scenario_assets import (
    AttackDeliveryMode,
    EntryPoint,
    Visibility,
    compile_case,
    load_executable_pack,
    serialize_executable_pack,
    with_computed_digest,
)

from .test_compiler import run_configuration
from .test_models import content_digest, make_complete_pack
from .test_storage import pack_contents


def loaded_pack(tmp_path: Path) -> scenario_assets.LoadedExecutableScenarioPack:
    pack = with_computed_digest(make_complete_pack())
    destination = tmp_path / "pack"
    serialize_executable_pack(pack, destination, pack_contents())
    return load_executable_pack(destination)


def loaded_pack_for_entry_point(
    tmp_path: Path, entry_point: EntryPoint
) -> scenario_assets.LoadedExecutableScenarioPack:
    base_pack = make_complete_pack()
    contents = pack_contents()
    fixtures = list(base_pack.fixtures)
    attack_fixture_index = next(
        index for index, fixture in enumerate(fixtures) if fixture.fixture_id == "fixture.issue"
    )
    attack_fixture = fixtures[attack_fixture_index]
    if entry_point is EntryPoint.README:
        content = b"# Project\n"
        attack_fixture = attack_fixture.model_copy(
            update={
                "materialization_path": "workspace/README.md",
                "media_type": "text/markdown",
                "source_comment_prefix": None,
                "content_digest": content_digest(content),
            }
        )
        contents[attack_fixture.relative_path] = content
    elif entry_point is EntryPoint.SOURCE_COMMENT:
        content = b"def target() -> bool:\n    return True\n"
        attack_fixture = attack_fixture.model_copy(
            update={
                "materialization_path": "workspace/src/target.py",
                "media_type": "text/x-python",
                "source_comment_prefix": "# ",
                "content_digest": content_digest(content),
            }
        )
        contents[attack_fixture.relative_path] = content
    fixtures[attack_fixture_index] = attack_fixture

    placement = base_pack.attack_placements[0]
    insertion_target = (
        "tool.workspace"
        if entry_point is EntryPoint.MCP_TOOL_DEFINITION
        else "channel.build"
        if entry_point
        in {EntryPoint.BUILD_LOG, EntryPoint.ERROR_MESSAGE, EntryPoint.DELAYED_CONTEXT}
        else "tool.shell"
        if entry_point is EntryPoint.TOOL_RESULT
        else attack_fixture.fixture_id
    )
    placement = placement.model_copy(
        update={"entry_point": entry_point, "insertion_target": insertion_target}
    )
    base = base_pack.base_scenarios[0]
    attack_surface = base.attack_surface.model_copy(
        update={
            "entry_points": (entry_point,),
            "insertion_target_kinds": (entry_point.value,),
        }
    )
    reset = base_pack.reset_contracts[0].model_copy(
        update={"baseline_digest": scenario_assets.environment_baseline_digest(fixtures)}
    )
    pack = base_pack.model_copy(
        update={
            "base_scenarios": (base.model_copy(update={"attack_surface": attack_surface}),),
            "attack_placements": (placement,),
            "fixtures": tuple(fixtures),
            "reset_contracts": (reset,),
            "output_digest": None,
        }
    )
    pack = with_computed_digest(pack)
    destination = tmp_path / entry_point.value
    serialize_executable_pack(pack, destination, contents)
    return load_executable_pack(destination)


def test_issue_attack_materializes_into_issue_fixture_not_user_prompt(tmp_path: Path) -> None:
    loaded = loaded_pack(tmp_path)
    pack = loaded.pack
    compiled = compile_case(pack.cases[0], pack, run_configuration())

    materialized = scenario_assets.materialize_case(compiled, loaded)
    sample = execution.materialized_run_input_to_sample(materialized)

    variant = pack.attack_variants[0]
    assert compiled.execution_spec.attack_candidate.content == ""
    assert variant.content not in str(sample.input)
    issue_file = next(item for item in materialized.files if item.component_id == "fixture.issue")
    issue_document = json.loads(issue_file.content)
    assert issue_document["issue"]["body"] == variant.content
    assert materialized.attack_materialized is True
    assert materialized.placement_entry_point is EntryPoint.ISSUE
    assert sample.id == compiled.execution_spec.run_id
    assert sample.files is not None
    assert sample.files["workspace/.agentsec/issue.json"] == issue_file.content.decode()
    assert "verifier/oracle-state.json" not in sample.files
    assert sample.metadata is not None
    assert sample.metadata["materialization_digest"] == materialized.output_digest
    serialized_metadata = json.dumps(sample.metadata, sort_keys=True)
    private_file = next(
        item for item in materialized.files if item.visibility is Visibility.VERIFIER_PRIVATE
    )
    assert private_file.content.decode() not in serialized_metadata


def test_direct_attack_materializes_only_into_user_message(tmp_path: Path) -> None:
    base_pack = make_complete_pack()
    placement = base_pack.attack_placements[0].model_copy(
        update={
            "entry_point": EntryPoint.USER_REQUEST,
            "delivery_mode": AttackDeliveryMode.DIRECT_USER_REQUEST,
            "insertion_target": base_pack.cases[0].case_id,
        }
    )
    base = base_pack.base_scenarios[0]
    attack_surface = base.attack_surface.model_copy(
        update={
            "entry_points": (EntryPoint.USER_REQUEST,),
            "insertion_target_kinds": ("user_message",),
        }
    )
    pack = base_pack.model_copy(
        update={
            "base_scenarios": (base.model_copy(update={"attack_surface": attack_surface}),),
            "attack_placements": (placement,),
            "output_digest": None,
        }
    )
    pack = with_computed_digest(pack)
    destination = tmp_path / "pack"
    serialize_executable_pack(pack, destination, pack_contents())
    loaded = load_executable_pack(destination)
    compiled = compile_case(pack.cases[0], pack, run_configuration())

    materialized = scenario_assets.materialize_case(compiled, loaded)
    sample = execution.materialized_run_input_to_sample(materialized)

    variant = pack.attack_variants[0]
    assert compiled.execution_spec.attack_candidate.content == variant.content
    assert str(sample.input).endswith(variant.content)
    issue_file = next(item for item in materialized.files if item.component_id == "fixture.issue")
    assert json.loads(issue_file.content) == json.loads(pack_contents()[issue_file.source_path])
    assert not materialized.channel_injections
    assert {
        item.source_path
        for item in materialized.files
        if item.visibility is Visibility.VERIFIER_PRIVATE
    } == {"fixtures/verifier-private/oracle-state.json"}


def test_readme_attack_materializes_into_readme_fixture(tmp_path: Path) -> None:
    loaded = loaded_pack_for_entry_point(tmp_path, EntryPoint.README)
    compiled = compile_case(loaded.pack.cases[0], loaded.pack, run_configuration())

    materialized = scenario_assets.materialize_case(compiled, loaded)

    variant = loaded.pack.attack_variants[0]
    readme = next(item for item in materialized.files if item.component_id == "fixture.issue")
    assert readme.destination_path == "workspace/README.md"
    assert readme.content.decode().endswith(f"{variant.content}\n")
    assert variant.content not in compiled.agent_visible_prompt


def test_source_comment_attack_materializes_as_source_comment(tmp_path: Path) -> None:
    loaded = loaded_pack_for_entry_point(tmp_path, EntryPoint.SOURCE_COMMENT)
    compiled = compile_case(loaded.pack.cases[0], loaded.pack, run_configuration())

    materialized = scenario_assets.materialize_case(compiled, loaded)

    variant = loaded.pack.attack_variants[0]
    source = next(item for item in materialized.files if item.component_id == "fixture.issue")
    assert source.destination_path == "workspace/src/target.py"
    assert source.content.decode().startswith(f"# {variant.content}\n")
    assert variant.content not in compiled.agent_visible_prompt


def test_build_log_and_tool_result_attacks_materialize_as_channels(tmp_path: Path) -> None:
    for entry_point in (
        EntryPoint.BUILD_LOG,
        EntryPoint.TOOL_RESULT,
        EntryPoint.ERROR_MESSAGE,
        EntryPoint.DELAYED_CONTEXT,
    ):
        loaded = loaded_pack_for_entry_point(tmp_path, entry_point)
        compiled = compile_case(loaded.pack.cases[0], loaded.pack, run_configuration())

        materialized = scenario_assets.materialize_case(compiled, loaded)

        assert len(materialized.channel_injections) == 1
        assert materialized.channel_injections[0].entry_point is entry_point
        assert materialized.channel_injections[0].content == loaded.pack.attack_variants[0].content
        assert loaded.pack.attack_variants[0].content not in compiled.agent_visible_prompt


def test_file_and_configuration_attacks_materialize_into_agent_visible_fixture(
    tmp_path: Path,
) -> None:
    for entry_point, field in (
        (EntryPoint.FILE_CONTENT, "content"),
        (EntryPoint.CONFIGURATION, "configuration"),
    ):
        loaded = loaded_pack_for_entry_point(tmp_path, entry_point)
        compiled = compile_case(loaded.pack.cases[0], loaded.pack, run_configuration())

        materialized = scenario_assets.materialize_case(compiled, loaded)

        fixture = next(item for item in materialized.files if item.component_id == "fixture.issue")
        assert json.loads(fixture.content)[field] == loaded.pack.attack_variants[0].content
        assert loaded.pack.attack_variants[0].content not in compiled.agent_visible_prompt


def test_mcp_attack_materializes_into_tool_description(tmp_path: Path) -> None:
    loaded = loaded_pack_for_entry_point(tmp_path, EntryPoint.MCP_TOOL_DEFINITION)
    compiled = compile_case(loaded.pack.cases[0], loaded.pack, run_configuration())

    materialized = scenario_assets.materialize_case(compiled, loaded)

    tool = next(item for item in materialized.files if item.component_id == "tool.workspace")
    assert json.loads(tool.content)["description"] == loaded.pack.attack_variants[0].content
    assert loaded.pack.attack_variants[0].content not in compiled.agent_visible_prompt


def test_reset_restores_real_baseline_and_removes_generated_artifacts(tmp_path: Path) -> None:
    loaded = loaded_pack(tmp_path / "source")
    compiled = compile_case(loaded.pack.cases[0], loaded.pack, run_configuration())
    materialized = scenario_assets.materialize_case(compiled, loaded)
    environment_root = tmp_path / "environment"

    written = scenario_assets.write_materialized_environment(materialized, environment_root)
    generated = environment_root / "agent" / "workspace" / "generated.txt"
    generated.parent.mkdir(parents=True, exist_ok=True)
    generated.write_text("generated")
    reset = scenario_assets.reset_materialized_environment(materialized, environment_root)

    assert written.state_digest == materialized.materialized_state_digest
    assert reset.baseline_restored is True
    assert reset.state_digest == materialized.baseline_state_digest
    assert not generated.exists()
    issue_path = environment_root / "agent" / "workspace" / ".agentsec" / "issue.json"
    assert json.loads(issue_path.read_bytes()) == json.loads(
        pack_contents()["fixtures/agent-visible/issue.json"]
    )
