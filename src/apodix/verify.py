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
from .mutate import Mutant, mutants_for
from .runner import MutantRunner, count_tests, run_pytest
from .words import words

PROVEN, UNPROVEN, MISSING = "proven", "unproven", "missing"
_WORKERS = min(8, os.cpu_count() or 2)


@dataclass(frozen=True)
class MutantOutcome:
    file: str
    line: int
    description: str
    killed: bool
    depth: int = 1        # 1 = in code the test calls directly, 2 = one call deeper, ...
    invalid: bool = False  # the tests never imported the changed file, so the change says nothing
    function: str = ""    # the function the change is in
    weight: float = 1.0   # how much this change counts toward the verdict (see _weight)


@dataclass
class CriterionResult:
    id: str
    text: str
    verdict: str
    reason: str
    tests: list[str] = field(default_factory=list)
    killed: int = 0
    total: int = 0
    invalid: int = 0
    score: float = 0.0    # share of the weight that the tests caught, 0..1
    sampled_from: int = 0  # when not every change was tried: how many there were
    hint: str = ""        # a suggestion for an unproven criterion, for example which function to name
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


NAME_BONUS = 3.0   # a change in a function the criterion names counts this many times more


def _weight(mutant: Mutant, wanted: set[str], explicit: bool) -> float:
    """Nearer code counts more (1 / depth). Without named functions, code whose function name shares a
    word with the criterion counts NAME_BONUS times more, since that is most likely what it is about."""
    weight = 1.0 / mutant.depth
    if not explicit and mutant.function and wanted & words(mutant.function):
        weight *= NAME_BONUS
    return weight


def _hint(outcomes: list[MutantOutcome], wanted: set[str], min_score: float) -> str:
    """For an unproven criterion: is there a function the criterion names that the tests do cover well?
    If so the low score probably comes from unrelated code, and naming that function would show it."""
    by_function: dict[str, list[int]] = {}
    for o in outcomes:
        if o.function and wanted & words(o.function):
            counts = by_function.setdefault(o.function, [0, 0])
            counts[0] += o.killed
            counts[1] += 1
    good = {f: c for f, c in by_function.items() if c[1] >= 2 and c[0] / c[1] >= min_score}
    if not good:
        return ""
    name, (caught, total) = max(good.items(), key=lambda item: (item[1][1], item[0]))
    return (f"The tests caught {caught} of {total} changes inside `{name}`, which the criterion names. "
            f"If the criterion is about that function, add [in: {name}] to it and only that code is judged.")


