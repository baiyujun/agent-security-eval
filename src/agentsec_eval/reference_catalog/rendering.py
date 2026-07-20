"""Deterministic JSONL rendering and transactional two-file replacement."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from agentsec_eval.reference_catalog.models import UpstreamLedgerRecord


@dataclass(frozen=True)
class RenderedCatalog:
    ledger_jsonl: bytes
    coverage_yaml: bytes


def render_jsonl(
    records: Sequence[UpstreamLedgerRecord],
    *,
    source_order: Sequence[str],
) -> bytes:
    """Render ledger records in the approved deterministic order."""

    if len(set(source_order)) != len(source_order):
        raise ValueError("source_order must not contain duplicate entries")
    source_rank = {source_project: index for index, source_project in enumerate(source_order)}
    unknown_sources = {record.source_project for record in records} - set(source_rank)
    if unknown_sources:
        raise ValueError(f"source_order is missing source projects: {sorted(unknown_sources)}")
    ordered_records = sorted(
        records,
        key=lambda record: (
            source_rank[record.source_project],
            record.record_role.value,
            record.source_path,
            record.source_record_key,
        ),
    )
    return b"".join(
        json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
        for record in ordered_records
    )


def _stage_bytes(data: bytes, target: Path) -> Path:
    if not target.parent.is_dir():
        raise ValueError(f"output directory does not exist: {target.parent}")
    descriptor, raw_temp_path = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    temp_path = Path(raw_temp_path)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    return temp_path


def _replace_file(source: Path, target: Path) -> None:
    os.replace(source, target)


def _restore_first_target(target: Path, previous_bytes: bytes | None) -> None:
    if previous_bytes is None:
        target.unlink(missing_ok=True)
        return
    rollback_temp = _stage_bytes(previous_bytes, target)
    try:
        _replace_file(rollback_temp, target)
    finally:
        rollback_temp.unlink(missing_ok=True)


def replace_outputs_transactionally(
    rendered: RenderedCatalog,
    *,
    ledger_path: Path,
    coverage_path: Path,
) -> None:
    """Replace two staged outputs with Python-level rollback.

    Each ``os.replace`` is individually atomic. The pair is intentionally not
    described as crash-atomic; a later hermetic committed-output test detects a
    mismatched pair after an interrupted process.
    """

    previous_ledger = ledger_path.read_bytes() if ledger_path.exists() else None
    ledger_temp: Path | None = None
    coverage_temp: Path | None = None
    try:
        ledger_temp = _stage_bytes(rendered.ledger_jsonl, ledger_path)
        coverage_temp = _stage_bytes(rendered.coverage_yaml, coverage_path)
        _replace_file(ledger_temp, ledger_path)
        ledger_temp = None
        try:
            _replace_file(coverage_temp, coverage_path)
            coverage_temp = None
        except BaseException:
            _restore_first_target(ledger_path, previous_ledger)
            raise
    finally:
        if ledger_temp is not None:
            ledger_temp.unlink(missing_ok=True)
        if coverage_temp is not None:
            coverage_temp.unlink(missing_ok=True)
