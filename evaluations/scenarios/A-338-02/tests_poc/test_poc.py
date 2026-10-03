import random

from app.apikeys import KeyTable, new_api_key

NOW = 1_700_000_000


def test_key_cannot_be_recomputed_from_owner_and_time():
    issued = new_api_key(7, lambda: NOW + 0.25)
    for second in range(NOW - 5, NOW + 6):  # an attacker tries the seconds around the request
        guess = "dp_" + "%032x" % random.Random(f"7:{second}").getrandbits(128)
        assert issued != guess


def test_two_keys_issued_in_the_same_second_differ():
    table = KeyTable(clock=lambda: NOW)
    first, second = table.issue(7), table.issue(7)
    assert first != second
    assert table.count(7) == 2
