from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath

import pytest

from agentsec_eval.reference_catalog.discovery.base import (
    DiscoveryContext,
    SourceCheckout,
    SourceDiscoverer,
)
from agentsec_eval.reference_catalog.models import UpstreamLedgerRecord
from agentsec_eval.reference_catalog.validation import validate_records


def make_record(**changes: object) -> UpstreamLedgerRecord:
    values: dict[str, object] = {
        "source_project": "saber",
        "source_repository": "https://github.com/ethz-spylab/saber",
        "source_commit": "a" * 40,
        "source_path": "tasks/A/info/A_info_001.json",
        "source_record_key": "A_info_001",
        "source_record_digest": "b" * 64,
        "record_role": "benchmark_scenario",
        "source_asset_kind": "saber_task",
        "asset_family": "saber",
        "scenario_class": "A",
        "category": "info",
        "attack_present": True,
        "attack_origin": "environment",
        "attack_delivery_mode": "tool_output",
        "raw_reuse_disposition": "review_required",
        "native_conversion_disposition": "eligible_for_semantic_reconstruction",
        "conversion_reason": "Reconstruct the semantics without copying source text.",
    }
    values.update(changes)
    return UpstreamLedgerRecord.model_validate(values)


def test_validate_records_returns_a_tuple_without_mutating_input() -> None:
    first = make_record()
    second = make_record(
        source_path="tasks/B/benign/B_benign_001.json",
        source_record_key="B_benign_001",
        source_record_digest="c" * 64,
    )
    records = [first, second]
    snapshot = records.copy()

    result = validate_records(records)

    assert result == (first, second)
    assert isinstance(result, tuple)
    assert records == snapshot


def test_validate_records_rejects_duplicate_identity() -> None:
    first = make_record()
    duplicate = first.model_copy(update={"source_record_digest": "c" * 64})

    with pytest.raises(ValueError, match="duplicate.*saber.*A_info_001"):
        validate_records([first, duplicate])


@pytest.mark.parametrize(
    "source_path",
    ["/host/reference/tasks/item.json", "C:/host/reference/tasks/item.json"],
)
def test_validate_records_rejects_host_absolute_paths_even_for_constructed_models(
    source_path: str,
) -> None:
    record = make_record().model_copy(update={"source_path": source_path})

    with pytest.raises(ValueError, match="relative POSIX"):
        validate_records([record])


@pytest.mark.parametrize("source_record_key", ["unsafe\nkey", "unsafe\x00key"])
def test_validate_records_rejects_unsafe_text_bearing_keys(source_record_key: str) -> None:
    record = make_record(source_record_key=source_record_key)

    with pytest.raises(ValueError, match="unsafe.*key"):
        validate_records([record])


def test_validate_records_requires_initial_native_outputs_by_default() -> None:
    converted = make_record(
        native_output_kind="scenario_asset",
        native_output_id="scenario/A_info_001",
    )

    with pytest.raises(ValueError, match="initial.*native output"):
        validate_records([converted])

    assert validate_records([converted], require_initial_outputs=False) == (converted,)


@pytest.mark.parametrize("native_output_id", ["unsafe\noutput", "unsafe\x00output"])
def test_validate_records_rejects_unsafe_native_output_ids(native_output_id: str) -> None:
    converted = make_record(
        native_output_kind="scenario_asset",
        native_output_id=native_output_id,
    )

    with pytest.raises(ValueError, match="unsafe.*native_output_id"):
        validate_records([converted], require_initial_outputs=False)


class FakeCheckout:
    source_project: str = "saber"
    repository: str = "https://github.com/ethz-spylab/saber"
    commit: str = "a" * 40
    root: Path = Path("fixtures/saber")
    audited_files: tuple[PurePosixPath, ...] = (PurePosixPath("dataset/manifest.json"),)


class FakeDiscoverer:
    source_project: str = "saber"

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]:
        assert context.repository_root == Path("repository")
        return [make_record()]


def accepts_checkout(checkout: SourceCheckout) -> None:
    assert checkout.source_project == "saber"


def accepts_discoverer(discoverer: SourceDiscoverer) -> None:
    context = DiscoveryContext(
        repository_root=Path("repository"),
        checkouts={"saber": FakeCheckout()},
    )
    assert discoverer.discover(context) == [make_record()]


def test_discovery_protocols_are_small_and_structural() -> None:
    checkouts: Mapping[str, SourceCheckout] = {"saber": FakeCheckout()}
    context = DiscoveryContext(repository_root=Path("repository"), checkouts=checkouts)

    accepts_checkout(context.checkouts["saber"])
    accepts_discoverer(FakeDiscoverer())
