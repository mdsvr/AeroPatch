"""Static checks on the scenario set and the Opengrep ruleset (no Docker needed)."""

import json
import shutil
import subprocess

import pytest

from aeropatch import scenario
from aeropatch.agent import prompts
from aeropatch.agent.gates import check
from aeropatch.config import SCENARIOS_DIR
from aeropatch.contracts import Finding
from aeropatch.tools import scanners
from aeropatch.tools.context import function_span, get_context
from aeropatch.tools.git_ops import Workspace

IDS = scenario.list_ids()


def test_split_covers_every_scenario_once():
    split = json.loads((SCENARIOS_DIR / "split.json").read_text())
    assert sorted(split["dev"] + split["test"] + split["test_b"] + split["test_c"]) == IDS
    assert (len(split["dev"]), len(split["test"])) == (13, 27)  # frozen 2026-10-03
    assert len(split["test_b"]) == 10  # Tier B, frozen 2026-10-05
    assert len(split["test_c"]) == 5  # Tier C, set aside from the teacher pilot on 2026-10-06


def test_original_rule_rescan_reports_present_absent_or_unavailable(monkeypatch, tmp_path):
    original = Finding(tool="opengrep", rule_id="aeropatch.python.test", path="app.py", line=10)
    finding = Finding(tool="opengrep", rule_id="aeropatch.python.test", path="app.py", line=12)
    monkeypatch.setattr(scanners, "run_opengrep", lambda repo: [finding])
    assert scanners.original_rule_present(tmp_path, original) is True

    monkeypatch.setattr(scanners, "run_opengrep", lambda repo: [])
    assert scanners.original_rule_present(tmp_path, original) is False

    monkeypatch.setattr(scanners, "run_opengrep", lambda repo: None)
    assert scanners.original_rule_present(tmp_path, original) is None


@pytest.mark.parametrize("sid", IDS)
def test_scenario_loads_and_points_at_target(sid):
    task = scenario.load(sid)
    src = (task.repo_path / task.finding.path).read_text(encoding="utf-8")
    start, end = function_span(src, task.target_function)
    assert task.finding.path in task.allowed_paths
    assert start <= task.finding.line <= end or task.finding.line < start  # module-level finding allowed


@pytest.mark.parametrize("sid", IDS)
def test_first_prompt_passes_the_secret_filter(sid):
    # A scenario whose own code trips the filter is SECRET_BLOCKED on every route but oracle.
    task = scenario.load(sid)
    ctx = get_context(task.repo_path, task.finding.path, task.finding.line, task.allowed_paths)
    prompts.check_no_secrets(prompts.SYSTEM_PROMPT + "\n\n" + prompts.first_user_message(task, ctx))


@pytest.mark.parametrize("sid", IDS)
def test_reference_fix_passes_the_gates(sid):
    task = scenario.load(sid)
    with Workspace(task.repo_path) as ws:
        originals = ws.read_many(task.allowed_paths)
        assert ws.apply_patch((SCENARIOS_DIR / sid / "reference_fix.patch").read_text(encoding="utf-8")) == ""
        changed = ws.read_many(ws.changed_paths())
    gate = check(originals, changed, task.allowed_paths, allow_imports=task.allow_imports)
    assert gate.ok, gate.details


needs_opengrep = pytest.mark.skipif(scanners.opengrep_binary() is None, reason="opengrep/semgrep not installed")


@needs_opengrep
@pytest.mark.parametrize("sid", [s for s in IDS if scenario.load(s).finding.tool == "opengrep"])  # Tier A
def test_rules_fire_on_vulnerable_and_not_on_fixed(sid, tmp_path):
    task = scenario.load(sid)
    before = scanners.run_opengrep(task.repo_path)
    assert any(f.path == task.finding.path and f.cwe == task.cwe for f in before), before
    fixed = tmp_path / "repo"
    shutil.copytree(task.repo_path, fixed)
    patch = (SCENARIOS_DIR / sid / "reference_fix.patch").read_bytes()  # bytes: no CRLF on Windows
    subprocess.run(["git", "apply", "-"], cwd=fixed, input=patch, check=True)
    after = scanners.run_opengrep(fixed)
    assert not [f for f in after if f.cwe == task.cwe], after
