from __future__ import annotations

import ast
from pathlib import Path


def test_economic_experiments_never_import_strategic_communication() -> None:
    root = Path("research/experiments/economic")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert "communication.strategic" not in imported
