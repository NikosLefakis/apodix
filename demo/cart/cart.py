"""Cart totals. Written by an AI agent for issue #142."""

from dataclasses import dataclass

DISCOUNT_THRESHOLD = 100
DISCOUNT_RATE = 0.10
PROMO_CODES = {"SAVE5": 5}


@dataclass(frozen=True)
class Item:
    name: str
    price: float
    no_discount: bool = False


def cart_total(items):
    subtotal = sum(item.price for item in items)
    if subtotal > DISCOUNT_THRESHOLD:
        return round(subtotal * (1 - DISCOUNT_RATE), 2)
    return subtotal


def apply_promo_code(total, code):
    if not code:
        return total
    if code not in PROMO_CODES:
        raise ValueError(f"unknown promo code: {code}")
    return total - PROMO_CODES[code]
