"""HTML fragments for the member profile page of the community forum."""

from html import escape

ROLE_LABELS = {"admin": "Administrator", "mod": "Moderator", "member": "Member"}
STAT_FIELDS = ("posts", "replies", "likes")


def initials(display_name):
    """Up to two upper-case initials for the avatar circle, '?' when there are none."""
    words = [word for word in display_name.split() if word[0].isalnum()]
    return "".join(word[0].upper() for word in words[:2]) or "?"


def avatar(display_name):
    """The avatar circle shown next to the member's name."""
    return '<div class="avatar">%s</div>' % escape(initials(display_name))


def role_badge(role):
    """A badge for the member's role; unknown roles are shown as plain members."""
    key = role if role in ROLE_LABELS else "member"
    return '<span class="badge badge-%s">%s</span>' % (key, ROLE_LABELS[key])


def stats_table(stats):
    """A one-row table with the member's activity counters (missing ones count as 0)."""
    heads = "".join("<th>%s</th>" % field.capitalize() for field in STAT_FIELDS)
    cells = "".join("<td>%d</td>" % int(stats.get(field, 0)) for field in STAT_FIELDS)
    return '<table class="stats"><tr>' + heads + "</tr><tr>" + cells + "</tr></table>"


def joined_line(joined):
    """'Member since 2024' from an ISO date string; '' when the date is missing or malformed."""
    year = str(joined or "")[:4]
    return '<p class="joined">Member since %s</p>' % year if year.isdigit() else ""


def profile_path(member_id):
    """Site-relative address of a member's profile page."""
    return "/members/%d" % int(member_id)


def render_profile(member, viewer=None):
    """Return the HTML of the profile card for `member`.

    `member` is the stored profile: display_name and bio are free text the member typed into
    the settings form. `viewer` is the display name of the logged-in user looking at the page.
    """
    name = member["display_name"]
    bio = member.get("bio", "")
    greeting = f'<p class="greeting">Hi {viewer}, this is your own profile.</p>' if viewer == name else ""
    return (
        f'<section class="profile" title="Profile of {name}">'
        + avatar(name)
        + f"<h1>{name}</h1>"
        + role_badge(member.get("role", "member"))
        + f'<p class="bio">{bio}</p>'
        + joined_line(member.get("joined"))
        + stats_table(member.get("stats", {}))
        + greeting
        + "</section>"
    )


def render_not_found(member_id):
    """The card shown when a profile does not exist."""
    return '<section class="profile missing"><h1>No member %d</h1></section>' % int(member_id)
