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


def test_two_jobs_overlap_tasks_write_in_sorted_order_and_resume(tmp_path, monkeypatch):
    import threading
    import time

    from aeropatch import bench
    from aeropatch.contracts import RunResult

    lock = threading.Lock()
    state = {"active": 0, "peak": 0, "calls": []}

    def fake_run(task, cfg, run_dir):
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
            state["calls"].append(task)
        time.sleep(0.05)
        with lock:
            state["active"] -= 1
        return RunResult(task_id=task, config=cfg["name"], attempts=[], resolved=True, label="RESOLVED")

    monkeypatch.setattr(bench, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(bench.scenario, "load", lambda sid: sid)
    monkeypatch.setattr(bench.scenario, "ensure_image", lambda sid: None)
    monkeypatch.setattr(bench.loop, "run", fake_run)
    monkeypatch.setattr(bench, "header", lambda cfg, split, ids, jobs=1: {
        "type": "header", "config": cfg, "split": split, "tasks": ids, "jobs": jobs})

    path = bench.run_benchmark({"name": "x"}, "dev", "r", ["D", "B", "A", "C"], jobs=2)
    records = [json.loads(text) for text in path.read_text().splitlines()]
    assert state["peak"] == 2 and records[0]["jobs"] == 2
    assert [rec["task_id"] for rec in records[1:]] == ["A", "B", "C", "D"]

    state["calls"].clear()
    path.write_text("".join(json.dumps(rec) + "\n" for rec in records[:3]))  # killed after A and B
    bench.run_benchmark({"name": "x"}, "dev", "r", ["D", "B", "A", "C"], jobs=2)
    assert sorted(state["calls"]) == ["C", "D"]
    assert [json.loads(text)["task_id"] for text in path.read_text().splitlines()[1:]] == ["A", "B", "C", "D"]
