"""Headroom of the untuned model on its own training pool (rung 2 of
reports/AeroPatch model improvement.md).

k one-attempt samples (`sample-local`: temperature 0.7, no feedback) on the 105 synthetic
scenarios that dataset v2 kept, one run file per sample, then pass@1 against pass@k:

    uv run python training/sample_synthetic.py --runs 8 --prefix 20261021-h

A stopped run resumes under the same run ID; finished runs are skipped. The model is unloaded
between runs, because the model server grows while one model stays loaded (NOTES, D20).
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess

from aeropatch import bench, scenario
from aeropatch.config import ROOT, RUNS_DIR, load_config
from aeropatch.metrics import pass_at_k

DATA = ROOT / "training" / "data" / "v2"
scenario.SCENARIOS_DIR = ROOT / "training" / "synthetic"  # as inject_cwe.py --student does


def drop_unanswered(jsonl) -> None:
    """A sample the model server never answered is no sample: remove it, so the resume redoes it.
    On 2026-10-21 Ollama's auto-update stopped the server in the middle of run 7."""
    if not jsonl.exists():
        return
    recs = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError:
            pass  # a torn last line from a kill
    bad = {r["task_id"] for r in recs if r["type"] == "result" and r["label"] == "PROVIDER_ERROR"}
    if bad:
        print("redoing", sorted(bad), "in", jsonl.name, flush=True)
        jsonl.write_text("".join(json.dumps(r, default=str) + "\n" for r in recs if r.get("task_id") not in bad),
                         encoding="utf-8")


def pool() -> list[str]:
    """The synthetic first attempts in dataset v2: the scenarios left after every filter."""
    rows = (json.loads(line) for f in ("train.jsonl", "val.jsonl")
            for line in (DATA / f).open(encoding="utf-8"))
    return sorted({r["id"] for r in rows if r["source"] == "synthetic" and r["slice"] == "first"})


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=8)
    p.add_argument("--prefix", required=True, help="run IDs are <prefix><i>-sample-local-train")
    p.add_argument("--local-model", default="aeropatch-control")
    args = p.parse_args()
    ids = pool()
    cfg = load_config("sample-local", local_model=args.local_model)
    files = []
    for i in range(1, args.runs + 1):
        run_id = f"{args.prefix}{i}-sample-local-train"
        drop_unanswered(RUNS_DIR / f"{run_id}.jsonl")
        path = bench.run_benchmark(cfg, "train", run_id, ids)
        subprocess.run(["ollama", "stop", args.local_model], check=False)
        files.append(path)

    solved = {sid: 0 for sid in ids}
    for f in files:
        for r in bench.read_run(f)[2]:
            solved[r["task_id"]] += bool(r["resolved"])
    n = len(files)
    counts = list(solved.values())
    print(f"{len(ids)} scenarios, {n} samples each")
    for k in sorted({1, 3, n}):
        print(f"pass@{k}: {statistics.fmean(pass_at_k(n, c, k) for c in counts):.1%}")
    print("never solved:", sum(c == 0 for c in counts), " always solved:", sum(c == n for c in counts),
          " partly solved:", sum(0 < c < n for c in counts))


if __name__ == "__main__":
    main()
