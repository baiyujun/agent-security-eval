from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agentsec_eval.reference_catalog import rendering as rendering_module
from agentsec_eval.reference_catalog.models import UpstreamLedgerRecord
from agentsec_eval.reference_catalog.rendering import (
    RenderedCatalog,
    render_jsonl,
    replace_outputs_transactionally,
)


def make_record(
    *,
    source_project: str,
    source_path: str,
    source_record_key: str,
    record_role: str = "benchmark_scenario",
    category: str = "category",
) -> UpstreamLedgerRecord:
    source_asset_kind = "mcpsecbench_taxonomy" if record_role == "attack_taxonomy" else "saber_task"
    return UpstreamLedgerRecord.model_validate(
        {
            "source_project": source_project,
            "source_repository": f"https://github.com/example/{source_project}",
            "source_commit": "a" * 40,
            "source_path": source_path,
            "source_record_key": source_record_key,
            "source_record_digest": "b" * 64,
            "record_role": record_role,
            "source_asset_kind": source_asset_kind,
            "asset_family": "family",
            "scenario_class": "class",
            "category": category,
            "attack_present": None,
            "attack_origin": None,
            "attack_delivery_mode": None,
            "raw_reuse_disposition": "review_required",
            "native_conversion_disposition": "eligible_for_semantic_reconstruction",
            "conversion_reason": "Safe metadata conversion.",
        }
    )


def test_render_jsonl_sorts_by_source_role_path_and_key() -> None:
    records = [
        make_record(source_project="second", source_path="z.json", source_record_key="z"),
        make_record(source_project="first", source_path="z.json", source_record_key="b"),
        make_record(source_project="first", source_path="z.json", source_record_key="a"),
        make_record(source_project="first", source_path="a.json", source_record_key="z"),
        make_record(
            source_project="first",
            source_path="taxonomy.json",
            source_record_key="taxonomy",
            record_role="attack_taxonomy",
        ),
    ]

    rendered = render_jsonl(records, source_order=("first", "second"))
    identities = [
        (row["source_project"], row["record_role"], row["source_path"], row["source_record_key"])
        for row in map(json.loads, rendered.decode().splitlines())
    ]

    assert identities == sorted(
        identities,
        key=lambda item: (
            ("first", "second").index(item[0]),
            item[1],
            item[2],
            item[3],
        ),
    )


