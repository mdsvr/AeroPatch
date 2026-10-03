import re

from app.reset import ResetCodes


class Clock:
    def __init__(self):
        self.now = 1_700_000_000.0

    def __call__(self):
        return self.now


def test_code_is_long_and_url_safe():
    code = ResetCodes().issue(7)
    assert isinstance(code, str) and len(code) >= 22
    assert re.fullmatch(r"[A-Za-z0-9_-]+", code)


def test_codes_are_unique():
    codes = ResetCodes()
    assert len({codes.issue(user_id) for user_id in range(200)}) == 200


def test_code_is_redeemed_once():
    codes = ResetCodes()
    code = codes.issue(7)
    assert codes.redeem(code) == 7
    assert codes.redeem(code) is None
    assert codes.redeem("not-a-code") is None


def test_new_code_replaces_the_old_one():
    codes = ResetCodes()
    old = codes.issue(7)
    new = codes.issue(7)
    other = codes.issue(8)
    assert codes.pending_count() == 2
    assert codes.redeem(old) is None
    assert codes.redeem(new) == 7 and codes.redeem(other) == 8


def test_code_expires_after_fifteen_minutes():
    clock = Clock()
    codes = ResetCodes(clock)
    late, in_time = codes.issue(7), codes.issue(8)
    clock.now += 15 * 60 - 1
    assert codes.pending_count() == 2 and codes.redeem(in_time) == 8
    clock.now += 2
    assert codes.pending_count() == 0 and codes.redeem(late) is None


def test_link_contains_a_redeemable_code():
    codes = ResetCodes()
    link = codes.link("https://shop.example/", 7)
    assert link.startswith("https://shop.example/reset?code=")
    assert codes.redeem(link.split("code=", 1)[1]) == 7
