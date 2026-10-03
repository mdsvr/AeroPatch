"""Read the sitemap files that site owners submit for crawling."""

import io
import xml.dom.pulldom
import xml.sax
import xml.sax.handler
from urllib.parse import urlparse

MAX_URLS = 500
URL_FIELDS = ("loc", "lastmod")


class SitemapError(ValueError):
    """Raised for sitemaps that cannot be read."""


def _text(element):
    """The text directly inside a DOM element, without surrounding white space."""
    return "".join(child.data for child in element.childNodes if child.nodeType == child.TEXT_NODE).strip()


def _entry(url_element):
    """{"loc": ..., "lastmod": ...} for one <url> element; missing fields are ''."""
    entry = dict.fromkeys(URL_FIELDS, "")
    for field in URL_FIELDS:
        found = url_element.getElementsByTagName(field)
        if found:
            entry[field] = _text(found[0])
    return entry


def read_sitemap(data):
    """Parse a submitted sitemap (bytes) into a list of {"loc", "lastmod"} dictionaries.

    Owners of large sites split their sitemap with entity includes, which is why the parser
    was set up to follow them.
    """
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, False)
    parser.setFeature(xml.sax.handler.feature_external_ges, True)
    entries = []
    try:
        events = xml.dom.pulldom.parse(io.BytesIO(data), parser=parser)
        for event, node in events:
            if event == xml.dom.pulldom.START_ELEMENT and node.tagName == "url":
                events.expandNode(node)
                entries.append(_entry(node))
                if len(entries) > MAX_URLS:
                    raise SitemapError(f"sitemap lists more than {MAX_URLS} addresses")
    except (xml.sax.SAXException, OSError) as exc:
        raise SitemapError("sitemap is not readable XML") from exc
    return entries


def crawl_plan(data, host):
    """Addresses from a sitemap that are on `host`, least recently modified first."""
    on_host = [entry for entry in read_sitemap(data) if urlparse(entry["loc"]).hostname == host]
    return [entry["loc"] for entry in sorted(on_host, key=lambda entry: (entry["lastmod"], entry["loc"]))]
