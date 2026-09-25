import os
from pathlib import Path

BASE = Path("/srv/files")
LIMIT = 10


def outer(name):
    def inner(x):
        return x * 2
    return open(os.path.join(BASE, name)).read()


class Store:
    """A store."""

    def __init__(self, root):
        self.root = root

    @property
    def size(self):
        return LIMIT

    @staticmethod
    def load(name):
        data = outer(name)
        return data.strip()


def caller():
    return outer("a")
