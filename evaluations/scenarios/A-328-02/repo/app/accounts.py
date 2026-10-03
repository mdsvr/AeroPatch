"""Local accounts for the admin console."""

import hashlib
import hmac

MIN_PASSWORD_LENGTH = 8


class AccountError(ValueError):
    """Raised for account operations that cannot be carried out."""


class Accounts:
    """Account table: user name -> stored password record."""

    def __init__(self):
        self._records = {}

    def create(self, username, password):
        """Add an account. User names are unique."""
        if not username or username in self._records:
            raise AccountError("user name is empty or already taken")
        self._records[username] = ""
        try:
            self.set_password(username, password)
        except AccountError:
            del self._records[username]
            raise

    def set_password(self, username, password):
        """Store a new password for an existing account."""
        if username not in self._records:
            raise AccountError("no such account")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise AccountError(f"passwords need at least {MIN_PASSWORD_LENGTH} characters")
        self._records[username] = hashlib.sha1(password.encode("utf-8")).hexdigest()

    def check_password(self, username, password):
        """True when `password` is the account's current password."""
        stored = self._records.get(username)
        if not stored:
            return False
        candidate = hashlib.sha1(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(candidate, stored)

    def record(self, username):
        """The stored password record, as it is written to the accounts file."""
        return self._records.get(username)

    def usernames(self):
        return sorted(self._records)

    def remove(self, username):
        """Delete an account. Returns False when it does not exist."""
        return self._records.pop(username, None) is not None
