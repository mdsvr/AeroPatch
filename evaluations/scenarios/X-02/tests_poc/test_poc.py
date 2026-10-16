import pytest

from app import db


@pytest.fixture
def conn():
    c = db.connect()
    db.add_user(c, "alice")
    db.add_user(c, "bob")
    return c


def test_quote_in_name_is_treated_as_data(conn):
    assert db.find_user(conn, "x' OR '1'='1") == []


def test_name_with_apostrophe_is_found(conn):
    db.add_user(conn, "o'brien")
    assert [row[1] for row in db.find_user(conn, "o'brien")] == ["o'brien"]
