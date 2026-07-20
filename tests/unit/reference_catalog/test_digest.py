from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from pydantic import JsonValue

from agentsec_eval.reference_catalog import digest as digest_module
from agentsec_eval.reference_catalog.digest import (
    canonical_json_digest,
    directory_manifest_digest,
    promptfoo_descriptor_digest,
    raw_file_digest,
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_canonical_json_digest_ignores_object_key_order_and_preserves_unicode() -> None:
    expected = sha256('{"a":"雪","b":2}'.encode())

    assert canonical_json_digest({"b": 2, "a": "雪"}) == expected
    assert canonical_json_digest({"a": "雪", "b": 2}) == expected


def test_raw_file_digest_hashes_original_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    content = b"\x00\xffraw\r\nbytes"
    source.write_bytes(content)

    assert raw_file_digest(source) == sha256(content)


def test_directory_manifest_digest_sorts_relative_posix_paths(tmp_path: Path) -> None:
    root = tmp_path / "task"
    (root / "nested").mkdir(parents=True)
    (root / "z.txt").write_bytes(b"last")
    (root / "nested" / "a.txt").write_bytes("雪".encode())
    manifest = (f"nested/a.txt:{sha256('雪'.encode())}\nz.txt:{sha256(b'last')}\n").encode()

    assert directory_manifest_digest(root) == sha256(manifest)


def test_directory_manifest_digest_rejects_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.write_text("secret", encoding="utf-8")
    root = tmp_path / "task"
    root.mkdir()
    (root / "escape").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        directory_manifest_digest(root)


def test_directory_manifest_digest_rejects_symlink_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "task"
    root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        directory_manifest_digest(root)


def test_directory_manifest_digest_rejects_non_regular_file(tmp_path: Path) -> None:
    root = tmp_path / "task"
    root.mkdir()
    os.mkfifo(root / "named-pipe")

    with pytest.raises(ValueError, match="regular file"):
        directory_manifest_digest(root)


def test_directory_manifest_digest_rejects_unreadable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "task"
    root.mkdir()
    source = root / "source.txt"
    source.write_text("content", encoding="utf-8")

    def deny_read(path: Path) -> bytes:
        if path == source:
            raise PermissionError("denied")
        return path.read_bytes()

    monkeypatch.setattr(digest_module, "_read_bytes", deny_read)

    with pytest.raises(ValueError, match="read"):
        directory_manifest_digest(root)


def test_directory_manifest_digest_rejects_path_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "task"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    monkeypatch.setattr(digest_module, "_iter_regular_files", lambda _root: (outside,))

    with pytest.raises(ValueError, match="escape"):
        directory_manifest_digest(root)


def test_promptfoo_descriptor_digest_excludes_project_judgments() -> None:
    source_descriptor: dict[str, JsonValue] = {
        "id": "plugin-id",
        "source_path": "src/redteam/constants/plugins.ts",
        "source_kind": "plugin",
        "native_conversion_disposition": "generator_adapter_candidate",
        "conversion_reason": "project judgment one",
        "runtime_ownership": "project",
        "requires_target_feedback": False,
        "state_scope": "none",
        "remote_inference_required": False,
        "generation_dependency": "local_only",
        "embedded_data_license_disposition": "not_applicable",
        "grader_disposition": None,
    }
    changed_judgments: dict[str, JsonValue] = {
        **source_descriptor,
        "native_conversion_disposition": "design_reference_only",
        "conversion_reason": "project judgment two",
        "runtime_ownership": "promptfoo_bound",
        "requires_target_feedback": True,
        "state_scope": "cross_run",
        "remote_inference_required": True,
        "generation_dependency": "remote_only",
        "embedded_data_license_disposition": "review_required",
        "grader_disposition": "AUXILIARY_EVIDENCE",
    }

    assert promptfoo_descriptor_digest(source_descriptor) == promptfoo_descriptor_digest(
        changed_judgments
    )
    assert promptfoo_descriptor_digest(source_descriptor) != promptfoo_descriptor_digest(
        {**source_descriptor, "id": "different-plugin"}
    )
