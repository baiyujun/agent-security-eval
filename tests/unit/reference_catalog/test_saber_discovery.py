from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest

from agentsec_eval.reference_catalog import validation as validation_module
from agentsec_eval.reference_catalog.digest import canonical_json_digest
from agentsec_eval.reference_catalog.discovery import saber as saber_module
from agentsec_eval.reference_catalog.discovery.base import (
    DiscoveryContext,
    SourceCheckout,
)
from agentsec_eval.reference_catalog.discovery.saber import SaberDiscoverer
from agentsec_eval.reference_catalog.models import UpstreamLedgerRecord

TASK_IDS = ("A_info_001", "B_code_001", "C_access_001")
TASK_LAYOUT = (
    ("A", "info_leak", "A_info_001"),
    ("B", "code_tampering", "B_code_001"),
    ("C", "unauthorized_access", "C_access_001"),
)


@dataclass(frozen=True)
class FixtureCheckout:
    source_project: str
    repository: str
    commit: str
    root: Path
    audited_files: tuple[PurePosixPath, ...] = ()


def write_task(
    root: Path,
    scenario: str,
    category: str,
    task_id: str,
    *,
    injection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task = {
        "id": task_id,
        "scenario": scenario,
        "category": category,
        "difficulty": "medium",
        "setup": {"task": "SABER_RESTRICTED_SETUP_SENTINEL"},
        "injection": injection
        if injection is not None
        else {
            "enabled": scenario == "A",
            **(
                {
                    "method": "tool_output",
                    "payload": "SABER_RESTRICTED_PAYLOAD_SENTINEL",
                }
                if scenario == "A"
                else {}
            ),
        },
        "ground_truth": {"expected": "SABER_RESTRICTED_GROUND_TRUTH_SENTINEL"},
    }
    path = root / "tasks" / scenario / category / f"{task_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(task), encoding="utf-8")
    return task


def write_manifest(
    root: Path,
    *,
    task_ids: tuple[str, ...] = TASK_IDS,
    task_total: int = 3,
    scenario_counts: dict[str, int] | None = None,
) -> None:
    manifest = {
        "name": "SABER fixture",
        "counts": {
            "tasks": task_total,
            "by_scenario": scenario_counts or {"A": 1, "B": 1, "C": 1},
        },
        "task_ids": list(task_ids),
    }
    path = root / "dataset" / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def make_context(tmp_path: Path) -> tuple[DiscoveryContext, Path, dict[str, dict[str, Any]]]:
    checkout_root = tmp_path / "saber"
    tasks = {
        task_id: write_task(checkout_root, scenario, category, task_id)
        for scenario, category, task_id in TASK_LAYOUT
    }
    write_manifest(checkout_root)
    checkout = FixtureCheckout(
        source_project="saber",
        repository="https://github.com/example/saber",
        commit="a" * 40,
        root=checkout_root,
    )
    checkouts: Mapping[str, SourceCheckout] = {"saber": cast(SourceCheckout, checkout)}
    context = DiscoveryContext(
        repository_root=tmp_path / "project",
        checkouts=checkouts,
    )
    return context, checkout_root, tasks


def test_discovers_three_scenarios_with_safe_metadata_and_canonical_digests(
    tmp_path: Path,
) -> None:
    context, _root, tasks = make_context(tmp_path)

    records = SaberDiscoverer(expected_total=3).discover(context)

    assert [record.source_record_key for record in records] == list(TASK_IDS)
    assert [record.source_path for record in records] == [
        "tasks/A/info_leak/A_info_001.json",
        "tasks/B/code_tampering/B_code_001.json",
        "tasks/C/unauthorized_access/C_access_001.json",
    ]
    assert [record.source_record_digest for record in records] == [
        canonical_json_digest(tasks[task_id]) for task_id in TASK_IDS
    ]
    assert all(record.source_project == "saber" for record in records)
    assert all(record.source_repository == "https://github.com/example/saber" for record in records)
    assert all(record.source_commit == "a" * 40 for record in records)
    assert all(record.asset_family == "saber" for record in records)
    assert all(record.conversion_reason for record in records)
    a, b, c = records
    assert (a.scenario_class, a.category, a.attack_present, a.attack_origin) == (
        "A",
        "info_leak",
        True,
        None,
    )
    assert a.attack_delivery_mode == "tool_output"
    assert (b.scenario_class, b.attack_present, b.attack_origin, b.attack_delivery_mode) == (
        "B",
        False,
        None,
        None,
    )
    assert (
        c.scenario_class,
        c.attack_present,
        c.attack_origin,
        c.attack_delivery_mode,
    ) == ("C", True, "user", "direct_user_request")
    assert all(record.record_role.value == "benchmark_scenario" for record in records)
    assert all(record.source_asset_kind.value == "saber_task" for record in records)
    assert all(record.raw_reuse_disposition.value == "review_required" for record in records)
    assert all(
        record.native_conversion_disposition.value == "eligible_for_semantic_reconstruction"
        for record in records
    )
    assert all(
        record.native_output_kind is None and record.native_output_id is None for record in records
    )

    rendered_metadata = json.dumps(
        [record.model_dump(mode="json") for record in records],
        ensure_ascii=False,
    )
    assert "SABER_RESTRICTED_SETUP_SENTINEL" not in rendered_metadata
    assert "SABER_RESTRICTED_PAYLOAD_SENTINEL" not in rendered_metadata
    assert "SABER_RESTRICTED_GROUND_TRUTH_SENTINEL" not in rendered_metadata


def test_validates_the_complete_record_sequence_before_returning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, _root, _tasks = make_context(tmp_path)
    calls: list[tuple[UpstreamLedgerRecord, ...]] = []

    def record_validation(
        records: list[UpstreamLedgerRecord],
        *,
        require_initial_outputs: bool = True,
    ) -> tuple[UpstreamLedgerRecord, ...]:
        captured = tuple(records)
        calls.append(captured)
        return validation_module.validate_records(
            captured,
            require_initial_outputs=require_initial_outputs,
        )

    monkeypatch.setattr(saber_module, "validate_records", record_validation, raising=False)

    returned = SaberDiscoverer(expected_total=3).discover(context)

    assert len(calls) == 1
    assert len(calls[0]) == 3
    assert tuple(returned) == calls[0]


def test_final_validation_failure_does_not_return_partial_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, _root, _tasks = make_context(tmp_path)

    def reject_records(
        records: list[UpstreamLedgerRecord],
        *,
        require_initial_outputs: bool = True,
    ) -> tuple[UpstreamLedgerRecord, ...]:
        del records, require_initial_outputs
        raise ValueError("final ledger validation failed")

    monkeypatch.setattr(saber_module, "validate_records", reject_records, raising=False)

    with pytest.raises(ValueError, match="final ledger validation failed"):
        SaberDiscoverer(expected_total=3).discover(context)


def test_ignores_pilot_file_outside_approved_task_glob(tmp_path: Path) -> None:
    context, root, _tasks = make_context(tmp_path)
    (root / "tasks" / "pilot_tasks.json").write_text("not json", encoding="utf-8")

    records = SaberDiscoverer(expected_total=3).discover(context)

    assert len(records) == 3


@pytest.mark.parametrize(
    "relative_path",
    [
        "tasks/README.md",
        "tasks/A/info_leak/unexpected.txt",
        "tasks/A/misplaced.json",
        "tasks/D/info_leak/D_info_001.json",
    ],
)
def test_rejects_every_unapproved_task_tree_file(
    tmp_path: Path,
    relative_path: str,
) -> None:
    context, root, _tasks = make_context(tmp_path)
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("unapproved", encoding="utf-8")

    with pytest.raises(ValueError, match="unapproved SABER task path"):
        SaberDiscoverer(expected_total=3).discover(context)


@pytest.mark.parametrize(
    "injection",
    [
        {"enabled": True},
        {"enabled": False},
    ],
)
def test_scenario_a_keeps_delivery_null_without_sufficient_structured_evidence(
    tmp_path: Path,
    injection: dict[str, Any],
) -> None:
    context, root, _tasks = make_context(tmp_path)
    write_task(root, "A", "info_leak", "A_info_001", injection=injection)

    record = SaberDiscoverer(expected_total=3).discover(context)[0]

    assert record.attack_present is True
    assert record.attack_origin is None
    assert record.attack_delivery_mode is None


def test_scenario_c_environment_warning_remains_a_direct_user_attack(tmp_path: Path) -> None:
    context, root, _tasks = make_context(tmp_path)
    write_task(
        root,
        "C",
        "unauthorized_access",
        "C_access_001",
        injection={"enabled": True, "method": "file_content"},
    )

    record = SaberDiscoverer(expected_total=3).discover(context)[2]

    assert (record.attack_present, record.attack_origin, record.attack_delivery_mode) == (
        True,
        "user",
        "direct_user_request",
    )


def test_rejects_duplicate_manifest_ids(tmp_path: Path) -> None:
    context, root, _tasks = make_context(tmp_path)
    write_manifest(root, task_ids=("A_info_001", "A_info_001", "C_access_001"))

    with pytest.raises(ValueError, match="duplicate manifest task ID"):
        SaberDiscoverer(expected_total=3).discover(context)


def test_rejects_duplicate_task_ids(tmp_path: Path) -> None:
    context, root, _tasks = make_context(tmp_path)
    write_task(root, "A", "code_tampering", "A_info_001")
    write_manifest(
        root,
        task_ids=("A_info_001", "B_code_001", "C_access_001", "A_code_999"),
        task_total=4,
        scenario_counts={"A": 2, "B": 1, "C": 1},
    )

    with pytest.raises(ValueError, match="duplicate parsed task ID"):
        SaberDiscoverer(expected_total=4).discover(context)


@pytest.mark.parametrize("mode", ["missing", "extra"])
def test_rejects_missing_or_extra_task_files(tmp_path: Path, mode: str) -> None:
    context, root, _tasks = make_context(tmp_path)
    if mode == "missing":
        (root / "tasks/B/code_tampering/B_code_001.json").unlink()
    else:
        write_task(root, "A", "data_destruction", "A_data_999")

    with pytest.raises(ValueError, match="expected 3 SABER task files"):
        SaberDiscoverer(expected_total=3).discover(context)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("scenario", "B", "scenario"),
        ("category", "network_outbound", "category"),
        ("id", "B_info_001", "task ID"),
        ("scenario", "D", "unknown scenario"),
    ],
)
def test_rejects_path_record_and_id_mismatches(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    context, root, tasks = make_context(tmp_path)
    changed = {**tasks["A_info_001"], field: value}
    path = root / "tasks/A/info_leak/A_info_001.json"
    path.write_text(json.dumps(changed), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        SaberDiscoverer(expected_total=3).discover(context)


def test_rejects_malformed_task_json(tmp_path: Path) -> None:
    context, root, _tasks = make_context(tmp_path)
    (root / "tasks/A/info_leak/A_info_001.json").write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="malformed JSON"):
        SaberDiscoverer(expected_total=3).discover(context)


@pytest.mark.parametrize(
    ("discoverer_total", "manifest_total", "task_ids", "message"),
    [
        (4, 3, TASK_IDS, "expected total"),
        (3, 2, TASK_IDS, "manifest count"),
        (3, 3, TASK_IDS[:-1], "manifest ID count"),
    ],
)
def test_rejects_total_disagreement(
    tmp_path: Path,
    discoverer_total: int,
    manifest_total: int,
    task_ids: tuple[str, ...],
    message: str,
) -> None:
    context, root, _tasks = make_context(tmp_path)
    write_manifest(root, task_ids=task_ids, task_total=manifest_total)

    with pytest.raises(ValueError, match=message):
        SaberDiscoverer(expected_total=discoverer_total).discover(context)


def test_rejects_scenario_count_disagreement(tmp_path: Path) -> None:
    context, root, _tasks = make_context(tmp_path)
    write_manifest(root, scenario_counts={"A": 2, "B": 0, "C": 1})

    with pytest.raises(ValueError, match="scenario counts"):
        SaberDiscoverer(expected_total=3).discover(context)
