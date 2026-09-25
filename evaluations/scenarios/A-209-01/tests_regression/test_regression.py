import sqlite3

from app.api import lookup_order


def db():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT)")
    c.execute("INSERT INTO orders VALUES (1, 'lamp')")
    return c


def test_found():
    assert lookup_order("1", db()) == (200, {"id": 1, "item": "lamp"})


def test_not_found():
    assert lookup_order("99", db()) == (404, {"error": "not found"})


def test_bad_id_is_an_error_response():
    status, body = lookup_order("abc", db())
    assert status >= 400 and "error" in body
