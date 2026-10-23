"""Run Opengrep and Bandit and normalize their findings (doc 06 §6-7).

Opengrep is looked up at $AEROPATCH_OPENGREP, .tools/opengrep(.exe), then PATH. The rules use
the Semgrep-compatible syntax, so `semgrep` on PATH is accepted as a local stand-in.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from aeropatch.config import ROOT, RULES_DIR
from aeropatch.contracts import Finding

SEV = {"ERROR": "high", "WARNING": "medium", "INFO": "low", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}


def fingerprint(rule_id: str, path: str, snippet: str) -> str:
    norm = " ".join(snippet.split())
    return hashlib.sha256(f"{rule_id}|{path}|{norm}".encode()).hexdigest()[:16]


def opengrep_binary() -> str | None:
    env = os.environ.get("AEROPATCH_OPENGREP")
    if env and Path(env).exists():
        return env
    for name in ("opengrep.exe", "opengrep"):
        local = ROOT / ".tools" / name
        if local.exists():
            return str(local)
    return shutil.which("opengrep") or shutil.which("semgrep")


def _snippet(repo: Path, path: str, line: int) -> str:
    try:
        return (repo / path).read_text(encoding="utf-8").split("\n")[line - 1]
    except (OSError, IndexError):
        return ""


def run_opengrep(repo: Path, rules: Path = RULES_DIR, targets: list[str] | None = None) -> list[Finding] | None:
    """`targets`: repo-relative files to scan instead of the whole repository."""
    binary = opengrep_binary()
    if not binary:
        return None
    cmd = [binary, "scan", "--config", str(rules), "--json", "--quiet", "--disable-version-check"]
    if Path(binary).name.startswith("semgrep"):
        cmd += ["--metrics", "off"]
    proc = subprocess.run(cmd + (targets or ["."]), cwd=repo, capture_output=True, text=True, encoding="utf-8",
                          check=False)
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return None
    out = []
    for r in data.get("results", []):
        meta = r.get("extra", {}).get("metadata", {})
        path = Path(r["path"]).as_posix()
        line = r["start"]["line"]
        rule_id = r["check_id"].split(".")[-1]
        rule_id = f"aeropatch.python.{rule_id}" if not r["check_id"].startswith("aeropatch") else r["check_id"]
        cwe = meta.get("cwe", "")
        cwe = cwe[0] if isinstance(cwe, list) else cwe
        out.append(Finding(
            tool="opengrep", rule_id=rule_id, path=path, line=line, end_line=r["end"]["line"],
            cwe=cwe.split(":")[0].strip(), severity=SEV.get(r.get("extra", {}).get("severity", ""), "medium"),
            message=r.get("extra", {}).get("message", "")[:200],
            fingerprint=fingerprint(rule_id, path, _snippet(repo, path, line)),
        ))
    return out


def run_bandit(repo: Path, targets: list[str] | None = None) -> list[Finding] | None:
    """`targets`: repo-relative files to scan instead of the whole repository."""
    # -I: the scanned folder is the cwd, and without it a json.py there would be imported by Bandit
    # (and leave a __pycache__ behind in a folder `check` promises not to write to).
    proc = subprocess.run([sys.executable, "-I", "-m", "bandit", "-q", "-f", "json", *(targets or ["-r", "."])],
                          cwd=repo, capture_output=True, text=True, encoding="utf-8", check=False)
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return None
    out = []
    for r in data.get("results", []):
        path = Path(r["filename"]).as_posix().removeprefix("./")
        cwe = r.get("issue_cwe", {}).get("id")
        out.append(Finding(
            tool="bandit", rule_id=r["test_id"], path=path, line=r["line_number"],
            end_line=r.get("line_range", [r["line_number"]])[-1], cwe=f"CWE-{cwe}" if cwe else "",
            severity=SEV.get(r["issue_severity"], "medium"), message=r["issue_text"][:200],
            confidence=SEV.get(r.get("issue_confidence", ""), ""),
            fingerprint=fingerprint(r["test_id"], path, _snippet(repo, path, r["line_number"])),
        ))
    return out


def rule_hits(repo: Path, finding: Finding) -> list[int] | None:
    """Lines where the finding's rule fires in the finding's own file, scanning only that file.
    None when no re-scan applies (an advisory finding, or the scanner is missing or failed)."""
    if finding.tool == "opengrep":
        findings = run_opengrep(repo, targets=[finding.path])
    elif finding.tool == "bandit":
        findings = run_bandit(repo, targets=[finding.path])
    else:
        return None
    if findings is None:
        return None
    return sorted(f.line for f in findings if f.rule_id == finding.rule_id and f.path == finding.path)


def original_rule_present(repo: Path, original: Finding, before: int | None = None) -> bool | None:
    """Does the finding's rule still fire in its file? Without `before`: any hit left. With `before`
    (the hit count on the pristine file), "still" means the count did not fall, so in a file with
    two separate hits of one rule, fixing the finding's own hit reads as fixed (doc 17 part 2 §2).
    The two agree on a one-hit file. On 2026-10-23, 43 scenarios had one hit, 15 had no re-scan
    (advisories), and A-079-02 (4 hits) and A-328-02 (2) had several, so only configs with
    `rescan_feedback` pass `before`, and every earlier config keeps the any-hit answer."""
    hits = rule_hits(repo, original)
    if hits is None:
        return None
    return len(hits) >= max(before or 0, 1)


def scan(repo: Path) -> dict:
    """Returns {"findings": [...], "opengrep": bool}. Findings on the same line are both kept."""
    repo = repo.resolve()
    og = run_opengrep(repo)
    findings = (og or []) + (run_bandit(repo) or [])
    findings.sort(key=lambda f: (f.path, f.line, f.tool))
    return {"findings": findings, "opengrep": og is not None}
