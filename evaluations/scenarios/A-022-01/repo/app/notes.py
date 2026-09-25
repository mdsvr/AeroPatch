"""Serve note files stored under a base directory."""

import os


def read_note(base_dir, name):
    """Return the text of note `name` stored under `base_dir`."""
    path = os.path.join(base_dir, name)
    with open(path, encoding="utf-8") as f:
        return f.read()
