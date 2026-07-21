from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest

from agentsec_eval.reference_catalog.discovery.base import DiscoveryContext, SourceCheckout
from agentsec_eval.reference_catalog.discovery.mcpsecbench import MCPSecBenchDiscoverer


@dataclass(frozen=True)
class FixtureCheckout:
    source_project: str
    repository: str
    commit: str
    root: Path
    audited_files: tuple[PurePosixPath, ...] = ()


def make_context(
    tmp_path: Path,
    structured: list[dict[str, Any]],
    taxonomy: tuple[str, ...],
) -> tuple[DiscoveryContext, Path]:
    checkout_root = tmp_path / "mcpsecbench"
    data_root = checkout_root / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "data.json").write_text(json.dumps(structured), encoding="utf-8")
    (data_root / "experiments.csv").write_text(
        ",".join(("MCP Provider", *taxonomy)) + "\n",
        encoding="utf-8",
    )
    checkout = FixtureCheckout(
        source_project="mcpsecbench",
        repository="https://github.com/example/mcpsecbench",
        commit="e" * 40,
        root=checkout_root,
    )
    checkouts: Mapping[str, SourceCheckout] = {"mcpsecbench": cast(SourceCheckout, checkout)}
    return (
        DiscoveryContext(repository_root=tmp_path / "project", checkouts=checkouts),
        checkout_root,
    )


def structured_attack(name: str) -> dict[str, Any]:
    return {
        "attack": name,
        "prompt": "MCPSECBENCH_RESTRICTED_PROMPT_SENTINEL",
        "result": "MCPSECBENCH_RESTRICTED_RESULT_SENTINEL",
    }


def test_discovers_structured_and_taxonomy_records_with_exact_taxonomy_digest(
    tmp_path: Path,
) -> None:
    structured = [structured_attack("Tool Poisoning Attack"), structured_attack("Rug Pull")]
    taxonomy = ("Tool Poisoning Attack", "Rug Pull Attack", "Schema Inconsistencies")
    context, _root = make_context(tmp_path, structured, taxonomy)

    discoverer = MCPSecBenchDiscoverer(
        expected_structured_total=2,
        expected_taxonomy_total=1,
    )
    records = discoverer.discover(context)

    assert [record.record_role.value for record in records] == [
        "benchmark_scenario",
        "benchmark_scenario",
        "attack_taxonomy",
    ]
    assert [record.category for record in records] == [
        "Tool Poisoning Attack",
        "Rug Pull",
        "Schema Inconsistencies",
    ]
    taxonomy_record = records[-1]
    expected_digest = hashlib.sha256(
        b"data/experiments.csv\nschema inconsistencies\nSchema Inconsistencies"
    ).hexdigest()
    assert taxonomy_record.source_record_digest == expected_digest
    assert taxonomy_record.native_output_kind is None
    assert taxonomy_record.native_output_id is None
    assert taxonomy_record.attack_present is None
    serialized = json.dumps([record.model_dump(mode="json") for record in records])
    assert "MCPSECBENCH_RESTRICTED_PROMPT_SENTINEL" not in serialized
    assert "MCPSECBENCH_RESTRICTED_RESULT_SENTINEL" not in serialized


def test_applies_only_approved_category_aliases_and_unicode_normalization(
    tmp_path: Path,
) -> None:
    aliases = (
        "Tool/Service Misuse via “Confused AI”",
        "Package Name Squatting(tools name)",
        "Package Name Squatting(server name)",
        "Rug Pull Attack",
    )
    structured = [structured_attack("Tool Misuse via Confused AI")]
    context, _root = make_context(tmp_path, structured, aliases)

    records = MCPSecBenchDiscoverer(
        expected_structured_total=1,
        expected_taxonomy_total=3,
    ).discover(context)

    assert [record.category for record in records[1:]] == [
        "Package Name Squatting(tools name)",
        "Package Name Squatting(server name)",
        "Rug Pull Attack",
    ]


def test_rejects_duplicate_structured_categories(tmp_path: Path) -> None:
    structured = [structured_attack("Tool Poisoning Attack") for _ in range(2)]
    context, _root = make_context(tmp_path, structured, ("Tool Poisoning Attack",))

    with pytest.raises(ValueError, match="duplicate structured"):
        MCPSecBenchDiscoverer(expected_structured_total=2, expected_taxonomy_total=0).discover(
            context
        )


def test_rejects_duplicate_taxonomy_categories_after_normalization(tmp_path: Path) -> None:
    context, _root = make_context(
        tmp_path,
        [structured_attack("Tool Poisoning Attack")],
        ("Schema Inconsistencies", " schema   inconsistencies "),
    )

    with pytest.raises(ValueError, match="duplicate taxonomy"):
        MCPSecBenchDiscoverer(expected_structured_total=1, expected_taxonomy_total=2).discover(
            context
        )


def test_rejects_missing_attack_field(tmp_path: Path) -> None:
    context, root = make_context(
        tmp_path,
        [{"prompt": "x", "result": "y"}],
        ("Schema Inconsistencies",),
    )

    with pytest.raises(ValueError, match="attack"):
        MCPSecBenchDiscoverer(expected_structured_total=1, expected_taxonomy_total=1).discover(
            context
        )


def test_rejects_inconsistent_structured_root(tmp_path: Path) -> None:
    context, root = make_context(tmp_path, [structured_attack("Tool Poisoning Attack")], ())
    (root / "data/data.json").write_text(json.dumps({"records": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="JSON array"):
        MCPSecBenchDiscoverer(expected_structured_total=1, expected_taxonomy_total=0).discover(
            context
        )
