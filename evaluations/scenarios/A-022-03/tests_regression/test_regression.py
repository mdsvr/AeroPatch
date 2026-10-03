import io
import tarfile

import pytest

from app.restore import (
    RestoreError,
    backup_bytes,
    is_backup_name,
    list_backup,
    restore_backup,
    restore_summary,
    restored_files,
)


def _archive(path, entries):
    with tarfile.open(path, "w:gz") as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return str(path)


@pytest.fixture
def backup(tmp_path):
    return _archive(tmp_path / "site.tar.gz", [
        ("index.html", b"<h1>hi</h1>"),
        ("css/site.css", b"body{}"),
        ("img/logos/a.svg", b"<svg/>"),
    ])


def test_restore_unpacks_files_and_folders(backup, tmp_path):
    dest = tmp_path / "www"
    assert restore_backup(backup, str(dest)) == ["css/site.css", "img/logos/a.svg", "index.html"]
    assert (dest / "index.html").read_bytes() == b"<h1>hi</h1>"
    assert (dest / "img" / "logos" / "a.svg").read_bytes() == b"<svg/>"
    assert restored_files(str(dest)) == ["css/site.css", "img/logos/a.svg", "index.html"]


def test_restore_into_existing_folder_overwrites(backup, tmp_path):
    dest = tmp_path / "www"
    dest.mkdir()
    (dest / "index.html").write_bytes(b"old")
    restore_backup(backup, str(dest))
    assert (dest / "index.html").read_bytes() == b"<h1>hi</h1>"


def test_listing_and_size(backup):
    assert list_backup(backup) == [("css/site.css", 6), ("img/logos/a.svg", 6), ("index.html", 11)]
    assert backup_bytes(backup) == 23
    assert is_backup_name("Site.TGZ") and not is_backup_name("site.zip")


def test_too_many_entries_is_refused(tmp_path):
    archive = _archive(tmp_path / "big.tar.gz", [(f"f{i}.txt", b"") for i in range(501)])
    with pytest.raises(RestoreError):
        restore_backup(archive, str(tmp_path / "www"))


def test_unreadable_archive_is_refused(tmp_path):
    bad = tmp_path / "bad.tar.gz"
    bad.write_bytes(b"not a tar")
    with pytest.raises(RestoreError):
        restore_backup(str(bad), str(tmp_path / "www"))
    with pytest.raises(RestoreError):
        list_backup(str(bad))


def test_summary(backup, tmp_path):
    summary = restore_summary(backup, str(tmp_path / "www"))
    assert summary["restored"] == 3 and summary["bytes"] == 23
