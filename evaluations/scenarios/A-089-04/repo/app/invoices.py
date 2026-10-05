"""Invoice list of the customer portal, backed by SQLite."""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    credit_limit_cents INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (id),
    number TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    issued_on TEXT NOT NULL
);
"""
SORTABLE = ("number", "amount_cents", "issued_on")
MAX_PAGE = 100


def connect(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def add_customer(conn, name, credit_limit_cents):
    """Insert a customer and return its id."""
    cur = conn.execute("INSERT INTO customers (name, credit_limit_cents) VALUES (?, ?)", (name, credit_limit_cents))
    return cur.lastrowid


def add_invoice(conn, customer_id, number, amount_cents, issued_on):
    """Insert an invoice and return its id."""
    cur = conn.execute("INSERT INTO invoices (customer_id, number, amount_cents, issued_on) VALUES (?, ?, ?, ?)",
                       (customer_id, number, amount_cents, issued_on))
    return cur.lastrowid


def sort_links(base_url):
    """Links for the table's column headers: {column: URL that sorts by it}."""
    return {column: f"{base_url}?sort={column}&dir=asc" for column in SORTABLE}


def list_invoices(conn, customer_id, sort="issued_on", direction="asc", limit=50):
    """Rows (number, amount_cents, issued_on) of one customer's invoices.

    `sort` and `direction` are the ?sort= and ?dir= values of the request. The header links
    of the table use the SORTABLE columns with "asc" or "desc".
    """
    limit = max(1, min(int(limit), MAX_PAGE))
    cur = conn.execute(
        f"SELECT number, amount_cents, issued_on FROM invoices WHERE customer_id = ? ORDER BY {sort} {direction} LIMIT ?",
        (customer_id, limit),
    )
    return cur.fetchall()
