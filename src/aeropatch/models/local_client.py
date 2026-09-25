"""Local SLM client for Ollama's /api/chat (doc 03 §9)."""

from __future__ import annotations

import time

import httpx

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
            "num_predict": cfg["max_tokens_local"],
        },
    }
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
    return Generation(text=data.get("message", {}).get("content", ""), model=cfg["local_model"],
                      usage=usage, latency_s=latency)
