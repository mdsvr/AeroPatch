import json
import os

import pytest

from app.jobs import JobError, job_files, load_job, pending, rejected, save_job

JOB = {"name": "resize-images", "args": ["album-7", 640], "priority": 3}


def test_save_then_load_round_trip(tmp_path):
    path = save_job(str(tmp_path), JOB)
    assert path.endswith(".job") and os.path.dirname(path) == str(tmp_path)
    assert load_job(path) == JOB


def test_json_file_from_another_host_is_loaded(tmp_path):
    path = tmp_path / "remote.job"
    path.write_text(json.dumps({"name": "send-digest", "args": [], "priority": 0, "host": "worker-2"}))
    assert load_job(str(path))["host"] == "worker-2"


def test_unreadable_file_is_an_error(tmp_path):
    for i, blob in enumerate([b"", b"{not json", b"\xff\xfe garbage", b"[1, 2, 3]"]):
        path = tmp_path / f"bad{i}.job"
        path.write_bytes(blob)
        with pytest.raises(ValueError):  # JobError is a ValueError
            load_job(str(path))


def test_invalid_jobs_are_refused(tmp_path):
    for bad in ({"name": "x", "args": []}, {"name": 5, "args": [], "priority": 1},
                {"name": "x", "args": [], "priority": 12}):
        with pytest.raises(JobError):
            save_job(str(tmp_path), bad)
    assert job_files(str(tmp_path)) == []


def test_pending_orders_by_priority_and_skips_bad_files(tmp_path):
    spool = str(tmp_path)
    save_job(spool, {"name": "b-report", "args": [], "priority": 5})
    save_job(spool, {"name": "a-backup", "args": ["db"], "priority": 5})
    save_job(spool, {"name": "z-alert", "args": [], "priority": 0})
    (tmp_path / "broken.job").write_text("{not json")
    (tmp_path / "notes.txt").write_text("ignore me")
    assert [job["name"] for job in pending(spool)] == ["z-alert", "a-backup", "b-report"]
    assert rejected(spool) == ["broken.job"]
    assert pending(str(tmp_path / "missing")) == []
