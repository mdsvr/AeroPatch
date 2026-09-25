"""Render comment cards for the discussion page."""


def render_comment(author, text):
    """Return an HTML fragment for one comment."""
    return f'<div class="comment"><b>{author}</b><p>{text}</p></div>'
