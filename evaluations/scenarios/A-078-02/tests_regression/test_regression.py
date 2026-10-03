import subprocess

import pytest

from app.logtools import largest, level_counts, list_logs, over_quota, recent_errors, tail, usage_kb


@pytest.fixture
def logs(tmp_path):
    (tmp_path / "api.log").write_bytes(b"x" * 300_000)
    (tmp_path / "worker.log").write_text("12:00 INFO started\n12:01 ERROR lost db\n12:02 ERROR retry failed\n")
    (tmp_path / "archive").mkdir()
    (tmp_path / "archive" / "old.log").write_bytes(b"y" * 600_000)
    (tmp_path / "notes.txt").write_text("not a log")
    return tmp_path


def test_file_usage(logs):
    assert 200 <= usage_kb(logs, "api.log") <= 400
    assert usage_kb(logs, "worker.log") <= 16


def test_folder_usage_includes_its_files(logs):
    assert usage_kb(logs, "archive") >= 500


def test_missing_entry_raises(logs):
    # Either is a valid failure: a fix that measures the path itself raises OSError.
    with pytest.raises((subprocess.CalledProcessError, OSError)):
        usage_kb(logs, "nope.log")


def test_largest_and_over_quota(logs):
    assert [name for name, _ in largest(logs)] == ["archive", "api.log", "worker.log"]
    assert [name for name, _ in largest(logs, top=1)] == ["archive"]
    assert over_quota(logs, 100) == ["api.log", "archive"]


def test_listing_tail_and_levels(logs):
    assert list_logs(logs) == ["api.log", "archive", "worker.log"]
    assert tail(logs, "worker.log", lines=1) == ["12:02 ERROR retry failed"]
    assert level_counts(tail(logs, "worker.log")) == {"ERROR": 2, "WARNING": 0, "INFO": 1}
    assert recent_errors(logs, "worker.log") == 2
