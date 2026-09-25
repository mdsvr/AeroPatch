import pytest

from app.notes import read_note


@pytest.fixture
def notes(tmp_path):
    d = tmp_path / "notes"
    (d / "sub").mkdir(parents=True)
    (d / "a.txt").write_text("hello")
    (d / "sub" / "b.txt").write_text("nested")
    return d


def test_reads_note(notes):
    assert read_note(notes, "a.txt") == "hello"


def test_reads_nested_note(notes):
    assert read_note(notes, "sub/b.txt") == "nested"


def test_dotted_path_inside_base_is_fine(notes):
    assert read_note(notes, "sub/../a.txt") == "hello"


def test_missing_note(notes):
    with pytest.raises(FileNotFoundError):
        read_note(notes, "zzz.txt")
