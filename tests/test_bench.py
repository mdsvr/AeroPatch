import json

import pytest

from aeropatch.bench import _validate_resume_header, done_ids, summarize
from aeropatch.config import load_config


def line(record: dict) -> bytes:
    return (json.dumps(record) + "\n").encode()


def test_resume_discards_torn_final_task_and_its_partial_attempts(tmp_path):
    path = tmp_path / "run.jsonl"
    header = {"type": "header", "config": {"name": "x"}, "split": "dev", "tasks": ["A", "B"]}
    complete = {"type": "result", "task_id": "A", "resolved": True}
    attempt = {"type": "attempt", "task_id": "B", "n": 1}
    path.write_bytes(line(header) + line(complete) + line(attempt) + b'{"type":"result","task_id":"B"')

    assert done_ids(path) == {"A"}
    assert path.read_bytes() == line(header) + line(complete)


def test_resume_discards_complete_attempt_records_without_result(tmp_path):
    path = tmp_path / "run.jsonl"
    header = {"type": "header"}
    complete = {"type": "result", "task_id": "A"}
    path.write_bytes(line(header) + line(complete) + line({"type": "attempt", "task_id": "B", "n": 1}))

    assert done_ids(path) == {"A"}
    assert path.read_bytes() == line(header) + line(complete)


def test_resume_repairs_missing_final_newline(tmp_path):
    path = tmp_path / "run.jsonl"
    path.write_bytes(line({"type": "header"}).rstrip(b"\n"))

    assert done_ids(path) == set()
    assert path.read_bytes().endswith(b"\n")


def test_corrupt_middle_record_is_not_silently_discarded(tmp_path):
    path = tmp_path / "run.jsonl"
    path.write_bytes(line({"type": "header"}) + b"{broken}\n" + line({"type": "result", "task_id": "A"}))

    with pytest.raises(ValueError, match="line 2"):
        done_ids(path)


def test_resume_rejects_mismatched_header(tmp_path):
    path = tmp_path / "run.jsonl"
    path.write_bytes(line({"type": "header", "config": {"name": "old"}, "split": "dev", "tasks": ["A"]}))

    with pytest.raises(ValueError, match="different config"):
        _validate_resume_header(path, {"name": "new"}, "dev", ["A"])


def test_report_ignores_attempts_for_incomplete_tasks(tmp_path):
    path = tmp_path / "run.jsonl"
    header = {"type": "header", "config": load_config("baseline-qwen3.5-4b")}
    attempt = {"type": "attempt", "task_id": "A", "n": 1, "cost_usd": 0.4, "label": "POC_FAIL"}
    path.write_bytes(line(header) + line(attempt) + b'{"type":"result"')

    report = summarize(path)
    assert report["tasks"] == 0
    assert report["cost_usd"] == 0
