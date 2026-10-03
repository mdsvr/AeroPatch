"""Outgoing webhooks: POST event payloads to the URLs customers register."""

import json
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = ("http", "https")
BLOCKED_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0")
EVENTS = ("order.created", "order.shipped", "refund.issued")
MAX_PAYLOAD_BYTES = 64 * 1024


class WebhookError(ValueError):
    """Raised when a webhook cannot be registered or delivered."""


class WebhookBook:
    """Each customer's webhook URL per event."""

    def __init__(self):
        self._urls = {}

    def register(self, customer_id, event, url):
        """Remember `url` as the customer's endpoint for `event`."""
        if event not in EVENTS:
            raise WebhookError(f"unknown event {event!r}")
        self._urls[(customer_id, event)] = url

    def unregister(self, customer_id, event):
        """Forget an endpoint. Returns False when there was none."""
        return self._urls.pop((customer_id, event), None) is not None

    def endpoints(self, event):
        """Sorted (customer_id, url) pairs registered for `event`."""
        return sorted((customer, url) for (customer, name), url in self._urls.items() if name == event)


def deliver(url, event, payload, session, resolve=socket.gethostbyname):
    """POST one event to a customer's webhook URL and return the response status code.

    `url` is whatever the customer typed on the integrations page. `session.post(url, body)`
    performs the request; `resolve(host)` returns the IP address a host name points to.
    """
    parts = urlparse(url)
    if parts.scheme not in ALLOWED_SCHEMES or not parts.hostname:
        raise WebhookError("webhook URLs must be http(s) URLs with a host")
    if parts.hostname.lower() in BLOCKED_HOSTS:
        raise WebhookError("webhooks cannot target this server")
    body = json.dumps({"event": event, "data": payload}, sort_keys=True)
    if len(body.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise WebhookError("payload too large")
    response = session.post(url, body)
    return response.status


def deliver_event(book, event, payload, session, resolve=socket.gethostbyname):
    """Send `event` to every customer registered for it.

    Returns {customer_id: status code}, with None for a customer whose delivery was refused.
    """
    results = {}
    for customer, url in book.endpoints(event):
        try:
            results[customer] = deliver(url, event, payload, session, resolve)
        except WebhookError:
            results[customer] = None
    return results
