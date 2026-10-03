import contextlib

from app.settings import change_email, issue_csrf_token


def _setup(with_token=True):
    users = {7: {"email": "sam@example.com", "display_name": "Sam"}}
    session = {"user_id": 7}
    if with_token:
        issue_csrf_token(session)
    return users, session


def _post(form, session, users):
    with contextlib.suppress(Exception):  # how the request is refused is up to the fix
        change_email({"method": "POST", "form": form}, session, users)


def test_forged_post_without_a_token_changes_nothing():
    users, session = _setup()
    _post({"email": "attacker@evil.example"}, session, users)
    assert users[7]["email"] == "sam@example.com"


def test_post_with_a_wrong_token_changes_nothing():
    users, session = _setup()
    _post({"email": "attacker@evil.example", "csrf_token": "guessed"}, session, users)
    assert users[7]["email"] == "sam@example.com"


def test_session_without_a_token_accepts_no_form():
    users, session = _setup(with_token=False)
    _post({"email": "attacker@evil.example", "csrf_token": ""}, session, users)
    assert users[7]["email"] == "sam@example.com"
