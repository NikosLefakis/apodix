# Apodix

[![CI](https://github.com/NikosLefakis/apodix/actions/workflows/ci.yml/badge.svg)](https://github.com/NikosLefakis/apodix/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-2447F5.svg)](LICENSE)
[![Landing page](https://img.shields.io/badge/site-nikoslefakis.github.io%2Fapodix-101A33.svg)](https://nikoslefakis.github.io/apodix/)

> "Done" is not proof.

Apodix checks the work your AI coding agent says it finished. For every acceptance
criterion it reports one of three verdicts:

- **Proven**: the linked tests pass, and they fail when Apodix breaks the matching code on purpose.
- **Unproven**: tests exist, but they still pass when the code is broken.
- **Missing**: no test is linked to the requirement.

![Apodix checking the demo cart: 1 of 3 criteria proven, so the work is not done yet](docs/demo.svg)

**Status: working prototype.** Python + pytest only. Not published to PyPI yet.

## Try it

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e .

# an agent said "all 3 requirements done, 12 tests pass"
.venv\Scripts\apodix verify demo\cart
# -> 1 of 3 proven. Not done yet.   (exit code 1)

# the same project after the gaps were sent back and fixed
.venv\Scripts\apodix verify demo\cart_fixed
# -> 3 of 3 proven. Done.           (exit code 0)
```

Other formats: `--format md` (PR comment), `--format json`. Run the prototype's own tests with
`.venv\Scripts\python -m pytest` (about a minute, it runs the demos end to end).

## How it works

1. Reads criteria from `criteria.md` (`- R1: Orders over 100 get 10% off`).
2. Finds tests linked to each ID by a marker: `@pytest.mark.covers("R1")`.
3. Runs those tests once and records which lines of project code ran **while the tests executed** (not at import),
   and how many calls away from the test each line is.
4. Breaks those lines one small change at a time, in a scratch copy
   (`>` to `>=`, constants, conditions forced true or false, a dropped `not`, return values replaced by 0)
   and reruns the linked tests on each variant. The copy goes first on the import path, so projects installed
   in editable mode are tested on the changed code too. A change the tests never imported is reported as
   untestable, never as a survivor.
5. Scores the criterion by weight. A change in code the test calls directly counts fully, one call deeper counts
   half, and so on. A change inside a function whose name shares a word with the criterion counts three times
   more. A criterion is **proven** when at least 60% of the weight is caught (`--min-score` changes this).
   The verdict comes from running code, never from a model's opinion.

### Tell it which functions a criterion is about

By default Apodix guesses from the call depth and the function names. To remove the guesswork, name the functions
at the end of the criterion and only those are changed:

```
- R1: bumping the major version resets minor and patch [in: bump_major]
- R2: orders over 100 get 10% off [in: cart_total, Cart.total]
```

### Link tests to criteria without marking them all by hand

```powershell
.venv\Scripts\apodix suggest demo\cart                  # list likely tests per criterion (word matching, no model)
.venv\Scripts\apodix suggest . --apply --apply-min 0.5   # write the strongest markers into the test files, then review the diff
```

### Let the agent check its own work (MCP)

```bash
claude mcp add apodix -- apodix mcp
```

This gives the agent two tools: `verify_done` (runs the check and answers `DONE` or `NOT DONE YET` with the
report) and `suggest_tests`. It speaks MCP over stdio with no extra package. It is tested over the protocol with a
real server process, not yet in daily use inside Claude Code. A check can take a minute or more; lower
`max_mutants` (default 60 for the agent) if your client times out.

## Known limits

- Linking needs a marker. `apodix suggest` helps, but it is word matching: review what it writes.
- Python and pytest only. Module-level functions and methods, no visual or async checks.
- A surviving variant is not always a bug. Some changes do not alter behavior, so "unproven" means
  "nothing would notice", not "wrong". The report lists what survived, nearest code first.
- The 60% threshold and the weights are a starting point. On two real projects they behaved sensibly
  (see `docs/RESEARCH.md`), which is not the same as calibrated.
- A test that exercises a lot of unrelated code (a wide setup, a deprecation wrapper) dilutes the score. Name the
  functions with `[in: ...]` to fix that.
- Speed: every change runs the linked tests in a new process. `--max-mutants` (default 150) keeps the changes
  nearest to the tests first and spreads the rest.

## Layout

- `src/apodix/` the tool: `criteria`, `link`, `suggest`, `words`, `mutate`, `linecov`, `plugin`, `runner`, `verify`, `report`, `mcp`, `cli`
- `demo/cart/` a cart discount where the agent's "done" claim does not hold up
- `demo/cart_fixed/` the same project after the gaps were fixed
- `tests/` tests for Apodix itself
- `.github/` CI (Linux, macOS, Windows, Python 3.10 and 3.12), issue and PR templates, landing page deploy
- `docs/demo.svg` the animated demo above, rebuilt from the real output with `python tools/make_demo_svg.py`
- `site/index.html` landing page, `brand/` logo and brand guidelines, `docs/RESEARCH.md` market notes

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The one rule: the verdict must come from running code, never from a model's opinion.

## Name

*ἀπόδειξις* (apódeixis) is Greek for "proof, demonstration". Checked 2026-10-23:
`apodix` is free on npm and PyPI, `apodix.dev` shows no DNS record, `apodix.io` and
`apodix.com` are taken.

## Brand and landing page

`brand/index.html` is the brand guidelines sheet. The mark is a Reuleaux triangle (Euclid I.1
built from circles) holding the end-of-proof square. `site/` is plain HTML, CSS and JS with no build step (`site/index.html`, `css/style.css`, `js/main.js`, `assets/`). The page is in English and Greek: English lives in the HTML, Greek in `js/i18n.js`, and the EN/ΕΛ toggle remembers the choice (`?lang=el` also works). Preview it with `.venv\Scripts\python -m http.server 5173 --directory site` and open http://localhost:5173. It has
three scroll-driven moments (pinned "How it works" terminal, a construction that draws itself, a
closing square). The terminal on the page shows the real output of `apodix verify demo\cart`.
