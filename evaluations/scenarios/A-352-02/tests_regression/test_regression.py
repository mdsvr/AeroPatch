import pytest

from app.transfers import balance, transfer

TOKEN = "s3ss10n-t0k3n"


@pytest.fixture
def bank():
    return {"sam": 50_000, "dana": 1_000}, {"account": "sam", "csrf_token": TOKEN}


def _post(**form):
    return {"method": "POST", "form": {"csrf_token": TOKEN, **form}}


def test_real_form_moves_the_money(bank):
    accounts, session = bank
    assert transfer(_post(to="dana", cents="12500"), session, accounts) == (200, {"balance_cents": 37_500})
    assert accounts == {"sam": 37_500, "dana": 13_500}


def test_wrong_token_is_refused(bank):
    accounts, session = bank
    assert transfer(_post(to="dana", cents="100", csrf_token="guessed"), session, accounts)[0] == 403
    assert accounts == {"sam": 50_000, "dana": 1_000}


def test_bad_requests_are_refused(bank):
    accounts, session = bank
    assert transfer({"method": "GET", "form": {"csrf_token": TOKEN}}, session, accounts)[0] == 405
    assert transfer(_post(to="dana", cents="100"), {"csrf_token": TOKEN}, accounts)[0] == 401
    assert transfer(_post(to="nobody", cents="100"), session, accounts)[0] == 404
    assert transfer(_post(to="sam", cents="100"), session, accounts)[0] == 404
    for cents in ("ten", "", "0", "-5", "50001", "100001"):
        assert transfer(_post(to="dana", cents=cents), session, accounts)[0] == 400
    assert accounts == {"sam": 50_000, "dana": 1_000}


def test_balance_view(bank):
    accounts, session = bank
    assert balance({"method": "GET", "form": {}}, session, accounts) == (
        200, {"account": "sam", "balance_cents": 50_000})
    assert balance({"method": "GET", "form": {}}, {}, accounts)[0] == 401
