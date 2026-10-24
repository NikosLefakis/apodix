"""A small MCP server (stdio) so an agent can check its own work before it says it is done.

    claude mcp add apodix -- apodix mcp

Tools:
  verify_done    run Apodix on a project and return the report, with an exit-style first line
  suggest_tests  suggest which tests probably cover which criteria

It speaks JSON-RPC 2.0 over newline-delimited stdin/stdout and needs no extra package. Anything the tools print
is sent to stderr, because stdout carries only protocol messages.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

from . import __version__

SUPPORTED = ("2024-11-05", "2025-03-26", "2025-06-18")
LATEST = SUPPORTED[-1]

TOOLS = [
    {
        "name": "verify_done",
        "description": (
            "Check whether the work is really done. Reads the acceptance criteria (criteria.md), runs the tests "
            "linked to each one with @pytest.mark.covers(\"R1\"), breaks the code on purpose, and reports each "
            "criterion as proven, unproven or missing. Call it before telling the user the task is finished. "
            "If the result is not 'Done.', fix what it lists and call it again. Python and pytest only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Path to the project folder (default: current folder)."},
                "criteria": {"type": "string", "description": "Path to the criteria file (default: PROJECT/criteria.md)."},
                "max_mutants": {
                    "type": "integer",
                    "description": "Most code changes to try per criterion, nearest code first. Lower is faster (default 60).",
                },
            },
        },
    },
    {
        "name": "suggest_tests",
        "description": (
            "Suggest which existing tests probably cover each acceptance criterion, from word matching. "
            "Review the suggestions, then mark the right tests with @pytest.mark.covers(\"R1\")."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Path to the project folder (default: current folder)."},
                "criteria": {"type": "string", "description": "Path to the criteria file (default: PROJECT/criteria.md)."},
            },
        },
    },
]


def _verify_done(args: dict) -> str:
    from .report import render_text
    from .verify import verify

    project = Path(args.get("project") or ".")
    criteria = Path(args["criteria"]) if args.get("criteria") else None
    report = verify(project, criteria, max_mutants=int(args.get("max_mutants") or 60))
    headline = "DONE" if report.done else "NOT DONE YET"
    return f"{headline}\n\n{render_text(report, color=False)}"


def _suggest_tests(args: dict) -> str:
    from .criteria import load_criteria
    from .link import discover_tests
    from .suggest import collect_tests, suggest

    project = Path(args.get("project") or ".").resolve()
    criteria = load_criteria(Path(args["criteria"]) if args.get("criteria") else project / "criteria.md")
    marked = {cid for t in discover_tests(project) for cid in t.criteria}
    tests = collect_tests(project)
    out: list[str] = []
    for c in criteria:
        if c.id in marked:
            out.append(f"{c.id}  already has marked tests")
            continue
        out.append(f"{c.id}  {c.text}")
        found = suggest(c, tests)
        out += [f"    {s.score:4.0%}  {s.nodeid}" for s in found] or ["    no test looks related"]
    return "\n".join(out)


_HANDLERS = {"verify_done": _verify_done, "suggest_tests": _suggest_tests}


def handle(message: dict) -> dict | None:
    """One JSON-RPC message in, one response out (None for notifications)."""
    method = message.get("method")
    mid = message.get("id")
    params = message.get("params") or {}

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def error(code, text):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": text}}

    if mid is None:  # notification, nothing to answer
        return None
    if method == "initialize":
        asked = params.get("protocolVersion")
        return ok({
            "protocolVersion": asked if asked in SUPPORTED else LATEST,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "apodix", "version": __version__},
        })
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        handler = _HANDLERS.get(params.get("name"))
        if handler is None:
            return error(-32602, f"unknown tool: {params.get('name')}")
        try:
            with contextlib.redirect_stdout(sys.stderr):
                text = handler(params.get("arguments") or {})
            return ok({"content": [{"type": "text", "text": text}], "isError": False})
        except (ValueError, FileNotFoundError, OSError) as exc:
            return ok({"content": [{"type": "text", "text": f"error: {exc}"}], "isError": True})
    return error(-32601, f"method not found: {method}")


def serve(stdin=None, stdout=None) -> int:
    reader = stdin or io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    writer = stdout or io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n", write_through=True)
    for line in reader:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            writer.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}) + "\n")
            writer.flush()
            continue
        response = handle(message)
        if response is not None:
            writer.write(json.dumps(response, ensure_ascii=False) + "\n")
            writer.flush()
    return 0
