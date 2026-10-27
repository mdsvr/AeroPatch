"""Repair prompts and labels with a faked model, sandbox and scanner (no Docker).

The golden file pins every prompt `repair-local` sends on the scripted paths below. It was recorded
before the hidden-suite changes (doc 17 part 2 §2), so a config with `hidden_suites: []` and
`rescan_feedback: False` must keep producing byte-identical prompts. Re-record only on purpose:

    AEROPATCH_WRITE_GOLDEN=1 uv run pytest tests/test_loop_labels.py -k golden
"""

import copy
import json
import os
from pathlib import Path

import pytest

from aeropatch import labels, scenario
from aeropatch.agent import loop, router
from aeropatch.config import load_config
from aeropatch.contracts import Failure, SandboxResult
from aeropatch.models.base import Generation
from aeropatch.sandbox import sandbox
from aeropatch.tools import scanners

GOLDEN = Path(__file__).parent / "fixtures" / "golden_repair_prompts.json"

GOOD = """RATIONALE: bind the parameter.
<<<<<<< SEARCH app/db.py
    cur = conn.execute(f"SELECT id, name FROM users WHERE name = '{name}'")
=======
    cur = conn.execute("SELECT id, name FROM users WHERE name = ?", (name,))
>>>>>>> REPLACE"""
HALF = GOOD.replace("(name,))", "name)")
LIST = GOOD.replace("(name,))", "[name])")
NOSEC = GOOD.replace("(name,))", "(name,))  # nosec")

# `suite` is set as parse_logs sets it; junit.summarize never prints it, so the golden file holds.
REG_FAIL = Failure(test_id="tests_regression/test_db.py::test_lookup", kind="failure",
                   message="AssertionError: assert [] == [(1, 'alice')]", trace="E   assert [] == [(1, 'alice')]",
                   suite="regression")
POC_FAIL = Failure(test_id="tests_poc/test_poc.py::test_injection", kind="failure",
                   message="AssertionError: the injected name returned every row", suite="poc")
POC_IMPORT = Failure(test_id="tests_poc/test_poc.py", kind="error", message="collection failure",
                     trace="ModuleNotFoundError: No module named 'app.dbx'", suite="poc")
REG_SYNTAX = Failure(test_id="tests_regression/test_db.py", kind="error", message="collection failure",
                     trace="SyntaxError: invalid syntax", suite="regression")


def sb(label, poc, reg, failures=()):
    return SandboxResult(applied=True, poc_passed=poc, regressions_passed=reg, poc_total=1, regression_total=3,
                         failures=list(failures), label=label)


# Each case: model outputs in call order, sandbox results in call order, re-scan answers in call order.
CASES = {
    "regression_poc_resolved": {
        "outputs": [GOOD, HALF, LIST],
        "sandbox": [sb("REGRESSION", True, False, [REG_FAIL]), sb("POC_FAIL", False, True, [POC_FAIL]),
                    sb("RESOLVED", True, True)],
        "rescan": [True, True, False],
    },
    "format_import_stuck": {
        "outputs": ["no blocks here", GOOD, GOOD, GOOD],
        "sandbox": [sb("IMPORT_ERROR", False, False, [POC_IMPORT])],
        "rescan": [True],
    },
    "gate_syntax_resolved": {
        "outputs": [NOSEC, GOOD, LIST],
        "sandbox": [sb("SYNTAX_ERROR", False, False, [REG_SYNTAX]), sb("RESOLVED", True, True)],
        "rescan": [True, False],
    },
}


def run_case(case, monkeypatch, tmp_path, config="repair-local", **overrides):
    """Run the loop on A-089-01 with everything outside the loop scripted. Returns (result, calls)."""
    outputs, results, rescans = iter(case["outputs"]), iter(case["sandbox"]), iter(case["rescan"])
    cfg = load_config(config, **overrides)
    calls, befores = [], []

    def fake_generate(route, messages, system, cfg, temperature, scenario_dir=None):
        calls.append({"route": route, "temperature": temperature, "messages": copy.deepcopy(messages)})
        return Generation(text=next(outputs), model="scripted")

    def fake_sandbox(*a, **k):
        assert cfg["run_tests"], "the Suggest level must never start the sandbox"
        return copy.deepcopy(next(results))

    def fake_rule_hits(repo, finding):
        assert cfg["rescan_feedback"], "an earlier config must make no extra scanner call"
        return [18]  # A-089-01 has one hit of B608

    def fake_rescan(repo, finding, before=None):
        befores.append(before)
        return next(rescans)

    monkeypatch.setattr(router, "generate", fake_generate)
    monkeypatch.setattr(sandbox, "run_tests", fake_sandbox)
    monkeypatch.setattr(scanners, "rule_hits", fake_rule_hits)
    monkeypatch.setattr(scanners, "original_rule_present", fake_rescan)
    task = scenario.load("A-089-01")
    task.id = case.get("task_id", task.id)
    res = loop.run(task, cfg, tmp_path)
    # Earlier configs keep the any-hit re-scan (before=None); rescan-feedback configs count hits.
    assert set(befores) <= {1 if cfg["rescan_feedback"] else None}
    return res, calls


