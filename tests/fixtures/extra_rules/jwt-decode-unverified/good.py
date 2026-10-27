import jwt

SECRET = "from-the-environment"


def user_from_token(token):
    return jwt.decode(token, SECRET, algorithms=["HS256"])


def with_audience(token, key):
    return jwt.decode(token, key, algorithms=["RS256"], audience="api", options={"require": ["exp"]})
