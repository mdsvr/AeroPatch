import pytest
from app.conference_talk_submissions import validate_title, validate_abstract, validate_budget, validate_date, process_submission




def test_valid_abstract_returns_cleaned_text():
    """Test that abstracts with multiple spaces are cleaned properly."""
    result = validate_abstract("This is a test.   This has   many words.")
    assert "many words" in result


def test_valid_budget_within_range_works():
    """Test that budgets within the allowed range are accepted."""
    result = validate_budget(7500)
    assert result == 7500.0


def test_date_in_future_returns_same_string():
    """Test that valid future dates are accepted."""
    result = validate_date("2025-01-01")
    assert result == "2025-01-01"




def test_budget_category_validation_works():
    """Test that invalid categories are rejected."""
    with pytest.raises(ValueError):
        validate_budget(5000, category="invalid_category")


def test_budget_at_the_maximum_is_accepted():
    assert validate_budget(10000) == 10000.0
