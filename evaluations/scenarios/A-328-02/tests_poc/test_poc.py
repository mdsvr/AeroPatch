import hashlib

from app.accounts import Accounts


def test_record_is_not_a_bare_fast_hash():
    accounts = Accounts()
    accounts.create("dana", "correct horse")
    stored = accounts.record("dana")
    for algo in ("md5", "sha1", "sha256", "sha512"):
        assert hashlib.new(algo, b"correct horse").hexdigest() not in stored


def test_same_password_gives_different_records():
    accounts = Accounts()
    accounts.create("dana", "correct horse")
    accounts.create("lee", "correct horse")
    assert accounts.record("dana") != accounts.record("lee")


def test_setting_the_same_password_again_gives_a_new_record():
    accounts = Accounts()
    accounts.create("dana", "correct horse")
    first = accounts.record("dana")
    accounts.set_password("dana", "correct horse")
    assert accounts.record("dana") != first
