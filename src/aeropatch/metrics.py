"""Metrics over run JSONL files (doc 12): Wilson intervals, resolve@k, exact McNemar, per CWE.

Pure functions over parsed records. No model or sandbox access, so re-scoring is instant.

    uv run aeropatch report runs/<a>.jsonl runs/<b>.jsonl
"""

from __future__ import annotations

import json
import statistics
from itertools import combinations
from math import comb, sqrt
from pathlib import Path

from aeropatch import bench
from aeropatch.agent.router import model_name
from aeropatch.config import SCENARIOS_DIR


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
    cfg = header.get("config", {})
    wins = {a["task_id"]: a for a in attempts if a["label"] == "RESOLVED"}
    trail: dict[str, list[str]] = {}
    for a in attempts:
        trail.setdefault(a["task_id"], []).append(a["label"])
    numbered = [a for a in attempts if a["n"] > 0]
    first = [a for a in numbered if a["n"] == 1]
    latency = [a["latency_s"] for a in numbered if a.get("latency_s") is not None]
    tok_s = [t for a in numbered if (t := ((a.get("proposal") or {}).get("usage") or {}).get("decode_tok_s"))]
    n = len(results)
    at = [sum(1 for a in wins.values() if a["n"] <= k) for k in (1, 2, 3)]  # the repair plans have 3 entries
    return {
        "run": jsonl.stem, "config": cfg.get("name", ""), "dirty": header.get("dirty"), "n": n,
        "model": " + ".join(dict.fromkeys(model_name(r, cfg) for r in cfg.get("attempt_plan", []))),
        "resolved": {r["task_id"] for r in results if r["resolved"]},
        "tasks": {r["task_id"]: r["label"] for r in results},
        "resolve_at": at,
        # Share of first-attempt failures that a later attempt fixed (doc 12 §3).
        "repair_gain": (at[-1] - at[0]) / (n - at[0]) if n > at[0] else None,
        "by_local": sum(1 for a in wins.values() if a["route"] == "local"),
        "escalated": len({a["task_id"] for a in attempts if a["route"] in ("frontier", "claude-code")}),
        # The finding's own rule no longer fires on the resolved fix (secondary signal, doc 06 §6).
        # None when no rescan applies (an advisory finding has no rule to re-run).
        "rule_gone": [(a.get("sandbox") or {}).get("original_rule_present") for a in wins.values()].count(False)
        if any((a.get("sandbox") or {}).get("original_rule_present") is not None for a in wins.values()) else None,
        # First attempts: the edit applied (it reached the gates), and its PoC passed.
        "applied": sum(1 for a in first if a.get("sandbox") or a["label"] == "GATE_REJECT"),
        "poc_fixed": sum(1 for a in first if (a.get("sandbox") or {}).get("poc_passed")),
        "latency_p50": statistics.median(latency) if latency else None,
        "tok_s_p50": statistics.median(tok_s) if tok_s else None,
        "refusals": sum(1 for a in attempts if a["label"] == "REFUSAL"),
        "cost_usd": sum(a.get("cost_usd", 0) for a in attempts),
        "trail": trail,
    }


def _table(columns: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    return "\n".join(lines + ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows])


def _fmt(value: float | None, spec: str) -> str:
    return "-" if value is None else format(value, spec)


def headline(runs: list[dict]) -> str:
    rows = []
    for m in runs:
        k, n = len(m["resolved"]), m["n"]
        lo, hi = wilson(k, n)
        rows.append([f"`{m['run']}`", m["config"], f"{k}/{n} ({_fmt(k / n if n else None, '.0%')})",
                     f"{lo:.0%}-{hi:.0%}", *m["resolve_at"], _fmt(m["repair_gain"], ".0%"), m["by_local"],
                     m["escalated"], "-" if m["rule_gone"] is None else f"{m['rule_gone']}/{k}"])
    return _table(["Run", "Config", "Resolved", "95% CI", "@1", "@2", "@3", "Repair gain", "Resolved locally",
                   "Escalated", "Rule gone"], rows)


def speed(runs: list[dict]) -> str:
    return _table(["Run", "Model", "Applied @1", "PoC fixed @1", "p50 latency s", "tok/s", "Refusals", "Cost $"],
                  [[m["label"], m["model"], f"{m['applied']}/{m['n']}", f"{m['poc_fixed']}/{m['n']}",
                    _fmt(m["latency_p50"], ".1f"), _fmt(m["tok_s_p50"], ".1f"), m["refusals"],
                    f"{m['cost_usd']:.2f}"] for m in runs])


def delta(runs: list[dict]) -> str:
    rows = []
    for a, b in combinations(runs, 2):
        shared = a["tasks"].keys() & b["tasks"].keys()
        only_a = len((a["resolved"] - b["resolved"]) & shared)
        only_b = len((b["resolved"] - a["resolved"]) & shared)
        rows.append([a["label"], b["label"], len(shared), only_a, only_b,
                     _fmt((only_b - only_a) / len(shared) if shared else None, "+.0%"),
                     f"{mcnemar_exact(only_a, only_b):.3f}"])
    return _table(["A", "B", "Shared tasks", "A only", "B only", "B - A", "McNemar p (exact)"], rows)


def per_cwe(runs: list[dict]) -> str:
    cwes: dict[str, set[str]] = {}
    for task in {t for m in runs for t in m["tasks"]}:
        cwes.setdefault(cwe_of(task), set()).add(task)
    return _table(["CWE", "Tasks", *(m["label"] for m in runs)],
                  [[cwe, len(cwes[cwe]), *(f"{len(m['resolved'] & cwes[cwe])}/{len(m['tasks'].keys() & cwes[cwe])}"
                                           for m in runs)]
                   for cwe in sorted(cwes, key=lambda c: int(c.rsplit("-", 1)[-1]) if c[-1].isdigit() else 0)])


def attribution(m: dict) -> str:
    """Failure-attribution chart for one run: primary cause per unresolved task (doc 05 §9)."""
    causes: dict[str, list[str]] = {}
    for task, label in sorted(m["tasks"].items()):
        if label != "RESOLVED":
            causes.setdefault(label, []).append(task)
    if not causes:
        return f"{m['label']}: every task resolved."
    return _table([f"Cause ({m['label']})", "Tasks", "", "Which (attempt labels)"],
                  [[label, len(tasks), "#" * len(tasks),
                    "; ".join(f"{t} [{cwe_of(t)}]: {' > '.join(m['trail'].get(t, []))}" for t in tasks)]
                   for label, tasks in sorted(causes.items(), key=lambda kv: -len(kv[1]))])


def report(paths: list[Path]) -> str:
    runs = [run_metrics(p) for p in paths]
    configs = [m["config"] for m in runs]
    for m in runs:  # two runs of one config are told apart by their run id
        m["label"] = m["config"] if configs.count(m["config"]) == 1 else m["run"]
    parts = ["### Headline (resolve@k is cumulative; 95% Wilson intervals)", headline(runs),
             "### First attempt, speed and cost", speed(runs)]
    if len(runs) > 1:
        parts += ["### Paired comparison on the tasks both runs share", delta(runs)]
    parts += ["### Resolved per CWE", per_cwe(runs), "### Failure attribution"]
    parts += [attribution(m) for m in runs]
    dirty = [m["run"] for m in runs if m["dirty"]]
    if dirty:
        parts.append(f"Not reproducible from a commit (dirty tree): {', '.join(dirty)}")
    return "\n\n".join(parts)
