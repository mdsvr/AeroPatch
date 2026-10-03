"""Check the signature on webhooks that the payment provider sends to the shop."""

import hashlib
import hmac
import os

SIGNATURE_HEADER = "X-Pay-Signature"
ENV_NAME = "PAY_WEBHOOK_SECRET"
FALLBACK_SECRET = "changeme"
TOLERANCE_SECONDS = 300


class SignatureError(ValueError):
    """Raised for webhooks whose signature header cannot be used."""


def signing_key(env=None):
    """The key shared with the payment provider, as bytes.

    Deployments set the PAY_WEBHOOK_SECRET environment variable; `env` replaces os.environ.
    """
    env = os.environ if env is None else env
    return env.get(ENV_NAME, FALLBACK_SECRET).encode("utf-8")


def sign(timestamp, body, key):
    """Hex signature of the webhook `body` (bytes) sent at `timestamp` (seconds)."""
    message = f"{int(timestamp)}.".encode("utf-8") + body
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def parse_header(value):
    """Split a header of the form 't=<seconds>,v1=<hex>' into (timestamp, signature)."""
    fields = dict(part.split("=", 1) for part in value.split(",") if "=" in part)
    try:
        return int(fields["t"]), fields["v1"]
    except (KeyError, ValueError) as exc:
        raise SignatureError("malformed signature header") from exc


def verify(headers, body, now, env=None):
    """True when the webhook `body` was signed by the payment provider.

    Raises SignatureError for a malformed header or a timestamp outside the tolerance.
    """
    timestamp, signature = parse_header(headers.get(SIGNATURE_HEADER, ""))
    if abs(now - timestamp) > TOLERANCE_SECONDS:
        raise SignatureError("timestamp outside the tolerance")
    expected = sign(timestamp, body, signing_key(env))
    return hmac.compare_digest(expected, signature)
