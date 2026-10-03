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


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
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
            "split": split, "tasks": ids, "aeropatch_commit": _git("rev-parse", "HEAD"),
            # True means the code, rules or scenarios differ from that commit (new, uncommitted
            # scenario directories included): the number is not reproducible from it.
            "dirty": bool(_git("status", "--porcelain", "--", "src", "evaluations", "rules", "docker",
                               "pyproject.toml", "uv.lock")),
            "images": images,
            "host": {"platform": platform.platform(), "python": platform.python_version()}}


def done_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    records: list[tuple[dict, int]] = []
    offset = 0
    truncate_at: int | None = None
    for index, line in enumerate(lines):
        start = offset
        offset += len(line)
        if not line.strip():
            continue
        try:
            rec = json.loads(line.rstrip(b"\r\n"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            if index == len(lines) - 1:
                truncate_at = start
                break
            raise ValueError(f"corrupt benchmark JSONL at line {index + 1}") from e
        if not isinstance(rec, dict):
            raise TypeError(f"benchmark JSONL line {index + 1} is not an object")
        records.append((rec, start))

    if truncate_at is not None:
        raw = raw[:truncate_at]
        records = [(rec, start) for rec, start in records if start < truncate_at]

    completed = {rec["task_id"] for rec, _ in records if rec.get("type") == "result" and "task_id" in rec}
    task_starts: dict[str, int] = {}
    for rec, start in records:
        if rec.get("type") == "attempt" and isinstance(rec.get("task_id"), str):
            task_starts.setdefault(rec["task_id"], start)
    unfinished = next((sid for sid in task_starts if sid not in completed), None)
    if unfinished is not None:
        raw = raw[:task_starts[unfinished]]
        records = [(rec, start) for rec, start in records if start < task_starts[unfinished]]
        completed = {rec["task_id"] for rec, _ in records if rec.get("type") == "result" and "task_id" in rec}

    if not records:
        raw = b""
    if raw and not raw.endswith(b"\n"):
        raw += b"\n"
    if raw != path.read_bytes():
        path.write_bytes(raw)
    return completed


def _validate_resume_header(path: Path, cfg: dict, split: str, ids: list[str]) -> None:
    raw = path.read_bytes()
    lines = raw.splitlines()
    if not lines:
        return
    try:
        record = json.loads(lines[0])
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        if len(lines) == 1 and not raw.endswith(b"\n"):
            return
        raise ValueError("benchmark run has no valid header; choose a new --run-id") from e
    if not isinstance(record, dict) or record.get("type") != "header":
        raise ValueError("benchmark run has no valid header; choose a new --run-id")
    tasks = record.get("tasks")
    if not isinstance(tasks, list) or any(not isinstance(task, str) for task in tasks):
        raise ValueError("benchmark run has an invalid task list in its header; choose a new --run-id")
    matches = (
        record.get("config") == cfg
        and record.get("split") == split
        and set(tasks) == set(ids)
    )
    if not matches:
        raise ValueError("run_id already belongs to a different config, split, or task set")


def run_benchmark(cfg: dict, split: str = "dev", run_id: str | None = None,
                  ids: list[str] | None = None) -> Path:
    ids = sorted(set(ids or scenario.list_ids(split)))
    run_id = run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-{cfg['name']}-{split}"
    run_dir = RUNS_DIR / run_id
    jsonl = RUNS_DIR / f"{run_id}.jsonl"
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    if jsonl.exists() and jsonl.stat().st_size:
        _validate_resume_header(jsonl, cfg, split, ids)
    finished = done_ids(jsonl)
    if jsonl.exists() and jsonl.stat().st_size:
        _validate_resume_header(jsonl, cfg, split, ids)
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
    lines = jsonl.read_bytes().splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            if index == len(lines) - 1:
                break
            raise ValueError(f"corrupt benchmark JSONL at line {index + 1}") from e
        if rec["type"] == "header":
            cfg_name = rec["config"]["name"]
            from aeropatch.agent.router import model_name

            model = " + ".join(dict.fromkeys(model_name(r, rec["config"]) for r in rec["config"]["attempt_plan"]))
        elif rec["type"] == "attempt":
            attempts.append(rec)
        elif rec["type"] == "result":
            results.append(rec)
    completed_ids = {rec.get("task_id") for rec in results}
    attempts = [rec for rec in attempts if rec.get("task_id") in completed_ids]
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
