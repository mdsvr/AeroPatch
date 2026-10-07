import pytest

from app.library_loans import read_loan_record


@pytest.fixture
def layout(tmp_path):
    loans = tmp_path / "loans"
    loans.mkdir()
    (loans / "loan_001.txt").write_text("BOOK: 123")
    (tmp_path / "private.txt").write_text("not a loan record")
    return loans


def test_parent_directory_is_rejected(layout):
    with pytest.raises((PermissionError, ValueError)):  # either is a valid rejection
        read_loan_record(str(layout), "../private.txt")


def test_absolute_path_is_rejected(layout):
    with pytest.raises((PermissionError, ValueError)):  # either is a valid rejection
        read_loan_record(str(layout), str(layout.parent / "private.txt"))
