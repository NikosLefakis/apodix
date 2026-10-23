"""Run pytest in a subprocess, optionally on a mutated copy of the project."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_PACKAGE_PARENT = Path(__file__).resolve().parents[1]
_IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git", ".venv", "venv", "*.pyc")


@dataclass(frozen=True)
class RunResult:
    passed: bool
    output: str
    timed_out: bool = False


def run_pytest(project: Path, args: list[str], *, timeout: float = 60, cov_out: Path | None = None) -> RunResult:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(_PACKAGE_PARENT), env.get("PYTHONPATH")]))
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
    return RunResult(done.returncode == 0, done.stdout + done.stderr)


def run_on_mutant(project: Path, file: Path, mutated_source: str, args: list[str]) -> RunResult:
    """Copy the project to a scratch directory, swap in the mutated file, run the tests."""
    with tempfile.TemporaryDirectory(prefix="apodix-") as scratch:
        copy = Path(scratch) / "project"
        shutil.copytree(project, copy, ignore=_IGNORE)
        (copy / file.relative_to(project)).write_text(mutated_source, encoding="utf-8")
        return run_pytest(copy, args, timeout=30)


def count_tests(output: str) -> tuple[int, int]:
    """(total, passed) from pytest's -q summary line."""
    def grab(word: str) -> int:
        match = re.search(rf"(\d+) {word}", output)
        return int(match.group(1)) if match else 0

    passed = grab("passed")
    return passed + grab("failed") + grab("error"), passed
