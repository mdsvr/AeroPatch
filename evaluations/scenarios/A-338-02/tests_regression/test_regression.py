import re

import pytest

from app.apikeys import KeyTable, digest, new_api_key


class Clock:
    def __init__(self):
        self.now = 1_700_000_000.0

    def __call__(self):
        self.now += 1.0
        return self.now


def test_key_format():
    api_key = new_api_key(7)
    assert api_key.startswith("dp_") and len(api_key) >= 35
    assert re.fullmatch(r"dp_[A-Za-z0-9_-]+", api_key)


def test_keys_are_unique_across_owners_and_time():
    clock = Clock()
    assert len({new_api_key(owner, clock) for owner in range(100)}) == 100
    assert len({new_api_key(7, clock) for _ in range(100)}) == 100


def test_issue_then_look_up():
    table = KeyTable(Clock())
    mine, theirs = table.issue(7), table.issue(8)
    assert table.owner_of(mine) == 7 and table.owner_of(theirs) == 8
    assert table.owner_of("dp_" + "0" * 32) is None
    assert table.count(7) == 1


def test_revoke():
    table = KeyTable(Clock())
    api_key = table.issue(7)
    assert table.revoke(api_key) is True
    assert table.revoke(api_key) is False
    assert table.owner_of(api_key) is None and table.count(7) == 0


def test_key_limit_per_owner():
    table = KeyTable(Clock())
    for _ in range(5):
        table.issue(7)
    with pytest.raises(ValueError):
        table.issue(7)
    assert table.issue(8)


def test_only_a_digest_is_stored():
    table = KeyTable(Clock())
    api_key = table.issue(7)
    assert digest(api_key) != api_key and len(digest(api_key)) == 64
    assert api_key not in str(vars(table))
