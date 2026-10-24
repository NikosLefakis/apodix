# Contributing to Apodix

Thanks for helping. Apodix is a small prototype, so a good bug report is as valuable as a pull request.

## The one rule

**The verdict must come from running code, never from a model's opinion.** Anything that decides
"proven", "unproven" or "missing" has to be explainable as "these tests passed, and these broken
versions of the code made them fail". Contributions that add an LLM judge to the verdict will not be merged.
Using a model to *suggest* things (for example, which test might cover which criterion) is welcome as long as
a human or a test run confirms it.

## Set up

```bash
git clone https://github.com/NikosLefakis/apodix
cd apodix
python3 -m venv .venv            # Windows: py -3.12 -m venv .venv
.venv/bin/pip install -e .       # Windows: .venv\Scripts\python -m pip install -e .
.venv/bin/python -m pytest -q    # about a minute: it runs both demos end to end
```

Try it by hand:

```bash
.venv/bin/apodix verify demo/cart          # 1 of 3 proven, exit code 1
.venv/bin/apodix verify demo/cart_fixed    # 3 of 3 proven, exit code 0
```

## Where things live

| Path | What it does |
|---|---|
| `src/apodix/criteria.py` | reads `- R1: ...` list items from markdown, with an optional `[in: func]` naming the code it is about |
| `src/apodix/link.py` | finds tests marked `@pytest.mark.covers("R1")` |
| `src/apodix/linecov.py` | pytest plugin that records which lines ran during the tests, and how many calls deep |
| `src/apodix/plugin.py` | pytest plugin installed with Apodix: registers the `covers` marker, checks the changed code was imported |
| `src/apodix/suggest.py`, `words.py` | suggests which tests cover which criteria by word matching (no model) |
| `src/apodix/mutate.py` | makes broken versions of the executed code, one change each |
| `src/apodix/runner.py` | runs pytest in a subprocess, on a scratch copy for each broken version |
| `src/apodix/verify.py` | weighs the results (depth, function names) into one verdict per criterion |
| `src/apodix/report.py`, `cli.py` | text, Markdown and JSON output, and the `verify`, `suggest`, `mcp` commands |
| `src/apodix/mcp.py` | the MCP server (`verify_done`, `suggest_tests`) over stdio, no dependencies |
| `demo/` | the cart project before and after the gaps were fixed |
| `site/` | the landing page (plain HTML, CSS, JS; Greek strings in `js/i18n.js`) |

## Good places to start

- **A new mutation operator** in `mutate.py` (for example swapping `and` and `or`, or dropping a `return`).
  Add a test in `tests/test_mutate.py` that shows the description and that the result is valid Python.
- **Reading criteria from a GitHub issue** (checkboxes with IDs) next to the markdown reader in `criteria.py`.
- **A way to tell the tool it is wrong.** Run it on a real project, then change a weight or the matching in `verify.py` / `suggest.py` and compare
  before and after on the same project.
- **A real project to try it on.** Run Apodix on an open source Python project, mark a few tests, and open an issue
  with what you saw: slow runs, surprising verdicts, mutants that could not change behavior.

## Pull requests

1. Keep it small and say what changed and why.
2. Add or update a test. `tests/test_demo.py` shows the expected verdicts for the demos, so a change that
   moves them needs an explanation.
3. Run `python -m pytest -q` locally. CI runs the same on Linux, macOS and Windows with Python 3.10 and 3.12.
4. For the landing page, keep English in the HTML and Greek in `site/js/i18n.js` in the same change.

## Reporting a bug

Include the command you ran, the output, and the smallest project that shows the problem. A surviving
broken version is not always a bug: some changes cannot alter behavior, so say what you expected instead.

## Licence

By contributing you agree that your work is released under the MIT licence of this project.
