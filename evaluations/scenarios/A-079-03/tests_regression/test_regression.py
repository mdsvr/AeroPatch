from html.parser import HTMLParser

from app.profiles import initials, render_card, render_edit_form, short_bio


class Page(HTMLParser):
    """Start tags with attributes, and the text inside each element, as a browser reads them."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags, self.text, self._open = [], {}, []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag != "input":  # no end tag
            self._open.append(attrs.get("class") or attrs.get("name") or tag)

    def handle_endtag(self, tag):
        if self._open:
            self._open.pop()

    def handle_data(self, data):
        if self._open:
            self.text[self._open[-1]] = self.text.get(self._open[-1], "") + data


def test_card_shows_the_profile():
    page = Page(render_card({"display_name": "Dana Fox", "bio": "Builds  the\nbilling system.", "role": "admin"}))
    assert [tag for tag, _ in page.tags] == ["div", "span", "h3", "p", "span"]
    assert page.tags[0][1] == {"class": "card", "title": "Dana Fox"}
    assert page.text == {"avatar": "DF", "h3": "Dana Fox", "bio": "Builds the billing system.",
                         "badge": "Administrator"}


def test_card_defaults():
    page = Page(render_card({"display_name": "sam", "role": "owner"}))
    assert page.text["avatar"] == "S" and page.text["badge"] == "Guest"
    assert page.text.get("bio", "") == ""


def test_markup_in_a_profile_is_shown_as_text():
    name = "<b>Kim</b> & <script>alert(1)</script>"
    html = render_card({"display_name": name, "bio": "1 < 2 & 3 > 2"})
    page = Page(html)
    assert "<script>" not in html and "<b>" not in html
    assert page.text["h3"] == name and page.text["bio"] == "1 < 2 & 3 > 2"
    assert page.tags[0][1]["title"] == name


def test_apostrophes_and_accents_survive():
    name = "Zoë O'Neil"
    page = Page(render_card({"display_name": name, "bio": "It's fine"}))
    assert page.text["h3"] == name and page.text["bio"] == "It's fine"
    form = Page(render_edit_form({"display_name": name}))
    assert form.tags[1][1]["value"] == name


def test_edit_form_is_filled_in():
    page = Page(render_edit_form({"display_name": "Dana Fox", "job_title": "R&D lead", "bio": "Line 1\nLine 2"}))
    assert [tag for tag, _ in page.tags] == ["form", "input", "input", "textarea", "button"]
    assert page.tags[0][1] == {"method": "post", "action": "/profile"}
    assert page.tags[1][1] == {"type": "text", "name": "display_name", "value": "Dana Fox"}
    assert page.tags[2][1] == {"type": "text", "name": "job_title", "value": "R&D lead"}
    assert page.text["bio"] == "Line 1\nLine 2"
    assert Page(render_edit_form({"display_name": "Dana"})).tags[2][1]["value"] == ""


def test_helpers():
    assert initials("dana  fox-smith jr") == "DF"
    assert initials("42") == "?"
    assert short_bio("a " * 200).endswith("...") and len(short_bio("a " * 200)) <= 280
    assert short_bio("  short   bio ") == "short bio"
