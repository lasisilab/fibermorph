"""Utility to inventory top-level imports used in the fibermorph package.

Run with:
    python tools/inventory_imports.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Dict, Set

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "fibermorph"


def collect_imports(path: Path) -> Dict[str, Set[str]]:
    modules: Dict[str, Set[str]] = {}
    for py_file in path.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(PROJECT_ROOT)
        with py_file.open("r", encoding="utf-8") as handle:
            try:
                tree = ast.parse(handle.read(), filename=str(rel_path))
            except SyntaxError:
                continue

        visitor = ImportCollector()
        visitor.visit(tree)
        modules[str(rel_path)] = visitor.modules
    return modules


class ImportCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.modules: Set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            top_level = alias.name.split(".")[0]
            self.modules.add(top_level)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            return
        top_level = node.module.split(".")[0]
        self.modules.add(top_level)


def main() -> None:
    data = collect_imports(PACKAGE_ROOT)
    unique_modules: Dict[str, Set[str]] = {}
    for file_path, modules in sorted(data.items()):
        for module in modules:
            unique_modules.setdefault(module, set()).add(file_path)

    print("Detected top-level imports:\n")
    for module in sorted(unique_modules):
        locations = ", ".join(sorted(unique_modules[module]))
        print(f"{module:15} -> {locations}")

    print("\nSummary:")
    for module in sorted(unique_modules):
        print(f"- {module}")


if __name__ == "__main__":
    sys.exit(main())
