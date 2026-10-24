"""Command line: apodix verify PROJECT"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .report import render_json, render_markdown, render_text
from .verify import verify


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apodix", description="Proof that your AI agent is actually done.")
    parser.add_argument("--version", action="version", version=f"apodix {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    v = sub.add_parser("verify", help="check each acceptance criterion against the project's tests")
    v.add_argument("project", type=Path, help="project directory (contains the code, tests and criteria.md)")
    v.add_argument("--criteria", type=Path, help="criteria file (default: PROJECT/criteria.md)")
    v.add_argument("--min-score", type=float, default=0.6,
                   help="share of broken variants the tests must catch to count as proven (default: 0.6)")
    v.add_argument("--max-depth", type=int, default=None,
                   help="only break code this many calls away from the tests (1 = functions the tests call directly)")
    v.add_argument("--max-mutants", type=int, default=150,
                   help="most changes to try per criterion, nearest code first (0 = no limit, default: 150)")
    v.add_argument("--format", choices=("text", "md", "json"), default="text")
    v.add_argument("--no-color", action="store_true")
    v.add_argument("--quiet", action="store_true", help="do not print progress")

    s = sub.add_parser("suggest", help="suggest which tests probably cover which criteria")
    s.add_argument("project", type=Path)
    s.add_argument("--criteria", type=Path, help="criteria file (default: PROJECT/criteria.md)")
    s.add_argument("--top", type=int, default=5, help="most suggestions per criterion (default: 5)")
    s.add_argument("--min-score", type=float, default=0.25, help="weakest match to show, 0 to 1 (default: 0.25)")
    s.add_argument("--all", action="store_true", help="also show criteria that already have marked tests")
    s.add_argument("--apply", action="store_true",
                   help="write @pytest.mark.covers markers for the strongest matches into your test files (review the diff)")
    s.add_argument("--apply-min", type=float, default=0.5, help="weakest match --apply may write (default: 0.5)")

    sub.add_parser("mcp", help="run as an MCP server over stdio, so an agent can call verify_done")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    if args.command == "mcp":
        from .mcp import serve

        return serve()

    if args.command == "suggest":
        return _suggest(args)

    if not args.project.is_dir():
        print(f"error: {args.project} is not a directory", file=sys.stderr)
        return 2

    log = (lambda _m: None) if args.quiet or args.format != "text" else (lambda m: print(m, file=sys.stderr))
    try:
        report = verify(args.project, args.criteria, args.min_score, log, args.max_depth, args.max_mutants)
    except (ValueError, FileNotFoundError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(render_json(report))
    elif args.format == "md":
        print(render_markdown(report))
    else:
        color = sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in os.environ
        print(render_text(report, color))
    return 0 if report.done else 1


def _suggest(args) -> int:
    from .criteria import load_criteria
    from .link import discover_tests
    from .suggest import apply_markers, collect_tests, suggest

    project = args.project.resolve()
    try:
        criteria = load_criteria((args.criteria or project / "criteria.md").resolve())
    except (ValueError, FileNotFoundError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    marked = {cid for t in discover_tests(project) for cid in t.criteria}
    tests = collect_tests(project)
    to_apply: dict[tuple[str, str], list[str]] = {}
    for criterion in criteria:
        if criterion.id in marked and not args.all:
            print(f"{criterion.id}  already has marked tests, skipped (use --all to see suggestions)")
            continue
        found = suggest(criterion, tests, args.top, args.min_score)
        print(f"{criterion.id}  {criterion.text}")
        if not found:
            print("    no test looks related. Write one, or mark the right test by hand.")
        for candidate in found:
            print(f"    {candidate.score:4.0%}  {candidate.nodeid}")
            if args.apply and candidate.score >= args.apply_min and "::" not in candidate.name:
                to_apply.setdefault((candidate.file, candidate.name), []).append(criterion.id)
    print()
    if args.apply:
        changes = apply_markers(project, to_apply)
        if changes:
            print("Wrote:")
            for change in changes:
                print(f"    {change}")
        else:
            print("Nothing met --apply-min, nothing written.")
    else:
        print("These are suggestions from word matching. Review them, then mark the right tests with")
        print('@pytest.mark.covers("R1"), or run again with --apply to write the strongest matches.')
    return 0
