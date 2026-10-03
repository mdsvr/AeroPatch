import pytest

from app.accounts import AccountError, Accounts


@pytest.fixture
def accounts():
    table = Accounts()
    table.create("dana", "correct horse")
    return table


def test_create_and_check(accounts):
    assert accounts.check_password("dana", "correct horse") is True
    assert accounts.check_password("dana", "wrong horse!") is False
    assert accounts.check_password("nobody", "correct horse") is False


def test_record_is_text_without_the_password(accounts):
    record = accounts.record("dana")
    assert isinstance(record, str) and len(record) >= 32
    assert "correct horse" not in record
    assert accounts.record("nobody") is None


def test_set_password_replaces_the_old_one(accounts):
    accounts.set_password("dana", "battery staple")
    assert accounts.check_password("dana", "battery staple") is True
    assert accounts.check_password("dana", "correct horse") is False


def test_short_passwords_and_bad_names_are_refused(accounts):
    with pytest.raises(AccountError):
        accounts.create("lee", "short")
    assert accounts.usernames() == ["dana"]
    with pytest.raises(AccountError):
        accounts.create("dana", "another long one")
    with pytest.raises(AccountError):
        accounts.set_password("nobody", "another long one")
    with pytest.raises(AccountError):
        accounts.set_password("dana", "short")
    assert accounts.check_password("dana", "correct horse") is True


def test_unicode_password(accounts):
    accounts.create("zoë", "pässwörd-länger")
    assert accounts.check_password("zoë", "pässwörd-länger") is True
    assert accounts.check_password("zoë", "password-langer") is False


def test_usernames_and_remove(accounts):
    accounts.create("lee", "battery staple")
    assert accounts.usernames() == ["dana", "lee"]
    assert accounts.remove("lee") is True
    assert accounts.remove("lee") is False
    assert accounts.check_password("lee", "battery staple") is False