def test_golden_repair_prompts_are_unchanged(monkeypatch, tmp_path):
    got = {}
    for name, case in CASES.items():
        res, calls = run_case(case, monkeypatch, tmp_path / name)
        got[name] = {"labels": [a.label for a in res.attempts], "calls": calls}
    if os.environ.get("AEROPATCH_WRITE_GOLDEN") == "1":
        GOLDEN.write_text(json.dumps(got, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        pytest.skip("golden file written")
    assert got == json.loads(GOLDEN.read_text(encoding="utf-8"))


def prompts_of(calls):
    """The user turns of the whole conversation: the last call carries every earlier one."""
    return [m["content"] for m in calls[-1]["messages"] if m["role"] == "user"]


RULE_LINE = "The scanner still reports B608 in app/db.py: Possible SQL injection vector"


def test_v1_stops_quiet_and_never_shows_the_hidden_poc(monkeypatch, tmp_path):
    # Attempt 1: PoC fails, rule fires. 2: PoC import error (truth IMPORT_ERROR) and a regression.
    # 3: PoC still fails, regressions pass, rule gone: the user would be offered it.
    case = {"outputs": [HALF, LIST, GOOD],
            "sandbox": [sb("POC_FAIL", False, True, [POC_FAIL]),
                        sb("IMPORT_ERROR", False, False, [POC_IMPORT, REG_FAIL]),
                        sb("POC_FAIL", False, True, [POC_FAIL])],
            "rescan": [True, True, False]}
    res, calls = run_case(case, monkeypatch, tmp_path, "repair-local-v1")
    assert [a.label for a in res.attempts] == ["POC_FAIL", "IMPORT_ERROR", "POC_FAIL"]  # truth kept
    assert res.user_label == res.attempts[-1].user_label == labels.QUIET_TESTS_PASS
    assert not res.resolved and res.label == "POC_STILL_FAILS" and res.final_diff
    text = "\n".join(prompts_of(calls))
    for leak in ("POC_FAIL", "IMPORT_ERROR", POC_FAIL.message, POC_FAIL.test_id, POC_IMPORT.test_id, "app.dbx"):
        assert leak not in text
    assert "Result: SCANNER_STILL_FLAGS." in prompts_of(calls)[1]
    assert "Result: REGRESSION." in prompts_of(calls)[2] and REG_FAIL.test_id in prompts_of(calls)[2]


def test_v1_does_not_stop_on_a_true_fix_the_scanner_still_flags(monkeypatch, tmp_path):
    case = {"outputs": [GOOD, HALF, LIST], "sandbox": [sb("RESOLVED", True, True)] * 3, "rescan": [True] * 3}
    res, calls = run_case(case, monkeypatch, tmp_path, "repair-local-v1")
    assert len(calls) == 3 and [a.label for a in res.attempts] == ["RESOLVED"] * 3
    repair = calls[1]["messages"][-1]["content"]
    assert "Result: SCANNER_STILL_FLAGS." in repair and RULE_LINE in repair
    assert res.user_label == labels.NOT_FIXED and not res.resolved and not res.final_diff


V2_CASE = {"outputs": [HALF, LIST, GOOD],
           "sandbox": [sb("REGRESSION", True, False, [REG_FAIL]), sb("POC_FAIL", False, True, [POC_FAIL]),
                       sb("POC_FAIL", False, False, [POC_FAIL, REG_FAIL])],
           "rescan": [True, True, False]}


def test_v2_shows_no_test_output_and_stops_quiet_not_tested(monkeypatch, tmp_path):
    res, calls = run_case(V2_CASE, monkeypatch, tmp_path, "repair-local-v2")
    assert res.user_label == labels.QUIET_NOT_TESTED and not res.resolved and len(calls) == 3
    text = "\n".join(prompts_of(calls))
    for leak in ("POC_FAIL", "REGRESSION", "FAILED ", REG_FAIL.message, POC_FAIL.message, "tests_"):
        assert leak not in text
    assert text.count(RULE_LINE) == 2


def test_suggest_never_runs_the_sandbox_and_matches_v2_prompts(monkeypatch, tmp_path):
    _, v2_calls = run_case(V2_CASE, monkeypatch, tmp_path / "v2", "repair-local-v2")
    # A folder that is not a scenario: the Suggest level needs no scenario directory.
    case = {**V2_CASE, "sandbox": [], "task_id": "my-folder"}
    res, calls = run_case(case, monkeypatch, tmp_path / "suggest", "suggest-local")
    assert [a.label for a in res.attempts] == ["NOT_RUN"] * 3 and res.label == "NOT_RUN"
    assert res.user_label == labels.QUIET_NOT_TESTED and not res.resolved
    assert calls == v2_calls
    assert "What a user would be told: Scanner quiet, not tested" in (
        tmp_path / "suggest" / "my-folder" / "report.md").read_text(encoding="utf-8")
