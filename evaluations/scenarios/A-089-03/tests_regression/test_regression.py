import pytest

from app import tickets


@pytest.fixture
def conn():
    c = tickets.connect()
    tickets.add_ticket(c, "Printer on floor 2 is offline", assignee="dana")
    tickets.add_ticket(c, "VPN drops every hour", assignee="lee")
    tickets.add_ticket(c, "Printer queue stuck", assignee="dana")
    closed = tickets.add_ticket(c, "Old printer driver", assignee="lee")
    tickets.set_status(c, closed, "closed")
    return c


def test_search_matches_substring_newest_first(conn):
    rows = tickets.search_tickets(conn, "rinter")
    assert [row[1] for row in rows] == ["Old printer driver", "Printer queue stuck", "Printer on floor 2 is offline"]
    assert rows[0] == (4, "Old printer driver", "closed", "lee")


def test_search_with_status_filter(conn):
    assert [row[0] for row in tickets.search_tickets(conn, "printer", status="open")] == [3, 1]
    assert [row[0] for row in tickets.search_tickets(conn, "printer", status="closed")] == [4]
    assert tickets.search_tickets(conn, "VPN", status="closed") == []


def test_search_without_match_is_empty(conn):
    assert tickets.search_tickets(conn, "scanner") == []


def test_limit_is_applied_and_clamped(conn):
    assert len(tickets.search_tickets(conn, "", limit=2)) == 2
    assert len(tickets.search_tickets(conn, "", limit=0)) == 1
    assert len(tickets.search_tickets(conn, "", limit="3")) == 3
    assert len(tickets.search_tickets(conn, "", limit=10_000)) == 4


def test_other_queries_still_work(conn):
    assert tickets.get_ticket(conn, 2) == (2, "VPN drops every hour", "open", "lee")
    assert tickets.count_by_status(conn) == {"open": 3, "pending": 0, "closed": 1}
    assert [row[0] for row in tickets.assigned_to(conn, "dana")] == [1, 3]
    with pytest.raises(ValueError):
        tickets.set_status(conn, 1, "archived")
