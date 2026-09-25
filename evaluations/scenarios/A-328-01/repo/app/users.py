"""Password storage for local accounts."""

import hashlib


def hash_password(password):
    """Return the string stored in the users table for `password`."""
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def verify_password(password, stored):
    return hash_password(password) == stored
