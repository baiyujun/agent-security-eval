"""Deterministic source-only digest functions."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Iterator, Mapping
from pathlib import Path

from pydantic import JsonValue

_PROJECT_JUDGMENT_KEYS = frozenset(
    {
        "conversion_reason",
        "native_conversion_disposition",
        "native_output_id",
        "native_output_kind",
        "raw_reuse_disposition",
        "repo_shell_applicable",
        "mcp_applicable",
        "future_domain_only",
        "runtime_ownership",
        "reuse_classification",
        "requires_target_feedback",
        "state_scope",
        "remote_inference_required",
        "generation_dependency",
        "embedded_data_license_disposition",
        "grader_disposition",
    }
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(value: JsonValue) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_json_digest(value: JsonValue) -> str:
    """Hash one JSON value using the catalog's canonical encoding."""

    return _sha256(_canonical_json_bytes(value))


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def raw_file_digest(path: Path) -> str:
    """Hash a file's bytes without text decoding or newline conversion."""

    try:
        return _sha256(_read_bytes(path))
    except OSError as error:
        raise ValueError(f"cannot read file for digest: {path}") from error


def _walk_directory(directory: Path) -> Iterator[Path]:
    try:
        entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
    except OSError as error:
        raise ValueError(f"cannot read directory for digest: {directory}") from error

    for entry in entries:
        path = Path(entry.path)
        if entry.is_symlink():
            raise ValueError(f"directory manifest rejects symlink: {path}")
        try:
            mode = entry.stat(follow_symlinks=False).st_mode
        except OSError as error:
            raise ValueError(f"cannot inspect directory entry: {path}") from error
        if stat.S_ISDIR(mode):
            yield from _walk_directory(path)
        elif stat.S_ISREG(mode):
            yield path
        else:
            raise ValueError(f"directory manifest requires a regular file: {path}")


def _iter_regular_files(root: Path) -> tuple[Path, ...]:
    return tuple(_walk_directory(root))


def directory_manifest_digest(root: Path) -> str:
    """Hash a recursively sorted manifest of regular files beneath ``root``."""

    if root.is_symlink():
        raise ValueError(f"directory manifest rejects symlink root: {root}")
    try:
        root_mode = root.stat().st_mode
        resolved_root = root.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"cannot read directory for digest: {root}") from error
    if not stat.S_ISDIR(root_mode):
        raise ValueError(f"directory manifest root must be a directory: {root}")

    manifest = bytearray()
    for source_path in _iter_regular_files(resolved_root):
        try:
            resolved_path = source_path.resolve(strict=True)
            relative_path = resolved_path.relative_to(resolved_root)
        except (OSError, ValueError) as error:
            raise ValueError(f"directory manifest path escape: {source_path}") from error
        try:
            file_digest = _sha256(_read_bytes(resolved_path))
        except OSError as error:
            raise ValueError(f"cannot read file for directory digest: {resolved_path}") from error
        manifest.extend(f"{relative_path.as_posix()}:{file_digest}\n".encode())
    return _sha256(bytes(manifest))


def promptfoo_descriptor_digest(descriptor: Mapping[str, JsonValue]) -> str:
    """Hash Promptfoo source facts while excluding project-owned judgments."""

    source_descriptor: dict[str, JsonValue] = {
        key: value for key, value in descriptor.items() if key not in _PROJECT_JUDGMENT_KEYS
    }
    return canonical_json_digest(source_descriptor)
