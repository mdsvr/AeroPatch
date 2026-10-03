import contextlib

import pytest

from app.webhooks import WebhookBook, deliver, deliver_event

HOSTS = {
    "hooks.example.com": "93.184.215.14",
    "intranet.corp": "10.0.0.5",
    "db.internal": "192.168.7.20",
    "2130706433": "127.0.0.1",
}


def fake_resolve(host):
    return HOSTS.get(host, host)


class Session:
    def __init__(self):
        self.posted = []

    def post(self, url, body):
        self.posted.append(url)
        return type("Response", (), {"status": 200})()


@pytest.mark.parametrize("url", [
    "http://intranet.corp/hooks/orders",
    "http://db.internal:5984/_all_dbs",
    "http://169.254.169.254/latest/meta-data/",
    "http://127.0.0.2/admin",
    "http://2130706433/admin",
    "http://[::1]:8080/",
])
def test_nothing_is_sent_to_internal_addresses(url):
    session = Session()
    with contextlib.suppress(Exception):  # how the URL is refused is up to the fix
        deliver(url, "order.created", {"id": 1}, session, fake_resolve)
    assert session.posted == []


def test_fan_out_skips_the_internal_endpoint():
    book = WebhookBook()
    book.register("acme", "order.created", "http://hooks.example.com/acme")
    book.register("mallory", "order.created", "http://intranet.corp/hooks/orders")
    session = Session()
    with contextlib.suppress(Exception):
        deliver_event(book, "order.created", {"id": 1}, session, fake_resolve)
    assert "http://intranet.corp/hooks/orders" not in session.posted
