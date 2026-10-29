"""Local SLM client for Ollama's /api/chat (doc 03 §9)."""

from __future__ import annotations

import json
import re
import time

import httpx

from aeropatch.config import ROOT
from aeropatch.models.base import Generation, LocalServerDown


def _stream(url: str, body: dict, on_token) -> tuple[int, dict, str]:
    """Ollama's streamed /api/chat: hand each piece to on_token("thinking" | "text", piece) and
    return (status, the final chunk with the counts, the whole answer)."""
    parts, last = [], {}
    with httpx.stream("POST", url, json=body, timeout=600) as r:
        if r.status_code != 200:
            return r.status_code, {"error": r.read().decode("utf-8", "replace")[:300]}, ""
        for line in r.iter_lines():
            if not line.strip():
                continue
            last = json.loads(line)
            msg = last.get("message") or {}
            if msg.get("thinking"):
                on_token("thinking", msg["thinking"])
            if msg.get("content"):
                parts.append(msg["content"])
                on_token("text", msg["content"])
    return 200, last, "".join(parts)


def generate(messages: list[dict], system: str, cfg: dict, temperature: float, on_token=None) -> Generation:
    """`on_token`: optional callable; when given, the answer is streamed to it as it is written."""
    body = {
        "model": cfg["local_model"],
        "messages": [{"role": "system", "content": system}, *messages],
        "stream": on_token is not None,
        "think": cfg.get("local_think", False),
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "num_ctx": cfg["local_num_ctx"],
            "num_gpu": cfg.get("local_num_gpu", -1),
            "num_predict": cfg["max_tokens_local"],
        },
    }
    if cfg.get("local_format"):  # a JSON schema the answer must follow (the check's judge, Phase C)
        body["format"] = cfg["local_format"]
    # Diagnosis configs only: the start of the answer is written for the model. Ollama continues
    # a trailing assistant message and returns the continuation alone.
    prefill = cfg.get("local_prefill", "")
    if prefill:
        first = messages[0]["content"]
        found = re.search(r"^Message: (.*)$", first, re.MULTILINE)
        prefill = prefill.replace("{message}", found.group(1) if found else "")
        if "{plan}" in prefill:  # one line per scenario, keyed by the prompt's "Finding:" line
            plans = json.loads((ROOT / cfg["local_prefill_plans"]).read_text(encoding="utf-8"))
            prefill = prefill.replace("{plan}", plans[re.search(r"^Finding: .*$", first, re.MULTILINE).group(0)])
        body["messages"].append({"role": "assistant", "content": prefill})
    start = time.monotonic()
    url = f"{cfg['local_host'].rstrip('/')}/api/chat"
    try:
        if on_token:
            status, data, content = _stream(url, body, on_token)
            text = data.get("error", "")
        else:
            r = httpx.post(url, json=body, timeout=600)
            status, text = r.status_code, r.text
            data = r.json() if status == 200 else {}
            content = data.get("message", {}).get("content", "")
    except httpx.ConnectError as e:
        raise LocalServerDown(f"cannot reach {cfg['local_host']}: {e}") from e
    except httpx.HTTPError as e:
        return Generation(text="", model=cfg["local_model"], error=f"PROVIDER_ERROR: {e}",
                          latency_s=time.monotonic() - start)
    latency = time.monotonic() - start
    if status != 200:
        return Generation(text="", model=cfg["local_model"], latency_s=latency,
                          error=f"PROVIDER_ERROR: HTTP {status}: {text[:300]}")
    eval_ns = data.get("eval_duration") or 0
    usage = {
        "input_tokens": data.get("prompt_eval_count", 0),
        "output_tokens": data.get("eval_count", 0),
        "decode_tok_s": round(data.get("eval_count", 0) / (eval_ns / 1e9), 1) if eval_ns else None,
    }
    return Generation(text=prefill + content, model=cfg["local_model"], usage=usage, latency_s=latency)
