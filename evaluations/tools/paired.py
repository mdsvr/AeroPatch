"""Paired comparisons for Phases D2 and E2 of reports/Real bug detection and model mix.md.

    python evaluations/tools/paired.py arms --a RUN.jsonl... --b RUN.jsonl...
    python evaluations/tools/paired.py mix --qwen SEED1_RUNS... --b SEED1_RUNS... [--qwen ... --b ...]

`arms`: each arm's outcome on a task is the majority of its runs (solved in at least 2 of 3), and
the exact McNemar test counts the tasks where the two majorities differ. Also the per-run counts
and how often "Scanner quiet, your tests still pass" was right.

`mix` (one --qwen/--b pair per seed, single-attempt sample runs in order): Qwen x10 against
Qwen x5 + B x5 at two layers. Coverage: some sample passes the hidden suites (oracle selection).
Deployable: walk the samples in a fixed order (Qwen 1-10, or Qwen 1, B 1, Qwen 2, B 2, ...), offer
the first that earns "Scanner quiet, your tests still pass" with the PoC hidden, and count the task
solved when that sample passes the hidden suites.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aeropatch import labels
from aeropatch.bench import read_run
from aeropatch.contracts import SandboxResult
from aeropatch.metrics import mcnemar_exact


def _results(path: Path) -> dict[str, dict]:
    _, attempts, results = read_run(path)
    by_task = {r["task_id"]: dict(r, attempts=[]) for r in results}
    for a in attempts:
        if a.get("task_id") in by_task:
            by_task[a["task_id"]]["attempts"].append(a)
    return by_task


def _verdict(a: list[bool], b: list[bool], tasks: list[str]) -> str:
    only_a = sum(x and not y for x, y in zip(a, b, strict=True))
    only_b = sum(y and not x for x, y in zip(a, b, strict=True))
    p = mcnemar_exact(only_a, only_b) if only_a + only_b else 1.0
    return f"A {sum(a)} of {len(tasks)}, B {sum(b)} of {len(tasks)}; only A {only_a}, only B {only_b}, exact McNemar p = {p:.3f}"


def arms(a_paths: list[Path], b_paths: list[Path]) -> None:
    runs = {"A": [_results(p) for p in a_paths], "B": [_results(p) for p in b_paths]}
    tasks = sorted(set.intersection(*(set(r) for rs in runs.values() for r in rs)))
    for name, rs in runs.items():
        counts = [sum(r[t]["resolved"] for t in tasks) for r in rs]
        offered = [r[t] for r in rs for t in tasks if r[t].get("user_label") == labels.QUIET_TESTS_PASS]
        print(f"{name}: resolved per run {counts} of {len(tasks)}; '{labels.QUIET_TESTS_PASS}' right "
              f"{sum(x['resolved'] for x in offered)} of {len(offered)}")
    major = {name: [sum(r[t]["resolved"] for r in rs) * 2 > len(rs) for t in tasks] for name, rs in runs.items()}
    print("majority of runs:", _verdict(major["A"], major["B"], tasks))
    for t, x, y in zip(tasks, major["A"], major["B"], strict=True):
        if x != y:
            print(f"   {t}: {'A' if x else 'B'} only")


def _sample(rec: dict | None) -> tuple[bool, bool]:
    """(passes the hidden suites, would be offered with the PoC hidden) for a one-attempt sample."""
    if rec is None:
        return False, False
    numbered = [a for a in rec["attempts"] if a.get("n")]
    sb = numbered[-1].get("sandbox") if numbered else None
    if not sb:
        return False, False
    res = SandboxResult(**{k: v for k, v in sb.items() if k in SandboxResult.__dataclass_fields__})
    res.failures = []
    offered = labels.user_label(res, ["poc"]) == labels.QUIET_TESTS_PASS
    return bool(sb.get("poc_passed") and sb.get("regressions_passed")), offered


def _deployable(samples: list[tuple[bool, bool]]) -> bool:
    return next((ok for ok, offered in samples if offered), False)


def mix(qwen_seeds: list[list[Path]], b_seeds: list[list[Path]]) -> None:
    seeds = []
    for q_paths, b_paths in zip(qwen_seeds, b_seeds, strict=True):
        q = [_results(p) for p in q_paths]
        b = [_results(p) for p in b_paths]
        tasks = sorted(set.union(*(set(r) for r in q + b)))
        row = {}
        for t in tasks:
            qs = [_sample(r.get(t)) for r in q]
            bs = [_sample(r.get(t)) for r in b]
            k = len(bs)
            mixed = [s for pair in zip(qs[:k], bs, strict=True) for s in pair]
            row[t] = {"cover_q": any(ok for ok, _ in qs), "cover_mix": any(ok for ok, _ in mixed),
                      "deploy_q": _deployable(qs), "deploy_mix": _deployable(mixed),
                      "b_only": any(ok for ok, _ in bs) and not any(ok for ok, _ in qs)}
        seeds.append(row)
        print(f"seed {len(seeds)}: coverage Qwen x{len(q)} {sum(v['cover_q'] for v in row.values())}, "
              f"mix {sum(v['cover_mix'] for v in row.values())}; deployable Qwen "
              f"{sum(v['deploy_q'] for v in row.values())}, mix {sum(v['deploy_mix'] for v in row.values())} "
              f"of {len(tasks)}; solved by B and by no Qwen sample: {[t for t, v in row.items() if v['b_only']]}")
    tasks = sorted(set.intersection(*(set(s) for s in seeds)))
    for layer in ("cover", "deploy"):
        a = [sum(s[t][f"{layer}_q"] for s in seeds) * 2 > len(seeds) for t in tasks]
        b = [sum(s[t][f"{layer}_mix"] for s in seeds) * 2 > len(seeds) for t in tasks]
        print(f"{layer:7} (A = Qwen only, B = mix): {_verdict(a, b, tasks)}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("arms")
    s.add_argument("--a", type=Path, nargs="+", required=True)
    s.add_argument("--b", type=Path, nargs="+", required=True)
    s = sub.add_parser("mix")
    s.add_argument("--qwen", type=Path, nargs="+", action="append", required=True)
    s.add_argument("--b", type=Path, nargs="+", action="append", required=True)
    a = p.parse_args(argv)
    if a.cmd == "arms":
        arms(a.a, a.b)
    else:
        mix(a.qwen, a.b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
