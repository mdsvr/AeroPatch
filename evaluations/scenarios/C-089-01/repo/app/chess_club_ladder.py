"""
chess_club_ladder.py - Chess club ladder on SQLite.
Players, match results and rating searches.
"""

import sqlite3
from typing import List, Tuple


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize the database schema for the chess club ladder."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            games_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            player_id INTEGER,
            opponent_id INTEGER,
            score_p1 INTEGER,
            score_p2 INTEGER,
            date TEXT,
            FOREIGN KEY(player_id) REFERENCES players(id),
            FOREIGN KEY(opponent_id) REFERENCES players(id)
        )
    """)
    conn.commit()


def get_player_stats(conn: sqlite3.Connection, player_name: str) -> Tuple[int, int, int, int] | None:
    """
    Retrieve statistics for a specific player by name.
    
    Returns a tuple (id, rating, games_played, wins) or None if not found.
    Uses parameterized queries to prevent SQL injection.
    """
    cursor = conn.cursor()
    query = "SELECT id, rating, games_played, wins FROM players WHERE name = ?"
    cursor.execute(query, (player_name,))
    row = cursor.fetchone()
    if row:
        return row
    return None


def insert_match_result(conn: sqlite3.Connection, player1_id: int, player2_id: int, 
                        score1: int, score2: int) -> int | None:
    """
    Insert a new match result into the database.
    
    Returns the ID of the inserted match or None if insertion fails.
    Uses parameterized queries to prevent SQL injection.
    """
    cursor = conn.cursor()
    query = "INSERT INTO matches (player_id, opponent_id, score_p1, score_p2) VALUES (?, ?, ?, ?)"
    cursor.execute(query, (player1_id, player2_id, score1, score2))
    conn.commit()
    return cursor.lastrowid


def update_player_stats(conn: sqlite3.Connection, player_name: str, 
                        new_games: int, new_wins: int) -> bool:
    """
    Update the games played and wins for a specific player.
    
    Returns True if the update was successful, False otherwise.
    Uses parameterized queries to prevent SQL injection.
    """
    cursor = conn.cursor()
    query = "UPDATE players SET games_played = ?, wins = ? WHERE name = ?"
    cursor.execute(query, (new_games, new_wins, player_name))
    conn.commit()
    return cursor.rowcount > 0


def get_all_players(conn: sqlite3.Connection) -> List[Tuple[int, str, int]]:
    """
    Retrieve a list of all players with their ratings.
    
    Returns a list of tuples (id, name, rating).
    Does not use parameterized queries as it retrieves all data.
    """
    cursor = conn.cursor()
    query = "SELECT id, name, rating FROM players ORDER BY rating DESC"
    cursor.execute(query)
    return cursor.fetchall()


def search_players_by_rating_range(conn: sqlite3.Connection, min_rating: int, 
                                   max_rating: int) -> List[Tuple[int, str, int]]:
    """
    Search for players within a specific rating range.
    
    Returns a list of tuples (id, name, rating) matching the criteria.
    Both bounds are inclusive.
    """
    cursor = conn.cursor()
    query = "SELECT id, name, rating FROM players WHERE rating >= {} AND rating <= {}".format(min_rating, max_rating)
    cursor.execute(query)
    return cursor.fetchall()
