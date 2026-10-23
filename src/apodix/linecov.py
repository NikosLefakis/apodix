"""Tiny pytest plugin: record which lines of the project's own code the tests ran.

Loaded with `-p apodix.linecov`. Reads APODIX_COV_ROOT (project directory) and
writes {file: [lines]} as JSON to APODIX_COV_OUT when the session ends.
"""

from __future__ import annotations

import json
import os
import sys
import threading

_ROOT = os.path.normcase(os.path.realpath(os.environ.get("APODIX_COV_ROOT", "")))
_OUT = os.environ.get("APODIX_COV_OUT")
_executed: dict[str, set[int]] = {}
_relevant: dict[str, bool] = {}


def _is_project_code(filename: str) -> bool:
    cached = _relevant.get(filename)
    if cached is not None:
        return cached
    real = os.path.normcase(os.path.realpath(filename))
    base = os.path.basename(real)
    ok = (
        real.startswith(_ROOT + os.sep)
        and real.endswith(".py")
        and not base.startswith("test_")
        and base != "conftest.py"
        and f"{os.sep}.venv{os.sep}" not in real
    )
    _relevant[filename] = ok
    return ok


def _local(frame, event, arg):
    if event == "line":
        lines = _executed.setdefault(frame.f_code.co_filename, set())
        lines.add(frame.f_lineno)
    return _local


def _global(frame, event, arg):
    if _is_project_code(frame.f_code.co_filename):
        _executed.setdefault(frame.f_code.co_filename, set()).add(frame.f_lineno)
        return _local
    return None


def pytest_sessionstart(session):
    sys.settrace(_global)
    threading.settrace(_global)


def pytest_sessionfinish(session, exitstatus):
    sys.settrace(None)
    if _OUT:
        data = {os.path.normcase(os.path.realpath(f)): sorted(lines) for f, lines in _executed.items()}
        with open(_OUT, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
