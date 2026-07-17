from __future__ import annotations

import ast
from pathlib import Path


def imported_roots(package: Path) -> set[str]:
    roots: set[str] = set()
    for source_path in package.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.partition(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.partition(".")[0])
    return roots


def test_assertions_package_does_not_import_pyrit() -> None:
    package = Path("src/agentsec_eval/assertions")

    assert list(package.rglob("*.py")), "assertions package must contain Python modules"
    assert "pyrit" not in imported_roots(package)
