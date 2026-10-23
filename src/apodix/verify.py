"""Give every acceptance criterion one verdict: proven, unproven or missing."""

from __future__ import annotations

import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .criteria import Criterion, load_criteria
from .link import discover_tests, source_files
from .mutate import mutants_for
from .runner import count_tests, run_on_mutant, run_pytest

PROVEN, UNPROVEN, MISSING = "proven", "unproven", "missing"
_WORKERS = min(8, os.cpu_count() or 2)


@dataclass(frozen=True)
class MutantOutcome:
    file: str
    line: int
    description: str
    killed: bool


@dataclass
class CriterionResult:
    id: str
    text: str
    verdict: str
    reason: str
    tests: list[str] = field(default_factory=list)
    killed: int = 0
    total: int = 0
    caught: list[MutantOutcome] = field(default_factory=list)
    survived: list[MutantOutcome] = field(default_factory=list)


@dataclass
class Report:
    project: str
    criteria_file: str
    results: list[CriterionResult]
    tests_total: int
    tests_passed: int

    @property
    def proven(self) -> int:
        return sum(r.verdict == PROVEN for r in self.results)

    @property
    def done(self) -> bool:
        return self.proven == len(self.results) and self.tests_passed == self.tests_total


def _norm(path: Path | str) -> str:
    return os.path.normcase(os.path.realpath(path))


def _judge(project: Path, criterion: Criterion, tests, sources, min_score: float, log) -> CriterionResult:
    linked = [t for t in tests if criterion.id in t.criteria]
    result = CriterionResult(criterion.id, criterion.text, MISSING, "", [t.name for t in linked])
    if not linked:
        result.reason = f'No test is marked @pytest.mark.covers("{criterion.id}").'
        return result

    nodeids = [t.nodeid for t in linked]
    with tempfile.TemporaryDirectory(prefix="apodix-cov-") as scratch:
        cov_file = Path(scratch) / "cov.json"
        baseline = run_pytest(project, nodeids, cov_out=cov_file)
        if not baseline.passed:
            result.verdict = UNPROVEN
            result.reason = "The linked tests fail on the current code."
            return result
        executed = json.loads(cov_file.read_text(encoding="utf-8")) if cov_file.exists() else {}

    jobs = []
    for source in sources:
        lines = executed.get(_norm(source))
        if not lines:
            continue
        rel = source.relative_to(project).as_posix()
        for mutant in mutants_for(source.read_text(encoding="utf-8"), set(lines)):
            jobs.append((source, rel, mutant))

    def run(job):
        source, rel, mutant = job
        passed = run_on_mutant(project, source, mutant.source, nodeids).passed
        return MutantOutcome(rel, mutant.line, mutant.description, killed=not passed)

    outcomes: list[MutantOutcome] = []
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:  # each job is a pytest subprocess
        for outcome in pool.map(run, jobs):
            log(f"  {criterion.id}: {outcome.file} line {outcome.line}, {outcome.description}: "
                f"{'caught' if outcome.killed else 'survived'}")
            outcomes.append(outcome)

    result.total = len(outcomes)
    result.killed = sum(o.killed for o in outcomes)
    result.caught = [o for o in outcomes if o.killed]
    result.survived = [o for o in outcomes if not o.killed]

    if result.total == 0:
        result.verdict = UNPROVEN
        result.reason = "The tests run no project code that Apodix could break."
    elif result.killed >= 1 and result.killed / result.total >= min_score:
        result.verdict = PROVEN
        result.reason = f"Broke the code {result.total} ways, the tests caught {result.killed}."
    else:
        result.verdict = UNPROVEN
        result.reason = f"Broke the code {result.total} ways, the tests caught only {result.killed}."
    return result


def verify(
    project: Path,
    criteria_file: Path | None = None,
    min_score: float = 0.6,
    log: Callable[[str], None] = lambda _msg: None,
) -> Report:
    project = project.resolve()
    criteria_path = (criteria_file or project / "criteria.md").resolve()
    criteria = load_criteria(criteria_path)
    tests = discover_tests(project)
    sources = source_files(project)

    log("Running the full test suite…")
    full = run_pytest(project, [])
    total, passed = count_tests(full.output)

    results = [_judge(project, c, tests, sources, min_score, log) for c in criteria]
    return Report(str(project), criteria_path.name, results, total, passed)
