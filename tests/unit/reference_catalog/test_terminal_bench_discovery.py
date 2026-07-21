from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

import pytest

from agentsec_eval.reference_catalog import digest as digest_module
from agentsec_eval.reference_catalog.digest import directory_manifest_digest
from agentsec_eval.reference_catalog.discovery.base import DiscoveryContext, SourceCheckout
from agentsec_eval.reference_catalog.discovery.terminal_bench import TerminalBenchDiscoverer


@dataclass(frozen=True)
class FixtureCheckout:
    source_project: str
    repository: str
    commit: str
    root: Path
    audited_files: tuple[PurePosixPath, ...] = ()


def make_context(
    tmp_path: Path,
    task_names: tuple[str, ...] = ("z-task", "a-task"),
) -> tuple[DiscoveryContext, Path]:
    checkout_root = tmp_path / "terminal-bench-2"
    for task_name in task_names:
        task_root = checkout_root / task_name
        (task_root / "environment").mkdir(parents=True, exist_ok=True)
        (task_root / "task.toml").write_text(
            "TB2_RESTRICTED_TASK_TOML_SENTINEL",
            encoding="utf-8",
        )
        (task_root / "instruction.md").write_text(
            "TB2_RESTRICTED_INSTRUCTION_SENTINEL",
            encoding="utf-8",
        )
        (task_root / "environment" / "Dockerfile").write_text(
            "TB2_RESTRICTED_DOCKERFILE_SENTINEL",
            encoding="utf-8",
        )
    (checkout_root / ".git").mkdir(parents=True, exist_ok=True)
    (checkout_root / "README.md").write_text("control", encoding="utf-8")
    checkout = FixtureCheckout(
        source_project="terminal-bench-2",
        repository="https://github.com/example/terminal-bench-2",
        commit="c" * 40,
        root=checkout_root,
    )
    checkouts: Mapping[str, SourceCheckout] = {"terminal-bench-2": cast(SourceCheckout, checkout)}
    return (
        DiscoveryContext(repository_root=tmp_path / "project", checkouts=checkouts),
        checkout_root,
    )


def test_discovers_sorted_task_directories_using_manifest_digests_only(tmp_path: Path) -> None:
    context, root = make_context(tmp_path)

    records = TerminalBenchDiscoverer(expected_total=2).discover(context)

    assert [record.source_record_key for record in records] == ["a-task", "z-task"]
    assert [record.source_path for record in records] == ["a-task", "z-task"]
    assert [record.source_record_digest for record in records] == [
        directory_manifest_digest(root / task_name) for task_name in ("a-task", "z-task")
    ]
    assert all(record.record_role.value == "normal_task_fixture" for record in records)
    assert all(
        record.source_asset_kind.value == "terminal_bench_task_directory" for record in records
    )
    assert all(
        record.native_output_kind is None and record.native_output_id is None for record in records
    )
    serialized = str([record.model_dump(mode="json") for record in records])
    assert "TB2_RESTRICTED_INSTRUCTION_SENTINEL" not in serialized
    assert "TB2_RESTRICTED_DOCKERFILE_SENTINEL" not in serialized
    assert "TB2_RESTRICTED_TASK_TOML_SENTINEL" not in serialized


def test_ignores_repository_control_files_and_git_directory(tmp_path: Path) -> None:
    context, _root = make_context(tmp_path)

    assert len(TerminalBenchDiscoverer(expected_total=2).discover(context)) == 2


def test_rejects_expected_total_disagreement(tmp_path: Path) -> None:
    context, _root = make_context(tmp_path)

    with pytest.raises(ValueError, match="expected 3 Terminal-Bench tasks"):
        TerminalBenchDiscoverer(expected_total=3).discover(context)


def test_rejects_top_level_task_directory_without_task_toml(tmp_path: Path) -> None:
    context, root = make_context(tmp_path)
    (root / "missing-task-toml").mkdir()

    with pytest.raises(ValueError, match="task.toml"):
        TerminalBenchDiscoverer(expected_total=2).discover(context)


def test_rejects_top_level_task_symlink(tmp_path: Path) -> None:
    context, root = make_context(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "linked-task").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        TerminalBenchDiscoverer(expected_total=2).discover(context)


def test_rejects_symlink_member_inside_task(tmp_path: Path) -> None:
    context, root = make_context(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (root / "a-task" / "escape").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        TerminalBenchDiscoverer(expected_total=2).discover(context)


def test_rejects_unreadable_member(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    context, root = make_context(tmp_path)
    unreadable = root / "a-task" / "instruction.md"
    real_read = Path.read_bytes

    def deny_read(path: Path) -> bytes:
        if path == unreadable:
            raise PermissionError("denied")
        return real_read(path)

    monkeypatch.setattr(digest_module, "_read_bytes", deny_read)

    with pytest.raises(ValueError, match="read"):
        TerminalBenchDiscoverer(expected_total=2).discover(context)


def test_rejects_path_escape_member(tmp_path: Path) -> None:
    context, root = make_context(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (root / "a-task" / "escape").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink|escape"):
        TerminalBenchDiscoverer(expected_total=2).discover(context)
