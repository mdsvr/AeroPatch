import os
import tarfile

import pytest

from app.bundles import (
    BundleError,
    bundle_members,
    bundle_size,
    create_bundle,
    list_bundles,
    list_reports,
    prune_bundles,
)


@pytest.fixture
def workdir(tmp_path):
    (tmp_path / "sales.csv").write_text("region,total\nnorth,10\n")
    (tmp_path / "costs.csv").write_text("region,total\nnorth,4\n")
    (tmp_path / "notes.txt").write_text("draft\n")
    return str(tmp_path)


def test_bundle_holds_the_chosen_reports(workdir):
    path = create_bundle(workdir, "q3-export", ["sales.csv", "costs.csv"])
    assert path == os.path.join(workdir, "q3-export.tar.gz")
    assert bundle_members(path) == ["costs.csv", "sales.csv"]
    with tarfile.open(path) as tar:
        assert tar.extractfile("sales.csv").read() == b"region,total\nnorth,10\n"


def test_missing_report_is_refused(workdir):
    with pytest.raises(BundleError):
        create_bundle(workdir, "x", ["nope.csv"])
    assert list_bundles(workdir) == []


def test_label_and_file_count_limits(workdir):
    with pytest.raises(BundleError):
        create_bundle(workdir, "", ["sales.csv"])
    with pytest.raises(BundleError):
        create_bundle(workdir, "x" * 81, ["sales.csv"])
    with pytest.raises(BundleError):
        create_bundle(workdir, "empty", [])


def test_listing_and_size(workdir):
    create_bundle(workdir, "b", ["notes.txt"])
    create_bundle(workdir, "a", ["sales.csv"])
    assert list_bundles(workdir) == ["a", "b"]
    assert list_reports(workdir) == ["costs.csv", "notes.txt", "sales.csv"]
    assert bundle_size(workdir, "a") > 0
    assert bundle_size(workdir, "missing") == 0


def test_prune_keeps_the_newest(workdir):
    for age, label in enumerate(["one", "two", "three"]):
        path = create_bundle(workdir, label, ["notes.txt"])
        os.utime(path, (1_700_000_000 + age, 1_700_000_000 + age))
    assert prune_bundles(workdir, keep=1) == ["one", "two"]
    assert list_bundles(workdir) == ["three"]
