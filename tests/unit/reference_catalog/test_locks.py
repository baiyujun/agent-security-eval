from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath

import pytest
import yaml

from agentsec_eval.reference_catalog import locks as locks_module
from agentsec_eval.reference_catalog.locks import (
    CatalogLocks,
    GitRunner,
    SourceLock,
    VerifiedCheckout,
    load_catalog_locks,
    resolve_source_path,
    verify_all_checkouts,
    verify_checkout,
)

SOURCE_ORDER = (
    "saber",
    "inspect-evals-codeipi",
    "terminal-bench-2",
    "mcp-safetybench",
    "mcpsecbench",
    "promptfoo",
    "harbor",
    "mcp-universe",
)


def write_lock_documents(
    repository_root: Path,
    *,
    source_order: Sequence[str] = SOURCE_ORDER,
    promptfoo_entries: int = 1,
) -> None:
    lock_path = repository_root / "references/source-locks/ac-reference-sources.yaml"
    lock_path.parent.mkdir(parents=True)
    sources = {
        source: {
            "repository": f"https://github.com/example/{source}",
            "commit": str(index) * 40,
            "local_checkout": f"../reference-sources/{source}",
            "audited_files": ["README.md"],
        }
        for index, source in enumerate(
            (name for name in SOURCE_ORDER if name != "promptfoo"),
            start=1,
        )
    }
    lock_path.write_text(
        yaml.safe_dump(
            {
                "source_lock_version": 1,
                "catalog_source_order": list(source_order),
                "sources": sources,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    references = [
        {
            "name": "promptfoo",
            "repository": "https://github.com/promptfoo/promptfoo",
            "commit": "f" * 40,
            "local_checkout": "../reference-sources/promptfoo-locked",
            "license_evidence": ["LICENSE"],
            "role": "attack candidate generator",
        }
        for _ in range(promptfoo_entries)
    ]
    references.append(
        {
            "name": "Inspect AI",
            "repository": "https://github.com/example/inspect-ai",
            "commit": "e" * 40,
        }
    )
    manifest_path = repository_root / "references/manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump({"references": references}, sort_keys=False),
        encoding="utf-8",
    )


def test_load_catalog_locks_merges_real_shapes_without_duplicating_promptfoo(
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "project"
    write_lock_documents(repository_root)

    locks = load_catalog_locks(repository_root)

    assert locks.source_order == SOURCE_ORDER
    assert tuple(locks.sources) == SOURCE_ORDER
    assert locks.sources["promptfoo"].repository == "https://github.com/promptfoo/promptfoo"
    assert locks.sources["promptfoo"].audited_files == (PurePosixPath("LICENSE"),)


@pytest.mark.parametrize(
    "source_order",
    [
        SOURCE_ORDER[:-1],
        (*SOURCE_ORDER, "extra"),
        (*SOURCE_ORDER, "saber"),
    ],
)
def test_load_catalog_locks_rejects_invalid_source_order(
    tmp_path: Path, source_order: tuple[str, ...]
) -> None:
    repository_root = tmp_path / "project"
    write_lock_documents(repository_root, source_order=source_order)

    with pytest.raises(ValueError, match="catalog_source_order"):
        load_catalog_locks(repository_root)


@pytest.mark.parametrize("promptfoo_entries", [0, 2])
def test_load_catalog_locks_requires_one_promptfoo_entry(
    tmp_path: Path, promptfoo_entries: int
) -> None:
    repository_root = tmp_path / "project"
    write_lock_documents(repository_root, promptfoo_entries=promptfoo_entries)

    with pytest.raises(ValueError, match="one promptfoo"):
        load_catalog_locks(repository_root)


def run(command: Sequence[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def make_git_checkout(tmp_path: Path) -> tuple[Path, SourceLock, Path]:
    workspace = tmp_path / "workspace"
    repository_root = workspace / "project"
    checkout = workspace / "checkout"
    repository_root.mkdir(parents=True)
    checkout.mkdir()
    run(("git", "init"), cwd=checkout)
    run(("git", "config", "user.email", "test@example.invalid"), cwd=checkout)
    run(("git", "config", "user.name", "Test User"), cwd=checkout)
    (checkout / "README.md").write_text("fixture", encoding="utf-8")
    run(("git", "add", "README.md"), cwd=checkout)
    run(("git", "commit", "-m", "fixture"), cwd=checkout)
    repository = "https://github.com/example/source"
    run(("git", "remote", "add", "origin", repository), cwd=checkout)
    commit = run(("git", "rev-parse", "HEAD"), cwd=checkout)
    lock = SourceLock(
        source_project="source",
        repository=repository,
        commit=commit,
        local_checkout=Path("../checkout"),
        audited_files=(PurePosixPath("README.md"),),
    )
    return repository_root, lock, checkout


def test_verify_checkout_accepts_clean_complete_repository(tmp_path: Path) -> None:
    repository_root, lock, checkout = make_git_checkout(tmp_path)

    verified = verify_checkout(lock, repository_root=repository_root)

    assert verified.root == checkout.resolve()
    assert verified.source_project == lock.source_project
    assert verified.repository == lock.repository
    assert verified.commit == lock.commit
    assert verified.audited_files == lock.audited_files


def test_verify_all_checkouts_preserves_source_order(tmp_path: Path) -> None:
    repository_root, lock, _checkout = make_git_checkout(tmp_path)
    locks = CatalogLocks(source_order=("source",), sources={"source": lock})

    verified = verify_all_checkouts(locks, repository_root=repository_root)

    assert tuple(verified) == ("source",)


def test_verify_checkout_rejects_missing_checkout(tmp_path: Path) -> None:
    repository_root = tmp_path / "workspace/project"
    repository_root.mkdir(parents=True)
    lock = SourceLock(
        source_project="missing",
        repository="https://github.com/example/missing",
        commit="a" * 40,
        local_checkout=Path("../missing"),
        audited_files=(),
    )

    with pytest.raises(ValueError, match="does not exist"):
        verify_checkout(lock, repository_root=repository_root)


def test_verify_checkout_rejects_dirty_checkout(tmp_path: Path) -> None:
    repository_root, lock, checkout = make_git_checkout(tmp_path)
    (checkout / "dirty.txt").write_text("dirty", encoding="utf-8")

    with pytest.raises(ValueError, match="dirty"):
        verify_checkout(lock, repository_root=repository_root)


def test_verify_checkout_rejects_wrong_commit(tmp_path: Path) -> None:
    repository_root, lock, _checkout = make_git_checkout(tmp_path)
    wrong_lock = SourceLock(
        source_project=lock.source_project,
        repository=lock.repository,
        commit="0" * 40,
        local_checkout=lock.local_checkout,
        audited_files=lock.audited_files,
    )

    with pytest.raises(ValueError, match="commit"):
        verify_checkout(wrong_lock, repository_root=repository_root)


def test_verify_checkout_rejects_wrong_remote(tmp_path: Path) -> None:
    repository_root, lock, _checkout = make_git_checkout(tmp_path)
    wrong_lock = SourceLock(
        source_project=lock.source_project,
        repository="https://github.com/example/other",
        commit=lock.commit,
        local_checkout=lock.local_checkout,
        audited_files=lock.audited_files,
    )

    with pytest.raises(ValueError, match="remote"):
        verify_checkout(wrong_lock, repository_root=repository_root)


def test_verify_checkout_does_not_trim_remote_for_comparison(tmp_path: Path) -> None:
    repository_root, lock, _checkout = make_git_checkout(tmp_path)
    runner = overriding_runner(
        ("remote", "get-url", "origin"),
        stdout=f" {lock.repository}\n",
    )

    with pytest.raises(ValueError, match="remote"):
        verify_checkout(lock, repository_root=repository_root, run_git=runner)


def overriding_runner(
    expected_args: tuple[str, ...],
    *,
    stdout: str,
    returncode: int = 0,
) -> GitRunner:
    def run_git(
        cwd: Path,
        args: tuple[str, ...],
        env: Mapping[str, str],
    ) -> subprocess.CompletedProcess[str]:
        if args == expected_args:
            return subprocess.CompletedProcess(
                args=("git", *args),
                returncode=returncode,
                stdout=stdout,
                stderr="",
            )
        return locks_module._run_git(cwd, args, env)

    return run_git


def test_verify_checkout_rejects_shallow_repository(tmp_path: Path) -> None:
    repository_root, lock, _checkout = make_git_checkout(tmp_path)
    runner = overriding_runner(("rev-parse", "--is-shallow-repository"), stdout="true\n")

    with pytest.raises(ValueError, match="shallow"):
        verify_checkout(lock, repository_root=repository_root, run_git=runner)


@pytest.mark.parametrize(
    "config_key",
    ["remote.origin.promisor", "extensions.partialclone", "remote.origin.partialclonefilter"],
)
def test_verify_checkout_rejects_promisor_and_partial_clone_configuration(
    tmp_path: Path, config_key: str
) -> None:
    repository_root, lock, _checkout = make_git_checkout(tmp_path)
    runner = overriding_runner(("config", "--get", config_key), stdout="enabled\n")

    with pytest.raises(ValueError, match="promisor|partial"):
        verify_checkout(lock, repository_root=repository_root, run_git=runner)


def test_verify_checkout_rejects_missing_objects_and_disables_lazy_fetch(tmp_path: Path) -> None:
    repository_root, lock, _checkout = make_git_checkout(tmp_path)

    def run_git(
        cwd: Path,
        args: tuple[str, ...],
        env: Mapping[str, str],
    ) -> subprocess.CompletedProcess[str]:
        if args == ("rev-list", "--objects", "--missing=print", "HEAD"):
            assert env["GIT_NO_LAZY_FETCH"] == "1"
            return subprocess.CompletedProcess(
                args=("git", *args),
                returncode=0,
                stdout="?deadbeef missing-object\n",
                stderr="",
            )
        return locks_module._run_git(cwd, args, env)

    with pytest.raises(ValueError, match="missing object"):
        verify_checkout(lock, repository_root=repository_root, run_git=run_git)


def test_verify_checkout_rejects_absolute_local_checkout(tmp_path: Path) -> None:
    repository_root, lock, checkout = make_git_checkout(tmp_path)
    absolute_lock = SourceLock(
        source_project=lock.source_project,
        repository=lock.repository,
        commit=lock.commit,
        local_checkout=checkout,
        audited_files=lock.audited_files,
    )

    with pytest.raises(ValueError, match="relative"):
        verify_checkout(absolute_lock, repository_root=repository_root)


def test_verify_checkout_rejects_parent_escape(tmp_path: Path) -> None:
    repository_root, lock, _checkout = make_git_checkout(tmp_path)
    escaped_lock = SourceLock(
        source_project=lock.source_project,
        repository=lock.repository,
        commit=lock.commit,
        local_checkout=Path("../../outside"),
        audited_files=lock.audited_files,
    )

    with pytest.raises(ValueError, match="escape"):
        verify_checkout(escaped_lock, repository_root=repository_root)


def test_verify_checkout_rejects_symlink_escape(tmp_path: Path) -> None:
    repository_root, lock, _checkout = make_git_checkout(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = repository_root.parent / "linked-checkout"
    link.symlink_to(outside, target_is_directory=True)
    linked_lock = SourceLock(
        source_project=lock.source_project,
        repository=lock.repository,
        commit=lock.commit,
        local_checkout=Path("../linked-checkout"),
        audited_files=lock.audited_files,
    )

    with pytest.raises(ValueError, match="escape"):
        verify_checkout(linked_lock, repository_root=repository_root)


@pytest.mark.parametrize("path", [PurePosixPath("/etc/passwd"), PurePosixPath("../outside")])
def test_resolve_source_path_rejects_absolute_and_parent_paths(
    tmp_path: Path, path: PurePosixPath
) -> None:
    repository_root, lock, checkout = make_git_checkout(tmp_path)
    verified = VerifiedCheckout(lock=lock, root=checkout.resolve())

    with pytest.raises(ValueError, match="relative|parent"):
        resolve_source_path(verified, path)


def test_resolve_source_path_rejects_symlink_escape(tmp_path: Path) -> None:
    repository_root, lock, checkout = make_git_checkout(tmp_path)
    del repository_root
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (checkout / "escape").symlink_to(outside)
    verified = VerifiedCheckout(lock=lock, root=checkout.resolve())

    with pytest.raises(ValueError, match="escape"):
        resolve_source_path(verified, PurePosixPath("escape"))
