"""User directory backed by SQLite."""

import sqlite3


def connect(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    return conn


def add_user(conn, name):
    conn.execute("INSERT INTO users (name) VALUES (?)", (name,))
    conn.commit()


def find_user(conn, name):
    cur = conn.execute(f"SELECT id, name FROM users WHERE name = '{name}'")
    return cur.fetchall()
