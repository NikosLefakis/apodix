# Apodix

> "Done" is not proof.

Apodix checks the work your AI coding agent says it finished. For every acceptance
criterion it reports one of three verdicts:

- **Proven**: the linked tests pass, and they fail when Apodix breaks the matching code on purpose.
- **Unproven**: tests exist, but they still pass when the code is broken.
- **Missing**: no test is linked to the requirement.

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
3. Runs those tests once and records which lines of project code they executed.
4. Breaks only those lines, one small change at a time, in a scratch copy
   (`>` to `>=`, constants, conditions forced true or false, a dropped `not`, return values replaced by 0)
   and reruns the linked tests on each variant.
5. A criterion is **proven** when at least 60% of the broken variants are caught
   (`--min-score` changes this). The verdict comes from running code, never from a model's opinion.

## Known limits

- Linking is explicit. A test counts for a criterion only if you (or the agent) mark it.
- Python and pytest only. Module-level functions and methods, no visual or async checks.
- A surviving variant is not always a bug. Some changes do not alter behavior, so "unproven" means
  "nothing would notice", not "wrong". The report lists what survived so a human can judge.
- The 60% threshold is a starting point, not a calibrated number. In the fixed demo, R2 passes at exactly 6 of 10.
- Mutation changes only the code the tests executed, so a criterion whose tests never reach the
  relevant code is reported as unproven.

## Layout

- `src/apodix/` the tool: `criteria`, `link`, `mutate`, `linecov`, `runner`, `verify`, `report`, `cli`
- `demo/cart/` a cart discount where the agent's "done" claim does not hold up
- `demo/cart_fixed/` the same project after the gaps were fixed
- `tests/` tests for Apodix itself
- `site/index.html` landing page, `brand/` logo and brand guidelines, `docs/RESEARCH.md` market notes

## Name

*ἀπόδειξις* (apódeixis) is Greek for "proof, demonstration". Checked 2026-10-23:
`apodix` is free on npm and PyPI, `apodix.dev` shows no DNS record, `apodix.io` and
`apodix.com` are taken.

## Brand and landing page

`brand/index.html` is the brand guidelines sheet. The mark is a Reuleaux triangle (Euclid I.1
built from circles) holding the end-of-proof square. `site/` is plain HTML, CSS and JS with no build step (`site/index.html`, `css/style.css`, `js/main.js`, `assets/`). The page is in English and Greek: English lives in the HTML, Greek in `js/i18n.js`, and the EN/ΕΛ toggle remembers the choice (`?lang=el` also works). Preview it with `.venv\Scripts\python -m http.server 5173 --directory site` and open http://localhost:5173. It has
three scroll-driven moments (pinned "How it works" terminal, a construction that draws itself, a
closing square). The terminal on the page shows the real output of `apodix verify demo\cart`.
