import sqlite3

from app.invoices import connect, export_invoice

# Things only the server's logs should hold: stack frames, driver errors, the interpreter's message.
LEAKS = ("Traceback", 'File "', "invoices.py", "sqlite3", "OperationalError", "no such table", "invalid literal")


def _text(value):
    """Every string an API client would receive, joined."""
    if isinstance(value, dict):
        return " ".join(_text(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(_text(v) for v in value)
    return str(value)


def _assert_generic(status, body):
    assert status >= 400
    text = _text(body)
    assert not [marker for marker in LEAKS if marker in text]


def test_database_failure_does_not_leak_internals():
    broken = sqlite3.connect(":memory:")  # no invoices table: the query fails inside the handler
    _assert_generic(*export_invoice({"invoice_id": "1"}, broken))


def test_bad_id_does_not_echo_the_exception():
    _assert_generic(*export_invoice({"invoice_id": "12abc"}, connect()))


def test_missing_parameter_does_not_return_a_traceback():
    _assert_generic(*export_invoice({}, connect()))
