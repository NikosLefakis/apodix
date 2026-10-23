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


@pytest.mark.covers("R2")
def test_no_discount_item_is_excluded():
    items = [Item("keyboard", 150), Item("gift card", 50, no_discount=True)]
    assert cart_total(items) == 185.0


@pytest.mark.covers("R2")
def test_cart_of_only_no_discount_items_pays_full_price():
    assert cart_total([Item("gift card", 150, no_discount=True)]) == 150


@pytest.mark.covers("R3")
def test_empty_code_changes_nothing():
    assert apply_promo_code(50, "") == 50


@pytest.mark.covers("R3")
def test_missing_code_changes_nothing():
    assert apply_promo_code(50, None) == 50


def test_empty_cart_is_zero():
    assert cart_total([]) == 0


def test_known_promo_code_applies():
    assert apply_promo_code(50, "SAVE5") == 45


def test_promo_codes_are_case_sensitive():
    with pytest.raises(ValueError):
        apply_promo_code(50, "save5")
