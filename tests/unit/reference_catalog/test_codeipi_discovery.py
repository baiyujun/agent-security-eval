from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

import pytest

from agentsec_eval.reference_catalog.digest import canonical_json_digest
from agentsec_eval.reference_catalog.discovery.base import DiscoveryContext, SourceCheckout
from agentsec_eval.reference_catalog.discovery.codeipi import CodeIPIDiscoverer

SOURCE_PATH = PurePosixPath("src/inspect_evals/ipi_coding_agent/dataset/samples.json")
RECORD_KEYS = (
    "id",
    "is_benign",
    "injection_vector",
    "payload_category",
    "severity",
    "issue_text",
    "task_description",
    "payload_indicator",
    "payload_sophistication",
    "repo_files",
    "persistence_targets",
    "expected_malicious_action",
    "expected_fix",
    "verification_command",
)


@dataclass(frozen=True)
class FixtureCheckout:
    source_project: str
    repository: str
    commit: str
    root: Path
    audited_files: tuple[PurePosixPath, ...] = ()


def make_sample(sample_id: str, *, benign: bool = False) -> dict[str, Any]:
    return {
        "id": sample_id,
        "is_benign": benign,
        "injection_vector": "none" if benign else "issue_text",
        "payload_category": "benign_control" if benign else "exfiltration",
        "severity": "S0" if benign else "S1",
        "issue_text": "CODEIPI_RESTRICTED_ISSUE_SENTINEL",
        "task_description": "CODEIPI_RESTRICTED_TASK_SENTINEL",
        "payload_indicator": "CODEIPI_RESTRICTED_PAYLOAD_SENTINEL",
        "payload_sophistication": "plain",
        "repo_files": {"README.md": "CODEIPI_RESTRICTED_REPO_SENTINEL"},
        "persistence_targets": None,
        "expected_malicious_action": "CODEIPI_RESTRICTED_ACTION_SENTINEL",
        "expected_fix": "CODEIPI_RESTRICTED_FIX_SENTINEL",
        "verification_command": "CODEIPI_RESTRICTED_COMMAND_SENTINEL",
    }


def make_context(
    tmp_path: Path,
    samples: list[dict[str, Any]],
) -> tuple[DiscoveryContext, Path]:
    checkout_root = tmp_path / "inspect-evals"
    source = checkout_root / SOURCE_PATH
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps(samples), encoding="utf-8")
    checkout = FixtureCheckout(
        source_project="inspect-evals-codeipi",
        repository="https://github.com/example/inspect-evals",
        commit="b" * 40,
        root=checkout_root,
    )
    checkouts: Mapping[str, SourceCheckout] = {
        "inspect-evals-codeipi": cast(SourceCheckout, checkout)
    }
    return (
        DiscoveryContext(repository_root=tmp_path / "project", checkouts=checkouts),
        checkout_root,
    )


def test_discovers_safe_metadata_and_digest_for_malicious_and_benign_samples(
    tmp_path: Path,
) -> None:
    samples = [make_sample("ipi-malicious-01"), make_sample("ipi-benign-01", benign=True)]
    context, _root = make_context(tmp_path, samples)

    records = CodeIPIDiscoverer(expected_total=2).discover(context)

    assert [record.source_record_key for record in records] == [
        "ipi-benign-01",
        "ipi-malicious-01",
    ]
    assert [record.source_path for record in records] == [str(SOURCE_PATH)] * 2
    samples_by_id = {sample["id"]: sample for sample in samples}
    assert [record.source_record_digest for record in records] == [
        canonical_json_digest(samples_by_id[record.source_record_key]) for record in records
    ]
    assert [record.attack_present for record in records] == [False, True]
    assert [record.attack_delivery_mode for record in records] == ["none", "issue_text"]
    assert all(record.source_project == "inspect-evals-codeipi" for record in records)
    assert all(record.source_commit == "b" * 40 for record in records)
    assert all(record.source_asset_kind.value == "codeipi_sample" for record in records)
    assert all(record.record_role.value == "benchmark_scenario" for record in records)
    assert all(record.native_output_kind is None for record in records)
    assert all(record.native_output_id is None for record in records)

    serialized = json.dumps([record.model_dump(mode="json") for record in records])
    for sentinel in (
        "CODEIPI_RESTRICTED_ISSUE_SENTINEL",
        "CODEIPI_RESTRICTED_TASK_SENTINEL",
        "CODEIPI_RESTRICTED_PAYLOAD_SENTINEL",
        "CODEIPI_RESTRICTED_REPO_SENTINEL",
        "CODEIPI_RESTRICTED_ACTION_SENTINEL",
        "CODEIPI_RESTRICTED_FIX_SENTINEL",
        "CODEIPI_RESTRICTED_COMMAND_SENTINEL",
    ):
        assert sentinel not in serialized


def test_rejects_duplicate_ids(tmp_path: Path) -> None:
    context, _root = make_context(
        tmp_path,
        [make_sample("duplicate"), make_sample("duplicate")],
    )

    with pytest.raises(ValueError, match="duplicate CodeIPI ID"):
        CodeIPIDiscoverer(expected_total=2).discover(context)


def test_rejects_expected_total_disagreement(tmp_path: Path) -> None:
    context, _root = make_context(tmp_path, [make_sample("sample")])

    with pytest.raises(ValueError, match="expected 2 CodeIPI samples"):
        CodeIPIDiscoverer(expected_total=2).discover(context)


def test_rejects_non_array_root(tmp_path: Path) -> None:
    context, root = make_context(tmp_path, [make_sample("sample")])
    (root / SOURCE_PATH).write_text(json.dumps({"sample": "not an array"}), encoding="utf-8")

    with pytest.raises(ValueError, match="JSON array"):
        CodeIPIDiscoverer(expected_total=1).discover(context)


@pytest.mark.parametrize("bad_value", ["true", 1, None])
def test_rejects_non_boolean_is_benign(tmp_path: Path, bad_value: Any) -> None:
    sample = make_sample("sample")
    sample["is_benign"] = bad_value
    context, _root = make_context(tmp_path, [sample])

    with pytest.raises(ValueError, match="is_benign"):
        CodeIPIDiscoverer(expected_total=1).discover(context)


@pytest.mark.parametrize("missing_key", ["id", "is_benign", "injection_vector", "payload_category"])
def test_rejects_missing_structural_field(tmp_path: Path, missing_key: str) -> None:
    sample = make_sample("sample")
    del sample[missing_key]
    context, _root = make_context(tmp_path, [sample])

    with pytest.raises(ValueError, match="structural fields"):
        CodeIPIDiscoverer(expected_total=1).discover(context)


def test_rejects_unknown_structural_field(tmp_path: Path) -> None:
    sample = make_sample("sample")
    sample["unexpected"] = "unknown"
    context, _root = make_context(tmp_path, [sample])

    with pytest.raises(ValueError, match="structural fields"):
        CodeIPIDiscoverer(expected_total=1).discover(context)


def test_rejects_malformed_json(tmp_path: Path) -> None:
    context, root = make_context(tmp_path, [make_sample("sample")])
    (root / SOURCE_PATH).write_text("[", encoding="utf-8")

    with pytest.raises(ValueError, match="malformed JSON"):
        CodeIPIDiscoverer(expected_total=1).discover(context)
