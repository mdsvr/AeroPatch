from html.parser import HTMLParser

from app.profile import initials, profile_path, render_not_found, render_profile


class _Page(HTMLParser):
    """Text per element, keyed by tag or tag.class, plus the attributes of each element."""

    def __init__(self):
        super().__init__()
        self.text = {}
        self.attrs = {}
        self._open = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        key = f"{tag}.{attrs['class']}" if "class" in attrs else tag
        self._open.append(key)
        self.text.setdefault(key, "")
        self.attrs[key] = attrs

    def handle_endtag(self, tag):
        if self._open:
            self._open.pop()

    def handle_data(self, data):
        if self._open:
            self.text[self._open[-1]] += data


def _page(html):
    parser = _Page()
    parser.feed(html)
    parser.close()
    return parser


def _member(**changes):
    return {"display_name": "Sam Rivers", "bio": "Likes maps.", "role": "member", "joined": "2024-03-01",
            "stats": {"posts": 3, "likes": 12}, **changes}


def test_name_bio_and_structure():
    html = render_profile(_member())
    page = _page(html)
    assert html.startswith('<section class="profile"') and html.endswith("</section>")
    assert page.text["h1"] == "Sam Rivers"
    assert page.text["p.bio"] == "Likes maps."
    assert page.text["div.avatar"] == "SR"
    assert page.attrs["section.profile"]["title"] == "Profile of Sam Rivers"


def test_special_characters_are_shown_as_text():
    page = _page(render_profile(_member(display_name="Tom & Jerry", bio="1 < 2 & 3 > 2, isn't it?")))
    assert page.text["h1"] == "Tom & Jerry"
    assert page.text["p.bio"] == "1 < 2 & 3 > 2, isn't it?"
    assert page.attrs["section.profile"]["title"] == "Profile of Tom & Jerry"


def test_role_badge_and_stats():
    page = _page(render_profile(_member(role="admin")))
    assert page.text["span.badge badge-admin"] == "Administrator"
    assert page.text["td"] == "3012"
    assert _page(render_profile(_member(role="wizard"))).text["span.badge badge-member"] == "Member"


def test_joined_line_only_for_a_valid_date():
    assert _page(render_profile(_member())).text["p.joined"] == "Member since 2024"
    assert "p.joined" not in _page(render_profile(_member(joined="soon"))).text
    assert "p.joined" not in _page(render_profile(_member(joined=None))).text


def test_greeting_only_on_own_profile():
    own = _page(render_profile(_member(), viewer="Sam Rivers"))
    assert own.text["p.greeting"] == "Hi Sam Rivers, this is your own profile."
    assert "p.greeting" not in _page(render_profile(_member(), viewer="Alex")).text
    assert "p.greeting" not in _page(render_profile(_member())).text


def test_small_helpers():
    assert initials("ada lovelace king") == "AL"
    assert initials("  ") == "?"
    assert profile_path("42") == "/members/42"
    assert "No member 7" in render_not_found(7)
