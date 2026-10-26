"""Phase A of reports/Real bug detection and model mix.md: a held-out detection set drawn from
PySASTBench (ICSE'26), frozen before any new rule is written, and the scanners' recall on it.

    python evaluations/tools/detection.py freeze --csv RealworldDataset.csv
    python evaluations/tools/detection.py fetch --to D:/aeropatch-detection
    python evaluations/tools/detection.py score --data D:/aeropatch-detection [--extra taint]

The dataset (108 real CVEs, each as a vulnerable and a fixed copy of the project) is CC-BY-4.0 at
https://zenodo.org/records/17936545; only the frozen list of CVE ids and locations is kept here.
A CVE counts as found when a finding lies inside one of its named functions in the vulnerable
copy. The same check on the fixed copy is reported beside it: the ICSE study counts a report on
the patched version as a false positive.
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import random
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

HELDOUT = ROOT / "evaluations" / "detection" / "heldout.json"
ZIP_URL = "https://zenodo.org/records/17936545/files/RealworldDataset.zip?download=1"
SEED = 20261026
PER_CWE = {"22": 10, "94": 10, "79": 10}  # the classes the new rules target (report, Phase A)
# A finding inside the CVE's function counts only when its CWE is the CVE's class, so an `assert`
# (B101) in a path-traversal function is not a detection. Bandit tags eval (B307) CWE-78.
# Set on 2026-10-26 after the baseline's loose count, before any extra rule was scored.
SAME_CLASS = {"CWE-22": {"CWE-22", "CWE-23", "CWE-36", "CWE-73"}, "CWE-94": {"CWE-94", "CWE-95", "CWE-78"},
              "CWE-79": {"CWE-79", "CWE-80", "CWE-116"}}


def _positions(text: str) -> list[dict]:
    """'a/b.py:Class.func; c.py:f' -> [{"path": "a/b.py", "function": "Class.func"}, ...]"""
    out = []
    for part in text.split(";"):
        path, _, func = part.strip().partition(":")
        if path:
            out.append({"path": path.strip(), "function": func.strip()})
    return out


def freeze(csv_path: Path) -> None:
    if HELDOUT.exists():
        raise SystemExit(f"{HELDOUT} is frozen; a new draw needs a new file name")
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    rng = random.Random(SEED)
    picked = []
    for cwe, n in PER_CWE.items():
        pool = sorted((r for r in rows if r["CWE Type"].split(";")[0] == cwe), key=lambda r: r["CVE"])
        picked += rng.sample(pool, n)
    items = [{"cve": r["CVE"].rsplit("=", 1)[-1], "cwe": f"CWE-{r['CWE Type'].split(';')[0]}", "type": r["Type"],
              "project": r["project"], "version": r["Version"], "positions": _positions(r["vul position"])}
             for r in picked]
    HELDOUT.parent.mkdir(parents=True, exist_ok=True)
    HELDOUT.write_text(json.dumps({
        "_note": (f"Frozen 2026-10-26, before any rule of Phase B was written: {PER_CWE} CVEs per CWE drawn "
                  f"with random.Random({SEED}) from PySASTBench's RealworldDataset.csv (108 CVEs; "
                  "github.com/Victor725/PySASTBench, data CC-BY-4.0 at zenodo.org/records/17936545). "
                  "Never write or tune a rule on these projects."),
        "items": items}, indent=2) + "\n", encoding="utf-8")
    print(f"froze {len(items)} CVEs into {HELDOUT}")


def fetch(to: Path) -> None:
    from remote_zip import open_zip
    items = json.loads(HELDOUT.read_text(encoding="utf-8"))["items"]
    outer = open_zip(ZIP_URL)
    names = outer.namelist()
    for it in items:
        dest = to / it["cve"]
        if (dest / ".done").exists():
            continue
        for member in (n for n in names if n.startswith(f"RealworldDataset/{it['cve']}/") and n.endswith(".zip")):
            kind = "vul" if member.endswith("-vul.zip") else "fix" if member.endswith("-fix.zip") else None
            if kind is None:
                continue
            with zipfile.ZipFile(io.BytesIO(outer.read(member))) as inner:
                root = (dest / kind).resolve()
                for m in inner.infolist():
                    target = (root / m.filename).resolve()
                    if m.is_dir() or not target.is_relative_to(root):
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(inner.read(m))
        dest.mkdir(parents=True, exist_ok=True)
        (dest / ".done").write_text("", encoding="utf-8")
        print(f"fetched {it['cve']}", flush=True)


def _project_root(copy: Path) -> Path:
    """The zips hold one top folder (thefuck-3.30/...) or the files directly."""
    kids = [p for p in copy.iterdir() if not p.name.startswith(".")] if copy.is_dir() else []
    return kids[0] if len(kids) == 1 and kids[0].is_dir() else copy


def _find(root: Path, rel: str) -> Path | None:
    """The CSV path is relative to the project's source root, which may sit one folder lower."""
    if (root / rel).is_file():
        return root / rel
    hits = [p for p in root.rglob(Path(rel).name) if p.as_posix().endswith(rel)]
    return hits[0] if hits else None


