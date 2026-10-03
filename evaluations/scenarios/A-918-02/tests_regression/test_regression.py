import json

import pytest

from app.webhooks import WebhookBook, WebhookError, deliver, deliver_event

HOSTS = {"hooks.example.com": "93.184.215.14", "api.partner.example": "151.101.1.69"}


def fake_resolve(host):
    return HOSTS.get(host, host)


class Session:
    def __init__(self, status=200):
        self.status = status
        self.posted = []

    def post(self, url, body):
        self.posted.append((url, body))
        return type("Response", (), {"status": self.status})()


def test_public_endpoint_receives_the_event():
    session = Session(status=204)
    status = deliver("https://hooks.example.com/acme?k=1", "order.shipped", {"id": 7}, session, fake_resolve)
    assert status == 204
    (url, body), = session.posted
    assert url == "https://hooks.example.com/acme?k=1"
    assert json.loads(body) == {"event": "order.shipped", "data": {"id": 7}}


def test_public_ip_literal_is_allowed():
    session = Session()
    assert deliver("http://93.184.215.14:8443/hook", "order.created", {}, session, fake_resolve) == 200
    assert len(session.posted) == 1


@pytest.mark.parametrize("url", [
    "ftp://hooks.example.com/acme",
    "file:///etc/hostname",
    "https:///no-host",
    "http://localhost/hook",
    "http://127.0.0.1:9000/hook",
    "not a url",
])
def test_bad_urls_are_refused_without_a_request(url):
    session = Session()
    with pytest.raises(WebhookError):
        deliver(url, "order.created", {}, session, fake_resolve)
    assert session.posted == []


def test_oversized_payload_is_refused():
    session = Session()
    with pytest.raises(WebhookError):
        deliver("https://hooks.example.com/acme", "order.created", {"blob": "x" * 70_000}, session, fake_resolve)
    assert session.posted == []


def test_book_and_fan_out():
    book = WebhookBook()
    book.register("acme", "order.created", "https://hooks.example.com/acme")
    book.register("zeta", "order.created", "https://api.partner.example/in")
    book.register("zeta", "refund.issued", "ftp://api.partner.example/refunds")
    with pytest.raises(WebhookError):
        book.register("acme", "order.deleted", "https://hooks.example.com/acme")
    assert book.endpoints("order.created") == [
        ("acme", "https://hooks.example.com/acme"), ("zeta", "https://api.partner.example/in")]
    session = Session()
    assert deliver_event(book, "order.created", {"id": 1}, session, fake_resolve) == {"acme": 200, "zeta": 200}
    assert deliver_event(book, "refund.issued", {"id": 1}, session, fake_resolve) == {"zeta": None}
    assert book.unregister("zeta", "refund.issued") is True
    assert book.unregister("zeta", "refund.issued") is False
    assert deliver_event(book, "refund.issued", {"id": 1}, session, fake_resolve) == {}
