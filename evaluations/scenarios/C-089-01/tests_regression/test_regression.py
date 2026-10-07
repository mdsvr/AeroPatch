import sqlite3
import pytest
from app.chess_club_ladder import (
    init_db, 
    get_player_stats,
    insert_match_result,
    update_player_stats,
    search_players_by_rating_range
)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    
    # Insert test data
    cursor = conn.cursor()
    cursor.execute("INSERT INTO players (name, rating, games_played, wins) VALUES (?, ?, 0, 0)", 
                   ("Alice", 1200))
    cursor.execute("INSERT INTO players (name, rating, games_played, wins) VALUES (?, ?, 0, 0)", 
                   ("Bob", 1500))
    cursor.execute("INSERT INTO players (name, rating, games_played, wins) VALUES (?, ?, 0, 0)", 
                   ("Charlie", 1800))
    conn.commit()
    
    yield conn
    
    conn.close()


def test_get_player_stats_exists(db):
    """Test retrieving stats for an existing player."""
    result = get_player_stats(db, "Alice")
    assert result is not None
    assert result[1] == 1200  # rating


def test_get_player_stats_not_found(db):
    """Test retrieving stats for non-existent player."""
    result = get_player_stats(db, "UnknownPlayer")
    assert result is None


def test_insert_match_result(db):
    """Test inserting a new match result."""
    cursor = db.cursor()
    cursor.execute("INSERT INTO players (name, rating) VALUES (?, ?)", 
                   ("Dave", 1300))
    db.commit()
    
    match_id = insert_match_result(db, 1, 2, 3, 1)
    assert match_id is not None




def test_update_player_stats_not_found(db):
    """Test updating stats for non-existent player."""
    result = update_player_stats(db, "Unknown", 10, 5)
    assert result is False


def test_search_players_by_rating_range_all(db):
    """Test searching all players with wide rating range."""
    result = search_players_by_rating_range(db, 1000, 2000)
    assert len(result) == 3


def test_search_players_by_rating_range_empty(db):
    """Test searching with no matching players."""
    result = search_players_by_rating_range(db, 5000, 6000)
    assert len(result) == 0
