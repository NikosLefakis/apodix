"""Render a Report as terminal text, Markdown (for a PR comment) or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict

from .verify import MISSING, PROVEN, UNPROVEN, Report

_ICON = {PROVEN: "✓", MISSING: "✗", UNPROVEN: "!"}
_LABEL = {PROVEN: "Proven", MISSING: "Missing", UNPROVEN: "Unproven"}
_ANSI = {PROVEN: "32", MISSING: "31", UNPROVEN: "33", "dim": "2", "bold": "1"}


def _paint(text: str, key: str, color: bool) -> str:
    return f"\033[{_ANSI[key]}m{text}\033[0m" if color else text


def _summary(report: Report) -> str:
    verdict = "Done." if report.done else "Not done yet."
    return f"{report.proven} of {len(report.results)} proven. {verdict}"


def render_text(report: Report, color: bool = False) -> str:
    out = [
        _paint(f"Read {len(report.results)} acceptance criteria from {report.criteria_file}", "dim", color),
    ]
    if report.tests_total == report.tests_passed:
        out.append(_paint(f"Ran {report.tests_total} tests, all passing", "dim", color))
    else:
        out.append(_paint(f"Ran {report.tests_total} tests, {report.tests_total - report.tests_passed} failing", "dim", color))
    out.append("")

    for r in report.results:
        out.append(_paint(f"{_ICON[r.verdict]} {r.id}  {r.text}", r.verdict, color))
        out.append(_paint(f"    {_LABEL[r.verdict]}. {r.reason}", "dim", color))
        if r.verdict == PROVEN and r.caught:
            c = r.caught[0]
            out.append(_paint(f"    caught: line {c.line}, {c.description}", "dim", color))
        for s in r.survived[:3]:
            out.append(_paint(f"    survived: line {s.line}, {s.description}", "dim", color))
        if len(r.survived) > 3:
            out.append(_paint(f"    …and {len(r.survived) - 3} more survived", "dim", color))
        if r.tests:
            out.append(_paint(f"    tests: {', '.join(r.tests)}", "dim", color))
    out += ["", _paint(_summary(report), "bold", color)]
    return "\n".join(out)


def render_markdown(report: Report) -> str:
    rows = ["| Criterion | Verdict | Evidence |", "|---|---|---|"]
    for r in report.results:
        evidence = r.reason
        if r.verdict == PROVEN and r.caught:
            evidence += f" Example: line {r.caught[0].line}, {r.caught[0].description}."
        elif r.survived:
            evidence += f" Survived: line {r.survived[0].line}, {r.survived[0].description}."
        rows.append(f"| **{r.id}** {r.text} | {_ICON[r.verdict]} {_LABEL[r.verdict]} | {evidence} |")
    return "\n".join([f"### Apodix: {_summary(report)}", "", *rows])


def render_json(report: Report) -> str:
    data = asdict(report)
    data["proven_count"] = report.proven
    data["done"] = report.done
    return json.dumps(data, indent=2, ensure_ascii=False)
