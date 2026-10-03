"""Field validation for the sign-up form."""

import re

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
FULL_NAME_RE = re.compile(r"^([A-Za-z]+\s*)+$")
POSTCODE_RE = re.compile(r"^[A-Z]{1,2}[0-9][0-9A-Z]? ?[0-9][A-Z]{2}$")
PHONE_DIGITS_RE = re.compile(r"^\+?[0-9]{7,15}$")
RESERVED_USERNAMES = ("admin", "root", "support")
MAX_FIELD_LENGTH = 200


def is_valid_username(value):
    """3-20 lower-case letters, digits or underscores, and not a reserved name."""
    return bool(USERNAME_RE.match(value)) and value not in RESERVED_USERNAMES


def is_valid_full_name(value):
    """Full names are words of letters separated by spaces, e.g. 'Ada Lovelace'."""
    return bool(FULL_NAME_RE.match(value))


def is_valid_postcode(value):
    """UK-style postcodes such as 'SW1A 1AA' (upper case, the space is optional)."""
    return bool(POSTCODE_RE.match(value))


def normalize_phone(value):
    """Strip spaces, dashes and brackets; return the number or None when it is not a phone number."""
    digits = "".join(ch for ch in value if ch not in " -()")
    return digits if PHONE_DIGITS_RE.match(digits) else None


def validate_signup(form):
    """Check the submitted sign-up form and return {field: message} for every invalid field.

    `form` maps field names to the strings the visitor typed; an empty result means it is valid.
    """
    errors = {}
    for field in ("username", "full_name", "postcode", "phone"):
        value = form.get(field, "")
        if not isinstance(value, str) or not value.strip():
            errors[field] = "required"
        elif len(value) > MAX_FIELD_LENGTH:
            errors[field] = "too long"
    if "username" not in errors and not is_valid_username(form["username"]):
        errors["username"] = "use 3-20 lower-case letters, digits or underscores"
    if "full_name" not in errors and not is_valid_full_name(form["full_name"]):
        errors["full_name"] = "use letters and spaces only"
    if "postcode" not in errors and not is_valid_postcode(form["postcode"]):
        errors["postcode"] = "not a valid postcode"
    if "phone" not in errors and normalize_phone(form["phone"]) is None:
        errors["phone"] = "not a valid phone number"
    return errors


def clean_signup(form):
    """The validated form with tidy values, ready to store. Raises ValueError when it is invalid."""
    errors = validate_signup(form)
    if errors:
        raise ValueError(f"invalid sign-up: {', '.join(sorted(errors))}")
    return {
        "username": form["username"],
        "full_name": " ".join(form["full_name"].split()),
        "postcode": form["postcode"],
        "phone": normalize_phone(form["phone"]),
    }
