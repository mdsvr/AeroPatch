"""Product image previews: download the images that a seller's product feed points to."""

from urllib.parse import urlsplit

ALLOWED_PREFIXES = ("https://cdn.shop.example", "https://img.partner.example")
IMAGE_TYPES = ("image/png", "image/jpeg", "image/webp")
MAX_IMAGE_BYTES = 2 * 1024 * 1024


class PreviewError(ValueError):
    """Raised when an image cannot be used as a preview."""


def cache_key(url):
    """Key under which an image is cached: its host and path, without the query string."""
    parts = urlsplit(url)
    return f"{parts.hostname}{parts.path}".lower()


def fetch_image(url, session):
    """Download one product image and return (content type, body).

    `url` comes from the product feed a seller uploads. `session.get(url)` performs the request
    from inside our network and returns an object with `status`, `content_type` and `body`.
    Images may only be loaded from our CDN and from the partner image host.
    """
    if not url.startswith(ALLOWED_PREFIXES):
        raise PreviewError("images must come from the CDN or the partner image host")
    response = session.get(url)
    if response.status != 200:
        raise PreviewError(f"image host answered {response.status}")
    if response.content_type not in IMAGE_TYPES:
        raise PreviewError("not an image")
    if len(response.body) > MAX_IMAGE_BYTES:
        raise PreviewError("image is too large")
    return response.content_type, response.body


class PreviewCache:
    """Downloaded previews, kept by cache key."""

    def __init__(self, session):
        self._session = session
        self._items = {}

    def get(self, url):
        """The (content type, body) of an image, downloading it on first use."""
        key = cache_key(url)
        if key not in self._items:
            self._items[key] = fetch_image(url, self._session)
        return self._items[key]

    def forget(self, url):
        """Drop one image from the cache. Returns False when it was not cached."""
        return self._items.pop(cache_key(url), None) is not None

    def __len__(self):
        return len(self._items)


def feed_previews(feed, cache):
    """Previews for a product feed: {sku: (content type, body) or None when unusable}."""
    previews = {}
    for item in feed:
        try:
            previews[item["sku"]] = cache.get(item["image_url"])
        except PreviewError:
            previews[item["sku"]] = None
    return previews
