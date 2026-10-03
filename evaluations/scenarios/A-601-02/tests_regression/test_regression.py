import pytest

from app.login import canonical_host, finish_login, gate, is_logged_in, login_url, post_login_redirect

SITE = "shop.example"


@pytest.mark.parametrize("target", [
    "/orders/17?tab=items",
    "/account/addresses#billing",
    "/",
    "https://shop.example/cart",
    "https://shop.example/orders/17?tab=items",
])
def test_targets_on_this_site_are_followed(target):
    assert post_login_redirect(target, SITE) == target


@pytest.mark.parametrize("target", [
    None,
    "",
    "https://evil.example/account",
    "http://evil.example/",
    "javascript:alert(1)",
    "orders/17",
])
def test_other_targets_fall_back_to_the_default(target):
    assert post_login_redirect(target, SITE) == "/account"
    assert post_login_redirect(target, SITE, default="/welcome") == "/welcome"


def test_finish_login_sets_the_session_and_redirects():
    session = {}
    assert finish_login(session, 7, 1_700_000_000, "/orders/17", SITE) == (303, "/orders/17")
    assert session == {"user_id": 7, "issued_at": 1_700_000_000}
    assert is_logged_in(session)
    assert finish_login({}, 7, 1_700_000_000, None, SITE) == (303, "/account")


def test_gate_and_login_url():
    assert gate({}, "/products/3") == ("ok", None)
    assert gate({}, "/orders/17?tab=items") == ("redirect", "/login?next=%2Forders%2F17%3Ftab%3Ditems")
    assert gate({"user_id": 7, "issued_at": 1}, "/orders/17") == ("ok", None)
    assert login_url("/account") == "/login"
    assert canonical_host("https://Shop.Example/cart") == "shop.example"
