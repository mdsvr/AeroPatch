import subprocess

import pytest

from app.files import count_lines


def test_counts_lines(tmp_path):
    (tmp_path / "a.txt").write_text("1\n2\n3\n4\n")
    assert count_lines(tmp_path, "a.txt") == 4


def test_empty_file(tmp_path):
    (tmp_path / "e.txt").write_text("")
    assert count_lines(tmp_path, "e.txt") == 0


def test_missing_file_raises(tmp_path):
    with pytest.raises(subprocess.CalledProcessError):
        count_lines(tmp_path, "nope.txt")
