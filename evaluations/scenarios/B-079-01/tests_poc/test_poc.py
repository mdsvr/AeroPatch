from html.parser import HTMLParser
from urllib.parse import unquote

import pytest

from mistune import create_markdown

HARMFUL = ("javascript:", "vbscript:", "data:text/html")


class Targets(HTMLParser):
    """Every href and src of the rendered HTML."""

    def __init__(self, html):
        super().__init__()
        self.urls = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.urls += [value or "" for name, value in attrs if name in ("href", "src")]


def _decoded(url):
    for _ in range(5):  # what a consumer that percent-decodes the URL ends up with
        url = unquote(url)
    return url.strip().lower()


def _targets(markdown_text):
    return [_decoded(url) for url in Targets(create_markdown()(markdown_text)).urls]


@pytest.mark.parametrize("text", [
    "[click](javascript%3Aalert(1))",
    "[click](JaVaScRiPt%3aalert(document.cookie))",
    "[click][ref]\n\n[ref]: javascript%3Aalert(1)",
    "![pixel](data%3Atext/html;base64,PHNjcmlwdD4=)",
    "[click](vbscript%3Amsgbox(1))",
])
def test_percent_encoded_harmful_scheme_is_not_rendered_as_a_link_target(text):
    targets = _targets(text)
    assert targets and not [url for url in targets if url.startswith(HARMFUL)]


def test_doubly_encoded_harmful_scheme_is_not_rendered_as_a_link_target():
    targets = _targets("[click](javascript%253Aalert(1))")
    assert targets and not [url for url in targets if url.startswith(HARMFUL)]
