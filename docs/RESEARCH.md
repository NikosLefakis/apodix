# Research notes (2026-10-23)

Sources are READMEs and blog posts. Maintenance and quality of the repos were not checked.

## Ideas ruled out (already crowded)

| Idea | Existing tools |
|---|---|
| Code provenance / "why" memory | Git AI, gitwhy, commitlore, Mantra |
| Cost / runaway-loop guard | claude-cost-guard, LoopGuard, claude-budget-guard |
| Multi-agent dashboard | Agent Orchestrator, Claude Squad, Superset, Emdash |
| Skill / MCP security scanner | Snyk agent-scan, NVIDIA SkillSpector, SkillScan |
| Hallucinated package guard | pkgtruth, pkg-guard, pkgguard, ExactGround |

Hallucinated API calls (methods, kwargs, removed functions in the installed version)
are less covered, but TypeScript compilers and pyright already catch much of it.

## The gap Apodix targets

Acceptance-criteria verification for AI agents exists only as:

- protocols (proof-loop), proposals (agent-tack #56), spec tooling that checks specs not code (Spec Kit, OpenSpec),
- MCP linkers (mk-spec-master) and a commercial product (Levr),
- LLM reviewers that read the diff and rule Met / Not met per criterion.

None found that requires **executable evidence** per criterion: a passing test that
also fails when the matching code is mutated. That is Apodix's differentiator.

## Risks

- Mutation checks are hard to do reliably for non-unit-testable criteria (UI, async, external APIs).
- Scope creep: keep v0 to Python + pytest and say what is out of scope.
- Re-check the landscape before launch; this space moves fast.

## Next steps

Done (prototype): cart-discount demo where the agent claims 3/3 and Apodix reports 1/3, criteria from
markdown, mutation with a small operator set, CLI with text, Markdown and JSON output.

Next:
1. Infer links between tests and criteria instead of requiring the `covers` marker.
2. Read criteria from GitHub issues.
3. MCP tool `verify_done` so the agent runs it before saying it is finished.
4. GitHub Action that posts the Markdown report on a pull request.
5. Calibrate the 60% threshold on real projects, and skip mutants that cannot change behavior.
6. TypeScript support.

## Trials on real projects (2026-10-24)

I wrote the criteria and marked the tests myself in scratch copies, so these results show how the tool behaves,
not how good those projects' tests are.

| Project | Criteria | Result | Run time |
|---|---|---|---|
| humanize (744 tests) | ordinal, intcomma, naturalsize | 3 of 3 proven (caught 21/31, 27/41, 29/35) | 80 s |
| python-semver (511 tests) | bump major, compare order, ignore build metadata | 1 of 3 proven (caught 18/45, 48/79, 28/73) | 136 s |

What the trials found:

1. **A real bug.** Both projects are installed in editable mode, so the tests imported the original code and not the
   changed copy: every change "survived" and everything came out unproven. The demo hid this because its code sits
   next to its tests. Fixed: the changed copy goes first on the import path, and a change the tests never imported is
   reported as "could not be tested" instead of "survived" (`tests/test_installed_copy.py`).
2. **Strict pytest settings** (`filterwarnings = error`, `--strict-markers`) broke on the unknown `covers` marker.
   Fixed: Apodix registers the marker through a pytest plugin installed with the package.
3. **Noise from code that is not the point of the criterion.** Lines run at import time and shared helpers
   (translation helpers in humanize, argument checks in semver) are mutated too and mostly survive. The semver
   "unproven" verdicts are partly this, partly genuinely narrow tests (one example per criterion). The 60% threshold
   is therefore not calibrated. Next step: trace only while the tests run (not at import), and weigh changes by
   how close they are to the code the criterion is about.
4. **Cost.** 107 and 197 changes took 80 and 136 seconds on Windows with 8 workers. Fine for a release check,
   slow for every commit.
5. On Windows, `git clone` turns symlinks into text files, which broke semver's own suite until I copied the targets.
   This is an environment issue, not an Apodix one.
