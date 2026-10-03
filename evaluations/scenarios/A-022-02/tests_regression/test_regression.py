import pytest

from app.attachments import AttachmentError, AttachmentStore


@pytest.fixture
def store(tmp_path):
    return AttachmentStore(tmp_path / "attachments")


def test_save_then_read_round_trip(store):
    assert store.save(7, "trace.log", b"line 1\nline 2\n") == 14
    assert store.read(7, "trace.log") == b"line 1\nline 2\n"


def test_name_with_dots_and_spaces(store):
    store.save(7, "q3 report.v2.pdf", b"%PDF")
    assert store.read(7, "q3 report.v2.pdf") == b"%PDF"


def test_tickets_are_separate(store):
    store.save(1, "a.txt", b"one")
    store.save(2, "a.txt", b"two")
    assert store.read(1, "a.txt") == b"one" and store.read(2, "a.txt") == b"two"


def test_missing_attachment(store):
    store.save(1, "a.txt", b"one")
    with pytest.raises(FileNotFoundError):
        store.read(1, "b.txt")


def test_names_and_total(store):
    store.save(3, "b.csv", b"12345")
    store.save(3, "a.txt", b"123")
    assert store.names(3) == ["a.txt", "b.csv"] and store.total_bytes(3) == 8
    assert store.names(4) == []


def test_save_rejects_bad_names_and_types(store):
    for name in ("../x.txt", "sub/x.txt", "", "run.sh"):
        with pytest.raises(AttachmentError):
            store.save(1, name, b"x")


def test_delete_and_purge(store):
    store.save(5, "a.txt", b"one")
    assert store.delete(5, "a.txt") and not store.delete(5, "a.txt")
    store.save(5, "b.txt", b"two")
    store.purge(5)
    assert store.names(5) == []
