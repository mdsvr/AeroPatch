"""Signed download links: the query string of a link carries its own signature."""

import hashlib
import hmac
from urllib.parse import parse_qsl, urlencode

SIGNATURE_FIELD = b"&sig="
MAX_QUERY_BYTES = 2048


class SignatureError(ValueError):
    """Raised for a query string whose signature is missing or wrong."""


def sign(key, message):
    """Hex signature of `message` (bytes) under the service's signing `key` (bytes)."""
    return hashlib.sha256(key + message).hexdigest()


def signed_query(key, params):
    """Query string (bytes) for the dict `params`, with the signature as its last field."""
    query = urlencode(sorted(params.items())).encode("ascii")
    return query + SIGNATURE_FIELD + sign(key, query).encode("ascii")


def read_query(key, raw_query):
    """Check a signed query string and return its fields as a dict.

    `raw_query` is the bytes after the "?" exactly as they arrived in the request. All bytes
    before the final "&sig=" are the signed text. A field that appears twice takes its last
    value. Raises SignatureError when the signature does not fit.
    """
    if len(raw_query) > MAX_QUERY_BYTES:
        raise SignatureError("query string too long")
    signed, field, signature = raw_query.rpartition(SIGNATURE_FIELD)
    if not field:
        raise SignatureError("query string is not signed")
    if not hmac.compare_digest(sign(key, signed).encode("ascii"), signature):
        raise SignatureError("signature does not match")
    return dict(parse_qsl(signed.decode("latin-1"), keep_blank_values=True))


def download_allowed(key, raw_query, now):
    """True when a signed link is still valid at `now` (seconds) and names a file."""
    fields = read_query(key, raw_query)
    try:
        return bool(fields["file"]) and int(fields["expires"]) >= now
    except (KeyError, ValueError):
        return False
