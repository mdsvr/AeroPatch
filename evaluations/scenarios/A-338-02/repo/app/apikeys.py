"""API keys for the developer portal. Only a digest of each key is kept."""

import hashlib
import random
import time

KEY_PREFIX = "dp_"
MAX_KEYS_PER_OWNER = 5


def new_api_key(owner_id, clock=time.time):
    """A fresh API key for the account `owner_id`; it is shown to the developer once."""
    rng = random.Random(f"{owner_id}:{int(clock())}")
    return KEY_PREFIX + "%032x" % rng.getrandbits(128)


def digest(api_key):
    """What the key table stores instead of the key itself."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


class KeyTable:
    """Issued keys: digest -> owner id."""

    def __init__(self, clock=time.time):
        self._clock = clock
        self._owners = {}

    def issue(self, owner_id):
        """Create a key for the owner and return it."""
        if self.count(owner_id) >= MAX_KEYS_PER_OWNER:
            raise ValueError(f"an account can hold at most {MAX_KEYS_PER_OWNER} keys")
        api_key = new_api_key(owner_id, self._clock)
        self._owners[digest(api_key)] = owner_id
        return api_key

    def owner_of(self, api_key):
        """The owner id for a presented key, or None when the key is unknown or revoked."""
        return self._owners.get(digest(api_key))

    def revoke(self, api_key):
        """Invalidate a key. Returns False when it was not valid."""
        return self._owners.pop(digest(api_key), None) is not None

    def count(self, owner_id):
        """How many valid keys an owner has."""
        return sum(1 for owner in self._owners.values() if owner == owner_id)
