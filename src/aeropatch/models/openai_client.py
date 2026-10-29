"""Any OpenAI-compatible chat server, hosted or local (OpenAI, Gemini, Mistral, DeepSeek, xAI, Groq,
Together, OpenRouter, Hugging Face, LM Studio, llama.cpp, vLLM, Jan): POST {base}/chat/completions.
The provider table and keys are in providers.py; the key never enters cfg or the run records.
"""

from __future__ import annotations

import json
import time

import httpx

from aeropatch import providers
from aeropatch.models.base import Generation

TIMEOUT_S = 300


def generate(messages: list[dict], system: str, cfg: dict, temperature: float, on_token=None) -> Generation:
    pid, model = cfg["api_provider"], cfg["api_model"]
    p = providers.PROVIDERS[pid]
    base = providers.base_url(pid)
    if not base:
        return Generation(text="", model=model, error="PROVIDER_ERROR: no address set for this server")
    body = {"model": model, "messages": [{"role": "system", "content": system}, *messages],
            "stream": on_token is not None}
    if p.get("reasoning_style"):  # OpenAI's current models take only the default temperature
        body["max_completion_tokens"] = cfg["max_tokens_frontier"]
    else:
        body["max_tokens"] = cfg["max_tokens_frontier"]
        body["temperature"] = temperature
    headers = providers.headers(pid)
    start = time.monotonic()
    usage: dict = {}
    finish = ""
    try:
        if on_token:
            parts = []
            with httpx.stream("POST", f"{base}/chat/completions", json=body, headers=headers,
                              timeout=TIMEOUT_S) as r:
                if r.status_code != 200:
                    return Generation(text="", model=model, latency_s=time.monotonic() - start,
                                      error=f"PROVIDER_ERROR: HTTP {r.status_code}: "
                                            f"{r.read().decode('utf-8', 'replace')[:300]}")
                for line in r.iter_lines():
                    if not line.startswith("data:") or line.strip() == "data: [DONE]":
                        continue
                    chunk = json.loads(line[5:])
                    usage = chunk.get("usage") or usage
                    for choice in chunk.get("choices", []):
                        piece = (choice.get("delta") or {}).get("content") or ""
                        finish = choice.get("finish_reason") or finish
                        if piece:
                            parts.append(piece)
                            on_token("text", piece)
            text = "".join(parts)
        else:
            r = httpx.post(f"{base}/chat/completions", json=body, headers=headers, timeout=TIMEOUT_S)
            if r.status_code != 200:
                return Generation(text="", model=model, latency_s=time.monotonic() - start,
                                  error=f"PROVIDER_ERROR: HTTP {r.status_code}: {r.text[:300]}")
            data = r.json()
            usage = data.get("usage") or {}
            choice = (data.get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content") or ""
            finish = choice.get("finish_reason") or ""
    except (httpx.HTTPError, ValueError) as e:
        return Generation(text="", model=model, error=f"PROVIDER_ERROR: {type(e).__name__}: {e}"[:300],
                          latency_s=time.monotonic() - start)
    gen = Generation(text=text, model=model, latency_s=time.monotonic() - start,
                     usage={"input_tokens": usage.get("prompt_tokens", 0),
                            "output_tokens": usage.get("completion_tokens", 0), "provider": pid})
    if finish == "content_filter" and not text:
        gen.refusal = {"provider": pid, "model": model, "category": "content_filter", "explanation": ""}
    return gen
