"""Dataset v3: the untuned model's own sandbox-passing answers (rung 3 of
reports/AeroPatch model improvement.md, as corrected in NOTES on 2026-10-21).

v2's synthetic examples keep their prompts, conversations and train/val split. Each target is
replaced by an answer of the model that resolved that same prompt in the sandbox: for a first
attempt, distinct answers from the sample-local runs of training/sample_synthetic.py (2 for a
scenario solved in some samples, 1 for one solved in all); for a repair turn, the student pass's
own next attempt when it resolved. v2's advisory fixes, bug fixes and reference-fix targets are
left out. A new target passes v2's secret, length and leakage checks again.

    uv run python training/own_fixes.py --runs 20261021-h --out training/data/v3
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_dataset as pd

from aeropatch import bench
from aeropatch.agent import edits, prompts
from aeropatch.config import RUNS_DIR

V2 = pd.DATA / "v2"
STUDENT = "20261009-student-pass"


def resolved(run_id: str) -> dict[tuple[str, int], list[dict]]:
    """{(scenario, attempt n): [{prompt, answer, diff, sent}]} for the resolved attempts of a run."""
    _, attempts, _ = bench.read_run(RUNS_DIR / f"{run_id}.jsonl")
    out: dict[tuple[str, int], list[dict]] = {}
    for a in attempts:
        if a["label"] == "RESOLVED" and a["n"]:
            adir = RUNS_DIR / run_id / a["task_id"] / f"attempt_{a['n']}"
            out.setdefault((a["task_id"], a["n"]), []).append({
                "prompt": (adir / "prompt.txt").read_text(encoding="utf-8"),
                "answer": (adir / "raw_output.txt").read_text(encoding="utf-8"),
                "diff": a["diff"], "sent": a["proposal"]["usage"].get("input_tokens")})
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", required=True, help="prefix of the sample runs: <prefix><i>-sample-local-train")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    v2 = [e for f in ("train.jsonl", "val.jsonl") for e in pd._jsonl(V2 / f) if e["source"] == "synthetic"]
    samples: dict[str, list[dict]] = {}
    files = sorted(RUNS_DIR.glob(f"{args.runs}*-sample-local-train.jsonl"))
    for f in files:
        for (sid, _), got in resolved(f.stem).items():
            samples.setdefault(sid, []).extend(got)
    student = resolved(STUDENT)
    runs, answers, _ = pd.benchmark()
    stats: Counter[str] = Counter()

    def clean(e: dict, target: str) -> bool:
        """v2's checks on a new target: no secret, no copied benchmark code. As in v2, the system
        prompt and its format example are left out: every prompt holds them, at inference too, and
        the example shares a line with the reference fix of A-089-01."""
        shown = "\n".join(m["content"] for m in e["messages"][1:]).replace(edits.FORMAT_EXAMPLE, "")
        mine = pd.grams(shown + "\n" + target, 13)
        # ponytail: the adversarial X- scenarios postdate v2; they are copies of A-089-01, so Tier A's limit.
        leaked = any(mine & a for a in answers.values()) or any(
            len(mine & r) > pd.LEAK_RUNS.get(sid[0], pd.LEAK_RUNS["A"]) for sid, r in runs.items())
        stats["leaked"] += leaked
        return not (leaked or prompts._secret_reason(target))

    examples = []
    for e in v2:
        said = prompts.SYSTEM_PROMPT + "\n\n" + "\n\n".join(m["content"] for m in e["messages"][1:])
        sid = e["id"].split("#")[0]
        if e["slice"] == "first":
            got = samples.get(sid, [])
            want = 1 if len(got) == len(files) else 2
        else:  # a repair turn after attempt n: the student's attempt n + 1, if it resolved
            got, want = student.get((sid, int(e["id"].split("#")[1]) + 1), []), 1
        stats[f"{e['slice']}: v2 examples"] += 1
        stats[f"{e['slice']}: prompt differs from v2"] += sum(g["prompt"] != said for g in got)
        diffs: set[str] = set()
        for g in got:
            if len(diffs) == want:
                break
            if g["prompt"] != said or g["diff"] in diffs:
                continue
            tokens = (g["sent"] or pd.n_tokens(said)) + pd.n_tokens(g["answer"])
            if tokens > pd.MAX_TOKENS or not clean(e, g["answer"]):
                continue
            diffs.add(g["diff"])
            examples.append({**e, "id": f"{e['id']}~{len(diffs)}", "source": "own", "tokens": tokens,
                             "prompt_tokens": g["sent"], "target": g["answer"],
                             "format": e["format"] if e["slice"] != "first" else
                             g["answer"].count("<<<<<<< SEARCH") >= 3})
        stats[f"{e['slice']}: examples"] += len(diffs)
    args.out.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val"):
        with (args.out / f"{split}.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            out.writelines(json.dumps(x) + "\n" for x in examples if x["split"] == split)
    stats["train"], stats["val"] = (sum(x["split"] == s for x in examples) for s in ("train", "val"))
    print(f"{len(files)} sample runs;", dict(sorted(stats.items())))


if __name__ == "__main__":
    main()
