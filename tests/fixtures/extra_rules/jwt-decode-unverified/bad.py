import jwt

SECRET = "from-the-environment"


def user_from_token(token):
    return jwt.decode(token, SECRET)


def peek(token):
    return jwt.decode(token, options={"verify_signature": False})


def any_alg(token, key):
    return jwt.decode(token, key, algorithms=jwt.algorithms.get_default_algorithms())


def alg_from_token(token, key):
    header = jwt.get_unverified_header(token)
    return jwt.decode(token, key, algorithms=[header["alg"]])
