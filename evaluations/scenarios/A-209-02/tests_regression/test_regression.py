import sqlite3

import pytest

from app.invoices import add_invoice, connect, export_invoice, list_invoices


@pytest.fixture
def conn():
    c = connect()
    add_invoice(c, "Acme Ltd", 12500, paid=True)
    add_invoice(c, "Bolt & Co", 990)
    return c


def test_export_as_json(conn):
    assert export_invoice({"invoice_id": "1"}, conn) == (
        200, {"id": 1, "customer": "Acme Ltd", "total_cents": 12500, "paid": True})
    assert export_invoice({"invoice_id": "2", "format": "json"}, conn)[1]["paid"] is False


def test_export_as_csv(conn):
    assert export_invoice({"invoice_id": "2", "format": "csv"}, conn) == (
        200, {"content_type": "text/csv", "text": "2,Bolt & Co,990,0\n"})


def test_unknown_invoice_and_format(conn):
    assert export_invoice({"invoice_id": "99"}, conn) == (404, {"error": "invoice not found"})
    assert export_invoice({"invoice_id": "1", "format": "xml"}, conn) == (400, {"error": "format must be json or csv"})


def test_failures_still_answer_with_an_error_body(conn):
    status, body = export_invoice({"invoice_id": "abc"}, conn)
    assert status in (400, 500) and isinstance(body.get("error"), str) and body["error"]
    status, body = export_invoice({"invoice_id": "1"}, sqlite3.connect(":memory:"))
    assert status >= 500 and isinstance(body.get("error"), str) and body["error"]


def test_listing(conn):
    status, body = list_invoices({}, conn)
    assert status == 200 and body["page"] == 1
    assert [invoice["customer"] for invoice in body["invoices"]] == ["Acme Ltd", "Bolt & Co"]
    assert list_invoices({"page": "2"}, conn) == (200, {"page": 2, "invoices": []})
    assert list_invoices({"page": "x"}, conn) == (500, {"error": "could not list invoices"})
