import pytest

from cart import Item, apply_promo_code, cart_total


@pytest.mark.covers("R1")
def test_discount_over_100():
    assert cart_total([Item("keyboard", 150)]) == 135.0


@pytest.mark.covers("R1")
def test_no_discount_at_exactly_100():
    assert cart_total([Item("mouse", 100)]) == 100


@pytest.mark.covers("R1")
def test_discount_is_rounded_to_cents():
    assert cart_total([Item("cable", 33.33)] * 4) == 119.99


@pytest.mark.covers("R3")
def test_empty_code():
    assert apply_promo_code(50, "") is not None


def test_empty_cart_is_zero():
    assert cart_total([]) == 0


def test_single_item_under_threshold():
    assert cart_total([Item("pen", 5)]) == 5


def test_several_items_under_threshold():
    assert cart_total([Item("pen", 5), Item("pad", 7)]) == 12


def test_items_are_discountable_by_default():
    assert Item("pen", 5).no_discount is False


def test_item_keeps_its_price():
    assert Item("pen", 5).price == 5


def test_known_promo_code_applies():
    assert apply_promo_code(50, "SAVE5") == 45


def test_promo_codes_are_case_sensitive():
    with pytest.raises(ValueError):
        apply_promo_code(50, "save5")


def test_total_is_a_number():
    assert isinstance(cart_total([Item("pen", 5)]), (int, float))
