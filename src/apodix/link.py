"""Find which tests claim to cover which criteria.

Tests declare it with a pytest marker, read from the source without importing it:

    @pytest.mark.covers("R1")
    def test_discount_over_100(): ...
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_SKIP_DIRS = {"__pycache__", ".venv", "venv", ".git", ".pytest_cache", "node_modules"}


@dataclass(frozen=True)
class TestCase:
    __test__ = False  # not a pytest test class

    file: str  # relative to the project, posix style
    name: str  # "test_x" or "TestClass::test_x"
    criteria: tuple[str, ...]

    @property
    def nodeid(self) -> str:
        return f"{self.file}::{self.name}"


def _walk_files(project: Path, pattern: str):
    for path in sorted(project.rglob(pattern)):
        if not any(part in _SKIP_DIRS for part in path.relative_to(project).parts):
            yield path


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _covers(func: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    ids: list[str] = []
    for deco in func.decorator_list:
        if isinstance(deco, ast.Call) and _dotted(deco.func).endswith("mark.covers"):
            ids += [a.value for a in deco.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    return tuple(ids)


def _tests_in(body: list[ast.stmt], prefix: str = ""):
    for stmt in body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name.startswith("test"):
            yield prefix + stmt.name, stmt
        elif isinstance(stmt, ast.ClassDef) and stmt.name.startswith("Test"):
            yield from _tests_in(stmt.body, f"{prefix}{stmt.name}::")


def discover_tests(project: Path) -> list[TestCase]:
    tests: list[TestCase] = []
    for path in _walk_files(project, "test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(project).as_posix()
        for name, func in _tests_in(tree.body):
            tests.append(TestCase(rel, name, _covers(func)))
    return tests


def source_files(project: Path) -> list[Path]:
    """Project code that mutation may change: every .py file that is not a test or conftest."""
    return [
        p for p in _walk_files(project, "*.py")
        if not p.name.startswith("test_") and p.name != "conftest.py"
    ]
