"""JSON handlers for the invoice endpoints of the billing API."""

import logging
import sqlite3
import traceback

log = logging.getLogger("billing.invoices")

EXPORT_FORMATS = ("json", "csv")
PAGE_SIZE = 25


def connect(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS invoices ("
        "id INTEGER PRIMARY KEY, customer TEXT NOT NULL, total_cents INTEGER NOT NULL, paid INTEGER NOT NULL DEFAULT 0)"
    )
    return conn


def add_invoice(conn, customer, total_cents, paid=False):
    """Insert an invoice and return its id."""
    cur = conn.execute(
        "INSERT INTO invoices (customer, total_cents, paid) VALUES (?, ?, ?)", (customer, total_cents, int(paid))
    )
    conn.commit()
    return cur.lastrowid


def _render(row, fmt):
    """The export body for one invoice row in the requested format."""
    invoice_id, customer, total_cents, paid = row
    if fmt == "csv":
        return {"content_type": "text/csv", "text": f"{invoice_id},{customer},{total_cents},{paid}\n"}
    return {"id": invoice_id, "customer": customer, "total_cents": total_cents, "paid": bool(paid)}


def list_invoices(request, conn):
    """Handle GET /invoices?page=N and return (status, body)."""
    try:
        page = max(1, int(request.get("page", 1)))
        rows = conn.execute(
            "SELECT id, customer, total_cents, paid FROM invoices ORDER BY id LIMIT ? OFFSET ?",
            (PAGE_SIZE, (page - 1) * PAGE_SIZE),
        ).fetchall()
    except (ValueError, sqlite3.Error):
        log.exception("listing invoices failed")
        return 500, {"error": "could not list invoices"}
    return 200, {"page": page, "invoices": [_render(row, "json") for row in rows]}


def export_invoice(request, conn):
    """Handle GET /invoices/<invoice_id>/export?format=json|csv and return (status, body).

    `request` holds the path and query parameters as strings; the body goes to the API client.
    """
    try:
        invoice_id = int(request["invoice_id"])
        fmt = request.get("format", "json")
        if fmt not in EXPORT_FORMATS:
            return 400, {"error": "format must be json or csv"}
        row = conn.execute(
            "SELECT id, customer, total_cents, paid FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
        if row is None:
            return 404, {"error": "invoice not found"}
        return 200, _render(row, fmt)
    except Exception as exc:
        log.error("export failed: %s", exc)
        return 500, {"error": "export failed", "detail": repr(exc), "trace": traceback.format_exc()}
