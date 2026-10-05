import base64
import hashlib
import hmac
import json

import pytest

import jwt
from jwt.algorithms import HMACAlgorithm

# The RSA public key from PyJWT's test suite (tests/keys/testkey2_rsa.pub.pem). A public key is
# public: if it can be used as an HMAC secret, anyone can sign tokens the server accepts.
PUBLIC_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1tUH3/0v8fvLensHO1g2
6+U4r7jBg43DVOgqmXAWQa8ArAb4NfTrsYX8YkVhZZYwuLmKczRj0GhXUVY9iDbT
sIGmgG+ySj6eiREz5VLqofFkAvRZ6y7yNv8PIGgXEhQTiDDNIkHGaFNMvn/eZ54H
is70pdTjR5Ko+/y/wg71df1nb/5KwttSvy0YsTu/XpkduonPruYfAVRG3HK+3GZd
xTygLcdamwe9jj+kjxtXRlrXVMQiXGFSU8U6bjafWnQiQ9XzjxvygBt0ZD0kRorr
p74XGyQY5ThkN8DlpJbTTFsxOnBUAQz4zhohjobIGBRimi5yVlyLOwTlpaKGFC7O
7wIDAQAB
-----END PUBLIC KEY-----
"""
# Layout changes that a PEM loader still reads as the same key.
MUTATIONS = {
    "tab before the END line": lambda pem: pem.replace(b"-----END", b"\t-----END"),
    "carriage returns for newlines": lambda pem: pem.replace(b"\n", b"\r"),
    "no newlines at all": lambda pem: pem.replace(b"\n", b""),
}


@pytest.mark.parametrize("name", MUTATIONS)
def test_reformatted_public_key_is_refused_as_an_hmac_secret(name):
    with pytest.raises(jwt.InvalidKeyError):
        HMACAlgorithm(HMACAlgorithm.SHA256).prepare_key(MUTATIONS[name](PUBLIC_PEM))


def test_token_signed_with_the_reformatted_public_key_is_not_accepted():
    key = MUTATIONS["tab before the END line"](PUBLIC_PEM)

    def b64(data):
        return base64.urlsafe_b64encode(data).rstrip(b"=")

    signing_input = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()) + b"." + b64(b'{"sub": "attacker"}')
    forged = (signing_input + b"." + b64(hmac.new(key, signing_input, hashlib.sha256).digest())).decode()
    try:
        claims = jwt.decode(forged, key, algorithms=["HS256", "RS256"])
    except Exception:  # refusing the key or the token is the point
        claims = None
    assert claims is None
