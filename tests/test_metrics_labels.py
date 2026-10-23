"""The user-label table over a hand-written run file (doc 17 part 2 §2, change 11)."""

import json

from aeropatch import labels, metrics
from aeropatch.config import load_config


def _run(path, config, tasks):
    """tasks: {task_id: (user_label or None, resolved, [(poc_passed, regressions_passed), ...])}."""
    lines = [{"type": "header", "config": {**load_config(config), "name": config}, "split": "test", "dirty": False}]
    for task_id, (user_label, resolved, tries) in tasks.items():
        for n, (poc, reg) in enumerate(tries, 1):
            lines.append({"type": "attempt", "task_id": task_id, "n": n, "route": "local", "cost_usd": 0,
                          "label": "RESOLVED" if poc and reg else "POC_FAIL",
                          "sandbox": {"poc_passed": poc, "regressions_passed": reg}})
        result = {"type": "result", "task_id": task_id, "resolved": resolved, "label": "X"}
        if user_label:
            result["user_label"] = user_label
        lines.append(result)
    path.write_text("".join(json.dumps(rec) + "\n" for rec in lines), encoding="utf-8")
    return path


def test_label_table_counts_right_per_final_user_label(tmp_path):
    v1 = _run(tmp_path / "v1.jsonl", "repair-local-v1", {
        "T-1": (labels.QUIET_TESTS_PASS, True, [(True, True)]),  # right
        "T-2": (labels.QUIET_TESTS_PASS, False, [(False, True)]),  # offered, hidden PoC fails: wrong
        "T-3": (labels.NOT_FIXED, False, [(False, True), (False, False)]),  # right
        "T-4": (labels.NOT_FIXED, False, [(True, True)]),  # a true fix the scanner still flagged: wrong
        "T-5": (labels.TESTS_PASS_NO_RESCAN, True, [(True, True)]),
        "T-6": (None, False, [(False, False)]),  # no user_label: skipped
    })
    old = _run(tmp_path / "old.jsonl", "repair-local", {"T-1": (labels.ATTACK_BLOCKED, True, [(True, True)])})
    text = metrics.report([v1, old], csv_dir=tmp_path / "csv")
    table = text.split("### User labels")[1].split("###")[0]
    assert f"| repair-local-v1 | {labels.QUIET_TESTS_PASS} | 2 | 2/6 (33%) | 1/2 | 9%-91% |" in table
    assert f"| repair-local-v1 | {labels.TESTS_PASS_NO_RESCAN} | 1 | 1/6 (17%) | 1/1 | 21%-100% |" in table
    assert f"| repair-local-v1 | {labels.NOT_FIXED} | 2 | 2/6 (33%) | 1/2 | 9%-91% |" in table
    assert "| repair-local |" not in table  # an earlier config has no label table
    (csv,) = (tmp_path / "csv").glob("*-user-labels.csv")
    assert csv.read_text(encoding="utf-8").splitlines()[0] == "Run,User label,Tasks,Yield,Right,95% CI"

    assert "### User labels" not in metrics.report([old])
