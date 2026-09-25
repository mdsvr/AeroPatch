"""Login helpers."""


def redirect_after_login(next_url, default="/home"):
    """Return where to send the user after a successful login.

    `next_url` comes from the ?next= query parameter of the login page.
    """
    if not next_url:
        return default
    return next_url
