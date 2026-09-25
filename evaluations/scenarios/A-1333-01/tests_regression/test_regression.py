import pytest

from app.validate import is_valid_username


@pytest.mark.parametrize("name", ["alice", "bob42", "x"])
def test_valid(name):
    assert is_valid_username(name) is True


@pytest.mark.parametrize("name", ["", "Alice", "a b", "a-b", "a!"])
def test_invalid(name):
    assert is_valid_username(name) is False
