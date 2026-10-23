import ast
import textwrap

from apodix.mutate import mutants_for

SOURCE = textwrap.dedent("""
    LIMIT = 100
    UNUSED = 7

    def over(total):
        if total > LIMIT:
            return total - 1
        return total

    def never_called(x):
        return x + 1
""")


def descriptions(executed=None):
    return [m.description for m in mutants_for(SOURCE, executed)]


def test_every_mutant_is_valid_python_and_differs_from_the_original():
    for mutant in mutants_for(SOURCE):
        ast.parse(mutant.source)
        assert mutant.source != ast.unparse(ast.parse(SOURCE))


def test_covers_comparisons_constants_branches_and_returns():
    found = descriptions()
    assert "`>` became `>=`" in found
    assert "100 became 101" in found
    assert "condition `total > LIMIT` always false" in found
    assert "condition `total > LIMIT` always true" in found
    assert "returned value replaced by 0" in found


def test_only_executed_lines_are_changed():
    # lines 5-8 are `over`; line 11 is `never_called`
    found = descriptions(executed={5, 6, 7, 8})
    assert "`+` became `-`" not in found           # never_called was not run
    assert "100 became 101" in found                # LIMIT is read by an executed line
    assert not any("7 became 8" in d for d in found)  # UNUSED is not


def test_mutation_numbers_are_stable_between_runs():
    assert [m.index for m in mutants_for(SOURCE)] == list(range(len(mutants_for(SOURCE))))
    assert descriptions() == descriptions()
