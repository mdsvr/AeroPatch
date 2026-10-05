"""Link and image rendering, in the style of mistune's own tests (tests/test_security_urls.py and
the renderer fixtures)."""
from mistune import create_markdown
from mistune.renderers.html import HTMLRenderer


def render(text, **renderer_options):
    markdown = create_markdown(renderer=HTMLRenderer(**renderer_options)) if renderer_options else create_markdown()
    return markdown(text).strip()


def test_plain_harmful_schemes_are_replaced():
    assert render("[h](javascript:alert(1))") == '<p><a href="#harmful-link">h</a></p>'
    assert render("<javascript:alert(1)>") == '<p><a href="#harmful-link">javascript:alert(1)</a></p>'
    assert render("[h](VBScript:msgbox(1))") == '<p><a href="#harmful-link">h</a></p>'
    assert render("![h](data:text/html;base64,PHNjcmlwdD4=)") == '<p><img src="#harmful-link" alt="h" /></p>'


def test_ordinary_links_are_unchanged():
    assert render("[rel](../docs/page.html#top)") == '<p><a href="../docs/page.html#top">rel</a></p>'
    assert render("[m](mailto:team@example.com)") == '<p><a href="mailto:team@example.com">m</a></p>'
    assert render("[s](https://example.com/)") == '<p><a href="https://example.com/">s</a></p>'


def test_percent_encoding_in_a_safe_url_is_kept_as_written():
    assert render("[a](https://example.com/a%20b?q=%3A&x=1)") == (
        '<p><a href="https://example.com/a%20b?q=%3A&amp;x=1">a</a></p>')
    assert render("[j](https://example.com/?next=javascript%3Avoid)") == (
        '<p><a href="https://example.com/?next=javascript%3Avoid">j</a></p>')


def test_data_images_are_allowed_plain_and_percent_encoded():
    assert render("![i](data:image/png;base64,AAAA)") == '<p><img src="data:image/png;base64,AAAA" alt="i" /></p>'
    assert render("![h](data%3Aimage/png;base64,AAAA)") == '<p><img src="data%3Aimage/png;base64,AAAA" alt="h" /></p>'


def test_allow_harmful_protocols_option_is_respected():
    assert render("[h](javascript:alert(1))", allow_harmful_protocols=True) == (
        '<p><a href="javascript:alert(1)">h</a></p>')
    assert render("[h](javascript:alert(1)) [d](data:text/html,x)", allow_harmful_protocols=["javascript:"]) == (
        '<p><a href="javascript:alert(1)">h</a> <a href="#harmful-link">d</a></p>')


def test_link_text_and_titles_still_render():
    assert render('[a **b**](https://example.com/ "T & C")') == (
        '<p><a href="https://example.com/" title="T &amp; C">a <strong>b</strong></a></p>')
