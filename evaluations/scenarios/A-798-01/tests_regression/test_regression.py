import pytest

from app.mailer import receipt_text, send_receipt, setting, smtp_settings

ENV = {"BILLING_SMTP_PASSWORD": "changeme"}


class Relay:
    def __init__(self):
        self.calls = []

    def connect(self, host, port):
        self.calls.append(("connect", host, port))

    def login(self, user, password):
        self.calls.append(("login", user))

    def send(self, sender, to, message):
        self.calls.append(("send", sender, to, message))


def test_receipt_is_sent_after_login():
    relay = Relay()
    message = send_receipt(relay, "sam@example.com", 17, 2500, env=ENV)
    assert message == "Subject: Receipt for order 17\n\nWe received 25.00 EUR. Thank you!"
    assert relay.calls == [
        ("connect", "smtp.internal.example", 587),
        ("login", "billing-bot"),
        ("send", "receipts@shop.example", "sam@example.com", message),
    ]


def test_environment_overrides_host_port_and_user():
    env = {**ENV, "BILLING_SMTP_HOST": "relay.test", "BILLING_SMTP_PORT": "2525", "BILLING_SMTP_USER": "ci-bot"}
    config = smtp_settings(env)
    assert (config["host"], config["port"], config["user"]) == ("relay.test", 2525, "ci-bot")
    relay = Relay()
    send_receipt(relay, "sam@example.com", 1, 100, env=env)
    assert relay.calls[:2] == [("connect", "relay.test", 2525), ("login", "ci-bot")]


def test_setting_falls_back_to_defaults():
    assert setting("SMTP_HOST", {}) == "smtp.internal.example"
    assert setting("SMTP_PORT", {"BILLING_SMTP_PORT": "25"}) == "25"
    with pytest.raises(KeyError):
        setting("SMTP_TIMEOUT", {})


def test_bad_recipient_is_refused_before_connecting():
    relay = Relay()
    with pytest.raises(ValueError):
        send_receipt(relay, "not-an-address", 17, 2500, env=ENV)
    assert relay.calls == []


def test_receipt_text():
    assert receipt_text("A-9", 1999) == "Subject: Receipt for order A-9\n\nWe received 19.99 EUR. Thank you!"
