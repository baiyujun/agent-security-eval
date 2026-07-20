"""Strict loading and read-only verification of catalog source locks."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType

import yaml

GitRunner = Callable[
    [Path, tuple[str, ...], Mapping[str, str]],
    subprocess.CompletedProcess[str],
]


@dataclass(frozen=True)
class SourceLock:
    source_project: str
    repository: str
    commit: str
    local_checkout: Path
    audited_files: tuple[PurePosixPath, ...]

    def __post_init__(self) -> None:
        if not self.source_project or self.source_project != self.source_project.strip():
            raise ValueError("source_project must be non-empty without surrounding whitespace")
        if not self.repository or self.repository != self.repository.strip():
            raise ValueError("repository must be non-empty without surrounding whitespace")
        if re.fullmatch(r"[0-9a-f]{40}", self.commit) is None:
            raise ValueError("commit must be a lowercase 40-character Git SHA")
        for audited_file in self.audited_files:
            _validate_relative_posix_path(audited_file, field_name="audited file")


@dataclass(frozen=True)
class VerifiedCheckout:
    lock: SourceLock
    root: Path

    @property
    def source_project(self) -> str:
        return self.lock.source_project

    @property
    def repository(self) -> str:
        return self.lock.repository

    @property
    def commit(self) -> str:
        return self.lock.commit

    @property
    def audited_files(self) -> tuple[PurePosixPath, ...]:
        return self.lock.audited_files


@dataclass(frozen=True)
class CatalogLocks:
    source_order: tuple[str, ...]
    sources: Mapping[str, SourceLock]

    def __post_init__(self) -> None:
        copied_sources = MappingProxyType(dict(self.sources))
        if len(set(self.source_order)) != len(self.source_order):
            raise ValueError("catalog_source_order must not contain duplicates")
        if set(self.source_order) != set(copied_sources):
            raise ValueError("catalog_source_order must exactly match loaded source keys")
        ordered_sources = {
            source_project: copied_sources[source_project] for source_project in self.source_order
        }
        object.__setattr__(self, "sources", MappingProxyType(ordered_sources))


def _read_yaml(path: Path) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"cannot load catalog lock document: {path}") from error


def _as_mapping(value: object, *, context: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{context} must be a string-keyed mapping")
    return value


def _as_sequence(value: object, *, context: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{context} must be a sequence")
    return value


def _required_text(values: Mapping[str, object], key: str, *, context: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{context}.{key} must be non-empty text")
    return value


def _optional_paths(
    values: Mapping[str, object], key: str, *, context: str
) -> tuple[PurePosixPath, ...]:
    raw_paths = values.get(key, ())
    paths = _as_sequence(raw_paths, context=f"{context}.{key}")
    result: list[PurePosixPath] = []
    for raw_path in paths:
        if not isinstance(raw_path, str):
            raise ValueError(f"{context}.{key} entries must be text")
        path = PurePosixPath(raw_path)
        _validate_relative_posix_path(path, field_name=f"{context}.{key}")
        result.append(path)
    return tuple(result)


def _source_lock_from_mapping(
    source_project: str,
    values: Mapping[str, object],
    *,
    audited_files_key: str = "audited_files",
) -> SourceLock:
    local_checkout = Path(_required_text(values, "local_checkout", context=source_project))
    return SourceLock(
        source_project=source_project,
        repository=_required_text(values, "repository", context=source_project),
        commit=_required_text(values, "commit", context=source_project),
        local_checkout=local_checkout,
        audited_files=_optional_paths(values, audited_files_key, context=source_project),
    )


def load_catalog_locks(repository_root: Path) -> CatalogLocks:
    """Merge the A/C locks with the one authoritative Promptfoo manifest entry."""

    ac_document = _as_mapping(
        _read_yaml(repository_root / "references/source-locks/ac-reference-sources.yaml"),
        context="A/C source lock",
    )
    raw_order = _as_sequence(
        ac_document.get("catalog_source_order"),
        context="catalog_source_order",
    )
    if not all(isinstance(source, str) and source for source in raw_order):
        raise ValueError("catalog_source_order entries must be non-empty text")
    source_order = tuple(source for source in raw_order if isinstance(source, str))

    raw_sources = _as_mapping(ac_document.get("sources"), context="A/C sources")
    sources: dict[str, SourceLock] = {}
    for source_project, raw_source in raw_sources.items():
        sources[source_project] = _source_lock_from_mapping(
            source_project,
            _as_mapping(raw_source, context=f"sources.{source_project}"),
        )

    manifest = _as_mapping(
        _read_yaml(repository_root / "references/manifest.yaml"),
        context="reference manifest",
    )
    raw_references = _as_sequence(manifest.get("references"), context="manifest.references")
    promptfoo_entries: list[Mapping[str, object]] = []
    for index, raw_reference in enumerate(raw_references):
        reference = _as_mapping(raw_reference, context=f"manifest.references[{index}]")
        if reference.get("name") == "promptfoo":
            promptfoo_entries.append(reference)
    if len(promptfoo_entries) != 1:
        raise ValueError("reference manifest must contain exactly one promptfoo entry")
    if "promptfoo" in sources:
        raise ValueError("Promptfoo facts must not be duplicated in the A/C source lock")
    sources["promptfoo"] = _source_lock_from_mapping(
        "promptfoo",
        promptfoo_entries[0],
        audited_files_key="license_evidence",
    )
    return CatalogLocks(source_order=source_order, sources=sources)


def _run_git(
    cwd: Path,
    args: tuple[str, ...],
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=cwd,
        env={**os.environ, **env},
        check=False,
        text=True,
        capture_output=True,
    )


def _git_output(
    run_git: GitRunner,
    cwd: Path,
    args: tuple[str, ...],
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    completed = run_git(cwd, args, {} if env is None else env)
    if completed.returncode != 0:
        raise ValueError(f"read-only Git command failed: git {' '.join(args)}")
    return completed.stdout.rstrip("\r\n")


def _optional_git_config(run_git: GitRunner, cwd: Path, key: str) -> str | None:
    args = ("config", "--get", key)
    completed = run_git(cwd, args, {})
    if completed.returncode == 1:
        return None
    if completed.returncode != 0:
        raise ValueError(f"read-only Git command failed: git {' '.join(args)}")
    return completed.stdout.strip() or None


def _normalize_remote(remote: str) -> str:
    normalized = remote.rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized.rstrip("/")


def _resolve_checkout_root(repository_root: Path, local_checkout: Path) -> Path:
    if local_checkout.is_absolute():
        raise ValueError("local_checkout must be relative")
    try:
        resolved_repository = repository_root.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"repository root does not exist: {repository_root}") from error
    workspace_root = resolved_repository.parent
    candidate = resolved_repository / local_checkout
    try:
        resolved_checkout = candidate.resolve(strict=False)
    except OSError as error:
        raise ValueError(f"cannot resolve checkout path: {candidate}") from error
    if not resolved_checkout.is_relative_to(workspace_root):
        raise ValueError(f"local_checkout path escape: {local_checkout}")
    try:
        resolved_checkout = candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"checkout does not exist: {candidate}") from error
    if not resolved_checkout.is_dir():
        raise ValueError(f"checkout is not a directory: {resolved_checkout}")
    return resolved_checkout


def verify_checkout(
    lock: SourceLock,
    *,
    repository_root: Path,
    run_git: GitRunner = _run_git,
) -> VerifiedCheckout:
    """Fail closed unless one checkout exactly matches its source lock."""

    checkout_root = _resolve_checkout_root(repository_root, lock.local_checkout)
    remote = _git_output(run_git, checkout_root, ("remote", "get-url", "origin"))
    if _normalize_remote(remote) != _normalize_remote(lock.repository):
        raise ValueError(f"wrong remote for {lock.source_project}")
    commit = _git_output(run_git, checkout_root, ("rev-parse", "HEAD"))
    if commit != lock.commit:
        raise ValueError(f"wrong commit for {lock.source_project}")
    if _git_output(run_git, checkout_root, ("status", "--porcelain")):
        raise ValueError(f"dirty checkout for {lock.source_project}")
    shallow = _git_output(
        run_git,
        checkout_root,
        ("rev-parse", "--is-shallow-repository"),
    )
    if shallow != "false":
        raise ValueError(f"shallow checkout for {lock.source_project}")

    promisor = _optional_git_config(run_git, checkout_root, "remote.origin.promisor")
    if promisor is not None:
        raise ValueError(f"promisor remote is prohibited for {lock.source_project}")
    partial_extension = _optional_git_config(run_git, checkout_root, "extensions.partialclone")
    partial_filter = _optional_git_config(
        run_git,
        checkout_root,
        "remote.origin.partialclonefilter",
    )
    if partial_extension is not None or partial_filter is not None:
        raise ValueError(f"partial clone is prohibited for {lock.source_project}")

    object_listing = _git_output(
        run_git,
        checkout_root,
        ("rev-list", "--objects", "--missing=print", "HEAD"),
        env={"GIT_NO_LAZY_FETCH": "1"},
    )
    if any(line.startswith("?") for line in object_listing.splitlines()):
        raise ValueError(f"missing object in checkout for {lock.source_project}")
    return VerifiedCheckout(lock=lock, root=checkout_root)


def verify_all_checkouts(
    locks: CatalogLocks,
    *,
    repository_root: Path,
    run_git: GitRunner = _run_git,
) -> Mapping[str, VerifiedCheckout]:
    verified = {
        source_project: verify_checkout(
            locks.sources[source_project],
            repository_root=repository_root,
            run_git=run_git,
        )
        for source_project in locks.source_order
    }
    return MappingProxyType(verified)


def _validate_relative_posix_path(path: PurePosixPath, *, field_name: str) -> None:
    if (
        path.is_absolute()
        or path == PurePosixPath(".")
        or ".." in path.parts
        or "\\" in path.as_posix()
    ):
        raise ValueError(f"{field_name} must be a safe relative POSIX path")


def resolve_source_path(checkout: VerifiedCheckout, path: PurePosixPath) -> Path:
    """Resolve an existing source path without allowing host or symlink escape."""

    _validate_relative_posix_path(path, field_name="source path")
    candidate = checkout.root.joinpath(*path.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"source path does not exist: {path}") from error
    if not resolved.is_relative_to(checkout.root.resolve(strict=True)):
        raise ValueError(f"source path symlink escape: {path}")
    return resolved
