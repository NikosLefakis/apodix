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


BOOL_SOURCE = textwrap.dedent("""
    def eligible(age, member):
        return age >= 18 and member

    def either(a, b, c):
        if a or b or c:
            return 1
        return 0

    def never_called(x, y):
        return x and y
""")


def bool_mutants(executed=None):
    return [m for m in mutants_for(BOOL_SOURCE, executed) if "and" in m.description and "or" in m.description]


def test_and_and_or_are_swapped():
    by_function = {m.function: m for m in bool_mutants()}
    assert by_function["eligible"].description == "`and` became `or`"
    assert "age >= 18 or member" in by_function["eligible"].source
    assert by_function["either"].description == "`or` became `and`"
    assert "a and b and c" in by_function["either"].source
    ast.parse(by_function["eligible"].source)  # still valid Python


def test_a_chain_of_three_operands_is_one_change():
    chain = [m for m in bool_mutants() if m.function == "either"]
    assert len(chain) == 1


def test_and_or_swap_only_touches_executed_lines():
    # lines 2-3 are `eligible`; `either` and `never_called` were not run
    assert {m.function for m in bool_mutants(executed={2, 3})} == {"eligible"}
