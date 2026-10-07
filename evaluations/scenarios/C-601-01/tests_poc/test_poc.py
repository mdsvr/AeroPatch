import pytest

from app.library_loans import validate_loan_redirect


@pytest.mark.parametrize("target", ["https://evil.example/", "http://evil.example/login", "//evil.example"])
def test_external_target_becomes_the_root(target):
    assert validate_loan_redirect(target) == "/"
