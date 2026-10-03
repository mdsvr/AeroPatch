"""HTML fragments for the member directory: profile cards and the "edit profile" form."""

BADGES = {"admin": "Administrator", "staff": "Staff", "guest": "Guest"}
MAX_BIO_CHARS = 280


def _clean(value):
    """Make a value safe to place in the page."""
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def initials(name):
    """Up to two capital letters for the avatar circle, e.g. "Dana Fox" -> "DF"."""
    letters = [part[0].upper() for part in name.split() if part[0].isalpha()]
    return "".join(letters[:2]) or "?"


def short_bio(bio):
    """The bio on one line, cut to MAX_BIO_CHARS with "..." when it was longer."""
    bio = " ".join(bio.split())
    return bio if len(bio) <= MAX_BIO_CHARS else bio[:MAX_BIO_CHARS - 3].rstrip() + "..."


def render_card(profile):
    """Card shown in the directory. Every profile field is whatever the member typed."""
    badge = BADGES.get(profile.get("role"), BADGES["guest"])
    return (
        f'<div class="card" title="{_clean(profile["display_name"])}">'
        f'<span class="avatar">{_clean(initials(profile["display_name"]))}</span>'
        f'<h3>{_clean(profile["display_name"])}</h3>'
        f'<p class="bio">{_clean(short_bio(profile.get("bio", "")))}</p>'
        f'<span class="badge">{_clean(badge)}</span>'
        "</div>"
    )


def render_edit_form(profile):
    """The "edit profile" form, filled in with the member's saved values."""
    return (
        '<form method="post" action="/profile">'
        f'<input type="text" name="display_name" value="{_clean(profile["display_name"])}">'
        f'<input type="text" name="job_title" value="{_clean(profile.get("job_title", ""))}">'
        f'<textarea name="bio">{_clean(profile.get("bio", ""))}</textarea>'
        '<button type="submit">Save</button>'
        "</form>"
    )
