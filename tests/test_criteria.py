import pytest

from apodix.criteria import parse_criteria


def test_parses_plain_and_checkbox_items():
    md = """
## Acceptance criteria
- R1: Orders over 100 get 10% off
- [ ] R2: Items marked "no discount" are excluded
* [x] R3. An empty promo code does nothing
"""
    found = parse_criteria(md)
    assert [c.id for c in found] == ["R1", "R2", "R3"]
    assert found[1].text == 'Items marked "no discount" are excluded'


def test_ignores_lines_without_an_id():
    assert parse_criteria("- just a note\n- R1: real one") == parse_criteria("- R1: real one")


def test_duplicate_ids_are_rejected():
    with pytest.raises(ValueError, match="R1"):
        parse_criteria("- R1: a\n- R1: b")
