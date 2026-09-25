import hashlib

from app.users import hash_password


def test_not_a_bare_fast_hash():
    stored = hash_password("correct horse")
    for algo in ("md5", "sha1", "sha256"):
        assert hashlib.new(algo, b"correct horse").hexdigest() not in stored


def test_salted():
    assert hash_password("same") != hash_password("same")
