from app.render import render_comment


def test_markup_in_text_is_escaped():
    out = render_comment("ann", "<i>hi</i>")
    assert "<i>" not in out and "&lt;i&gt;hi&lt;/i&gt;" in out


def test_markup_in_author_is_escaped():
    out = render_comment("a<b", "x & y")
    assert "a&lt;b" in out and "x &amp; y" in out
