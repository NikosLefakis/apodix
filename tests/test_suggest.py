import ast
from textwrap import dedent

from apodix.criteria import Criterion
from apodix.link import discover_tests
from apodix.suggest import apply_markers, collect_tests, suggest

TESTS = dedent('''\
    import pytest
    from shop import apply_discount, cart_total


    def test_discount_over_100_gets_ten_percent():
        assert apply_discount(150) == 135


    @pytest.mark.parametrize("n", [1, 2])
    def test_empty_cart_is_zero(n):
        assert cart_total([]) == 0


    def test_unrelated_thing():
        """Checks the logo renders."""
        assert True
''')


def _project(tmp_path):
    (tmp_path / "test_shop.py").write_text(TESTS)
    return tmp_path


def test_finds_the_test_whose_name_and_calls_match_the_criterion(tmp_path):
    tests = collect_tests(_project(tmp_path))
    found = suggest(Criterion("R1", "Orders over €100 get a 10% discount"), tests)
    assert found[0].name == "test_discount_over_100_gets_ten_percent"
    assert all(c.name != "test_unrelated_thing" for c in found)


def test_example_values_do_not_drown_the_real_words(tmp_path):
    tests = collect_tests(_project(tmp_path))
    found = suggest(Criterion("R2", "An empty cart totals 0, 5 and 17 items"), tests)
    assert found and found[0].name == "test_empty_cart_is_zero"


def test_nothing_related_means_no_suggestion(tmp_path):
    tests = collect_tests(_project(tmp_path))
    assert suggest(Criterion("R3", "Passwords are hashed with bcrypt"), tests) == []


def test_apply_writes_markers_that_the_linker_reads_and_keeps_the_file_valid(tmp_path):
    project = _project(tmp_path)
    changes = apply_markers(project, {
        ("test_shop.py", "test_discount_over_100_gets_ten_percent"): ["R1"],
        ("test_shop.py", "test_empty_cart_is_zero"): ["R2", "R4"],
    })

    assert len(changes) == 2
    ast.parse((project / "test_shop.py").read_text())                    # still valid Python
    marked = {t.name: t.criteria for t in discover_tests(project)}
    assert marked["test_discount_over_100_gets_ten_percent"] == ("R1",)
    assert marked["test_empty_cart_is_zero"] == ("R2", "R4")
    assert marked["test_unrelated_thing"] == ()


def test_apply_adds_the_pytest_import_when_the_file_has_none(tmp_path):
    (tmp_path / "test_x.py").write_text('"""Docs."""\nfrom __future__ import annotations\n\n\ndef test_a():\n    pass\n')
    apply_markers(tmp_path, {("test_x.py", "test_a"): ["R1"]})
    text = (tmp_path / "test_x.py").read_text()
    ast.parse(text)
    assert text.index("import pytest") > text.index("from __future__")   # after the future import, which must come first
    assert "@pytest.mark.covers(\"R1\")" in text
