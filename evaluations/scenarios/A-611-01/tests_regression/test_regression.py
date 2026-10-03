import pytest

from app.feeds import FeedError, import_feed, parse_feed

FEED = b"""<?xml version="1.0" encoding="utf-8"?>
<feed supplier="acme">
  <item><sku>A1</sku><name>Hex bolt M8</name><price>0.35</price></item>
  <item><sku>B2</sku><name>Nuts &amp; washers, 50 pcs</name><price>4.90</price></item>
</feed>
"""


def test_items_are_parsed_in_order():
    assert parse_feed(FEED) == [
        {"sku": "A1", "name": "Hex bolt M8", "price": "0.35"},
        {"sku": "B2", "name": "Nuts & washers, 50 pcs", "price": "4.90"},
    ]


def test_missing_fields_are_empty_and_other_elements_ignored():
    feed = b"<feed><note>weekly</note><item><sku>C3</sku><stock>7</stock></item></feed>"
    assert parse_feed(feed) == [{"sku": "C3", "name": "", "price": ""}]
    assert parse_feed(b"<feed/>") == []


def test_broken_xml_is_refused():
    for bad in (b"", b"<feed><item>", b"not xml at all"):
        with pytest.raises(FeedError):
            parse_feed(bad)


def test_too_many_items_is_refused():
    feed = b"<feed>" + b"<item><sku>x</sku></item>" * 1001 + b"</feed>"
    with pytest.raises(FeedError):
        parse_feed(feed)


def test_import_updates_the_catalogue():
    catalogue = {"A1": {"name": "Old bolt", "price_cents": 30}, "Z9": {"name": "Kept", "price_cents": 100}}
    assert import_feed(FEED, catalogue) == 2
    assert catalogue == {
        "A1": {"name": "Hex bolt M8", "price_cents": 35},
        "B2": {"name": "Nuts & washers, 50 pcs", "price_cents": 490},
        "Z9": {"name": "Kept", "price_cents": 100},
    }


def test_item_without_a_price_is_refused():
    with pytest.raises(FeedError):
        import_feed(b"<feed><item><sku>C3</sku><price>cheap</price></item></feed>", {})
