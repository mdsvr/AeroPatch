"""Benchmark runner and baseline table (doc 11 §8, doc 12).

One append-only JSONL per run: a header line, then one line per Attempt and a RunResult line
per task. A killed run resumes by skipping task IDs that already have a RunResult line.
"""

from __future__ import annotations

import json
import platform
import statistics
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from aeropatch import scenario
from aeropatch.agent import loop
from aeropatch.config import ROOT, RUNS_DIR


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    except OSError:
        return ""


def header(cfg: dict, split: str, ids: list[str]) -> dict:
    images = {}
    for sid in ids:
        try:
            from aeropatch.sandbox import sandbox

            images[sid] = sandbox.image_id(scenario.image_tag(sid))
        except Exception:  # noqa: BLE001 - header info is best effort
            images[sid] = None
    return {"type": "header", "time": datetime.now(UTC).isoformat(), "config": cfg,
            "split": split, "tasks": ids, "aeropatch_commit": _git_commit(), "images": images,
            "host": {"platform": platform.platform(), "python": platform.python_version()}}


def done_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec.get("type") == "result":
            out.add(rec["task_id"])
    return out


def run_benchmark(cfg: dict, split: str = "dev", run_id: str | None = None,
                  ids: list[str] | None = None) -> Path:
    ids = ids or scenario.list_ids(split)
    run_id = run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-{cfg['name']}-{split}"
    run_dir = RUNS_DIR / run_id
    jsonl = RUNS_DIR / f"{run_id}.jsonl"
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    finished = done_ids(jsonl)
    with jsonl.open("a", encoding="utf-8") as out:
        if not jsonl.stat().st_size:
            out.write(json.dumps(header(cfg, split, ids), default=str) + "\n")
        for sid in sorted(ids):
            if sid in finished:
                continue
            task = scenario.load(sid)
            scenario.ensure_image(sid)
            result = loop.run(task, cfg, run_dir)
            for a in result.attempts:
                out.write(json.dumps({"type": "attempt", "task_id": sid, **a.to_dict()}, default=str) + "\n")
            summary = result.to_dict()
            summary.pop("attempts")
            out.write(json.dumps({"type": "result", **summary}, default=str) + "\n")
            out.flush()
            print(f"{sid}: {result.label} ({result.duration_s}s)", flush=True)
    return jsonl


def summarize(jsonl: Path) -> dict:
    cfg_name, attempts, results = "", [], []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["type"] == "header":
            cfg_name = rec["config"]["name"]
            model = rec["config"].get("local_model") if rec["config"]["attempt_plan"][0] == "local" \
                else rec["config"].get("frontier_model")
        elif rec["type"] == "attempt":
            attempts.append(rec)
        elif rec["type"] == "result":
            results.append(rec)
    numbered = [a for a in attempts if a["n"] > 0]
    first = [a for a in numbered if a["n"] == 1]
    n = len(results) or 1
    applied = sum(1 for a in first if a.get("sandbox") or a["label"] == "GATE_REJECT")
    poc = sum(1 for a in first if (a.get("sandbox") or {}).get("poc_passed"))
    lat = [a["latency_s"] for a in numbered]
    tok_s = [((a.get("proposal") or {}).get("usage") or {}).get("decode_tok_s") for a in numbered]
    tok_s = [t for t in tok_s if t]
    return {
        "config": cfg_name, "model": model if results else "", "tasks": len(results),
        "apply_rate": applied / n, "poc_fixed_rate": poc / n,
        "resolve_rate": sum(r["resolved"] for r in results) / n,
        "latency_p50_s": statistics.median(lat) if lat else None,
        "decode_tok_s_p50": statistics.median(tok_s) if tok_s else None,
        "refusals": sum(1 for a in attempts if a["label"] == "REFUSAL"),
        "cost_usd": round(sum(a.get("cost_usd", 0) for a in attempts), 4),
        "labels": {lab: sum(1 for r in results if r["label"] == lab) for lab in sorted({r["label"] for r in results})},
    }


def table(paths: list[Path]) -> str:
    rows = ["| Config | Model | Tasks | Apply | PoC fixed | Resolved | p50 latency (s) | tok/s | Cost $ | Failure causes |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for p in paths:
        s = summarize(p)
        causes = ", ".join(f"{k} {v}" for k, v in s["labels"].items() if k != "RESOLVED")
        lat = f"{s['latency_p50_s']:.1f}" if s["latency_p50_s"] is not None else "-"
        rows.append(f"| {s['config']} | {s['model']} | {s['tasks']} | {s['apply_rate']:.0%} | "
                    f"{s['poc_fixed_rate']:.0%} | {s['resolve_rate']:.0%} | {lat} | "
                    f"{s['decode_tok_s_p50'] or '-'} | {s['cost_usd']} | {causes or '-'} |")
    return "\n".join(rows)
