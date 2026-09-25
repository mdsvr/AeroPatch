"""Static checks on the scenario set and the Opengrep ruleset (no Docker needed)."""

import json
import shutil
import subprocess

import pytest

from aeropatch import scenario
from aeropatch.agent.gates import check
from aeropatch.config import SCENARIOS_DIR
from aeropatch.tools import scanners
from aeropatch.tools.context import function_span
from aeropatch.tools.git_ops import Workspace

IDS = scenario.list_ids()


def test_split_covers_every_scenario_once():
    split = json.loads((SCENARIOS_DIR / "split.json").read_text())
    assert sorted(split["dev"] + split["test"]) == IDS
    assert len(split["dev"]) == 10


@pytest.mark.parametrize("sid", IDS)
def test_scenario_loads_and_points_at_target(sid):
    task = scenario.load(sid)
    src = (task.repo_path / task.finding.path).read_text()
    start, end = function_span(src, task.target_function)
    assert task.finding.path in task.allowed_paths
    assert start <= task.finding.line <= end or task.finding.line < start  # module-level finding allowed


@pytest.mark.parametrize("sid", IDS)
def test_reference_fix_passes_the_gates(sid):
    task = scenario.load(sid)
    with Workspace(task.repo_path) as ws:
        originals = ws.read_many(task.allowed_paths)
        assert ws.apply_patch((SCENARIOS_DIR / sid / "reference_fix.patch").read_text()) == ""
        changed = ws.read_many(ws.changed_paths())
    gate = check(originals, changed, task.allowed_paths, allow_imports=task.allow_imports)
    assert gate.ok, gate.details


needs_opengrep = pytest.mark.skipif(scanners.opengrep_binary() is None, reason="opengrep/semgrep not installed")


@needs_opengrep
@pytest.mark.parametrize("sid", IDS)
def test_rules_fire_on_vulnerable_and_not_on_fixed(sid, tmp_path):
    task = scenario.load(sid)
    before = scanners.run_opengrep(task.repo_path)
    assert any(f.path == task.finding.path and f.cwe == task.cwe for f in before), before
    fixed = tmp_path / "repo"
    shutil.copytree(task.repo_path, fixed)
    patch = (SCENARIOS_DIR / sid / "reference_fix.patch").read_text()
    subprocess.run(["git", "apply", "-"], cwd=fixed, input=patch, text=True, check=True)
    after = scanners.run_opengrep(fixed)
    assert not [f for f in after if f.cwe == task.cwe], after
