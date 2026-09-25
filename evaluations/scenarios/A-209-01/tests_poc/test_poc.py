import sqlite3

from app.api import lookup_order


def db():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT)")
    return c


def test_bad_id_error_has_no_internals():
    status, body = lookup_order("12abc", db())
    assert "invalid literal" not in body["error"] and "ValueError" not in body["error"]


def test_database_error_has_no_internals():
    c = db()
    c.close()
    status, body = lookup_order("1", c)
    assert status == 500
    assert "closed" not in body["error"].lower() and "Error" not in body["error"]
