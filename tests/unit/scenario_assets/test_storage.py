from __future__ import annotations

from pathlib import Path

import pytest

from agentsec_eval.scenario_assets import (
    Visibility,
    load_executable_pack,
    serialize_executable_pack,
    with_computed_digest,
)

from .test_models import (
    AGENT_FIXTURE_CONTENT,
    ATTACK_FIXTURE_CONTENT,
    DOCKERFILE_CONTENT,
    PACK_TEST_CONTENT,
    PRIVATE_FIXTURE_CONTENT,
    TOOL_INTERFACE_CONTENT,
    make_complete_pack,
)


def pack_contents() -> dict[str, bytes]:
    return {
        "fixtures/agent-visible/request.json": AGENT_FIXTURE_CONTENT,
        "fixtures/agent-visible/issue.json": ATTACK_FIXTURE_CONTENT,
        "fixtures/verifier-private/oracle-state.json": PRIVATE_FIXTURE_CONTENT,
        "docker/Dockerfile": DOCKERFILE_CONTENT,
        "tools/workspace.json": TOOL_INTERFACE_CONTENT,
        "tests/test_pack.py": PACK_TEST_CONTENT,
    }


def test_pack_serializer_writes_complete_physical_layout_and_round_trips(
    tmp_path: Path,
) -> None:
    pack = with_computed_digest(make_complete_pack())
    destination = tmp_path / "ExecutableScenarioPack"

    manifest = serialize_executable_pack(pack, destination, pack_contents())
    loaded = load_executable_pack(destination)

    assert loaded.pack == pack
    assert manifest.pack_content_digest == pack.output_digest
    assert {path.name for path in destination.iterdir()} == {
        "scenario.yaml",
        "cases",
        "fixtures",
        "docker",
        "tools",
        "oracles",
        "assertions",
        "provenance.yaml",
        "reset",
        "tests",
    }
    assert (destination / "cases" / "case.saber-a.yaml").is_file()
    assert (destination / "fixtures" / "manifest.yaml").is_file()
    assert (destination / "docker" / "manifest.yaml").is_file()
    assert (destination / "tools" / "manifest.yaml").is_file()
    assert (destination / "oracles" / "suites.yaml").is_file()
    assert (destination / "assertions" / "contexts.yaml").is_file()
    assert (destination / "reset" / "contracts.yaml").is_file()
    assert (destination / "tests" / "manifest.yaml").is_file()


def test_pack_serializer_is_byte_deterministic(tmp_path: Path) -> None:
    pack = with_computed_digest(make_complete_pack())
    first = tmp_path / "first"
    second = tmp_path / "second"

    serialize_executable_pack(pack, first, pack_contents())
    serialize_executable_pack(pack, second, pack_contents())

    first_files = {
        path.relative_to(first).as_posix(): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second).as_posix(): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files


def test_loaded_pack_separates_file_visibility(tmp_path: Path) -> None:
    destination = tmp_path / "pack"
    serialize_executable_pack(
        with_computed_digest(make_complete_pack()), destination, pack_contents()
    )

    loaded = load_executable_pack(destination)

    assert {
        item.relative_path for item in loaded.files_for_visibility(Visibility.AGENT_VISIBLE)
    } == {
        "fixtures/agent-visible/request.json",
        "fixtures/agent-visible/issue.json",
        "tools/workspace.json",
    }
    assert {
        item.relative_path for item in loaded.files_for_visibility(Visibility.VERIFIER_PRIVATE)
    } == {"fixtures/verifier-private/oracle-state.json"}
    assert {
        item.relative_path for item in loaded.files_for_visibility(Visibility.HARNESS_INTERNAL)
    } == {"docker/Dockerfile", "tests/test_pack.py"}


def test_pack_loader_rejects_tampered_content(tmp_path: Path) -> None:
    destination = tmp_path / "pack"
    serialize_executable_pack(
        with_computed_digest(make_complete_pack()), destination, pack_contents()
    )
    (destination / "fixtures" / "agent-visible" / "request.json").write_bytes(b"tampered")

    with pytest.raises(ValueError, match="digest"):
        load_executable_pack(destination)


@pytest.mark.parametrize("mutation", ["missing", "extra", "symlink"])
def test_pack_loader_rejects_incomplete_or_undeclared_files(tmp_path: Path, mutation: str) -> None:
    destination = tmp_path / "pack"
    serialize_executable_pack(
        with_computed_digest(make_complete_pack()), destination, pack_contents()
    )
    if mutation == "missing":
        (destination / "tools" / "workspace.json").unlink()
    elif mutation == "extra":
        (destination / "fixtures" / "agent-visible" / "extra.txt").write_text("extra")
    else:
        target = destination / "fixtures" / "agent-visible" / "request.json"
        target.unlink()
        target.symlink_to(destination / "docker" / "Dockerfile")

    with pytest.raises(ValueError, match="missing|undeclared|symlink"):
        load_executable_pack(destination)


def test_pack_serializer_fails_before_creating_destination_on_digest_mismatch(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "pack"
    contents = pack_contents()
    contents["docker/Dockerfile"] = b"different"

    with pytest.raises(ValueError, match="digest"):
        serialize_executable_pack(with_computed_digest(make_complete_pack()), destination, contents)

    assert not destination.exists()
