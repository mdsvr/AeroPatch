"""Money-transfer views of the banking demo.

A view takes (request, session, accounts) and returns (status, body). `request` is
{"method": ..., "form": {...}}; `accounts` maps an account name to its balance in cents.
"""

import hmac

MAX_TRANSFER_CENTS = 1_000_00


def _owner(session, accounts):
    """The logged-in user's account name, or None."""
    name = session.get("account")
    return name if name in accounts else None


def balance(request, session, accounts):
    """Handle GET /balance."""
    owner = _owner(session, accounts)
    if owner is None:
        return 401, {"error": "log in first"}
    return 200, {"account": owner, "balance_cents": accounts[owner]}


def transfer(request, session, accounts):
    """Handle POST /transfer: send money from the logged-in user's account to another one.

    The transfer form embeds the session's CSRF token in a hidden csrf_token field.
    """
    if request["method"] != "POST":
        return 405, {"error": "use POST"}
    form = request["form"]
    if "csrf_token" in form and not hmac.compare_digest(form["csrf_token"], session.get("csrf_token", "")):
        return 403, {"error": "invalid CSRF token"}
    owner = _owner(session, accounts)
    if owner is None:
        return 401, {"error": "log in first"}
    recipient = form.get("to", "")
    if recipient not in accounts or recipient == owner:
        return 404, {"error": "unknown recipient"}
    try:
        cents = int(form.get("cents", ""))
    except ValueError:
        return 400, {"error": "amount must be a whole number of cents"}
    if not 0 < cents <= MAX_TRANSFER_CENTS or cents > accounts[owner]:
        return 400, {"error": "amount is out of range"}
    accounts[owner] -= cents
    accounts[recipient] += cents
    return 200, {"balance_cents": accounts[owner]}
