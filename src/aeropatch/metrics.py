"""Metrics over run JSONL files (doc 12): Wilson intervals, resolve@k, exact McNemar, per CWE.

Pure functions over parsed records. No model or sandbox access, so re-scoring is instant.

    uv run aeropatch metrics runs/<a>.jsonl runs/<b>.jsonl
"""

from __future__ import annotations

import json
from itertools import combinations
from math import comb, sqrt
from pathlib import Path

from aeropatch import bench
from aeropatch.config import SCENARIOS_DIR

MAX_K = 3  # attempts in the repair plans (doc 08 part 1)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    centre = p + z * z / (2 * n)
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    denom = 1 + z * z / n
    return max(0.0, (centre - half) / denom), min(1.0, (centre + half) / denom)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for b and c discordant pairs (a binomial test at 0.5)."""
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def cwe_of(task_id: str) -> str:
    try:
        return json.loads((SCENARIOS_DIR / task_id / "scenario.json").read_text(encoding="utf-8"))["cwe"]
    except (OSError, KeyError, ValueError):
        return "?"


def run_metrics(jsonl: Path) -> dict:
    header, attempts, results = bench.read_run(jsonl)
    wins = {a["task_id"]: a for a in attempts if a["label"] == "RESOLVED"}
    trail: dict[str, list[str]] = {}
    for a in attempts:
        trail.setdefault(a["task_id"], []).append(a["label"])
    n = len(results)
    at = [sum(1 for a in wins.values() if a["n"] <= k) for k in range(1, MAX_K + 1)]
    return {
        "run": jsonl.stem, "config": header.get("config", {}).get("name", ""), "split": header.get("split", ""),
        "dirty": header.get("dirty"), "n": n,
        "resolved": {r["task_id"] for r in results if r["resolved"]},
        "tasks": {r["task_id"]: r["label"] for r in results},
        "resolve_at": at,
        # Share of first-attempt failures that a later attempt fixed (doc 12 §3).
        "repair_gain": (at[-1] - at[0]) / (n - at[0]) if n > at[0] else None,
        "by_local": sum(1 for a in wins.values() if a["route"] == "local"),
        "escalated": len({a["task_id"] for a in attempts if a["route"] in ("frontier", "claude-code")}),
        # The finding's own rule no longer fires on the resolved fix (secondary signal, doc 06 §6).
        "rule_gone": sum(1 for a in wins.values() if (a.get("sandbox") or {}).get("original_rule_present") is False),
        "cost_usd": sum(a.get("cost_usd", 0) for a in attempts),
        "trail": trail,
    }


def _pct(k: int, n: int) -> str:
    return f"{k}/{n} ({k / n:.0%})" if n else "-"


def headline(runs: list[dict]) -> str:
    columns = ["Run", "Config", "Resolved", "95% CI", "@1", "@2", "@3", "Repair gain", "Resolved locally",
               "Escalated", "Rule gone", "Cost $"]
    rows = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for m in runs:
        k, n = len(m["resolved"]), m["n"]
        lo, hi = wilson(k, n)
        gain = f"{m['repair_gain']:.0%}" if m["repair_gain"] is not None else "-"
        rows.append(f"| `{m['run']}` | {m['config']} | {_pct(k, n)} | {lo:.0%}-{hi:.0%} | "
                    + " | ".join(str(x) for x in m["resolve_at"])
                    + f" | {gain} | {m['by_local']} | {m['escalated']} | {m['rule_gone']}/{k} | {m['cost_usd']:.2f} |")
    return "\n".join(rows)


def delta(runs: list[dict]) -> str:
    rows = ["| A | B | Shared tasks | A only | B only | B - A | McNemar p (exact) |", "|---|---|---|---|---|---|---|"]
    for a, b in combinations(runs, 2):
        shared = a["tasks"].keys() & b["tasks"].keys()
        only_a = len((a["resolved"] - b["resolved"]) & shared)
        only_b = len((b["resolved"] - a["resolved"]) & shared)
        diff = f"{(only_b - only_a) / len(shared):+.0%}" if shared else "-"
        rows.append(f"| {a['config']} | {b['config']} | {len(shared)} | {only_a} | {only_b} | {diff} | "
                    f"{mcnemar_exact(only_a, only_b):.3f} |")
    return "\n".join(rows)


def per_cwe(runs: list[dict]) -> str:
    cwes: dict[str, list[str]] = {}
    for task in sorted({t for m in runs for t in m["tasks"]}):
        cwes.setdefault(cwe_of(task), []).append(task)
    rows = ["| CWE | Tasks | " + " | ".join(m["config"] for m in runs) + " |", "|---|---|" + "---|" * len(runs)]
    for cwe in sorted(cwes, key=lambda c: int(c.rsplit("-", 1)[-1]) if c[-1].isdigit() else 0):
        cells = [f"{len(m['resolved'] & set(cwes[cwe]))}/{len(m['tasks'].keys() & set(cwes[cwe]))}" for m in runs]
        rows.append(f"| {cwe} | {len(cwes[cwe])} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def attribution(m: dict) -> str:
    """Failure-attribution chart for one run: primary cause per unresolved task (doc 05 §9)."""
    causes: dict[str, list[str]] = {}
    for task, label in sorted(m["tasks"].items()):
        if label != "RESOLVED":
            causes.setdefault(label, []).append(task)
    rows = [f"| Cause ({m['config']}) | Tasks | | Which (attempt labels) |", "|---|---|---|---|"]
    for label, tasks in sorted(causes.items(), key=lambda kv: -len(kv[1])):
        which = "; ".join(f"{t} [{cwe_of(t)}]: {' > '.join(m['trail'].get(t, []))}" for t in tasks)
        rows.append(f"| {label} | {len(tasks)} | {'#' * len(tasks)} | {which} |")
    return "\n".join(rows) if causes else f"{m['config']}: every task resolved."


def report(paths: list[Path]) -> str:
    runs = [run_metrics(p) for p in paths]
    parts = ["### Headline (resolve@k is cumulative; 95% Wilson intervals)", headline(runs)]
    if len(runs) > 1:
        parts += ["### Paired comparison on the tasks both runs share", delta(runs)]
    parts += ["### Resolved per CWE", per_cwe(runs), "### Failure attribution"]
    parts += [attribution(m) for m in runs]
    dirty = [m["run"] for m in runs if m["dirty"]]
    if dirty:
        parts.append(f"Not reproducible from a commit (dirty tree): {', '.join(dirty)}")
    return "\n\n".join(parts)
