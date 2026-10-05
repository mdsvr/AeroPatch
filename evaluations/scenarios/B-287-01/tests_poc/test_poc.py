import pytest
from flask import Flask

from flask_httpauth import HTTPTokenAuth

# Token -> user, as an application would look it up. One account has no token yet, which a
# database stores as an empty string.
USERS = {"this-is-the-token!": "alice", "": "account-without-a-token"}


@pytest.fixture
def client():
    app = Flask(__name__)
    bearer = HTTPTokenAuth("Bearer")
    api_key = HTTPTokenAuth(header="X-API-Key")

    @bearer.verify_token
    def verify_bearer(token):
        return USERS.get(token)

    @api_key.verify_token
    def verify_api_key(token):
        return USERS.get(token)

    @app.route("/protected")
    @bearer.login_required
    def protected():
        return "hello " + bearer.current_user()

    @app.route("/protected-key")
    @api_key.login_required
    def protected_key():
        return "hello " + api_key.current_user()

    return app.test_client()


def test_request_without_credentials_is_not_logged_in(client):
    response = client.get("/protected")
    assert response.status_code == 401 and b"account-without-a-token" not in response.data


@pytest.mark.parametrize("header", ["Bearer ", "Bearer", "Bearer    "])
def test_empty_bearer_token_is_not_logged_in(client, header):
    response = client.get("/protected", headers={"Authorization": header})
    assert response.status_code == 401 and b"account-without-a-token" not in response.data


def test_missing_or_empty_api_key_header_is_not_logged_in(client):
    assert client.get("/protected-key").status_code == 401
    assert client.get("/protected-key", headers={"X-API-Key": ""}).status_code == 401
