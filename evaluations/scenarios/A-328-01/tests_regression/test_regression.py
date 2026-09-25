from app.users import hash_password, verify_password


def test_hash_is_nonempty_string():
    h = hash_password("pw")
    assert isinstance(h, str) and len(h) >= 32


def test_verify_correct_password():
    assert verify_password("s3cret!", hash_password("s3cret!")) is True


def test_verify_wrong_password():
    assert verify_password("wrong", hash_password("s3cret!")) is False


def test_unicode_password():
    assert verify_password("pässwörd", hash_password("pässwörd")) is True
