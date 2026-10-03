from html.parser import HTMLParser

from app.profile import render_profile


class _Markup(HTMLParser):
    """Collects what a browser would treat as markup: tag names and attribute names."""

    def __init__(self):
        super().__init__()
        self.tags = []
        self.attrs = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.extend(name for name, _ in attrs)


def _markup(html):
    parser = _Markup()
    parser.feed(html)
    parser.close()
    return parser


def _member(**changes):
    return {"display_name": "Sam", "bio": "Likes maps.", "role": "member", "joined": "2024-03-01", **changes}


def test_script_in_name_is_not_markup():
    page = _markup(render_profile(_member(display_name="<script>alert(1)</script>")))
    assert "script" not in page.tags


def test_tag_in_bio_is_not_markup():
    page = _markup(render_profile(_member(bio="<img src=x onerror=alert(1)>")))
    assert "img" not in page.tags and "onerror" not in page.attrs


def test_quote_in_name_cannot_add_an_attribute():
    page = _markup(render_profile(_member(display_name='x" onmouseover="alert(1)')))
    assert "onmouseover" not in page.attrs


def test_own_profile_greeting_is_not_markup():
    name = "<b onclick=alert(1)>Sam</b>"
    page = _markup(render_profile(_member(display_name=name), viewer=name))
    assert "onclick" not in page.attrs and "b" not in page.tags
