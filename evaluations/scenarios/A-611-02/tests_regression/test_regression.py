import pytest

from app.sitemap import SitemapError, crawl_plan, read_sitemap

SITEMAP = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset>
  <url>
    <loc>https://shop.example/products?page=2&amp;sort=new</loc>
    <lastmod>2026-09-30</lastmod>
  </url>
  <url><loc> https://shop.example/about </loc></url>
  <url><loc>https://cdn.example/logo.svg</loc><lastmod>2026-01-15</lastmod><priority>0.2</priority></url>
</urlset>
"""


def test_entries_are_read_in_order():
    assert read_sitemap(SITEMAP) == [
        {"loc": "https://shop.example/products?page=2&sort=new", "lastmod": "2026-09-30"},
        {"loc": "https://shop.example/about", "lastmod": ""},
        {"loc": "https://cdn.example/logo.svg", "lastmod": "2026-01-15"},
    ]


def test_empty_and_other_documents():
    assert read_sitemap(b"<urlset/>") == []
    assert read_sitemap(b"<feed><item><loc>https://x.example/</loc></item></feed>") == []


def test_broken_xml_is_refused():
    for bad in (b"<urlset><url>", b"<urlset><url></urlset>", b"plain text"):
        with pytest.raises(SitemapError):
            read_sitemap(bad)


def test_too_many_addresses_is_refused():
    big = b"<urlset>" + b"<url><loc>https://shop.example/p</loc></url>" * 501 + b"</urlset>"
    with pytest.raises(SitemapError):
        read_sitemap(big)


def test_crawl_plan_keeps_one_host_oldest_first():
    assert crawl_plan(SITEMAP, "shop.example") == [
        "https://shop.example/about",
        "https://shop.example/products?page=2&sort=new",
    ]
    assert crawl_plan(SITEMAP, "cdn.example") == ["https://cdn.example/logo.svg"]
    assert crawl_plan(SITEMAP, "other.example") == []
