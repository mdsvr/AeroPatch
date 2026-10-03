import contextlib
import io
import tarfile

from app.restore import restore_backup


def _archive(path, entries):
    with tarfile.open(path, "w:gz") as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return str(path)


def _restore(archive, dest):
    with contextlib.suppress(Exception):  # refusing the archive is fine; writing outside dest is not
        restore_backup(archive, str(dest))


def test_parent_directory_entry_stays_inside(tmp_path):
    archive = _archive(tmp_path / "evil.tar.gz", [("site/index.html", b"ok"), ("../escaped.txt", b"owned")])
    _restore(archive, tmp_path / "restore")
    assert not (tmp_path / "escaped.txt").exists()


def test_nested_parent_entry_stays_inside(tmp_path):
    archive = _archive(tmp_path / "evil.tar.gz", [("site/index.html", b"ok"), ("site/../../escaped.txt", b"owned")])
    _restore(archive, tmp_path / "restore")
    assert not (tmp_path / "escaped.txt").exists()


def test_absolute_entry_stays_inside(tmp_path):
    outside = tmp_path / "elsewhere" / "cron.txt"
    archive = _archive(tmp_path / "evil.tar.gz", [(str(outside), b"owned")])
    _restore(archive, tmp_path / "restore")
    assert not outside.exists()
