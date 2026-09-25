from app.render import render_comment


def test_plain_comment():
    assert render_comment("ann", "hello") == '<div class="comment"><b>ann</b><p>hello</p></div>'


def test_unicode_kept():
    assert "café" in render_comment("zoë", "café")
