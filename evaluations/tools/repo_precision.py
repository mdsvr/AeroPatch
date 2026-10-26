"""Precision of the shown findings on real repositories (doc 17 part 3 §4.2; Phases A-C of
reports/Real bug detection and model mix.md).

    python evaluations/tools/repo_precision.py run --repos D:/aeropatch-repos F:/AeroPatch/runs/github --out DIR
    python evaluations/tools/repo_precision.py score --labels evaluations/detection/repo_labels.csv

`run` checks every repository folder three ways (today's default, --extra-rules, --extra-rules
with --judge), confirms each check left the folder byte-identical, and writes one row per shown
card and per advisory to DIR/findings.csv for labelling. `score` reads the labelled file: label is
`real` or `false` (a finding is real when the flagged code has the rule's CWE weakness and
outside input can reach it, judged against the CWE definition).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aeropatch import check
from aeropatch.tools import scanners

MODES = {"default": {}, "extra": {"extra_rules": True}, "extra+judge": {"extra_rules": True, "use_judge": True}}
FIELDS = ["repo", "commit", "mode", "n", "kind", "tool", "rule_id", "cwe", "path", "line", "code", "judge", "label",
          "note"]


def _digest(folder: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if p.is_file() and ".git" not in p.relative_to(folder).parts:
            h.update(p.relative_to(folder).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def _commit(folder: Path) -> str:
    r = subprocess.run(["git", "-C", str(folder), "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True, check=False)
    return r.stdout.strip()


def run(repo_roots: list[Path], out: Path, modes: list[str]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    rows, timing = [], []
    folders = sorted(p for root in repo_roots for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    for folder in folders:
        before = _digest(folder)
        for mode in modes:
            start = time.monotonic()
            res = check.check_folder(folder, offline=mode != "default", **MODES[mode])
            secs = round(time.monotonic() - start, 1)
            same = _digest(folder) == before
            timing.append({"repo": folder.name, "mode": mode, "seconds": secs, "byte_identical": same,
                           "shown": len(res.shown), "parked": len(res.parked), "advisories": len(res.advisories),
                           "notes": res.notes})
            print(f"{folder.name:32} {mode:12} {secs:6}s shown={len(res.shown)} parked={len(res.parked)} "
                  f"adv={len(res.advisories)} identical={same}", flush=True)
            judged = {(f.path, f.line, f.rule_id): r for f, r in res.parked if r.startswith(check.JUDGED)}
            for c in res.shown:
                f = c.finding
                rows.append({"repo": folder.name, "commit": _commit(folder), "mode": mode, "n": c.n, "kind": c.kind,
                             "tool": f.tool, "rule_id": f.rule_id, "cwe": f.cwe, "path": f.path, "line": f.line,
                             "code": "" if c.kind == "secret" else scanners._snippet(folder, f.path, f.line).strip()[:160],
                             "judge": "keep" if mode == "extra+judge" else "", "label": "", "note": ""})
            for f, r in judged.items():
                rows.append({"repo": folder.name, "commit": _commit(folder), "mode": mode, "n": "", "kind": "judged",
                             "tool": "", "rule_id": f[2], "cwe": "", "path": f[0], "line": f[1],
                             "code": scanners._snippet(folder, f[0], f[1]).strip()[:160], "judge": r,
                             "label": "", "note": ""})
            for a in res.advisories:
                rows.append({"repo": folder.name, "commit": _commit(folder), "mode": mode, "n": "", "kind": "advisory",
                             "tool": "osv", "rule_id": ",".join(a.ids[:4]), "cwe": "", "path": a.pin.path,
                             "line": a.pin.line, "code": f"{a.pin.name}=={a.pin.version} -> {a.fixed}",
                             "judge": "", "label": "", "note": ""})
    with open(out / "findings.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    (out / "runs.json").write_text(json.dumps(timing, indent=2) + "\n", encoding="utf-8")


def score(labels: Path) -> None:
    with open(labels, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for mode in dict.fromkeys(r["mode"] for r in rows):
        shown = [r for r in rows if r["mode"] == mode and r["kind"] in ("finding", "secret")]
        if not shown:
            continue
        real = sum(r["label"] == "real" for r in shown)
        judged = [r for r in rows if r["mode"] == mode and r["kind"] == "judged"]
        print(f"{mode:18} shown {len(shown):3}  real {real:3}  precision {real / len(shown):.0%}"
              + (f"  | judge set aside {len(judged)}, real among them {sum(r['label'] == 'real' for r in judged)}"
                 if "judge" in mode else ""))
        for repo in sorted({r["repo"] for r in shown}):
            sub = [r for r in shown if r["repo"] == repo]
            print(f"    {repo:32} {sum(r['label'] == 'real' for r in sub)} of {len(sub)}")
    adv = [r for r in rows if r["kind"] == "advisory" and r["mode"] == "default"]
    print(f"advisory cards: {len(adv)}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("run")
    s.add_argument("--repos", type=Path, nargs="+", required=True)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--modes", nargs="+", default=list(MODES), choices=list(MODES))
    s = sub.add_parser("score")
    s.add_argument("--labels", type=Path, required=True)
    a = p.parse_args(argv)
    if a.cmd == "run":
        run(a.repos, a.out, a.modes)
    else:
        score(a.labels)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
