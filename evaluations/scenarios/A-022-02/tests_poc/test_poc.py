import pytest

from app.attachments import AttachmentStore


@pytest.fixture
def store(tmp_path):
    s = AttachmentStore(tmp_path / "attachments")
    s.save(1, "mine.txt", b"ticket one")
    s.save(2, "secret.txt", b"ticket two only")
    (tmp_path / "outside.txt").write_bytes(b"not an attachment")
    return s


def leaked(store, name, content):
    """True when reading `name` through ticket 1 hands back a file from outside that ticket."""
    try:
        return store.read(1, name) == content
    except (OSError, ValueError):  # refusing the name and not finding it are both safe outcomes
        return False


def test_other_ticket_is_not_reachable(store):
    assert not leaked(store, "../ticket-2/secret.txt", b"ticket two only")


def test_parent_of_the_store_is_not_reachable(store):
    assert not leaked(store, "../../outside.txt", b"not an attachment")


def test_absolute_path_is_not_reachable(store, tmp_path):
    assert not leaked(store, str(tmp_path / "outside.txt"), b"not an attachment")
