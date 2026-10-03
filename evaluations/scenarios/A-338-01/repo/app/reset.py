"""Password-reset links: issue a one-time code, mail it, redeem it once."""

import random
import string
import time

CODE_ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 32
LIFETIME_SECONDS = 15 * 60


def _new_code():
    """A fresh reset code; it goes into the link that is mailed to the user."""
    return "".join(random.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


class ResetCodes:
    """Pending password resets: code -> (user id, expiry time)."""

    def __init__(self, clock=time.time):
        self._clock = clock
        self._pending = {}

    def issue(self, user_id):
        """Create a reset code for the user; an earlier code of theirs stops working."""
        for code, (owner, _) in list(self._pending.items()):
            if owner == user_id:
                del self._pending[code]
        code = _new_code()
        self._pending[code] = (user_id, self._clock() + LIFETIME_SECONDS)
        return code

    def redeem(self, code):
        """Use up a code. Returns the user id, or None for an unknown, used or expired code."""
        user_id, expires_at = self._pending.pop(code, (None, 0))
        if user_id is None or self._clock() > expires_at:
            return None
        return user_id

    def link(self, base_url, user_id):
        """The address mailed to the user."""
        return f"{base_url.rstrip('/')}/reset?code={self.issue(user_id)}"

    def pending_count(self):
        """How many unexpired codes are outstanding."""
        now = self._clock()
        return sum(1 for _, expires_at in self._pending.values() if expires_at >= now)
