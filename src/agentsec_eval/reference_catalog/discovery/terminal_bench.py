"""Safe discovery of locked Terminal-Bench 2 task directories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import ClassVar

from agentsec_eval.reference_catalog.digest import directory_manifest_digest
from agentsec_eval.reference_catalog.discovery.base import DiscoveryContext, SourceCheckout
from agentsec_eval.reference_catalog.enums import (
    NativeConversionDisposition,
    RawReuseDisposition,
    RecordRole,
    SourceAssetKind,
)
from agentsec_eval.reference_catalog.models import UpstreamLedgerRecord
from agentsec_eval.reference_catalog.validation import validate_records

_CONTROL_DIRECTORIES = frozenset({".git"})


def _safe_root(root: Path) -> Path:
    if root.is_symlink():
        raise ValueError(f"Terminal-Bench checkout must not be a symlink: {root}")
    try:
        resolved = root.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"Terminal-Bench checkout does not exist: {root}") from error
    if not resolved.is_dir():
        raise ValueError(f"Terminal-Bench checkout is not a directory: {root}")
    return resolved


@dataclass(frozen=True)
class TerminalBenchDiscoverer:
    """Discover every top-level task directory or fail before returning records."""

    source_project: ClassVar[str] = "terminal-bench-2"
    expected_total: int = 89

    def discover(self, context: DiscoveryContext) -> list[UpstreamLedgerRecord]:
        checkout = context.checkouts.get(self.source_project)
        if checkout is None:
            raise ValueError("Terminal-Bench checkout is missing from the discovery context")
        if self.expected_total < 0:
            raise ValueError("Terminal-Bench expected total must be non-negative")
        root = _safe_root(checkout.root)
        task_directories: list[tuple[str, Path]] = []
        try:
            entries = sorted(root.iterdir(), key=lambda path: path.name)
        except OSError as error:
            raise ValueError(f"cannot enumerate Terminal-Bench checkout: {root}") from error
        for entry in entries:
            if entry.is_symlink():
                raise ValueError(f"Terminal-Bench top-level task symlink is prohibited: {entry}")
            if entry.name in _CONTROL_DIRECTORIES:
                if not entry.is_dir():
                    raise ValueError(f"Terminal-Bench control path must be a directory: {entry}")
                continue
            if not entry.is_dir():
                continue
            task_toml = entry / "task.toml"
            if task_toml.is_symlink() or not task_toml.is_file():
                raise ValueError(f"Terminal-Bench task directory lacks regular task.toml: {entry}")
            task_directories.append((entry.name, entry))

        if len(task_directories) != self.expected_total:
            raise ValueError(
                f"expected {self.expected_total} Terminal-Bench tasks, "
                f"discovered {len(task_directories)}"
            )

        records = [
            self._build_record(checkout, task_name=task_name, task_root=task_root)
            for task_name, task_root in task_directories
        ]
        return list(validate_records(records, require_initial_outputs=True))

    def _build_record(
        self,
        checkout: SourceCheckout,
        *,
        task_name: str,
        task_root: Path,
    ) -> UpstreamLedgerRecord:
        source_path = PurePosixPath(task_name)
        return UpstreamLedgerRecord(
            source_project=self.source_project,
            source_repository=checkout.repository,
            source_commit=checkout.commit,
            source_path=source_path.as_posix(),
            source_record_key=task_name,
            source_record_digest=directory_manifest_digest(task_root),
            record_role=RecordRole.NORMAL_TASK_FIXTURE,
            source_asset_kind=SourceAssetKind.TERMINAL_BENCH_TASK_DIRECTORY,
            asset_family="terminal_bench_2",
            scenario_class="normal_task",
            category="normal_task",
            attack_present=False,
            attack_origin=None,
            attack_delivery_mode=None,
            raw_reuse_disposition=RawReuseDisposition.REVIEW_REQUIRED,
            native_conversion_disposition=(
                NativeConversionDisposition.ELIGIBLE_FOR_SEMANTIC_RECONSTRUCTION
            ),
            conversion_reason=(
                "Raw Terminal-Bench task content requires project-authored semantic reconstruction."
            ),
        )
