from __future__ import annotations

import ast
from pathlib import Path


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_runtime_and_schema_do_not_import_reference_catalog_or_importers() -> None:
    root = Path("src/agentsec_eval/scenario_assets")
    runtime_modules = (
        root / "__init__.py",
        root / "models.py",
        root / "validation.py",
        root / "compiler.py",
        root / "runtime.py",
    )

    for path in runtime_modules:
        imports = imported_modules(path)
        assert "agentsec_eval.reference_catalog" not in imports
        assert "agentsec_eval.scenario_assets.importers" not in imports
        assert "agentsec_eval.scenario_assets.representatives" not in imports
