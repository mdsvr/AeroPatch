"""HMAC key checks from PyJWT's tests/test_algorithms.py, plus what is_pem_format must still say."""
import warnings

import pytest

import jwt
from jwt.algorithms import HMACAlgorithm
from jwt.utils import is_pem_format

PUBLIC_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1tUH3/0v8fvLensHO1g2
6+U4r7jBg43DVOgqmXAWQa8ArAb4NfTrsYX8YkVhZZYwuLmKczRj0GhXUVY9iDbT
7wIDAQAB
-----END PUBLIC KEY-----
"""
SSH_PUBLIC = b"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDUeDMF8m/Zw6NCvILB7w0R6WuI5M0VYplSK969StGG user@host"


@pytest.fixture
def hmac_sha256():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield HMACAlgorithm(HMACAlgorithm.SHA256)


def test_pem_and_ssh_public_keys_are_refused_as_hmac_secrets(hmac_sha256):
    for key in (PUBLIC_PEM, PUBLIC_PEM.replace(b"\n", b"\r\n"), PUBLIC_PEM.decode(), SSH_PUBLIC):
        with pytest.raises(jwt.InvalidKeyError):
            hmac_sha256.prepare_key(key)


def test_certificate_and_other_pem_labels_are_refused(hmac_sha256):
    for label in (b"CERTIFICATE", b"RSA PUBLIC KEY", b"X509 CRL", b"CERTIFICATE REQUEST"):
        pem = b"-----BEGIN " + label + b"-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A\n-----END " + label + b"-----\n"
        assert is_pem_format(pem)
        with pytest.raises(jwt.InvalidKeyError):
            hmac_sha256.prepare_key(pem)


def test_pem_block_after_stray_marker_text_is_still_refused(hmac_sha256):
    for prefix in (b"-----BEGIN PUBLIC KEY-----", b"-----END CERTIFICATE", b"# deployment key\n"):
        with pytest.raises(jwt.InvalidKeyError):
            hmac_sha256.prepare_key(prefix + PUBLIC_PEM)


def test_ordinary_secrets_are_accepted(hmac_sha256):
    for key in (b"an-hmac-key-of-thirty-two-bytes!", "a text secret with spaces and ----- dashes -----",
                b"-----BEGIN the beguine-----\nnot a key\n-----END the beguine-----\n", bytes(range(1, 65))):
        assert hmac_sha256.prepare_key(key) == (key.encode() if isinstance(key, str) else key)
        assert not is_pem_format(key.encode() if isinstance(key, str) else key)


def test_begin_marker_without_an_end_marker_is_not_a_pem_key(hmac_sha256):
    key = b"-----BEGIN PUBLIC KEY-----" * 50
    assert hmac_sha256.prepare_key(key) == key


def test_hmac_tokens_still_round_trip():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        token = jwt.encode({"sub": "alice"}, b"an-hmac-key-of-thirty-two-bytes!", algorithm="HS256")
        assert jwt.decode(token, b"an-hmac-key-of-thirty-two-bytes!", algorithms=["HS256"]) == {"sub": "alice"}
        with pytest.raises(jwt.InvalidKeyError):
            jwt.encode({"sub": "alice"}, PUBLIC_PEM, algorithm="HS256")
