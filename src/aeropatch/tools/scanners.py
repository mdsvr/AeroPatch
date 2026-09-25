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


def run_opengrep(repo: Path, rules: Path = RULES_DIR) -> list[Finding] | None:
    binary = opengrep_binary()
    if not binary:
        return None
    cmd = [binary, "scan", "--config", str(rules), "--json", "--quiet", "--disable-version-check"]
    if Path(binary).name.startswith("semgrep"):
        cmd += ["--metrics", "off"]
    proc = subprocess.run(cmd + ["."], cwd=repo, capture_output=True, text=True, encoding="utf-8", check=False)
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


def run_bandit(repo: Path) -> list[Finding]:
    proc = subprocess.run([sys.executable, "-m", "bandit", "-q", "-r", "-f", "json", "."],
                          cwd=repo, capture_output=True, text=True, encoding="utf-8", check=False)
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return []
    out = []
    for r in data.get("results", []):
        path = Path(r["filename"]).as_posix().removeprefix("./")
        cwe = r.get("issue_cwe", {}).get("id")
        out.append(Finding(
            tool="bandit", rule_id=r["test_id"], path=path, line=r["line_number"],
            end_line=r.get("line_range", [r["line_number"]])[-1], cwe=f"CWE-{cwe}" if cwe else "",
            severity=SEV.get(r["issue_severity"], "medium"), message=r["issue_text"][:200],
            fingerprint=fingerprint(r["test_id"], path, _snippet(repo, path, r["line_number"])),
        ))
    return out


def scan(repo: Path) -> dict:
    """Returns {"findings": [...], "opengrep": bool}. Findings on the same line are both kept."""
    repo = repo.resolve()
    og = run_opengrep(repo)
    findings = (og or []) + run_bandit(repo)
    findings.sort(key=lambda f: (f.path, f.line, f.tool))
    return {"findings": findings, "opengrep": og is not None}
