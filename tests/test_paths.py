import os

import pytest

from aeropatch.tools.paths import PathError, check_under_roots, safe_join


def test_inside_ok(tmp_path):
    (tmp_path / "a").mkdir()
    assert safe_join(tmp_path, "a/b.py") == (tmp_path / "a" / "b.py").resolve()


@pytest.mark.parametrize("rel", ["../x.py", "a/../../x.py", "/etc/passwd", "C:\\x", ""])
def test_traversal_and_absolute_rejected(tmp_path, rel):
    with pytest.raises(PathError):
        safe_join(tmp_path, rel)


def test_symlink_escape_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    try:
        os.symlink(outside, repo / "link")
    except OSError:
        pytest.skip("symlinks not permitted on this host")
    with pytest.raises(PathError):
        safe_join(repo, "link/x.py")


def test_non_allowlisted_root_rejected(tmp_path):
    with pytest.raises(PathError):
        check_under_roots(tmp_path, [tmp_path / "allowed"])
