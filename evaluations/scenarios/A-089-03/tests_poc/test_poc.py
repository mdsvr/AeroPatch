import pytest

from app import tickets


@pytest.fixture
def conn():
    c = tickets.connect()
    tickets.add_ticket(c, "Printer on floor 2 is offline")
    tickets.add_ticket(c, "VPN drops every hour")
    closed = tickets.add_ticket(c, "Badge reader broken")
    tickets.set_status(c, closed, "closed")
    tickets.add_agent(c, "root@helpdesk.example", "admin", "pbkdf2$31337")
    return c


def test_quote_in_term_is_treated_as_data(conn):
    assert tickets.search_tickets(conn, "zzz' OR '1' LIKE '1") == []


def test_quote_in_status_is_treated_as_data(conn):
    assert tickets.search_tickets(conn, "Printer", status="closed' OR '1'='1") == []


def test_union_payload_leaks_no_agent_rows(conn):
    payload = "zzz%' UNION SELECT id, email, role, pin_hash FROM agents --"
    rows = tickets.search_tickets(conn, payload)
    assert not any("root@helpdesk.example" in str(row) for row in rows)
    assert rows == []


def test_title_with_apostrophe_is_found(conn):
    tickets.add_ticket(conn, "Can't log in to payroll")
    assert [row[1] for row in tickets.search_tickets(conn, "Can't log")] == ["Can't log in to payroll"]
