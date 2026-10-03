import pytest

from app.webhook_auth import SignatureError, parse_header, sign, signing_key, verify

NOW = 1_700_000_000
BODY = b'{"event": "payment.succeeded", "amount": 2500}'
ENV = {"PAY_WEBHOOK_SECRET": "from-the-deployment"}
KEY = b"from-the-deployment"


def _headers(timestamp=NOW, key=KEY, body=BODY):
    return {"X-Pay-Signature": f"t={timestamp},v1={sign(timestamp, body, key)}"}


def test_webhook_signed_with_the_configured_key_is_accepted():
    assert verify(_headers(), BODY, NOW, env=ENV) is True
    assert verify(_headers(NOW - 299), BODY, NOW, env=ENV) is True


def test_wrong_key_or_changed_body_is_rejected():
    assert verify(_headers(key=b"someone-else"), BODY, NOW, env=ENV) is False
    assert verify(_headers(), BODY + b" ", NOW, env=ENV) is False


def test_stale_or_malformed_headers_raise():
    with pytest.raises(SignatureError):
        verify(_headers(NOW - 301), BODY, NOW, env=ENV)
    for bad in ({}, {"X-Pay-Signature": "v1=abc"}, {"X-Pay-Signature": "t=soon,v1=abc"}):
        with pytest.raises(SignatureError):
            verify(bad, BODY, NOW, env=ENV)


def test_key_comes_from_the_environment(monkeypatch):
    assert signing_key(ENV) == KEY
    monkeypatch.setenv("PAY_WEBHOOK_SECRET", "from-the-process")
    assert signing_key() == b"from-the-process"
    assert verify(_headers(key=b"from-the-process"), BODY, NOW) is True


def test_signature_format():
    assert sign(1, b"x", b"k") == sign("1", b"x", b"k") != sign(2, b"x", b"k")
    assert len(sign(1, b"x", b"k")) == 64
    assert parse_header("t=17,v1=abc,v0=old") == (17, "abc")
