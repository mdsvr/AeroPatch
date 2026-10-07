import sqlite3

import pytest

from app.chess_club_ladder import init_db, search_players_by_rating_range


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    conn.executemany("INSERT INTO players (name, rating) VALUES (?, ?)",
                     [("Alice", 1200), ("Bob", 1500), ("Charlie", 1800)])
    conn.commit()
    yield conn
    conn.close()


def found(db, low, high):
    try:
        return search_players_by_rating_range(db, low, high)
    except (TypeError, ValueError):  # refusing a rating that is not a number is a valid fix
        return []


def test_condition_in_the_minimum_does_not_widen_the_search(db):
    assert found(db, "0 OR 1=1 --", 0) == []


def test_quote_in_a_rating_is_treated_as_data(db):
    assert found(db, "x' OR '1'='1", "x' OR '1'='2") == []
