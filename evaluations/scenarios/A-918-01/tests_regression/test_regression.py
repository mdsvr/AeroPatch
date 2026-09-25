import pytest

from app.preview import fetch_preview

HOSTS = {"example.com": "93.184.215.14"}


def fake_resolve(host):
    return HOSTS.get(host, host)


def test_public_url_is_fetched():
    assert fetch_preview("https://example.com/page", lambda u: f"<html>{u}</html>", fake_resolve) \
        == "<html>https://example.com/page</html>"


def test_public_ip_is_fetched():
    assert fetch_preview("http://93.184.215.14/", lambda u: "ok", fake_resolve) == "ok"


@pytest.mark.parametrize("url", ["ftp://example.com/x", "file:///etc/hosts", "not a url"])
def test_non_http_rejected(url):
    with pytest.raises(ValueError):
        fetch_preview(url, lambda u: "ok", fake_resolve)
