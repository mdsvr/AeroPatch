import hashlib

from app.parking_permits import store_permits


def stored(password):
    return store_permits({"permit_id": "p1", "user_name": "alice", "password": password})["hashed_password"]


def test_not_a_bare_fast_hash():
    value = stored("correct horse")
    for algo in ("md5", "sha1", "sha256"):
        digest = hashlib.new(algo, b"correct horse")
        assert value not in (digest.hexdigest(), digest.digest())


def test_salted():
    assert stored("same") != stored("same")
