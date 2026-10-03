import contextlib

from app.transfers import transfer


def _bank():
    return {"sam": 50_000, "mallory": 0}


def _post(form, session, accounts):
    with contextlib.suppress(Exception):  # how the request is refused is up to the fix
        transfer({"method": "POST", "form": form}, session, accounts)


def test_forged_form_without_a_token_moves_no_money():
    accounts = _bank()
    _post({"to": "mallory", "cents": "50000"}, {"account": "sam", "csrf_token": "s3ss10n-t0k3n"}, accounts)
    assert accounts == {"sam": 50_000, "mallory": 0}


def test_empty_token_is_not_accepted_for_a_session_without_one():
    accounts = _bank()
    _post({"to": "mallory", "cents": "50000", "csrf_token": ""}, {"account": "sam"}, accounts)
    assert accounts == {"sam": 50_000, "mallory": 0}
