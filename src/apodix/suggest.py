"""Suggest which tests probably cover which criteria, so nobody has to mark every test by hand.

This is plain word matching, no model: the words of a criterion are compared with the words in a test's name,
in the names of the functions it calls, in its docstring and in its short string literals. Words that appear in
many tests count less. The output is a list of suggestions to review. A wrong marker would make a criterion look
proven, so nothing is written to your files unless you pass --apply.
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from pathlib import Path

from .criteria import Criterion
from .link import _tests_in, _walk_files
from .words import words as _words

_WEIGHTS = {"calls": 2.5, "name": 2.0, "doc": 1.0, "text": 0.5}


@dataclass
class Candidate:
    file: str
    name: str
    score: float
    words: dict[str, float] = field(repr=False, default_factory=dict)
    line: int = 0

    @property
    def nodeid(self) -> str:
        return f"{self.file}::{self.name}"


def _test_words(func: ast.AST) -> dict[str, float]:
    found: dict[str, float] = {}

    def add(words: set[str], kind: str) -> None:
        for w in words:
            found[w] = max(found.get(w, 0.0), _WEIGHTS[kind])

    add(_words(func.name), "name")
    add(_words(ast.get_docstring(func) or ""), "doc")
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Name):
                add(_words(target.id), "calls")
            elif isinstance(target, ast.Attribute):
                add(_words(target.attr), "calls")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) <= 40:
            add(_words(node.value), "text")
    return found


def collect_tests(project: Path) -> list[Candidate]:
    tests: list[Candidate] = []
    for path in _walk_files(project, "test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(project).as_posix()
        for name, func in _tests_in(tree.body):
            tests.append(Candidate(rel, name, 0.0, _test_words(func), func.lineno))
    return tests


def suggest(criterion: Criterion, tests: list[Candidate], top: int = 5, min_score: float = 0.25) -> list[Candidate]:
    wanted = {w for w in _words(criterion.text) if not w.isdigit()}
    if not wanted or not tests:
        return []
    n = len(tests)
    df = {w: sum(w in t.words for t in tests) for w in wanted}
    wanted = {w for w in wanted if df[w] > 0}  # a word no test mentions cannot point to a test (often an example value)
    if not wanted:
        return []
    idf = {w: math.log(1 + n / (1 + df[w])) for w in wanted}
    total = sum(idf.values())
    ranked: list[Candidate] = []
    for t in tests:
        hit = sum(idf[w] * min(t.words.get(w, 0.0), 2.5) / 2.5 for w in wanted)
        score = hit / total if total else 0.0
        if score >= min_score:
            ranked.append(Candidate(t.file, t.name, score, t.words, t.line))
    ranked.sort(key=lambda c: (-c.score, c.file, c.name))
    return ranked[:top]


def apply_markers(project: Path, ids_by_test: dict[tuple[str, str], list[str]]) -> list[str]:
    """Insert @pytest.mark.covers(...) above top-level tests. Returns a line per change made."""
    changes: list[str] = []
    by_file: dict[str, dict[str, list[str]]] = {}
    for (file, name), ids in ids_by_test.items():
        by_file.setdefault(file, {})[name] = ids

    for file, tests in by_file.items():
        path = project / file
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        tree = ast.parse(text)
        edits: list[tuple[int, str]] = []
        for name, func in _tests_in(tree.body):
            if name in tests and "::" not in name:
                first = min([func.lineno] + [d.lineno for d in func.decorator_list])
                ids = ", ".join(f'"{i}"' for i in tests[name])
                edits.append((first, f"@pytest.mark.covers({ids})\n"))
                changes.append(f"{file}::{name}  @pytest.mark.covers({ids})")
        for line_no, marker in sorted(edits, reverse=True):
            lines.insert(line_no - 1, marker)
        new_text = "".join(lines)
        if "import pytest" not in new_text:
            insert_at = 0
            body = ast.parse(text).body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                insert_at = body[0].end_lineno
            for stmt in body[1 if insert_at else 0:]:
                if isinstance(stmt, ast.ImportFrom) and stmt.module == "__future__":
                    insert_at = stmt.end_lineno
                else:
                    break
            lines = new_text.splitlines(keepends=True)
            lines.insert(insert_at, "import pytest\n")
            new_text = "".join(lines)
        path.write_text(new_text, encoding="utf-8")
    return changes
