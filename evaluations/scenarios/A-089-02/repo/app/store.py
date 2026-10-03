"""Product catalogue backed by SQLite."""

import sqlite3

from app.filters import build_filter, order_clause

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    supplier TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0)
)
"""
MAX_PAGE = 100


def connect(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    return conn


def add_product(conn, name, category, supplier, price_cents):
    """Insert a product and return its id."""
    cur = conn.execute(
        "INSERT INTO products (name, category, supplier, price_cents) VALUES (?, ?, ?, ?)",
        (name, category, supplier, price_cents),
    )
    conn.commit()
    return cur.lastrowid


def get_product(conn, product_id):
    """Return the row (id, name, category, supplier, price_cents) of one product, or None."""
    cur = conn.execute(
        "SELECT id, name, category, supplier, price_cents FROM products WHERE id = ?", (product_id,)
    )
    return cur.fetchone()


def update_price(conn, product_id, price_cents):
    """Set a product's price. Returns True when the product exists."""
    if price_cents < 0:
        raise ValueError("price cannot be negative")
    cur = conn.execute("UPDATE products SET price_cents = ? WHERE id = ?", (price_cents, product_id))
    conn.commit()
    return cur.rowcount == 1


def delete_product(conn, product_id):
    """Remove a product. Returns True when a row was deleted."""
    cur = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    return cur.rowcount == 1


def search_products(conn, sort="name", limit=20, **criteria):
    """Return the products matching every criterion (see filters.FILTERABLE), sorted and capped.

    The criteria values come straight from the query string of the catalogue page.
    """
    limit = max(1, min(int(limit), MAX_PAGE))
    where = build_filter(**criteria)
    cur = conn.execute(
        f"SELECT id, name, category, supplier, price_cents FROM products{where}{order_clause(sort)} LIMIT {limit}"
    )
    return cur.fetchall()


def count_by_category(conn):
    """Return {category: number of products}."""
    cur = conn.execute("SELECT category, COUNT(*) FROM products GROUP BY category")
    return dict(cur.fetchall())


def price_range(conn, category):
    """Return (lowest, highest) price in cents for a category, or None when it is empty."""
    cur = conn.execute(
        "SELECT MIN(price_cents), MAX(price_cents) FROM products WHERE category = ?", (category,)
    )
    low, high = cur.fetchone()
    return None if low is None else (low, high)
