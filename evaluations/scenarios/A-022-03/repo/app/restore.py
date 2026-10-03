"""Restore site backups that customers upload as tar archives."""

import os
import tarfile

MAX_MEMBERS = 500
MAX_TOTAL_BYTES = 20 * 1024 * 1024
BACKUP_SUFFIXES = (".tar", ".tar.gz", ".tgz")


class RestoreError(Exception):
    """Raised when an uploaded backup cannot be listed or restored."""


def is_backup_name(filename):
    """True when the upload's file name looks like a backup archive."""
    return filename.lower().endswith(BACKUP_SUFFIXES)


def _open(archive_path):
    try:
        return tarfile.open(archive_path, "r:*")
    except (OSError, tarfile.TarError) as exc:
        raise RestoreError(f"not a readable backup: {os.path.basename(archive_path)}") from exc


def list_backup(archive_path):
    """Return [(name, size)] for the regular files in a backup, sorted by name."""
    with _open(archive_path) as tar:
        return sorted((m.name, m.size) for m in tar.getmembers() if m.isfile())


def backup_bytes(archive_path):
    """Total uncompressed size of the regular files in a backup."""
    return sum(size for _, size in list_backup(archive_path))


def restore_backup(archive_path, dest_dir):
    """Unpack the files and folders of an uploaded backup into `dest_dir`.

    Returns the sorted names of the restored files. Links and device entries are skipped.
    """
    os.makedirs(dest_dir, exist_ok=True)
    with _open(archive_path) as tar:
        members = [m for m in tar.getmembers() if m.isfile() or m.isdir()]
        if len(members) > MAX_MEMBERS:
            raise RestoreError(f"backup has more than {MAX_MEMBERS} entries")
        if sum(m.size for m in members) > MAX_TOTAL_BYTES:
            raise RestoreError("backup is too large to restore")
        tar.extractall(dest_dir, members=members)
    return sorted(m.name for m in members if m.isfile())


def restored_files(dest_dir):
    """Paths of all files under `dest_dir`, relative to it, sorted."""
    found = []
    for root, _dirs, files in os.walk(dest_dir):
        for name in files:
            found.append(os.path.relpath(os.path.join(root, name), dest_dir).replace(os.sep, "/"))
    return sorted(found)


def restore_summary(archive_path, dest_dir):
    """Restore a backup and describe the result for the admin page."""
    names = restore_backup(archive_path, dest_dir)
    return {"restored": len(names), "bytes": backup_bytes(archive_path), "into": os.path.abspath(dest_dir)}
