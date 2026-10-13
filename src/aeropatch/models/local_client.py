"""Local SLM client for Ollama's /api/chat (doc 03 §9)."""

from __future__ import annotations

import json
import re
import time

import httpx

from aeropatch.config import ROOT
from aeropatch.models.base import Generation, LocalServerDown


def generate(messages: list[dict], system: str, cfg: dict, temperature: float) -> Generation:
    body = {
        "model": cfg["local_model"],
        "messages": [{"role": "system", "content": system}, *messages],
        "stream": False,
        "think": cfg.get("local_think", False),
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "num_ctx": cfg["local_num_ctx"],
            "num_gpu": cfg.get("local_num_gpu", -1),
            "num_predict": cfg["max_tokens_local"],
        },
    }
    # Diagnosis configs only: the start of the answer is written for the model. Ollama continues
    # a trailing assistant message and returns the continuation alone.
    prefill = cfg.get("local_prefill", "")
    if prefill:
        first = messages[0]["content"]
        found = re.search(r"^Message: (.*)$", first, re.M)
        prefill = prefill.replace("{message}", found.group(1) if found else "")
        if "{plan}" in prefill:  # one line per scenario, keyed by the prompt's "Finding:" line
            plans = json.loads((ROOT / cfg["local_prefill_plans"]).read_text(encoding="utf-8"))
            prefill = prefill.replace("{plan}", plans[re.search(r"^Finding: .*$", first, re.M).group(0)])
        body["messages"].append({"role": "assistant", "content": prefill})
    start = time.monotonic()
    try:
        r = httpx.post(f"{cfg['local_host'].rstrip('/')}/api/chat", json=body, timeout=600)
    except httpx.ConnectError as e:
        raise LocalServerDown(f"cannot reach {cfg['local_host']}: {e}") from e
    except httpx.HTTPError as e:
        return Generation(text="", model=cfg["local_model"], error=f"PROVIDER_ERROR: {e}",
                          latency_s=time.monotonic() - start)
    latency = time.monotonic() - start
    if r.status_code != 200:
        return Generation(text="", model=cfg["local_model"], latency_s=latency,
                          error=f"PROVIDER_ERROR: HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    eval_ns = data.get("eval_duration") or 0
    usage = {
        "input_tokens": data.get("prompt_eval_count", 0),
        "output_tokens": data.get("eval_count", 0),
        "decode_tok_s": round(data.get("eval_count", 0) / (eval_ns / 1e9), 1) if eval_ns else None,
    }
    return Generation(text=prefill + data.get("message", {}).get("content", ""),
                      model=cfg["local_model"], usage=usage, latency_s=latency)
