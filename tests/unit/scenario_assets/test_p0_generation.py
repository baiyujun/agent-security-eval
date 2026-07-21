from __future__ import annotations

from pathlib import Path

import pytest

from agentsec_eval.scenario_assets.importers import (
    ConversionConfig,
    ImportResult,
    SaberOfflineImporter,
)
from agentsec_eval.scenario_assets.p0_generation import P0CanonicalAssetGenerator
from agentsec_eval.scenario_assets.representatives import (
    make_representative_request,
)
from agentsec_eval.scenario_assets.storage import load_executable_pack

from .test_saber_batch_import import _RecordSpec, checkout, record, rights


def imported_result() -> ImportResult:
    source_record = record(_RecordSpec("A", "info_leak", "A_info_001", "tool_output", True, None))
    request = make_representative_request(
        source_record,
        checkout=checkout(),
        rights_decision=rights(source_record),
        config=ConversionConfig(importer_version="1.0.0", deterministic_seed=7),
    )
    return SaberOfflineImporter().import_record(request)


def test_p0_generator_writes_one_loadable_canonical_collection(tmp_path: Path) -> None:
    destination = tmp_path / "assets" / "scenarios"
    report = P0CanonicalAssetGenerator().generate(
        imports=(imported_result(),),
        destination=destination,
    )

    assert report.pack_ids == ("pack.case.saber.A_info_001",)
    assert report.approved_executable_count == 0
    assert report.review_queue == report.pack_ids
    assert (destination / "collection.json").is_file()
    assert (destination / "coverage.json").is_file()
    assert (destination / "conversion-report.json").is_file()
    assert (destination / "review-queue.json").is_file()
    assert (destination / "packs" / report.pack_ids[0] / "scenario.yaml").is_file()
    loaded = load_executable_pack(destination / "packs" / report.pack_ids[0])
    assert loaded.pack.pack_id == report.pack_ids[0]
    assert loaded.pack.review_state.status.value == "proposed"


def test_p0_generator_is_deterministic_and_rejects_duplicates(tmp_path: Path) -> None:
    result = imported_result()
    first = tmp_path / "first"
    second = tmp_path / "second"
    generator = P0CanonicalAssetGenerator()

    first_report = generator.generate(imports=(result,), destination=first)
    second_report = generator.generate(imports=(result,), destination=second)

    assert first_report.output_digest == second_report.output_digest
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
    with pytest.raises(ValueError, match="duplicate pack"):
        generator.generate(imports=(result, result), destination=tmp_path / "duplicate")
