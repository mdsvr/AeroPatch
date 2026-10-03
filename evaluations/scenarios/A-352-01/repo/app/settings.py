"""Account settings views. A view takes (request, session, users) and returns (status, body).

`request` is {"method": ..., "form": {...}}; `session` is the visitor's server-side session;
`users` maps user ids to their stored profile.
"""

import hmac
import secrets


def issue_csrf_token(session):
    """Create the session's CSRF token on first use and return it; every form embeds it."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def csrf_ok(request, session):
    """True when the submitted form carries the session's CSRF token."""
    sent = request["form"].get("csrf_token", "")
    expected = session.get("csrf_token", "")
    return bool(expected) and hmac.compare_digest(sent, expected)


def update_display_name(request, session, users):
    """Handle POST /settings/name."""
    if request["method"] != "POST":
        return 405, {"error": "use POST"}
    if not csrf_ok(request, session):
        return 403, {"error": "invalid CSRF token"}
    user = users.get(session.get("user_id"))
    if user is None:
        return 401, {"error": "log in first"}
    name = request["form"].get("display_name", "").strip()
    if not 1 <= len(name) <= 40:
        return 400, {"error": "names have 1 to 40 characters"}
    user["display_name"] = name
    return 200, {"display_name": name}


def change_email(request, session, users):
    """Handle POST /settings/email: set a new e-mail address for the logged-in user."""
    if request["method"] != "POST":
        return 405, {"error": "use POST"}
    user = users.get(session.get("user_id"))
    if user is None:
        return 401, {"error": "log in first"}
    email = request["form"].get("email", "").strip().lower()
    if "@" not in email or " " in email:
        return 400, {"error": "not an e-mail address"}
    user["email"] = email
    return 200, {"email": email}
