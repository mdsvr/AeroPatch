import pytest

from app import db


@pytest.fixture
def conn():
    c = db.connect()
    db.add_user(c, "alice")
    db.add_user(c, "bob")
    return c


def test_find_existing_user(conn):
    rows = db.find_user(conn, "alice")
    assert len(rows) == 1 and rows[0][1] == "alice"


def test_unknown_user_is_empty(conn):
    assert db.find_user(conn, "carol") == []


def test_add_then_find(conn):
    db.add_user(conn, "dave")
    assert [r[1] for r in db.find_user(conn, "dave")] == ["dave"]
