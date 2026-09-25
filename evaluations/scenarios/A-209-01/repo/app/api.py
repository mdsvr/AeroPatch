"""JSON handler for the order-lookup endpoint."""


def lookup_order(order_id, conn):
    """Return (status_code, body) for GET /orders/<order_id>."""
    try:
        oid = int(order_id)
        row = conn.execute("SELECT id, item FROM orders WHERE id = ?", (oid,)).fetchone()
    except Exception as exc:
        return 500, {"error": f"lookup failed: {exc!r}"}
    if row is None:
        return 404, {"error": "not found"}
    return 200, {"id": row[0], "item": row[1]}
