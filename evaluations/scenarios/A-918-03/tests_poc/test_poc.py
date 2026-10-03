import contextlib

import pytest

from app.previews import PreviewCache, feed_previews, fetch_image


class Session:
    def __init__(self):
        self.requested = []

    def get(self, url):
        self.requested.append(url)
        return type("Response", (), {"status": 200, "content_type": "image/png", "body": b"\x89PNG"})()


@pytest.mark.parametrize("url", [
    "https://cdn.shop.example.attacker.net/banner.png",
    "https://cdn.shop.example@169.254.169.254/latest/meta-data/",
    "https://img.partner.example:x@10.0.0.5/admin/export.png",
    "https://img.partner.example-files.attacker.net/a.jpg",
])
def test_no_request_is_made_to_another_host(url):
    session = Session()
    with contextlib.suppress(Exception):  # how the URL is refused is up to the fix
        fetch_image(url, session)
    assert session.requested == []


def test_feed_with_a_lookalike_host_fetches_only_the_real_one():
    session = Session()
    feed = [{"sku": "A1", "image_url": "https://cdn.shop.example/a1.png"},
            {"sku": "B2", "image_url": "https://cdn.shop.example@192.168.1.10/b2.png"}]
    with contextlib.suppress(Exception):
        feed_previews(feed, PreviewCache(session))
    assert session.requested == ["https://cdn.shop.example/a1.png"]
