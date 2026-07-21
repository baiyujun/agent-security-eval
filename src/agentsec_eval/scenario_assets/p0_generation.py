"""Deterministic generation of the single project-native P0 scenario collection."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from agentsec_eval.scenario_assets.importers import ImportResult
from agentsec_eval.scenario_assets.representatives import deterministic_pack_asset_contents
from agentsec_eval.scenario_assets.storage import serialize_executable_pack
from agentsec_eval.scenario_assets.validation import validate_pack

Sha256Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]


class P0GenerationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pack_ids: tuple[str, ...]
    source_records_processed: int
    approved_executable_count: int
    review_queue: tuple[str, ...]
    output_digest: Sha256Digest


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


class P0CanonicalAssetGenerator:
    """Materialize one canonical collection from reviewed importer candidates."""

    def generate(
        self,
        *,
        imports: Sequence[ImportResult],
        destination: Path,
    ) -> P0GenerationReport:
        validated_imports = tuple(
            ImportResult.model_validate(item.model_dump(mode="python")) for item in imports
        )
        ordered = tuple(sorted(validated_imports, key=lambda item: item.pack.pack_id))
        pack_ids = tuple(item.pack.pack_id for item in ordered)
        if len(pack_ids) != len(set(pack_ids)):
            raise ValueError("duplicate pack identity in P0 canonical collection")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"canonical collection destination already exists: {destination}")

        source_counts = Counter(item.pack.provenance[0].source_project for item in ordered)
        review_queue = tuple(
            item.pack.pack_id for item in ordered if item.review_state.status.value != "approved"
        )
        conversion_report = tuple(
            {
                "source_project": item.pack.provenance[0].source_project,
                "source_path": item.pack.provenance[0].source_path,
                "source_record_key": item.pack.provenance[0].source_record_key,
                "source_record_digest": item.pack.provenance[0].source_record_digest,
                "native_output_id": item.pack.pack_id,
                "output_digest": item.output_digest,
                "review_status": item.review_state.status.value,
                "lineage_count": len(item.field_lineage),
                "conversion_loss_count": len(item.conversion_losses),
            }
            for item in ordered
        )
        coverage = {
            "source_records_processed": len(ordered),
            "by_source_project": dict(sorted(source_counts.items())),
            "canonical_pack_count": len(ordered),
            "approved_executable_count": len(ordered) - len(review_queue),
        }
        review = {
            "review_queue": list(review_queue),
            "approved_executable_count": len(ordered) - len(review_queue),
        }
        collection_without_digest = {
            "schema_version": "1.0.0",
            "pack_ids": list(pack_ids),
            "coverage": coverage,
            "review_queue": review,
            "conversion_report": list(conversion_report),
        }
        output_digest = _canonical_digest(collection_without_digest)
        collection = {**collection_without_digest, "output_digest": output_digest}

        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent))
        try:
            packs_root = staging / "packs"
            packs_root.mkdir()
            for item in ordered:
                pack = validate_pack(item.pack)
                serialize_executable_pack(
                    pack,
                    packs_root / pack.pack_id,
                    deterministic_pack_asset_contents(pack),
                )
            _write_json(staging / "collection.json", collection)
            _write_json(staging / "coverage.json", coverage)
            _write_json(staging / "conversion-report.json", list(conversion_report))
            _write_json(staging / "review-queue.json", review)
            os.replace(staging, destination)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return P0GenerationReport(
            pack_ids=pack_ids,
            source_records_processed=len(ordered),
            approved_executable_count=len(ordered) - len(review_queue),
            review_queue=review_queue,
            output_digest=output_digest,
        )


__all__ = ["P0CanonicalAssetGenerator", "P0GenerationReport"]
