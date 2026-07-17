"""Cross-record validation for upstream ledger records."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import TypeAdapter, ValidationError

from agentsec_eval.reference_catalog.models import RelativePosixPath, UpstreamLedgerRecord

_RELATIVE_PATH_ADAPTER = TypeAdapter(RelativePosixPath)


def _reject_unsafe_key(value: str, *, field_name: str) -> None:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"unsafe {field_name}: control characters are prohibited")


def validate_records(
    records: Sequence[UpstreamLedgerRecord],
    *,
    require_initial_outputs: bool = True,
) -> tuple[UpstreamLedgerRecord, ...]:
    """Validate ledger-wide invariants without mutating or reordering records."""

    validated = tuple(records)
    identities: set[tuple[str, str, str]] = set()
    for record in validated:
        try:
            _RELATIVE_PATH_ADAPTER.validate_python(record.source_path)
        except ValidationError as error:
            raise ValueError(
                f"source_path must be a relative POSIX path: {record.source_path!r}"
            ) from error

        _reject_unsafe_key(record.source_record_key, field_name="text-bearing key")
        if record.native_output_id is not None:
            _reject_unsafe_key(record.native_output_id, field_name="native_output_id")
        if require_initial_outputs and (
            record.native_output_kind is not None or record.native_output_id is not None
        ):
            raise ValueError("initial ledger records must not contain a native output")

        identity = (record.source_project, record.source_path, record.source_record_key)
        if identity in identities:
            raise ValueError(
                "duplicate ledger identity: "
                f"{record.source_project}/{record.source_path}/{record.source_record_key}"
            )
        identities.add(identity)

    return validated
