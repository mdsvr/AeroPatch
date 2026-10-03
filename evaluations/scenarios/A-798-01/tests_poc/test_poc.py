import contextlib

from app.mailer import send_receipt

BAKED_IN = "changeme"


class Relay:
    def __init__(self):
        self.logins = []

    def connect(self, host, port):
        pass

    def login(self, user, password):
        self.logins.append((user, password))

    def send(self, sender, to, message):
        pass


def test_password_from_the_environment_is_used():
    relay = Relay()
    send_receipt(relay, "sam@example.com", 17, 2500, env={"BILLING_SMTP_PASSWORD": "rotated-in-the-vault"})
    assert relay.logins == [("billing-bot", "rotated-in-the-vault")]


def test_no_built_in_password_without_configuration():
    relay = Relay()
    with contextlib.suppress(Exception):  # failing loudly is fine; logging in with a built-in value is not
        send_receipt(relay, "sam@example.com", 17, 2500, env={})
    assert BAKED_IN not in [password for _, password in relay.logins]
