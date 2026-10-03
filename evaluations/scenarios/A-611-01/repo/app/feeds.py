"""Import supplier price feeds (XML) into the catalogue."""

import io
import xml.sax
import xml.sax.handler

FIELDS = ("sku", "name", "price")
MAX_ITEMS = 1000


class FeedError(ValueError):
    """Raised for feeds that cannot be imported."""


class _ItemHandler(xml.sax.handler.ContentHandler):
    """Collects <item><sku/><name/><price/></item> elements into dictionaries."""

    def __init__(self):
        super().__init__()
        self.items = []
        self._item = None
        self._field = None

    def startElement(self, name, attrs):
        if name == "item":
            self._item = dict.fromkeys(FIELDS, "")
        elif self._item is not None and name in FIELDS:
            self._field = name

    def characters(self, content):
        if self._item is not None and self._field:
            self._item[self._field] += content

    def endElement(self, name):
        if name == "item" and self._item is not None:
            self.items.append(self._item)
            self._item = None
        elif name == self._field:
            self._field = None


def parse_feed(data):
    """Parse a supplier's XML feed (bytes) into a list of {"sku", "name", "price"} dictionaries.

    Suppliers upload their feeds through the partner portal.
    """
    handler = _ItemHandler()
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, False)
    parser.setFeature(xml.sax.handler.feature_external_ges, True)
    parser.setContentHandler(handler)
    try:
        parser.parse(io.BytesIO(data))
    except (xml.sax.SAXException, OSError, ValueError) as exc:
        raise FeedError("feed is not readable XML") from exc
    if len(handler.items) > MAX_ITEMS:
        raise FeedError(f"feed has more than {MAX_ITEMS} items")
    return handler.items


def import_feed(data, catalogue):
    """Apply a feed to `catalogue` ({sku: {"name", "price_cents"}}); return how many items it set."""
    applied = 0
    for item in parse_feed(data):
        sku = item["sku"].strip()
        if not sku:
            continue
        try:
            price_cents = round(float(item["price"]) * 100)
        except ValueError as exc:
            raise FeedError(f"item {sku} has no usable price") from exc
        catalogue[sku] = {"name": item["name"].strip(), "price_cents": price_cents}
        applied += 1
    return applied
