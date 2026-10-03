"""Helpdesk tickets stored in SQLite."""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    assignee TEXT
);
CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    pin_hash TEXT NOT NULL
);
"""
STATUSES = ("open", "pending", "closed")
MAX_RESULTS = 200


def connect(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def add_agent(conn, email, role, pin_hash):
    """Register a helpdesk agent and return their id."""
    cur = conn.execute("INSERT INTO agents (email, role, pin_hash) VALUES (?, ?, ?)", (email, role, pin_hash))
    conn.commit()
    return cur.lastrowid


def add_ticket(conn, title, body="", assignee=None):
    """Open a ticket and return its id."""
    if not title.strip():
        raise ValueError("a ticket needs a title")
    cur = conn.execute("INSERT INTO tickets (title, body, assignee) VALUES (?, ?, ?)", (title, body, assignee))
    conn.commit()
    return cur.lastrowid


def get_ticket(conn, ticket_id):
    """Return (id, title, status, assignee) of one ticket, or None."""
    cur = conn.execute("SELECT id, title, status, assignee FROM tickets WHERE id = ?", (ticket_id,))
    return cur.fetchone()


def set_status(conn, ticket_id, status):
    """Move a ticket to another status. Returns False when the ticket does not exist."""
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    cur = conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
    conn.commit()
    return cur.rowcount == 1


def count_by_status(conn):
    """Number of tickets per status, e.g. {"open": 3, "pending": 0, "closed": 1}."""
    counts = dict.fromkeys(STATUSES, 0)
    for status, n in conn.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status"):
        counts[status] = n
    return counts


def search_tickets(conn, term, status=None, limit=50):
    """Tickets whose title contains `term`, newest first, as (id, title, status, assignee) rows.

    `term` and `status` are the search box and the status drop-down of the ticket list page.
    """
    limit = max(1, min(int(limit), MAX_RESULTS))
    where = "title LIKE '%%%s%%'" % term
    if status:
        where += " AND status = '%s'" % status
    cur = conn.execute(
        "SELECT id, title, status, assignee FROM tickets WHERE %s ORDER BY id DESC LIMIT %d" % (where, limit)
    )
    return cur.fetchall()


def assigned_to(conn, assignee):
    """Open and pending tickets of one agent, oldest first."""
    cur = conn.execute(
        "SELECT id, title, status, assignee FROM tickets WHERE assignee = ? AND status != 'closed' ORDER BY id",
        (assignee,),
    )
    return cur.fetchall()
