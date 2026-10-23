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
    v.add_argument("--format", choices=("text", "md", "json"), default="text")
    v.add_argument("--no-color", action="store_true")
    v.add_argument("--quiet", action="store_true", help="do not print progress")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    if not args.project.is_dir():
        print(f"error: {args.project} is not a directory", file=sys.stderr)
        return 2

    log = (lambda _m: None) if args.quiet or args.format != "text" else (lambda m: print(m, file=sys.stderr))
    try:
        report = verify(args.project, args.criteria, args.min_score, log)
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