def _evenly(items: list, count: int) -> list:
    """`count` items spread evenly across the list, in order."""
    if count >= len(items):
        return list(items)
    if count <= 0:
        return []
    if count == 1:
        return [items[len(items) // 2]]
    picks = sorted({round(i * (len(items) - 1) / (count - 1)) for i in range(count)})
    return [items[i] for i in picks]


def _select(jobs: list, limit: int) -> list:
    """Keep every change in code the test calls directly; spread the rest over what is left of the budget."""
    if limit <= 0 or len(jobs) <= limit:
        return jobs
    shallow = [j for j in jobs if j[2].depth == 1]
    deeper = [j for j in jobs if j[2].depth > 1]
    if len(shallow) >= limit:
        return _evenly(shallow, limit)
    return shallow + _evenly(deeper, limit - len(shallow))


def _judge(
    project: Path,
    criterion: Criterion,
    tests,
    sources,
    min_score: float,
    max_depth: int | None,
    max_mutants: int,
    runner: MutantRunner,
    log,
) -> CriterionResult:
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
        raw = json.loads(cov_file.read_text(encoding="utf-8")) if cov_file.exists() else {}
    executed = {path: {int(line): depth for line, depth in lines.items()} for path, lines in raw.items()}

    jobs: list[tuple[Path, str, Mutant]] = []
    for source in sources:
        lines = executed.get(_norm(source))
        if not lines:
            continue
        rel = source.relative_to(project).as_posix()
        for mutant in mutants_for(source.read_text(encoding="utf-8"), lines, criterion.targets or None):
            if max_depth is None or mutant.depth <= max_depth:
                jobs.append((source, rel, mutant))
    jobs.sort(key=lambda j: (j[2].depth, j[1], j[2].line, j[2].index))

    total_found = len(jobs)
    jobs = _select(jobs, max_mutants)
    if len(jobs) < total_found:
        result.sampled_from = total_found

    wanted = words(criterion.text)
    explicit = bool(criterion.targets)

    def run(job):
        source, rel, mutant = job
        run_result = runner.run(source, mutant.source, nodeids)
        return MutantOutcome(rel, mutant.line, mutant.description,
                             killed=not run_result.passed and run_result.loaded,
                             depth=mutant.depth, invalid=not run_result.loaded, function=mutant.function,
                             weight=_weight(mutant, wanted, explicit))

    all_outcomes: list[MutantOutcome] = []
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:  # each job is a pytest subprocess
        for outcome in pool.map(run, jobs):
            state = "not loaded" if outcome.invalid else "caught" if outcome.killed else "survived"
            log(f"  {criterion.id}: {outcome.file} line {outcome.line}, {outcome.description}: {state}")
            all_outcomes.append(outcome)

    # A change the tests never imported says nothing either way, so it is not counted
    outcomes = [o for o in all_outcomes if not o.invalid]
    result.invalid = len(all_outcomes) - len(outcomes)
    result.total = len(outcomes)
    result.killed = sum(o.killed for o in outcomes)
    result.caught = [o for o in outcomes if o.killed]
    result.survived = sorted((o for o in outcomes if not o.killed), key=lambda o: (-o.weight, o.file, o.line))
    result.caught = sorted(result.caught, key=lambda o: (-o.weight, o.file, o.line))
    weight = sum(o.weight for o in outcomes)
    result.score = sum(o.weight for o in result.caught) / weight if weight else 0.0

    notes = ""
    if result.sampled_from:
        notes += f" Tried {len(jobs)} of {result.sampled_from} changes."
    if result.invalid:
        notes += f" {result.invalid} changes could not be tested."
    caught = f"{result.killed} ({result.score:.0%} by weight)"

    if result.total == 0 and result.invalid:
        result.verdict = UNPROVEN
        result.reason = ("Apodix could not make the tests import its changed copy of the code, so it cannot judge this. "
                         "The project probably imports its code from somewhere else, such as an install outside the project folder.")
    elif result.total == 0:
        result.verdict = UNPROVEN
        result.reason = "The tests run no project code that Apodix could break."
    elif result.killed >= 1 and result.score >= min_score - 1e-9:
        result.verdict = PROVEN
        result.reason = f"Broke the code {result.total} ways, the tests caught {caught}.{notes}"
    else:
        result.verdict = UNPROVEN
        result.reason = f"Broke the code {result.total} ways, the tests caught only {caught}.{notes}"
        if not explicit:
            result.hint = _hint(outcomes, wanted, min_score)
    return result


def verify(
    project: Path,
    criteria_file: Path | None = None,
    min_score: float = 0.6,
    log: Callable[[str], None] = lambda _msg: None,
    max_depth: int | None = None,
    max_mutants: int = 150,
) -> Report:
    project = project.resolve()
    criteria_path = (criteria_file or project / "criteria.md").resolve()
    criteria = load_criteria(criteria_path)
    tests = discover_tests(project)
    sources = source_files(project)

    log("Running the full test suite…")
    full = run_pytest(project, [])
    total, passed = count_tests(full.output)

    with MutantRunner(project, _WORKERS) as runner:
        results = [
            _judge(project, c, tests, sources, min_score, max_depth, max_mutants, runner, log)
            for c in criteria
        ]
    return Report(str(project), criteria_path.name, results, total, passed)
