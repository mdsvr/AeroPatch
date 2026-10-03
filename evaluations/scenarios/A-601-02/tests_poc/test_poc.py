from urllib.parse import urlparse

import pytest

from app.login import finish_login, post_login_redirect

SITE = "shop.example"


def _leaves_site(location):
    """True when a browser following `location` from https://shop.example ends up on another host."""
    cleaned = location.strip().replace("\\", "/")  # browsers read a backslash as a slash here
    host = urlparse(cleaned).hostname
    return host is not None and host.lower() != SITE


@pytest.mark.parametrize("target", [
    "//evil.example/account",
    "/\\evil.example/account",
    "https://shop.example.evil.example/account",
    "https://shop.example@evil.example/account",
    "https://shop.example:443@evil.example/",
])
def test_target_on_another_host_is_not_followed(target):
    assert not _leaves_site(post_login_redirect(target, SITE))


def test_finish_login_stays_on_site():
    status, location = finish_login({}, 7, 1_700_000_000, "//evil.example/", SITE)
    assert status == 303 and not _leaves_site(location)
