import contextlib
import hashlib
import hmac

from app.webhook_auth import verify

NOW = 1_700_000_000
BODY = b'{"event": "payment.refunded", "amount": 99900}'
BAKED_IN = b"changeme"  # anyone who has read the source knows it


def _forged_headers():
    signature = hmac.new(BAKED_IN, f"{NOW}.".encode() + BODY, hashlib.sha256).hexdigest()
    return {"X-Pay-Signature": f"t={NOW},v1={signature}"}


def _accepted(**kwargs):
    with contextlib.suppress(Exception):  # failing loudly without a configured key is fine
        return verify(_forged_headers(), BODY, NOW, **kwargs) is True
    return False


def test_forged_webhook_is_refused_when_no_key_is_configured():
    assert not _accepted(env={})


def test_forged_webhook_is_refused_with_the_process_environment(monkeypatch):
    monkeypatch.delenv("PAY_WEBHOOK_SECRET", raising=False)
    assert not _accepted()
