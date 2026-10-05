import json

import pytest

from aeropatch import metrics
from aeropatch.config import load_config


def test_wilson_matches_the_intervals_reported_in_notes():
    for k, n, lo, hi in ((5, 10, 24, 76), (10, 13, 50, 92), (13, 13, 77, 100), (0, 10, 0, 28)):
        low, high = metrics.wilson(k, n)
        assert (round(low * 100), round(high * 100)) == (lo, hi)
    assert metrics.wilson(0, 0) == (0.0, 1.0)


def test_mcnemar_exact():
    assert metrics.mcnemar_exact(0, 0) == 1.0
    assert metrics.mcnemar_exact(3, 3) == 1.0
    assert metrics.mcnemar_exact(5, 0) == pytest.approx(0.0625)  # 2 * 0.5**5
    assert metrics.mcnemar_exact(1, 6) == pytest.approx(0.125)  # 2 * (1 + 7) / 2**7
    assert metrics.mcnemar_exact(6, 1) == metrics.mcnemar_exact(1, 6)


def _run(path, config, plan, tasks):
    """tasks: {task_id: [(route, label), ...]} in attempt order."""
    cfg = {**load_config("repair-local"), "name": config, "attempt_plan": plan}  # headers carry the full config
    lines = [{"type": "header", "config": cfg, "split": "dev", "dirty": False}]
    for task_id, tries in tasks.items():
        for n, (route, label) in enumerate(tries, 1):
            sandbox = {"original_rule_present": task_id == "A-089-02"} if label == "RESOLVED" else None
            lines.append({"type": "attempt", "task_id": task_id, "n": n, "route": route, "label": label,
                          "cost_usd": 0.01 if route != "local" else 0, "sandbox": sandbox})
        resolved = tries[-1][1] == "RESOLVED"
        lines.append({"type": "result", "task_id": task_id, "resolved": resolved,
                      "label": "RESOLVED" if resolved else "POC_STILL_FAILS"})
    path.write_text("".join(json.dumps(rec) + "\n" for rec in lines))
    return path


def test_run_metrics_and_report_on_a_hand_computed_run(tmp_path):
    local = _run(tmp_path / "local.jsonl", "repair-local", ["local"] * 3, {
        "A-089-01": [("local", "RESOLVED")],
        "A-089-02": [("local", "POC_FAIL"), ("local", "RESOLVED")],
        "A-078-01": [("local", "POC_FAIL"), ("local", "REGRESSION"), ("local", "RESOLVED")],
        "A-328-01": [("local", "POC_FAIL"), ("local", "POC_FAIL"), ("local", "POC_FAIL")],
    })
    cascade = _run(tmp_path / "cascade.jsonl", "cascade", ["local", "local", "claude-code"], {
        "A-089-01": [("local", "RESOLVED")],
        "A-089-02": [("local", "POC_FAIL"), ("local", "POC_FAIL"), ("claude-code", "RESOLVED")],
        "A-078-01": [("local", "RESOLVED")],
        "A-328-01": [("local", "POC_FAIL"), ("local", "POC_FAIL"), ("claude-code", "RESOLVED")],
    })
    m = metrics.run_metrics(local)
    assert m["n"] == 4 and m["resolved"] == {"A-089-01", "A-089-02", "A-078-01"}
    assert m["resolve_at"] == [1, 2, 3]
    assert m["repair_gain"] == pytest.approx(2 / 3)  # 2 of the 3 first-attempt failures
    assert (m["by_local"], m["escalated"], m["rule_gone"]) == (3, 0, 2)

    c = metrics.run_metrics(cascade)
    assert c["resolve_at"] == [2, 2, 4] and (c["by_local"], c["escalated"]) == (2, 2)
    assert c["cost_usd"] == pytest.approx(0.02)

    text = metrics.report([local, cascade])
    assert "| repair-local | cascade | 4 | 0 | 1 | +25% | 1.000 |" in text
    assert "| CWE-89 | 2 | 2/2 | 2/2 |" in text and "| CWE-328 | 1 | 0/1 | 1/1 |" in text
    assert "A-328-01 [CWE-328]: POC_FAIL > POC_FAIL > POC_FAIL" in text
    assert "cascade: every task resolved." in text
