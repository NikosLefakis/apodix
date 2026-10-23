"""Read acceptance criteria from a markdown file.

A criterion is a list item that starts with an ID such as R1:

    - R1: Orders over 100 get 10% off
    - [ ] R2: Items marked "no discount" are excluded
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s*(?:\[[ xX]\]\s*)?(R\d+)\s*[:.)\-]\s*(.+?)\s*$")


@dataclass(frozen=True)
class Criterion:
    id: str
    text: str


def parse_criteria(markdown: str) -> list[Criterion]:
    found: list[Criterion] = []
    seen: set[str] = set()
    for line in markdown.splitlines():
        match = _LINE.match(line)
        if not match:
            continue
        cid, text = match.group(1), match.group(2)
        if cid in seen:
            raise ValueError(f"criterion {cid} appears twice")
        seen.add(cid)
        found.append(Criterion(cid, text))
    return found


def load_criteria(path: Path) -> list[Criterion]:
    criteria = parse_criteria(path.read_text(encoding="utf-8"))
    if not criteria:
        raise ValueError(f"no criteria found in {path}. Write them as '- R1: ...' list items.")
    return criteria
