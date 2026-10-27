"""Phase E0 of reports/Real bug detection and model mix.md: does a candidate model fit the 4 GB GPU
and write usable edits with thinking off? No sandbox; the model sees each dev scenario's real
first prompt once.

    python evaluations/tools/model_fit.py nemotron-3-nano:4b [--ids A-089-01 ...]

Reports: share of the model in VRAM (/api/ps), peak GPU memory (nvidia-smi, sampled), load time
(load_duration), decode tok/s, whether any thinking came back, and how many answers parse and
apply as SEARCH/REPLACE edits.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aeropatch import config, scenario
from aeropatch.agent import edits, prompts
from aeropatch.tools.context import get_context

HOST = "http://127.0.0.1:11434"


def _gpu_mib() -> int:
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, check=False).stdout
    return int(out.split()[0]) if out.strip() else 0


def measure(model: str, ids: list[str]) -> dict:
    cfg = config.load_config("baseline-qwen3.5-4b")
    httpx.post(f"{HOST}/api/generate", json={"model": model, "keep_alive": 0}, timeout=120)  # unload first
    peak, stop = [_gpu_mib()], threading.Event()

    def sample():
        while not stop.is_set():
            peak.append(_gpu_mib())
            time.sleep(0.5)
    threading.Thread(target=sample, daemon=True).start()
    rows = []
    for sid in ids:
        task = scenario.load(sid)
        ctx = get_context(task.repo_path, task.finding.path, task.finding.line, task.allowed_paths)
        body = {"model": model, "stream": False, "think": False,
                "messages": [{"role": "system", "content": prompts.SYSTEM_PROMPT},
                             {"role": "user", "content": prompts.first_user_message(task, ctx)}],
                "options": {"temperature": cfg["temperature_first"], "top_p": 0.9, "num_ctx": cfg["local_num_ctx"],
                            "num_gpu": cfg["local_num_gpu"], "num_predict": cfg["max_tokens_local"]}}
        try:
            r = httpx.post(f"{HOST}/api/chat", json=body, timeout=600).json()
        except httpx.HTTPError as e:
            rows.append({"id": sid, "error": str(e)})
            continue
        msg = r.get("message", {})
        text = msg.get("content", "")
        originals = {p: (task.repo_path / p).read_text(encoding="utf-8") for p in task.allowed_paths}
        p = edits.parse(text, originals)
        applies = False
        if not p.parse_error and p.edits:
            try:
                edits.apply_edits(dict(originals), p.edits)
                applies = True
            except edits.ApplyError:
                pass
        rows.append({"id": sid, "error": r.get("error", ""), "load_s": round(r.get("load_duration", 0) / 1e9, 2),
                     "tok_s": round(r["eval_count"] / (r["eval_duration"] / 1e9), 1) if r.get("eval_duration") else None,
                     "out_tokens": r.get("eval_count"), "thinking_chars": len(msg.get("thinking") or ""),
                     "think_tag": "<think>" in text, "parses": not p.parse_error and bool(p.edits),
                     "applies": applies})
    ps = httpx.get(f"{HOST}/api/ps", timeout=30).json().get("models", [])
    stop.set()
    loaded = next((m for m in ps if m["name"] == model or m["model"] == model), {})
    good = [x for x in rows if not x.get("error")]
    summary = {
        "model": model, "size": loaded.get("size"), "size_vram": loaded.get("size_vram"),
        "fully_on_gpu": bool(loaded) and loaded.get("size") == loaded.get("size_vram"),
        "peak_gpu_mib": max(peak),
        "first_load_s": good[0]["load_s"] if good else None,
        "median_tok_s": sorted(x["tok_s"] for x in good if x["tok_s"])[len(good) // 2] if good else None,
        "thinking_seen": sum(x["thinking_chars"] > 0 or x["think_tag"] for x in good),
        "parses": sum(x["parses"] for x in good), "applies": sum(x["applies"] for x in good), "n": len(rows),
        "rows": rows}
    httpx.post(f"{HOST}/api/generate", json={"model": model, "keep_alive": 0}, timeout=120)
    return summary


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("model")
    p.add_argument("--ids", nargs="*")
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    s = measure(a.model, a.ids or scenario.list_ids("dev"))
    print(json.dumps({k: v for k, v in s.items() if k != "rows"}, indent=2))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(s, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
