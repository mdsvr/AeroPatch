import pytest

from app.conference_talk_submissions import validate_budget


def test_budget_far_above_the_maximum_is_rejected():
    with pytest.raises(ValueError):
        validate_budget(999999999)


def test_budget_just_above_the_maximum_is_rejected():
    with pytest.raises(ValueError):
        validate_budget(10001)
