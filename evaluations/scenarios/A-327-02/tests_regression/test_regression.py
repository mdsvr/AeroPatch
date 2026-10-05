import re

import pytest

from app.signing import SignatureError, download_allowed, read_query, sign, signed_query

KEY = b"k" * 24
NOW = 1_700_000_000


def test_signature_is_stable_hex_and_depends_on_key_and_message():
    assert sign(KEY, b"file=a.pdf") == sign(KEY, b"file=a.pdf")
    assert re.fullmatch(r"[0-9a-f]{32,}", sign(KEY, b"file=a.pdf"))
    assert sign(KEY, b"file=a.pdf") != sign(KEY, b"file=b.pdf")
    assert sign(KEY, b"file=a.pdf") != sign(b"another key", b"file=a.pdf")


def test_signed_query_round_trips():
    query = signed_query(KEY, {"file": "q3 report.pdf", "expires": str(NOW + 60), "user": "sam"})
    assert query.startswith(b"expires=") and b"&sig=" in query
    assert read_query(KEY, query) == {"file": "q3 report.pdf", "expires": str(NOW + 60), "user": "sam"}


def test_changed_field_or_wrong_key_is_refused():
    query = signed_query(KEY, {"file": "manual.pdf", "expires": str(NOW + 60)})
    with pytest.raises(SignatureError):
        read_query(KEY, query.replace(b"manual.pdf", b"salary.pdf"))
    with pytest.raises(SignatureError):
        read_query(b"another key", query)
    with pytest.raises(SignatureError):
        read_query(KEY, query[:-1] + (b"0" if query[-1:] != b"0" else b"1"))


def test_unsigned_or_oversized_query_is_refused():
    with pytest.raises(SignatureError):
        read_query(KEY, b"file=manual.pdf&expires=1")
    with pytest.raises(SignatureError):
        read_query(KEY, signed_query(KEY, {"file": "x" * 3000}))


def test_repeated_field_takes_its_last_value():
    text = b"file=a.pdf&file=b.pdf"
    query = text + b"&sig=" + sign(KEY, text).encode("ascii")
    assert read_query(KEY, query) == {"file": "b.pdf"}


def test_download_allowed_checks_the_expiry():
    fresh = signed_query(KEY, {"file": "manual.pdf", "expires": str(NOW + 60)})
    stale = signed_query(KEY, {"file": "manual.pdf", "expires": str(NOW - 1)})
    no_file = signed_query(KEY, {"expires": str(NOW + 60)})
    assert download_allowed(KEY, fresh, NOW) is True
    assert download_allowed(KEY, stale, NOW) is False
    assert download_allowed(KEY, no_file, NOW) is False
    with pytest.raises(SignatureError):
        download_allowed(KEY, fresh + b"0", NOW)
