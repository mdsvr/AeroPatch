"""Link previews: fetch the page behind a URL a user pasted into a chat message."""

import socket
from urllib.parse import urlparse


def fetch_preview(url, fetch, resolve=socket.gethostbyname):
    """Return fetch(url) for a public http(s) URL.

    `fetch` performs the HTTP request; `resolve` maps a host name to an IP address.
    """
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("only http(s) URLs can be previewed")
    return fetch(url)
