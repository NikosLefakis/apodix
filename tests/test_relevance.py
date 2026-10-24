"""How much a change counts: call depth, named functions, name matching, and sampling."""

import json
from textwrap import dedent

from apodix.criteria import parse_criteria
from apodix.mutate import Mutant, mutants_for
from apodix.runner import run_pytest
from apodix.verify import NAME_BONUS, PROVEN, _select, _weight, verify
from apodix.words import words


def _mutant(depth=1, function="helper", index=0):
    return Mutant(index, 1, "x", "", depth, function)


# ---- criteria can name their functions ----------------------------------------------------------

def test_criterion_can_name_the_functions_it_is_about():
    found = parse_criteria("- R1: bumping the major version resets the rest [in: bump_major, Version.bump_major()]\n- R2: plain\n")
    assert found[0].text == "bumping the major version resets the rest"
    assert found[0].targets == ("bump_major", "Version.bump_major")
    assert found[1].targets == ()


# ---- mutation can be limited to named functions -------------------------------------------------

SOURCE = dedent("""
    class Version:
        def bump_major(self):
            return self.major + 1

        def other(self):
            return self.minor + 1

    def bump_major(v):
        return v + 1

    def untouched(v):
        return v - 1
""")


def test_only_limits_changes_to_named_functions():
    functions = {m.function for m in mutants_for(SOURCE, None, {"bump_major"})}
    assert functions == {"bump_major"}                      # both the method and the module function


def test_qualified_names_pick_one_class_member():
    mutants = mutants_for(SOURCE, None, {"Version.bump_major"})
    assert {m.function for m in mutants} == {"bump_major"}
    assert len(mutants) == 3                                # in the method only: `+` becomes `-`, 1 becomes 2, return replaced
    assert all("def bump_major(v):\n    return v + 1" in m.source for m in mutants)   # the module function is untouched


def test_without_only_every_function_is_changed():
    assert {m.function for m in mutants_for(SOURCE)} == {"bump_major", "other", "untouched"}


# ---- weights ------------------------------------------------------------------------------------

def test_nearer_code_counts_more():
    assert _weight(_mutant(depth=1), set(), False) == 1.0
    assert _weight(_mutant(depth=2), set(), False) == 0.5
    assert _weight(_mutant(depth=4), set(), False) == 0.25


def test_a_function_named_like_the_criterion_counts_more():
    wanted = words("bumping the major version")
    assert _weight(_mutant(function="bump_major"), wanted, False) == NAME_BONUS
    assert _weight(_mutant(function="_check_flags"), wanted, False) == 1.0


def test_named_functions_replace_the_name_guess():
    wanted = words("bumping the major version")
    assert _weight(_mutant(function="bump_major"), wanted, True) == 1.0


def test_sampling_keeps_all_changes_in_directly_called_code_first():
    jobs = [(None, "f.py", _mutant(1, index=i)) for i in range(6)] + [(None, "f.py", _mutant(3, index=10 + i)) for i in range(20)]
    picked = _select(jobs, 10)
    assert len(picked) == 10
    assert sum(j[2].depth == 1 for j in picked) == 6        # nothing shallow is dropped
    assert _select(jobs, 10) == picked                       # deterministic
    assert _select(jobs, 0) == jobs                          # 0 means no limit


# ---- the tracer: only the test call, with depth -------------------------------------------------

def test_tracer_ignores_import_time_code_and_records_depth(tmp_path):
    (tmp_path / "lib.py").write_text(dedent("""\
        def make():
            return 5

        VALUE = make()

        def inner(x):
            return x * 2

        def outer(x):
            return inner(x) + 1
    """))
    (tmp_path / "test_lib.py").write_text(dedent("""\
        from lib import VALUE, outer

        def test_it():
            assert VALUE == 5
            assert outer(2) == 5
    """))
    cov = tmp_path / "cov.json"
    run = run_pytest(tmp_path, ["test_lib.py"], cov_out=cov)
    assert run.passed, run.output
    lines = next(iter(json.loads(cov.read_text()).values()))

    assert "2" not in lines                                  # `return 5` ran at import, not during the test
    assert lines["10"] == 1                                  # `return inner(x) + 1`: the test calls outer directly
    assert lines["7"] == 2                                   # `return x * 2`: one call deeper


# ---- end to end: naming the function removes the noise ------------------------------------------

def _noisy_project(root, criteria):
    (root / "lib.py").write_text(dedent("""\
        def audit(x):
            if x > 100:
                return 1
            if x < -100:
                return 2
            return 0

        def target(x):
            audit(x)
            return x + 1
    """))
    (root / "test_lib.py").write_text(dedent("""\
        import pytest
        from lib import target

        @pytest.mark.covers("R1")
        def test_target():
            assert target(1) == 2
    """))
    (root / "criteria.md").write_text(criteria)


def test_naming_the_function_ignores_unrelated_code_the_test_happens_to_run(tmp_path):
    named, unnamed = tmp_path / "named", tmp_path / "unnamed"
    named.mkdir(), unnamed.mkdir()
    _noisy_project(named, "- R1: the answer goes up by one [in: target]\n")
    _noisy_project(unnamed, "- R1: the answer goes up by one\n")

    with_names = verify(named).results[0]
    without = verify(unnamed).results[0]

    assert with_names.verdict == PROVEN
    assert with_names.total < without.total                  # the `audit` changes are not counted
    assert with_names.score > without.score
    assert all(o.function == "target" for o in with_names.caught + with_names.survived)


# ---- the hint for an unproven criterion ---------------------------------------------------------

def test_unproven_criterion_hints_at_the_function_it_names(tmp_path):
    (tmp_path / "lib.py").write_text(dedent("""\
        def audit(x):
            if x > 1: return 1
            if x > 2: return 2
            if x > 3: return 3
            if x > 4: return 4
            if x > 5: return 5
            if x > 6: return 6
            return 0

        def increase(x):
            audit(x)
            return x + 1
    """))
    (tmp_path / "test_lib.py").write_text(dedent("""\
        import pytest
        from lib import increase

        @pytest.mark.covers("R1")
        def test_increase():
            assert increase(0) == 1
    """))
    (tmp_path / "criteria.md").write_text("- R1: increase the number by one\n")

    result = verify(tmp_path).results[0]

    assert result.verdict == "unproven"                       # the unrelated `audit` branches pull the score down
    assert "[in: increase]" in result.hint
    assert "increase" in result.hint and "caught 3 of 3" in result.hint


def test_no_hint_when_the_function_is_named_or_the_criterion_is_proven(tmp_path):
    _noisy_project(tmp_path, "- R1: the answer goes up by one [in: target]\n")
    assert verify(tmp_path).results[0].hint == ""
