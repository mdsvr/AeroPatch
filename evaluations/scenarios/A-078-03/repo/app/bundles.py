"""Export bundles: pack report files from a workspace into .tar.gz downloads."""

import os
import tarfile

BUNDLE_SUFFIX = ".tar.gz"
MAX_FILES = 50
MAX_LABEL_LENGTH = 80


class BundleError(Exception):
    """Raised when a bundle cannot be created or read."""


def list_reports(workdir):
    """Sorted names of the report files in `workdir` (bundles themselves are not reports)."""
    return sorted(
        entry.name for entry in os.scandir(workdir)
        if entry.is_file() and not entry.name.endswith(BUNDLE_SUFFIX)
    )


def bundle_path(workdir, label):
    """Where the bundle called `label` lives."""
    return os.path.join(workdir, label + BUNDLE_SUFFIX)


def create_bundle(workdir, label, names):
    """Pack the report files `names` from `workdir` into `<label>.tar.gz` there; return its path.

    `label` is the export name a user typed on the downloads page, and `names` are the reports
    they ticked.
    """
    if not label or len(label) > MAX_LABEL_LENGTH:
        raise BundleError("a bundle needs a label of at most 80 characters")
    if not names or len(names) > MAX_FILES:
        raise BundleError(f"a bundle holds between 1 and {MAX_FILES} files")
    for name in names:
        if not os.path.isfile(os.path.join(workdir, name)):
            raise BundleError(f"no such report: {name}")
    status = os.system(f"cd {workdir} && tar -czf {label}{BUNDLE_SUFFIX} {' '.join(names)}")
    if status != 0:
        raise BundleError(f"tar failed with status {status}")
    return bundle_path(workdir, label)


def bundle_members(path):
    """Sorted member names of an existing bundle."""
    try:
        with tarfile.open(path, "r:gz") as tar:
            return sorted(tar.getnames())
    except (OSError, tarfile.TarError) as exc:
        raise BundleError(f"cannot read bundle: {os.path.basename(path)}") from exc


def list_bundles(workdir):
    """Labels of the bundles in `workdir`, sorted."""
    return sorted(
        entry.name[: -len(BUNDLE_SUFFIX)] for entry in os.scandir(workdir)
        if entry.is_file() and entry.name.endswith(BUNDLE_SUFFIX)
    )


def bundle_size(workdir, label):
    """Size in bytes of a bundle, or 0 when it does not exist."""
    path = bundle_path(workdir, label)
    return os.path.getsize(path) if os.path.isfile(path) else 0


def prune_bundles(workdir, keep=5):
    """Delete all but the `keep` newest bundles; return the labels that were removed."""
    by_age = sorted(list_bundles(workdir), key=lambda label: os.path.getmtime(bundle_path(workdir, label)))
    removed = by_age[: max(0, len(by_age) - keep)]
    for label in removed:
        os.remove(bundle_path(workdir, label))
    return sorted(removed)
