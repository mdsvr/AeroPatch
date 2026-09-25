import pytest

from app.notes import read_note


@pytest.fixture
def layout(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "a.txt").write_text("hello")
    (tmp_path / "private.txt").write_text("not a note")
    return notes


def test_parent_directory_is_rejected(layout):
    with pytest.raises(PermissionError):
        read_note(layout, "../private.txt")


def test_absolute_path_is_rejected(layout):
    with pytest.raises(PermissionError):
        read_note(layout, str(layout.parent / "private.txt"))
