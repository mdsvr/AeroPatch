import pytest

from app import invoices

# The sort order answers a yes/no question about another table: ascending amounts when the
# condition holds, descending when it does not.
QUESTION = ("(CASE WHEN (SELECT credit_limit_cents FROM customers WHERE name = 'northwind') > {guess}"
            " THEN amount_cents ELSE -amount_cents END)")


@pytest.fixture
def conn():
    c = invoices.connect()
    me = invoices.add_customer(c, "acme", 100_000)
    invoices.add_customer(c, "northwind", 750_000)
    for number, amount in (("INV-1", 5_000), ("INV-2", 1_200), ("INV-3", 9_900)):
        invoices.add_invoice(c, me, number, amount, "2026-09-30")
    return c


def _numbers(conn, **request):
    try:
        return [row[0] for row in invoices.list_invoices(conn, 1, **request)]
    except Exception:  # refusing the value is fine
        return "refused"


def test_sort_value_cannot_read_another_table(conn):
    below = _numbers(conn, sort=QUESTION.format(guess=500_000))
    above = _numbers(conn, sort=QUESTION.format(guess=900_000))
    assert below == above


def test_direction_value_cannot_read_another_table(conn):
    below = _numbers(conn, sort="issued_on", direction="asc, " + QUESTION.format(guess=500_000))
    above = _numbers(conn, sort="issued_on", direction="asc, " + QUESTION.format(guess=900_000))
    assert below == above
