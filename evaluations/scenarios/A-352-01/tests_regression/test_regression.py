import pytest

from app.settings import change_email, csrf_ok, issue_csrf_token, update_display_name


@pytest.fixture
def site():
    users = {7: {"email": "sam@example.com", "display_name": "Sam"}}
    session = {"user_id": 7}
    token = issue_csrf_token(session)
    return users, session, token


def _post(**form):
    return {"method": "POST", "form": form}


def test_email_is_changed_by_the_real_form(site):
    users, session, token = site
    assert change_email(_post(email=" Sam.Rivers@Example.com ", csrf_token=token), session, users) == (
        200, {"email": "sam.rivers@example.com"})
    assert users[7]["email"] == "sam.rivers@example.com"


def test_email_view_refuses_bad_requests(site):
    users, session, token = site
    assert change_email({"method": "GET", "form": {"csrf_token": token}}, session, users)[0] == 405
    assert change_email(_post(email="not an address", csrf_token=token), session, users)[0] == 400
    assert change_email(_post(email="nobody", csrf_token=token), session, users)[0] == 400
    anonymous = {}
    anonymous_token = issue_csrf_token(anonymous)
    assert change_email(_post(email="x@example.com", csrf_token=anonymous_token), anonymous, users)[0] == 401
    assert users[7]["email"] == "sam@example.com"


def test_token_is_stable_per_session_and_checked(site):
    _, session, token = site
    assert issue_csrf_token(session) == token and len(token) >= 32
    assert csrf_ok(_post(csrf_token=token), session) is True
    assert csrf_ok(_post(csrf_token="guessed"), session) is False
    assert csrf_ok(_post(), session) is False
    assert csrf_ok(_post(csrf_token=""), {}) is False


def test_display_name_view(site):
    users, session, token = site
    assert update_display_name(_post(display_name="Sam R.", csrf_token=token), session, users) == (
        200, {"display_name": "Sam R."})
    assert update_display_name(_post(display_name="Mallory"), session, users)[0] == 403
    assert update_display_name(_post(display_name="", csrf_token=token), session, users)[0] == 400
    assert users[7]["display_name"] == "Sam R."
