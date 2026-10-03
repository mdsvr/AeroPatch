import pytest

from app.cart import CartError, add_item, cart_total, line_total, remove_item, summary

CATALOGUE = {
    "pen": {"name": "Pen", "price_cents": 150},
    "desk": {"name": "Desk", "price_cents": 24900},
    "lamp": {"name": "Lamp", "price_cents": 3200},
}


def test_adding_units_accumulates():
    cart = {}
    assert add_item(cart, "pen", "3", CATALOGUE) == 3
    assert add_item(cart, "pen", 2, CATALOGUE) == 5
    assert add_item(cart, "desk", "1", CATALOGUE) == 1
    assert cart == {"pen": 5, "desk": 1}


def test_limits_can_be_reached_exactly():
    cart = {}
    assert add_item(cart, "pen", "99", CATALOGUE) == 99
    assert add_item(cart, "lamp", "98", CATALOGUE) == 98
    assert add_item(cart, "lamp", "1", CATALOGUE) == 99


def test_unknown_product_and_non_numbers_are_refused():
    cart = {}
    with pytest.raises(CartError):
        add_item(cart, "sofa", "1", CATALOGUE)
    for bad in ("two", "", "1.5", None):
        with pytest.raises((ValueError, TypeError)):
            add_item(cart, "pen", bad, CATALOGUE)
    assert cart == {}


def test_full_cart_refuses_new_lines_but_not_existing_ones():
    catalogue = {f"sku{i}": {"name": f"Item {i}", "price_cents": 100} for i in range(31)}
    cart = {}
    for i in range(30):
        add_item(cart, f"sku{i}", "1", catalogue)
    with pytest.raises(CartError):
        add_item(cart, "sku30", "1", catalogue)
    assert add_item(cart, "sku0", "1", catalogue) == 2


def test_totals_summary_and_remove():
    cart = {}
    add_item(cart, "pen", "4", CATALOGUE)
    add_item(cart, "desk", "1", CATALOGUE)
    assert line_total(cart, "pen", CATALOGUE) == 600
    assert cart_total(cart, CATALOGUE) == 25500
    assert summary(cart, CATALOGUE) == [("Desk", 1, 24900), ("Pen", 4, 600)]
    assert remove_item(cart, "pen") is True
    assert remove_item(cart, "pen") is False
    assert cart_total(cart, CATALOGUE) == 24900
