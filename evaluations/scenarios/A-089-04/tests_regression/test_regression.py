import pytest

from app import invoices


@pytest.fixture
def conn():
    c = invoices.connect()
    acme = invoices.add_customer(c, "acme", 100_000)
    other = invoices.add_customer(c, "northwind", 750_000)
    invoices.add_invoice(c, acme, "INV-3", 9_900, "2026-07-15")
    invoices.add_invoice(c, acme, "INV-1", 5_000, "2026-09-01")
    invoices.add_invoice(c, acme, "INV-2", 1_200, "2026-08-20")
    invoices.add_invoice(c, other, "INV-9", 70_000, "2026-08-01")
    return c


def numbers(rows):
    return [row[0] for row in rows]


def test_default_order_is_oldest_first(conn):
    assert numbers(invoices.list_invoices(conn, 1)) == ["INV-3", "INV-2", "INV-1"]


@pytest.mark.parametrize("sort, direction, expected", [
    ("number", "asc", ["INV-1", "INV-2", "INV-3"]),
    ("number", "desc", ["INV-3", "INV-2", "INV-1"]),
    ("amount_cents", "asc", ["INV-2", "INV-1", "INV-3"]),
    ("amount_cents", "desc", ["INV-3", "INV-1", "INV-2"]),
    ("issued_on", "desc", ["INV-1", "INV-2", "INV-3"]),
])
def test_every_header_link_sorts(conn, sort, direction, expected):
    assert numbers(invoices.list_invoices(conn, 1, sort=sort, direction=direction)) == expected


def test_rows_have_three_columns(conn):
    assert invoices.list_invoices(conn, 1, sort="number")[0] == ("INV-1", 5_000, "2026-09-01")


def test_only_the_customers_own_invoices(conn):
    assert numbers(invoices.list_invoices(conn, 2)) == ["INV-9"]
    assert invoices.list_invoices(conn, 3) == []


def test_limit_is_capped(conn):
    assert numbers(invoices.list_invoices(conn, 1, sort="number", limit=2)) == ["INV-1", "INV-2"]
    assert len(invoices.list_invoices(conn, 1, limit=0)) == 1
    assert len(invoices.list_invoices(conn, 1, limit="500")) == 3


def test_sort_links_cover_the_sortable_columns():
    assert invoices.sort_links("/invoices") == {
        "number": "/invoices?sort=number&dir=asc",
        "amount_cents": "/invoices?sort=amount_cents&dir=asc",
        "issued_on": "/invoices?sort=issued_on&dir=asc",
    }
