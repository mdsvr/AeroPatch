"""Input validation for account sign-up."""

import re

USERNAME_RE = re.compile(r"^([a-z0-9]+)+$")


def is_valid_username(name):
    """Usernames are lowercase letters and digits."""
    return bool(USERNAME_RE.match(name))
