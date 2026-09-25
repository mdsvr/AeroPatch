"""Deterministic safety gates, run before the sandbox (doc 08 part 2, §2)."""

from __future__ import annotations

import ast
import fnmatch
import re
from pathlib import PurePosixPath

from aeropatch.config import DEFAULTS
from aeropatch.contracts import GateResult

SUPPRESS_RE = re.compile(r"#\s*(nosec|noqa|nosemgrep)|pytest\.skip|pytest\.mark\.skip|xfail")


def _forbidden(path: str, globs: list[str]) -> bool:
    p = PurePosixPath(path)
    for g in globs:
        if g.endswith("/**"):
            if g[:-3] in p.parts[:-1]:
                return True
        elif fnmatch.fnmatch(p.name, g) or fnmatch.fnmatch(str(p), g):
            return True
    return False


def _symbols(tree: ast.AST) -> set[str]:
    out = set()
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        out.add(f"{node.name}.{sub.name}")
    return out


def _imports_and_calls(tree: ast.AST) -> tuple[set[str], set[str]]:
    mods, calls = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
            mods.update(f"{node.module}.{a.name}" for a in node.names)
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                calls.add(f.id)
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                calls.add(f"{f.value.id}.{f.attr}")
    return mods, calls


def _changed_lines(before: str, after: str) -> int:
    import difflib

    return sum(1 for line in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
               if line[:1] in "+-" and not line.startswith(("+++", "---")))


def check(originals: dict[str, str], changed: dict[str, str], allowed_paths: list[str],
          cfg: dict | None = None, allow_imports: list[str] | None = None) -> GateResult:
    """originals: path -> original content; changed: path -> patched content."""
    cfg = {**DEFAULTS, **(cfg or {})}
    violations: list[str] = []
    details: list[str] = []

    def flag(code: str, detail: str) -> None:
        if code not in violations:
            violations.append(code)
        details.append(f"{code}: {detail}")

    real = {p: c for p, c in changed.items() if c != originals.get(p)}
    if not real:
        flag("NO_CHANGE", "the edits produce an empty diff")
    if len(real) > cfg["max_files"]:
        flag("TOO_LARGE", f"{len(real)} files changed (max {cfg['max_files']})")
    total = 0
    risky_mods = set(cfg["risky_modules"]) - set(allow_imports or [])
    risky_calls = set(cfg["risky_calls"]) - set(allow_imports or [])
    for path, after in real.items():
        before = originals.get(path, "")
        if _forbidden(path, cfg["forbidden_globs"]):
            flag("FORBIDDEN_PATH", f"{path} may not be edited")
        if path not in allowed_paths:
            flag("OUT_OF_SCOPE", f"{path} is not in the allowed files {allowed_paths}")
        total += _changed_lines(before, after)
        added = [line for line in after.splitlines() if line not in set(before.splitlines())]
        if any(SUPPRESS_RE.search(line) for line in added):
            flag("SUPPRESSES_CHECKS", f"{path} adds a check-suppression marker")
        if not path.endswith(".py"):
            continue
        try:
            new_tree = ast.parse(after)
        except SyntaxError as e:
            flag("SYNTAX_ERROR", f"{path}:{e.lineno}: {e.msg}")
            continue
        try:
            old_tree = ast.parse(before)
        except SyntaxError:
            continue
        gone = _symbols(old_tree) - _symbols(new_tree)
        if gone:
            flag("DELETES_SYMBOL", f"{path} removes {sorted(gone)}")
        old_mods, old_calls = _imports_and_calls(old_tree)
        new_mods, new_calls = _imports_and_calls(new_tree)
        added_mods = {m for m in new_mods - old_mods
                      if any(m == r or m.startswith(r + ".") for r in risky_mods)}
        bad = sorted(added_mods | ((new_calls - old_calls) & risky_calls))
        if bad:
            flag("RISKY_IMPORT", f"{path} adds {bad}")
    if total > cfg["max_changed_lines"]:
        flag("TOO_LARGE", f"{total} changed lines (max {cfg['max_changed_lines']})")
    return GateResult(ok=not violations, violations=violations, details=details)
