"""Small structural interfaces shared by source discoverers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from agentsec_eval.reference_catalog.models import UpstreamLedgerRecord


class SourceCheckout(Protocol):
    source_project: str
    repository: str
    commit: str
    root: Path
    audited_files: tuple[PurePosixPath, ...]


@dataclass(frozen=True)
class DiscoveryContext:
    repository_root: Path
    checkouts: Mapping[str, SourceCheckout]


class SourceDiscoverer(Protocol):
    source_project: str

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]: ...
