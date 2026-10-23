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
