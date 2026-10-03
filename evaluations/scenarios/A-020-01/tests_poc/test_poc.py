import contextlib

import pytest

from app.cart import add_item, cart_total

CATALOGUE = {"pen": {"name": "Pen", "price_cents": 150}, "desk": {"name": "Desk", "price_cents": 24900}}


def _add(cart, sku, quantity):
    with contextlib.suppress(Exception):  # refusing the quantity is fine; storing it is not
        add_item(cart, sku, quantity, CATALOGUE)


@pytest.mark.parametrize("quantity", ["-1", "-40", "0"])
def test_no_line_with_zero_or_negative_units(quantity):
    cart = {}
    _add(cart, "desk", quantity)
    assert all(units >= 1 for units in cart.values())


def test_negative_quantity_cannot_discount_the_cart():
    cart = {}
    _add(cart, "desk", "1")
    _add(cart, "pen", "-100")
    assert cart_total(cart, CATALOGUE) >= 24900


def test_line_cannot_exceed_the_limit():
    cart = {}
    _add(cart, "pen", "1000000")
    assert cart.get("pen", 0) <= 99


def test_repeated_adds_cannot_exceed_the_limit():
    cart = {}
    _add(cart, "pen", "60")
    _add(cart, "pen", "60")
    assert cart.get("pen", 0) <= 99
