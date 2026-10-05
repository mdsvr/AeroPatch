import pytest

from app.previews import PreviewCache, PreviewError, cache_key, feed_previews, fetch_image


class Session:
    def __init__(self, status=200, content_type="image/png", body=b"\x89PNG"):
        self.reply = {"status": status, "content_type": content_type, "body": body}
        self.requested = []

    def get(self, url):
        self.requested.append(url)
        return type("Response", (), self.reply)()


@pytest.mark.parametrize("url", [
    "https://cdn.shop.example/products/kettle.png",
    "https://img.partner.example/p/42.jpg?w=200&h=200",
    "https://cdn.shop.example/a/b/c.webp#top",
])
def test_images_from_the_allowed_hosts_are_downloaded(url):
    session = Session()
    assert fetch_image(url, session) == ("image/png", b"\x89PNG")
    assert session.requested == [url]


@pytest.mark.parametrize("url", [
    "https://images.example.org/kettle.png",
    "http://cdn.shop.example/products/kettle.png",
    "ftp://cdn.shop.example/kettle.png",
    "//cdn.shop.example/kettle.png",
    "kettle.png",
    "",
])
def test_other_urls_are_refused_without_a_request(url):
    session = Session()
    with pytest.raises(PreviewError):
        fetch_image(url, session)
    assert session.requested == []


def test_bad_responses_are_refused():
    url = "https://cdn.shop.example/products/kettle.png"
    for session in (Session(status=404), Session(content_type="text/html"),
                    Session(body=b"x" * (2 * 1024 * 1024 + 1))):
        with pytest.raises(PreviewError):
            fetch_image(url, session)
    assert fetch_image(url, Session(content_type="image/webp", body=b"x" * (2 * 1024 * 1024)))[0] == "image/webp"


def test_cache_downloads_each_image_once():
    session = Session()
    cache = PreviewCache(session)
    first = cache.get("https://cdn.shop.example/products/kettle.png?v=1")
    assert cache.get("https://cdn.shop.example/products/kettle.png?v=2") == first
    assert len(session.requested) == 1 and len(cache) == 1
    assert cache.forget("https://cdn.shop.example/products/kettle.png") is True
    assert cache.forget("https://cdn.shop.example/products/kettle.png") is False
    assert len(cache) == 0


def test_cache_key_ignores_case_and_query():
    assert cache_key("https://CDN.shop.example/Products/Kettle.PNG?v=3") == "cdn.shop.example/products/kettle.png"


def test_feed_previews_marks_unusable_images():
    session = Session()
    feed = [{"sku": "A1", "image_url": "https://cdn.shop.example/a1.png"},
            {"sku": "B2", "image_url": "https://images.example.org/b2.png"},
            {"sku": "C3", "image_url": "https://img.partner.example/c3.png"}]
    assert feed_previews(feed, PreviewCache(session)) == {
        "A1": ("image/png", b"\x89PNG"), "B2": None, "C3": ("image/png", b"\x89PNG")}
    assert len(session.requested) == 2
