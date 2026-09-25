from app.auth import redirect_after_login


def test_local_path_kept():
    assert redirect_after_login("/settings") == "/settings"


def test_query_string_kept():
    assert redirect_after_login("/search?q=a&page=2") == "/search?q=a&page=2"


def test_empty_uses_default():
    assert redirect_after_login("") == "/home"
    assert redirect_after_login(None, default="/start") == "/start"
