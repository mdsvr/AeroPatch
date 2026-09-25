"""User preferences, stored as bytes in the session cookie."""

import pickle

DEFAULTS = {"theme": "light", "page_size": 20}


def dump_prefs(prefs):
    return pickle.dumps(prefs)


def load_prefs(blob):
    """Decode preferences sent back by the client and merge them over the defaults."""
    data = pickle.loads(blob)
    if not isinstance(data, dict):
        raise ValueError("preferences must be an object")
    return {**DEFAULTS, **data}
