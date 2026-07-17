from __future__ import annotations

import ast
from pathlib import Path


def imports_pyrit(source_path: Path) -> bool:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            alias.name.partition(".")[0] == "pyrit" for alias in node.names
        ):
            return True
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.partition(".")[0] == "pyrit":
                return True
    return False


def test_only_pyrit_integration_package_imports_pyrit() -> None:
    source_root = Path("src/agentsec_eval")
    allowed_root = source_root / "integrations" / "pyrit"
    importing_paths = {
        path.relative_to(source_root) for path in source_root.rglob("*.py") if imports_pyrit(path)
    }

    assert importing_paths
    assert all((source_root / path).is_relative_to(allowed_root) for path in importing_paths)
