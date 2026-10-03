import pytest

from app import store


@pytest.fixture
def conn():
    c = store.connect()
    store.add_product(c, "kettle", "kitchen", "acme", 2499)
    store.add_product(c, "toaster", "kitchen", "brightco", 3999)
    store.add_product(c, "lamp", "lighting", "acme", 1599)
    return c


def test_quote_in_value_is_treated_as_data(conn):
    assert store.search_products(conn, name="x' OR '1'='1") == []


def test_value_with_apostrophe_is_found(conn):
    store.add_product(conn, "o'neil's kettle", "kitchen", "acme", 1999)
    assert [row[1] for row in store.search_products(conn, name="o'neil's kettle")] == ["o'neil's kettle"]


def test_union_payload_returns_nothing(conn):
    payload = "kitchen' UNION SELECT 1, name, 'x', 'y', 0 FROM sqlite_master --"
    assert store.search_products(conn, category=payload) == []
