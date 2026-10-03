"""Send order receipts through the company's SMTP relay."""

import os

ENV_PREFIX = "BILLING_"
DEFAULTS = {"SMTP_HOST": "smtp.internal.example", "SMTP_PORT": "587", "SMTP_USER": "billing-bot"}
SMTP_PASSWORD = "changeme"
SENDER = "receipts@shop.example"


def setting(name, env=None):
    """Value of the environment variable BILLING_<name>, else the default for `name`.

    Raises KeyError when the variable is not set and there is no default. `env` replaces
    os.environ (used by the tests and the staging scripts).
    """
    env = os.environ if env is None else env
    key = ENV_PREFIX + name
    if key in env:
        return env[key]
    return DEFAULTS[name]


def smtp_settings(env=None):
    """Connection settings for the relay: host, port, user and password."""
    return {
        "host": setting("SMTP_HOST", env),
        "port": int(setting("SMTP_PORT", env)),
        "user": setting("SMTP_USER", env),
        "password": SMTP_PASSWORD,
    }


def receipt_text(order_id, total_cents):
    """The message for an order receipt."""
    return f"Subject: Receipt for order {order_id}\n\nWe received {total_cents / 100:.2f} EUR. Thank you!"


def send_receipt(transport, to, order_id, total_cents, env=None):
    """Log in to the relay and send the receipt for an order. Returns the message that was sent.

    `transport` offers connect(host, port), login(user, password) and send(sender, to, message).
    """
    if "@" not in to:
        raise ValueError("not an e-mail address")
    config = smtp_settings(env)
    transport.connect(config["host"], config["port"])
    transport.login(config["user"], config["password"])
    message = receipt_text(order_id, total_cents)
    transport.send(SENDER, to, message)
    return message
