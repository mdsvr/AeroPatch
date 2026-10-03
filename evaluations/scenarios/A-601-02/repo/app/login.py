"""Login flow helpers for the shop front end."""

from urllib.parse import quote, urlparse

LOGIN_PATH = "/login"
DEFAULT_LANDING = "/account"
PUBLIC_PREFIXES = ("/login", "/static/", "/products", "/help")
SESSION_KEYS = ("user_id", "issued_at")


def is_public(path):
    """True for pages that anonymous visitors may open."""
    return path == "/" or path.startswith(PUBLIC_PREFIXES)


def is_logged_in(session):
    """True when the session carries a user."""
    return all(session.get(key) for key in SESSION_KEYS)


def login_url(requested_path):
    """The login page address that brings the visitor back to `requested_path` afterwards."""
    if not requested_path or requested_path == DEFAULT_LANDING:
        return LOGIN_PATH
    return f"{LOGIN_PATH}?next={quote(requested_path, safe='')}"


def gate(session, path):
    """Decide what to do with a request: ("ok", None) or ("redirect", location)."""
    if is_public(path) or is_logged_in(session):
        return "ok", None
    return "redirect", login_url(path)


def canonical_host(url):
    """Lower-case host name of an absolute URL, '' when there is none."""
    return (urlparse(url).hostname or "").lower()


def post_login_redirect(next_url, site_host, default=DEFAULT_LANDING):
    """Where to send the browser after a successful login.

    `next_url` is the ?next= parameter of the login page. Only targets on this site are
    followed: site-relative paths and absolute https URLs on `site_host`. Anything else
    falls back to `default`.
    """
    if not next_url:
        return default
    if next_url.startswith("/") or next_url.startswith(f"https://{site_host}"):
        return next_url
    return default


def finish_login(session, user_id, issued_at, next_url, site_host):
    """Mark the session as logged in and return the (status, location) of the response."""
    session["user_id"] = user_id
    session["issued_at"] = issued_at
    return 303, post_login_redirect(next_url, site_host)
