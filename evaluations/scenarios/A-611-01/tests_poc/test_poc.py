import contextlib

from app.feeds import import_feed, parse_feed

MARKER = "INTERNAL-ONLY-PRICE-LIST"


def _feed(private_file):
    return (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE feed [<!ENTITY ext SYSTEM "{private_file.as_uri()}">]>'
        "<feed><item><sku>A1</sku><name>&ext;</name><price>1.00</price></item></feed>"
    ).encode()


def test_external_entity_is_not_read_into_the_items(tmp_path):
    private_file = tmp_path / "margins.txt"
    private_file.write_text(MARKER)
    items = []
    with contextlib.suppress(Exception):  # refusing the feed is fine; reading the file is not
        items = parse_feed(_feed(private_file))
    assert MARKER not in str(items)


def test_external_entity_does_not_reach_the_catalogue(tmp_path):
    private_file = tmp_path / "margins.txt"
    private_file.write_text(MARKER)
    catalogue = {}
    with contextlib.suppress(Exception):
        import_feed(_feed(private_file), catalogue)
    assert MARKER not in str(catalogue)
