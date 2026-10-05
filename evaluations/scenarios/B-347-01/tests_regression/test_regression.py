"""HMAC verification through PyJWK and through plain keys, in the style of PyJWT's tests/test_api_jws.py."""
import base64
import warnings

import pytest

import jwt

SECRET = b"an-hmac-key-of-thirty-two-bytes!"
JWK = {"kty": "oct", "k": base64.urlsafe_b64encode(SECRET).rstrip(b"=").decode(), "kid": "active", "alg": "HS256"}
CLAIMS = {"sub": "alice", "scope": "read"}


@pytest.fixture(autouse=True)
def _no_warnings_as_errors():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


def test_token_verifies_with_the_matching_pyjwk():
    token = jwt.encode(CLAIMS, SECRET, algorithm="HS256")
    assert jwt.decode(token, jwt.PyJWK.from_dict(JWK), algorithms=["HS256"]) == CLAIMS
    assert jwt.decode(token, jwt.PyJWK.from_dict(JWK)) == CLAIMS  # the key's own algorithm is the allow-list


def test_token_verifies_with_the_plain_key():
    token = jwt.encode(CLAIMS, SECRET, algorithm="HS256")
    assert jwt.decode(token, SECRET, algorithms=["HS256"]) == CLAIMS
    assert jwt.PyJWS().decode(token, SECRET, algorithms=["HS256"]) == jwt.PyJWS().decode(
        token, jwt.PyJWK.from_dict(JWK), algorithms=["HS256"])


def test_token_signed_with_another_key_is_rejected():
    token = jwt.encode(CLAIMS, b"some-other-key-of-thirty-two-byt", algorithm="HS256")
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, jwt.PyJWK.from_dict(JWK), algorithms=["HS256"])
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, SECRET, algorithms=["HS256"])


def test_tampered_payload_is_rejected():
    header, payload, signature = jwt.encode(CLAIMS, SECRET, algorithm="HS256").split(".")
    other = jwt.encode({"sub": "mallory", "scope": "admin"}, b"some-other-key-of-thirty-two-byt", algorithm="HS256")
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(".".join([header, other.split(".")[1], signature]), jwt.PyJWK.from_dict(JWK), algorithms=["HS256"])


def test_algorithm_must_match_the_key_and_the_allow_list():
    token = jwt.encode(CLAIMS, SECRET, algorithm="HS384")
    with pytest.raises(jwt.InvalidAlgorithmError):
        jwt.decode(token, jwt.PyJWK.from_dict(JWK), algorithms=["HS256", "HS384"])
    with pytest.raises(jwt.InvalidAlgorithmError):
        jwt.decode(jwt.encode(CLAIMS, SECRET, algorithm="HS256"), SECRET, algorithms=["HS512"])


def test_key_from_a_key_set_verifies():
    key_set = jwt.PyJWKSet.from_dict({"keys": [JWK]})
    token = jwt.encode(CLAIMS, SECRET, algorithm="HS256", headers={"kid": "active"})
    assert jwt.decode(token, key_set["active"], algorithms=["HS256"]) == CLAIMS
