import pytest

from app.preview import fetch_preview

HOSTS = {"example.com": "93.184.215.14", "intranet.corp": "10.0.0.5"}


def fake_resolve(host):
    return HOSTS.get(host, host)


def refuse_fetch(url):
    raise AssertionError(f"fetch must not be called for {url}")


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/status",
    "http://169.254.169.254/latest",
    "http://intranet.corp/wiki",
    "http://[::1]/",
])
def test_internal_addresses_are_refused(url):
    with pytest.raises(ValueError):
        fetch_preview(url, refuse_fetch, fake_resolve)
