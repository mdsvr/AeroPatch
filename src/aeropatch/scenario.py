"""Scenario loading and the 4-check scenario validator (doc 11 §5-6)."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

from aeropatch.config import SCENARIOS_DIR
from aeropatch.contracts import Finding, Task
from aeropatch.sandbox import sandbox
from aeropatch.tools import scanners
from aeropatch.tools.git_ops import Workspace

REQUIRED = ["id", "tier", "cwe", "finding", "description", "allowed_paths", "target_function",
            "poc_tests", "regression_tests", "split", "license"]


class ScenarioError(ValueError):
    pass


def scenario_dir(sid: str) -> Path:
    d = SCENARIOS_DIR / sid
    if not (d / "scenario.json").is_file():
        raise ScenarioError(f"no scenario {sid!r} in {SCENARIOS_DIR}")
    return d


def image_tag(sid: str) -> str:
    return f"aeropatch-sandbox:{sid.lower()}"


def load(sid: str) -> Task:
    d = scenario_dir(sid)
    meta = json.loads((d / "scenario.json").read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if k not in meta]
    if missing:
        raise ScenarioError(f"{sid}: scenario.json missing {missing}")
    if meta["id"] != sid:
        raise ScenarioError(f"{sid}: id field is {meta['id']!r}")
    for sub in ("repo", "tests_poc", "tests_regression"):
        if not (d / sub).is_dir():
            raise ScenarioError(f"{sid}: missing {sub}/")
    for f in ("reference_fix.patch", "requirements.lock"):
        if not (d / f).is_file():
            raise ScenarioError(f"{sid}: missing {f}")
    fnd = meta["finding"]
    return Task(
        id=sid, repo_path=d / "repo", cwe=meta["cwe"],
        finding=Finding(tool=fnd["tool"], rule_id=fnd["rule_id"], path=fnd["path"], line=fnd["line"],
                        end_line=fnd.get("end_line", fnd["line"]), cwe=meta["cwe"],
                        severity=fnd.get("severity", "high"), message=fnd["message"]),
        description=meta["description"], allowed_paths=meta["allowed_paths"],
        poc_tests=meta["poc_tests"], regression_tests=meta["regression_tests"],
        image=image_tag(sid), target_function=meta["target_function"],
        allow_imports=meta.get("allow_imports", []),
    )


def list_ids(split: str | None = None) -> list[str]:
    ids = sorted(p.parent.name for p in SCENARIOS_DIR.glob("*/scenario.json"))
    if split:
        splits = json.loads((SCENARIOS_DIR / "split.json").read_text())
        ids = [i for i in ids if i in splits.get(split, [])]
    return ids


def ensure_image(sid: str, rebuild: bool = False) -> str:
    tag = image_tag(sid)
    if rebuild or not sandbox.image_exists(tag):
        from aeropatch.config import RUNS_DIR

        sandbox.build_scenario(scenario_dir(sid), tag, RUNS_DIR / "builds" / f"{sid}.log")
    return tag


def destructive_patch(ws: Workspace, path: str, qualified: str) -> None:
    """Replace the target function's body with `return None` (validator check 3)."""
    src = ws.read(path)
    tree = ast.parse(src)
    parts = qualified.split(".")
    nodes = tree.body
    fn = None
    for i, part in enumerate(parts):
        match = next((n for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                      and n.name == part), None)
        if match is None:
            raise ScenarioError(f"target_function {qualified!r} not found in {path}")
        fn, nodes = match, match.body
    body = fn.body
    if len(body) > 1 and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
        body = body[1:]  # keep the docstring
    lines = src.split("\n")
    first, last = body[0].lineno - 1, fn.end_lineno - 1
    indent = lines[first][: len(lines[first]) - len(lines[first].lstrip())]
    ws.write({path: "\n".join(lines[:first] + [f"{indent}return None"] + lines[last + 1:])})


@dataclass
class Validation:
    sid: str
    checks: dict[str, str] = field(default_factory=dict)  # name -> PASS/FAIL/SKIPPED + detail

    @property
    def ok(self) -> bool:
        return all(not v.startswith("FAIL") for v in self.checks.values())


def validate(sid: str, rebuild: bool = False) -> Validation:
    task = load(sid)
    d = scenario_dir(sid)
    v = Validation(sid)
    image = ensure_image(sid, rebuild)

    with Workspace(task.repo_path) as ws:
        r = sandbox.run_tests(image, ws.src)
        ok = (not r.poc_passed) and r.poc_total > 0 and r.regressions_passed
        v.checks["1_vulnerable_baseline"] = ("PASS" if ok else "FAIL") + \
            f" (poc_passed={r.poc_passed}, regressions_passed={r.regressions_passed}, label={r.label})"

        err = ws.apply_patch((d / "reference_fix.patch").read_text(encoding="utf-8"))
        if err:
            v.checks["2_reference_fix"] = f"FAIL (patch does not apply: {err[:200]})"
        else:
            r = sandbox.run_tests(image, ws.src)
            v.checks["2_reference_fix"] = ("PASS" if r.resolved else "FAIL") + f" (label={r.label})"

        ws.reset()
        destructive_patch(ws, task.finding.path, task.target_function)
        r = sandbox.run_tests(image, ws.src)
        v.checks["3_destructive_fix_caught"] = ("PASS" if not r.regressions_passed else "FAIL") + \
            f" (regressions_passed={r.regressions_passed})"

    found = scanners.scan(task.repo_path)
    if task.finding.tool == "opengrep" and not found["opengrep"]:
        v.checks["4_finding_detected"] = "SKIPPED (opengrep not installed)"
    else:
        hit = any(f.rule_id == task.finding.rule_id and f.path == task.finding.path
                  and abs(f.line - task.finding.line) <= 3 for f in found["findings"])
        v.checks["4_finding_detected"] = ("PASS" if hit else "FAIL") + f" ({task.finding.rule_id})"
    return v
