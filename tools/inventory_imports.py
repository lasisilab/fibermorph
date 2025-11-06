"""Inventory top-level imports across the fibermorph package.

Run:
    python tools/inventory_imports.py
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "fibermorph"


class ImportCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.modules: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            top = alias.name.split(".")[0]
            self.modules.add(top)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not node.module:
            return
        top = node.module.split(".")[0]
        self.modules.add(top)


def collect_imports(root: Path) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for py_file in root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        rel = py_file.relative_to(PROJECT_ROOT)
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(rel))
        except SyntaxError:
            continue

        visitor = ImportCollector()
        visitor.visit(tree)
        mapping[str(rel)] = visitor.modules
    return mapping


def main() -> None:
    data = collect_imports(PACKAGE_ROOT)
    inverted: dict[str, set[str]] = {}
    for path, modules in data.items():
        for module in modules:
            inverted.setdefault(module, set()).add(path)

    print("Detected top-level imports:\n")
    for module in sorted(inverted):
        locations = ", ".join(sorted(inverted[module]))
        print(f"{module:15} -> {locations}")

    print("\nSummary:")
    for module in sorted(inverted):
        print(f"- {module}")


if __name__ == "__main__":
    main()
