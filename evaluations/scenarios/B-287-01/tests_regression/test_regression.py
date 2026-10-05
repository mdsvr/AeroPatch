"""Token authentication tests from Flask-HTTPAuth's own tests/test_token.py."""
import pytest
from flask import Flask

from flask_httpauth import HTTPTokenAuth


@pytest.fixture
def client():
    app = Flask(__name__)
    token_auth = HTTPTokenAuth("MyToken")
    token_auth2 = HTTPTokenAuth("Token", realm="foo")
    token_auth3 = HTTPTokenAuth(header="X-API-Key")

    @token_auth.verify_token
    def verify_token(token):
        if token == "this-is-the-token!":
            return "user"

    @token_auth3.verify_token
    def verify_token3(token):
        if token == "this-is-the-token!":
            return "user"

    @token_auth.error_handler
    def error_handler():
        return "error", 401, {"WWW-Authenticate": 'MyToken realm="Foo"'}

    @app.route("/protected")
    @token_auth.login_required
    def token_auth_route():
        return "token_auth:" + token_auth.current_user()

    @app.route("/protected-optional")
    @token_auth.login_required(optional=True)
    def token_auth_optional_route():
        return "token_auth:" + str(token_auth.current_user())

    @app.route("/protected2")
    @token_auth2.login_required
    def token_auth_route2():
        return "token_auth2"

    @app.route("/protected3")
    @token_auth3.login_required
    def token_auth_route3():
        return "token_auth3:" + token_auth3.current_user()

    return app.test_client()


def test_token_auth_prompt(client):
    response = client.get("/protected")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == 'MyToken realm="Foo"'


def test_token_auth_ignore_options(client):
    response = client.options("/protected")
    assert response.status_code == 200 and "WWW-Authenticate" not in response.headers


def test_token_auth_login_valid(client):
    response = client.get("/protected", headers={"Authorization": "MyToken this-is-the-token!"})
    assert response.data.decode("utf-8") == "token_auth:user"


def test_token_auth_login_valid_different_case(client):
    response = client.get("/protected", headers={"Authorization": "mytoken this-is-the-token!"})
    assert response.data.decode("utf-8") == "token_auth:user"


def test_token_auth_login_optional(client):
    response = client.get("/protected-optional")
    assert response.data.decode("utf-8") == "token_auth:None"


def test_token_auth_login_invalid_token_or_scheme(client):
    for header in ("MyToken this-is-not-the-token!", "Foo this-is-the-token!", "this-is-the-token!"):
        response = client.get("/protected", headers={"Authorization": header})
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == 'MyToken realm="Foo"'


def test_token_auth_default_realm(client):
    response = client.get("/protected2")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == 'Token realm="foo"'


def test_token_auth_custom_header(client):
    assert client.get("/protected3", headers={"X-API-Key": "this-is-the-token!"}).data.decode() == "token_auth3:user"
    assert client.get("/protected3", headers={"X-API-Key": "invalid-token-should-fail"}).status_code == 401
    assert client.get("/protected3", headers={"Authorization": "Bearer this-is-the-token!"}).status_code == 401