def test_render_jsonl_uses_compact_sorted_keys_and_utf8() -> None:
    record = make_record(
        source_project="source",
        source_path="unicode.json",
        source_record_key="记录",
        category="雪",
    )

    rendered = render_jsonl((record,), source_order=("source",))
    expected = (
        json.dumps(
            record.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        + b"\n"
    )

    assert rendered == expected
    assert "雪".encode() in rendered
    assert rendered.endswith(b"\n")
    assert not rendered.endswith(b"\n\n")


def test_render_jsonl_is_byte_stable() -> None:
    records = (
        make_record(source_project="source", source_path="b.json", source_record_key="b"),
        make_record(source_project="source", source_path="a.json", source_record_key="a"),
    )

    assert render_jsonl(records, source_order=("source",)) == render_jsonl(
        records, source_order=("source",)
    )


def test_render_jsonl_rejects_unknown_or_duplicate_source_order() -> None:
    record = make_record(source_project="source", source_path="a.json", source_record_key="a")

    with pytest.raises(ValueError, match="source_order"):
        render_jsonl((record,), source_order=("other",))
    with pytest.raises(ValueError, match="duplicate"):
        render_jsonl((record,), source_order=("source", "source"))


def test_replace_outputs_transactionally_replaces_both_files(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    coverage_path = tmp_path / "coverage.yaml"
    ledger_path.write_bytes(b"old-ledger")
    coverage_path.write_bytes(b"old-coverage")
    rendered = RenderedCatalog(ledger_jsonl=b"new-ledger\n", coverage_yaml=b"new-coverage\n")

    replace_outputs_transactionally(
        rendered,
        ledger_path=ledger_path,
        coverage_path=coverage_path,
    )

    assert ledger_path.read_bytes() == rendered.ledger_jsonl
    assert coverage_path.read_bytes() == rendered.coverage_yaml
    assert set(tmp_path.iterdir()) == {ledger_path, coverage_path}


def test_second_stage_failure_propagates_and_cleans_first_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    coverage_path = tmp_path / "coverage.yaml"
    ledger_path.write_bytes(b"old-ledger")
    coverage_path.write_bytes(b"old-coverage")
    rendered = RenderedCatalog(ledger_jsonl=b"new-ledger\n", coverage_yaml=b"new-coverage\n")
    real_stage_bytes = rendering_module._stage_bytes

    def fail_coverage_stage(data: bytes, target: Path) -> Path:
        if target == coverage_path:
            raise OSError("forced second stage failure")
        return real_stage_bytes(data, target)

    monkeypatch.setattr(rendering_module, "_stage_bytes", fail_coverage_stage)

    with pytest.raises(OSError, match="forced second stage failure"):
        replace_outputs_transactionally(
            rendered,
            ledger_path=ledger_path,
            coverage_path=coverage_path,
        )

    assert ledger_path.read_bytes() == b"old-ledger"
    assert coverage_path.read_bytes() == b"old-coverage"
    assert set(tmp_path.iterdir()) == {ledger_path, coverage_path}


def test_first_replace_failure_propagates_and_cleans_temps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    coverage_path = tmp_path / "coverage.yaml"
    ledger_path.write_bytes(b"old-ledger")
    coverage_path.write_bytes(b"old-coverage")
    rendered = RenderedCatalog(ledger_jsonl=b"new-ledger\n", coverage_yaml=b"new-coverage\n")

    def fail_ledger_replace(source: Path, target: Path) -> None:
        del source
        if target == ledger_path:
            raise OSError("forced first replace failure")
        raise AssertionError("coverage replacement must not run")

    monkeypatch.setattr(rendering_module, "_replace_file", fail_ledger_replace)

    with pytest.raises(OSError, match="forced first replace failure"):
        replace_outputs_transactionally(
            rendered,
            ledger_path=ledger_path,
            coverage_path=coverage_path,
        )

    assert ledger_path.read_bytes() == b"old-ledger"
    assert coverage_path.read_bytes() == b"old-coverage"
    assert set(tmp_path.iterdir()) == {ledger_path, coverage_path}


def test_second_replace_failure_rolls_back_first_file_and_cleans_temps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    coverage_path = tmp_path / "coverage.yaml"
    ledger_path.write_bytes(b"old-ledger")
    coverage_path.write_bytes(b"old-coverage")
    rendered = RenderedCatalog(ledger_jsonl=b"new-ledger\n", coverage_yaml=b"new-coverage\n")
    real_replace = os.replace

    def fail_coverage_replace(source: Path, target: Path) -> None:
        if Path(target) == coverage_path:
            raise OSError("forced second replace failure")
        real_replace(source, target)

    monkeypatch.setattr(rendering_module, "_replace_file", fail_coverage_replace)

    with pytest.raises(OSError, match="forced"):
        replace_outputs_transactionally(
            rendered,
            ledger_path=ledger_path,
            coverage_path=coverage_path,
        )

    assert ledger_path.read_bytes() == b"old-ledger"
    assert coverage_path.read_bytes() == b"old-coverage"
    assert set(tmp_path.iterdir()) == {ledger_path, coverage_path}


def test_second_replace_failure_removes_new_first_file_when_target_was_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    coverage_path = tmp_path / "coverage.yaml"
    rendered = RenderedCatalog(ledger_jsonl=b"new-ledger\n", coverage_yaml=b"new-coverage\n")
    real_replace = os.replace

    def fail_coverage_replace(source: Path, target: Path) -> None:
        if Path(target) == coverage_path:
            raise OSError("forced second replace failure")
        real_replace(source, target)

    monkeypatch.setattr(rendering_module, "_replace_file", fail_coverage_replace)

    with pytest.raises(OSError, match="forced"):
        replace_outputs_transactionally(
            rendered,
            ledger_path=ledger_path,
            coverage_path=coverage_path,
        )

    assert not ledger_path.exists()
    assert not coverage_path.exists()
    assert list(tmp_path.iterdir()) == []
