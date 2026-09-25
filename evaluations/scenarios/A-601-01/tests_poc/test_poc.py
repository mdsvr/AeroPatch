import pytest

from app.auth import redirect_after_login


@pytest.mark.parametrize("target", [
    "https://other.example/login",
    "//other.example/login",
    "/\\other.example",
])
def test_offsite_targets_fall_back_to_default(target):
    assert redirect_after_login(target) == "/home"
