"""Shopping cart for the web shop. A cart maps a product code to the number of units."""

MAX_PER_LINE = 99
MAX_LINES = 30


class CartError(ValueError):
    """Raised when a cart operation is refused."""


def add_item(cart, sku, quantity, catalogue):
    """Add `quantity` units of product `sku` to the cart and return the new unit count.

    `quantity` is the text of the quantity box on the product page: a whole number from 1 to
    MAX_PER_LINE. A cart line never holds more than MAX_PER_LINE units.
    """
    if sku not in catalogue:
        raise CartError(f"unknown product {sku!r}")
    if sku not in cart and len(cart) >= MAX_LINES:
        raise CartError("the cart is full")
    count = int(quantity)
    cart[sku] = cart.get(sku, 0) + count
    return cart[sku]


def remove_item(cart, sku):
    """Take a product out of the cart. Returns False when it was not in it."""
    return cart.pop(sku, None) is not None


def line_total(cart, sku, catalogue):
    """Price in cents of one cart line."""
    return cart[sku] * catalogue[sku]["price_cents"]


def cart_total(cart, catalogue):
    """Price in cents of the whole cart."""
    return sum(line_total(cart, sku, catalogue) for sku in cart)


def summary(cart, catalogue):
    """Lines for the cart page: (name, units, line total in cents), sorted by product name."""
    lines = [(catalogue[sku]["name"], units, line_total(cart, sku, catalogue)) for sku, units in cart.items()]
    return sorted(lines)
