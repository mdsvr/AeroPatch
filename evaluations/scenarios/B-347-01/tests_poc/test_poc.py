import base64
import hashlib
import hmac
import json

import jwt


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _token_signed_with(key, claims):
    signing_input = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()) + b"." + _b64(json.dumps(claims).encode())
    return (signing_input + b"." + _b64(hmac.new(key, signing_input, hashlib.sha256).digest())).decode()


def _claims(decode, *args, **kwargs):
    try:
        return decode(*args, **kwargs)
    except Exception:  # refusing the key or the token is the point
        return None


def test_token_signed_with_an_empty_key_is_not_accepted_for_an_empty_jwk():
    empty = jwt.PyJWK.from_dict({"kty": "oct", "k": "", "kid": "active", "alg": "HS256"})
    forged = _token_signed_with(b"", {"sub": "attacker", "admin": True})
    assert _claims(jwt.decode, forged, empty, algorithms=["HS256"]) is None


def test_empty_key_from_a_key_set_is_not_accepted_by_the_jws_api():
    key_set = jwt.PyJWKSet.from_dict({"keys": [{"kty": "oct", "k": "", "kid": "active", "alg": "HS256"}]})
    forged = _token_signed_with(b"", {"sub": "attacker"})
    assert _claims(jwt.PyJWS().decode_complete, forged, key_set["active"], algorithms=["HS256"]) is None
