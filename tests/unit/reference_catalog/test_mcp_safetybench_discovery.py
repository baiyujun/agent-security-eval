from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest

from agentsec_eval.reference_catalog.digest import canonical_json_digest
from agentsec_eval.reference_catalog.discovery.base import DiscoveryContext, SourceCheckout
from agentsec_eval.reference_catalog.discovery.mcp_safetybench import MCPSafetyBenchDiscoverer


@dataclass(frozen=True)
class FixtureCheckout:
    source_project: str
    repository: str
    commit: str
    root: Path
    audited_files: tuple[PurePosixPath, ...] = ()


def make_task(
    category: str,
    *,
    question: str = "MCP_RESTRICTED_QUESTION_SENTINEL",
) -> dict[str, Any]:
    return {
        "category": "tool-use",
        "attack_category": category,
        "question": question,
        "evaluators": ["MCP_RESTRICTED_EVALUATOR_SENTINEL"],
        "mcp_server_modifications": ["MCP_RESTRICTED_SERVER_SENTINEL"],
    }


def make_context(
    tmp_path: Path,
    tasks: Mapping[str, dict[str, Any]],
) -> tuple[DiscoveryContext, Path]:
    checkout_root = tmp_path / "mcp-safetybench"
    for relative_path, task in tasks.items():
        path = checkout_root / "mcpuniverse/benchmark/configs/test" / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(task), encoding="utf-8")
    checkout = FixtureCheckout(
        source_project="mcp-safetybench",
        repository="https://github.com/example/mcp-safetybench",
        commit="d" * 40,
        root=checkout_root,
    )
    checkouts: Mapping[str, SourceCheckout] = {"mcp-safetybench": cast(SourceCheckout, checkout)}
    return (
        DiscoveryContext(repository_root=tmp_path / "project", checkouts=checkouts),
        checkout_root,
    )


def test_discovers_sorted_attack_tasks_with_safe_metadata_and_digest(tmp_path: Path) -> None:
    tasks = {
        "finance/z.json": make_task("Credential Theft"),
        "calendar/a.json": make_task("Tool Shadowing"),
    }
    context, _root = make_context(tmp_path, tasks)

    records = MCPSafetyBenchDiscoverer(expected_total=2).discover(context)

    assert [record.source_record_key for record in records] == ["calendar/a", "finance/z"]
    assert [record.source_path for record in records] == [
        "mcpuniverse/benchmark/configs/test/calendar/a.json",
        "mcpuniverse/benchmark/configs/test/finance/z.json",
    ]
    assert [record.category for record in records] == ["Tool Shadowing", "Credential Theft"]
    assert [record.source_record_digest for record in records] == [
        canonical_json_digest(tasks["calendar/a.json"]),
        canonical_json_digest(tasks["finance/z.json"]),
    ]
    assert all(record.attack_present is True for record in records)
    assert all(record.record_role.value == "benchmark_scenario" for record in records)
    assert all(record.source_asset_kind.value == "mcp_safetybench_task" for record in records)
    assert all(
        record.native_output_kind is None and record.native_output_id is None for record in records
    )
    serialized = json.dumps([record.model_dump(mode="json") for record in records])
    for sentinel in (
        "MCP_RESTRICTED_QUESTION_SENTINEL",
        "MCP_RESTRICTED_EVALUATOR_SENTINEL",
        "MCP_RESTRICTED_SERVER_SENTINEL",
    ):
        assert sentinel not in serialized


def test_rejects_expected_total_disagreement(tmp_path: Path) -> None:
    context, _root = make_context(tmp_path, {"finance/a.json": make_task("Credential Theft")})

    with pytest.raises(ValueError, match="expected 2 MCP-SafetyBench tasks"):
        MCPSafetyBenchDiscoverer(expected_total=2).discover(context)


def test_rejects_file_outside_two_level_task_shape(tmp_path: Path) -> None:
    context, root = make_context(tmp_path, {"finance/a.json": make_task("Credential Theft")})
    extra = root / "mcpuniverse/benchmark/configs/test/finance/nested/bad.json"
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="two-level"):
        MCPSafetyBenchDiscoverer(expected_total=1).discover(context)


def test_ignores_non_json_domain_metadata_files(tmp_path: Path) -> None:
    context, root = make_context(tmp_path, {"finance/a.json": make_task("Credential Theft")})
    metadata = root / "mcpuniverse/benchmark/configs/test/finance.yaml"
    metadata.write_text("domain: finance\n", encoding="utf-8")

    records = MCPSafetyBenchDiscoverer(expected_total=1).discover(context)

    assert len(records) == 1


def test_rejects_missing_or_blank_attack_category(tmp_path: Path) -> None:
    task = make_task("Credential Theft")
    task["attack_category"] = " "
    context, _root = make_context(tmp_path, {"finance/a.json": task})

    with pytest.raises(ValueError, match="attack_category"):
        MCPSafetyBenchDiscoverer(expected_total=1).discover(context)


def test_rejects_malformed_json(tmp_path: Path) -> None:
    context, root = make_context(tmp_path, {"finance/a.json": make_task("Credential Theft")})
    path = root / "mcpuniverse/benchmark/configs/test/finance/a.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="malformed JSON"):
        MCPSafetyBenchDiscoverer(expected_total=1).discover(context)


def test_rejects_duplicate_record_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    context, _root = make_context(tmp_path, {"finance/a.json": make_task("Credential Theft")})
    duplicate_path = PurePosixPath("mcpuniverse/benchmark/configs/test/finance/a.json")
    monkeypatch.setattr(
        MCPSafetyBenchDiscoverer,
        "_approved_task_paths",
        lambda _self, _root: (duplicate_path, duplicate_path),
    )

    with pytest.raises(ValueError, match="duplicate MCP-SafetyBench record key"):
        MCPSafetyBenchDiscoverer(expected_total=2).discover(context)
