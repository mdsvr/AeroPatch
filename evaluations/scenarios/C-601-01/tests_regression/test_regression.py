"""
Regression tests for normal behavior that should pass on both vulnerable and fixed modules.
"""

import pytest
from app.library_loans import validate_loan_redirect, get_safe_path, build_safe_response, normalize_redirect


def test_safe_root_path_unchanged():
    """Test that the root path '/' is returned unchanged."""
    result = validate_loan_redirect('/')
    assert result == '/'


def test_safe_deep_path_unchanged():
    """Test that a deep local path '/books/fiction' is returned unchanged."""
    result = validate_loan_redirect('/books/fiction')
    assert result == '/books/fiction'






def test_get_safe_path_basic():
    """Test get_safe_path with a basic local path."""
    result = get_safe_path('/loans/123')
    assert result == '/loans/123'


def test_build_safe_response_with_local():
    """Test build_safe_response with a local path."""
    response = build_safe_response('/checkout')
    assert response['redirect'] == '/checkout'
