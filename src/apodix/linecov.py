"""pytest plugin: record which lines of the project's own code the tests ran, and how close each one is.

Loaded with `-p apodix.linecov`. Reads APODIX_COV_ROOT (project directory) and writes
{file: {line: depth}} as JSON to APODIX_COV_OUT when the session ends.

Only the test call itself is traced (not collection, import or fixtures), so setup code that merely builds
the world is left alone. Depth is the number of project-code frames between the test function and the
line: 1 means the test called that function directly, 2 means a function it calls, and so on.
Code outside the project (standard library, pytest, other packages) does not count as a step.
"""

from __future__ import annotations

import json
import os
import sys
import threading

import pytest

_ROOT = os.path.normcase(os.path.realpath(os.environ.get("APODIX_COV_ROOT", "")))
_OUT = os.environ.get("APODIX_COV_OUT")

_lines: dict[str, dict[int, int]] = {}
_depth: dict[int, int] = {}          # id(frame) -> depth, for project and test frames that are alive
_kind: dict[str, str] = {}           # filename -> "test" | "project" | "other"


def _classify(filename: str) -> str:
    known = _kind.get(filename)
    if known:
        return known
    real = os.path.normcase(os.path.realpath(filename))
    base = os.path.basename(real)
    kind = "other"
    if real.startswith(_ROOT + os.sep) and real.endswith(".py") and f"{os.sep}.venv{os.sep}" not in real:
        in_tests_dir = any(part in ("tests", "test", "testing") for part in real[len(_ROOT) + 1:].split(os.sep)[:-1])
        is_test = base.startswith("test_") or base.endswith("_test.py") or base == "conftest.py" or in_tests_dir
        kind = "test" if is_test else "project"
    _kind[filename] = kind
    return kind


def _parent_depth(frame) -> int:
    parent = frame.f_back
    while parent is not None and id(parent) not in _depth:
        parent = parent.f_back
    return _depth[id(parent)] if parent is not None else 0


def _local(frame, event, arg):
    if event == "line":
        record = _lines.setdefault(frame.f_code.co_filename, {})
        depth = _depth.get(id(frame), 1)
        if depth < record.get(frame.f_lineno, 1 << 30):
            record[frame.f_lineno] = depth
    elif event == "return":
        _depth.pop(id(frame), None)
    return _local


def _local_test(frame, event, arg):
    if event == "return":
        _depth.pop(id(frame), None)
    return _local_test


def _global(frame, event, arg):
    kind = _classify(frame.f_code.co_filename)
    if kind == "test":
        _depth[id(frame)] = 0
        frame.f_trace_lines = False
        return _local_test
    if kind == "project":
        _depth[id(frame)] = _parent_depth(frame) + 1
        return _local
    return None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    previous = sys.gettrace()
    sys.settrace(_global)
    threading.settrace(_global)
    try:
        yield
    finally:
        sys.settrace(previous)
        threading.settrace(None)
        _depth.clear()


def pytest_sessionfinish(session, exitstatus):
    if _OUT:
        data = {
            os.path.normcase(os.path.realpath(f)): {str(line): depth for line, depth in lines.items()}
            for f, lines in _lines.items()
        }
        with open(_OUT, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