def _span(path: Path, function: str) -> tuple[int, int] | None:
    """Lines of `Class.func` (or `func`) in the file; None when the name is not found."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError):
        return None
    want = function.split(".")

    def walk(node, prefix):
        for n in ast.iter_child_nodes(node):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = [*prefix, n.name]
                if name[-len(want):] == want and not isinstance(n, ast.ClassDef):
                    return (min([n.lineno, *(d.lineno for d in n.decorator_list)]), n.end_lineno)
                found = walk(n, name)
                if found:
                    return found
        return None
    return walk(tree, []) if function else None


def _hits(copy: Path, positions: list[dict], extra: str | None) -> tuple[list[dict], list[str]]:
    from aeropatch.tools import redos, scanners
    root = _project_root(copy)
    found, notes = [], []
    files = {}
    for pos in positions:
        f = _find(root, pos["path"])
        if f is None:
            notes.append(f"missing {pos['path']}")
            continue
        files.setdefault(f, []).append(pos["function"])
    for f, funcs in files.items():
        rel = f.relative_to(root).as_posix()
        findings = (scanners.run_opengrep(root, targets=[rel], extra=extra == "taint") or []) + \
                   (scanners.run_bandit(root, targets=[rel]) or []) + redos.scan_file(root, rel)
        spans = [s for s in (_span(f, fn) for fn in funcs) if s]
        if not spans:
            notes.append(f"no function {funcs} in {rel}; whole file used")
        for x in findings:
            if not spans or any(a <= x.line <= b for a, b in spans):
                found.append({"tool": x.tool, "rule": x.rule_id, "cwe": x.cwe, "path": rel, "line": x.line})
    return found, notes


def score(data: Path, extra: str | None, out: Path | None) -> None:
    items = json.loads(HELDOUT.read_text(encoding="utf-8"))["items"]
    rows = []
    for it in items:
        d = data / it["cve"]
        vul, notes = _hits(d / "vul", it["positions"], extra)
        fix, _ = _hits(d / "fix", it["positions"], extra) if (d / "fix").is_dir() else ([], ["no fix copy"])
        same = SAME_CLASS[it["cwe"]]
        found = [h for h in vul if h["cwe"] in same]
        on_fix = [h for h in fix if h["cwe"] in same]
        rows.append({"cve": it["cve"], "cwe": it["cwe"], "found": bool(found), "still_on_fix": bool(on_fix),
                     "any_in_function": bool(vul), "vul_hits": vul, "fix_hits": fix, "notes": notes})
        print(f"{it['cve']:16} {it['cwe']:7} found={bool(found)!s:5} on_fix={bool(on_fix)!s:5} "
              f"{sorted({h['rule'] for h in found})} other={sorted({h['rule'] for h in vul} - {h['rule'] for h in found})} "
              f"{'; '.join(notes)}", flush=True)
    n = sum(r["found"] for r in rows)
    print(f"\nfound {n} of {len(rows)}; of those, still reported on the fixed copy: "
          f"{sum(r['found'] and r['still_on_fix'] for r in rows)}")
    for cwe in sorted({r["cwe"] for r in rows}):
        sub = [r for r in rows if r["cwe"] == cwe]
        print(f"  {cwe}: {sum(r['found'] for r in sub)} of {len(sub)}")
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"extra": extra, "rows": rows}, indent=2) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("freeze")
    s.add_argument("--csv", type=Path, required=True)
    s = sub.add_parser("fetch")
    s.add_argument("--to", type=Path, required=True)
    s = sub.add_parser("score")
    s.add_argument("--data", type=Path, required=True)
    s.add_argument("--extra", choices=["taint"], help="also run the extra ruleset (rules-extra/)")
    s.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    if a.cmd == "freeze":
        freeze(a.csv)
    elif a.cmd == "fetch":
        fetch(a.to)
    else:
        score(a.data, a.extra, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
