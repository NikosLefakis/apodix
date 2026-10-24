"""Run pytest in a subprocess, optionally on a mutated copy of the project."""

from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

_PACKAGE_PARENT = Path(__file__).resolve().parents[1]
_IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git", ".venv", "venv", "*.pyc")


@dataclass(frozen=True)
class RunResult:
    passed: bool
    output: str
    timed_out: bool = False
    loaded: bool = True  # False when the changed file was never imported by the tests


NOT_LOADED = "APODIX_NOT_LOADED"


def run_pytest(
    project: Path,
    args: list[str],
    *,
    timeout: float = 60,
    cov_out: Path | None = None,
    first_on_path: Path | None = None,
    expect_loaded: Path | None = None,
) -> RunResult:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # first_on_path wins over an installed (editable) copy of the project, so the changed code is what gets imported
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [
        str(first_on_path) if first_on_path else None, str(_PACKAGE_PARENT), env.get("PYTHONPATH"),
    ]))
    if expect_loaded is not None:
        env["APODIX_EXPECT_LOADED"] = str(expect_loaded)
    cmd = [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", *args]
    if cov_out is not None:
        cmd += ["-p", "apodix.linecov"]
        env["APODIX_COV_ROOT"] = str(project.resolve())
        env["APODIX_COV_OUT"] = str(cov_out)
    try:
        done = subprocess.run(
            cmd, cwd=project, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return RunResult(False, "timed out", True)
    output = done.stdout + done.stderr
    return RunResult(done.returncode == 0, output, loaded=NOT_LOADED not in output)


def import_root(copy: Path, file: Path) -> Path:
    """The directory that must be on sys.path for `file` to import under its package name."""
    root = file.parent
    while root != copy and (root / "__init__.py").exists():
        root = root.parent
    return root


class MutantRunner:
    """Runs the tests against changed copies of one project.

    The project is copied once per worker (not once per change). For each change the runner takes a free
    copy, swaps in the changed file, runs the tests, and puts the original file back. The copy is put first
    on the import path and the run checks that the changed file was really imported. If the project imports
    its code from elsewhere (an editable install, say), the result comes back with loaded=False instead of a
    misleading "the tests did not notice".
    """

    def __init__(self, project: Path, workers: int):
        self.project = project
        self._scratch = tempfile.TemporaryDirectory(prefix="apodix-")
        self._free: queue.Queue[Path] = queue.Queue()
        base = Path(self._scratch.name)
        for i in range(workers):
            copy = base / f"copy{i}"
            shutil.copytree(project, copy, ignore=_IGNORE)
            self._free.put(copy)
        self._originals: dict[Path, bytes] = {}
        self._lock = threading.Lock()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._scratch.cleanup()

    def _original(self, rel: Path, copy: Path) -> bytes:
        with self._lock:
            if rel not in self._originals:
                self._originals[rel] = (copy / rel).read_bytes()
            return self._originals[rel]

    def run(self, file: Path, mutated_source: str, args: list[str]) -> RunResult:
        rel = file.relative_to(self.project)
        copy = self._free.get()
        try:
            target = copy / rel
            original = self._original(rel, copy)
            target.write_text(mutated_source, encoding="utf-8")
            try:
                return run_pytest(copy, args, timeout=30, first_on_path=import_root(copy, target), expect_loaded=target)
            finally:
                target.write_bytes(original)
        finally:
            self._free.put(copy)


def count_tests(output: str) -> tuple[int, int]:
    """(total, passed) from pytest's -q summary line."""
    def grab(word: str) -> int:
        match = re.search(rf"(\d+) {word}", output)
        return int(match.group(1)) if match else 0

    passed = grab("passed")
    return passed + grab("failed") + grab("error"), passed
