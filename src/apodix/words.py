"""Split text and identifiers into comparable words (used to relate criteria to tests and functions)."""

from __future__ import annotations

import re

STOP = frozenset(
    "a an the of to and or is are be been it its in on for with by when if as at from that this these those into "
    "than then so can will should must may does do get gets has have had over under per each every any all".split()
)


def stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            word = word[: -len(suffix)]
            break
    if len(word) > 3 and word.endswith("e"):
        word = word[:-1]
    return word


def words(text: str) -> set[str]:
    """Lower-cased word stems from prose, snake_case and CamelCase. Stop words and single letters are dropped."""
    text = text.replace("_", " ")
    parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z][a-z0-9]*|[0-9]+", text)
    return {stem(p.lower()) for p in parts if p.lower() not in STOP and len(p) > 1}
