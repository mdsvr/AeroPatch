"""Frontier fallback via the official anthropic SDK (doc 04 §6-7).

- Adaptive thinking; depth via output_config.effort.
- Server-side refusal fallbacks (`fallbacks: "default"`, beta server-side-fallback-2026-07-01).
- stop_reason is checked before content: a refusal is a routing event, not an error.
- The stable system prompt is marked cacheable; usage (incl. cache reads) is recorded per call.
"""

from __future__ import annotations

import time

import anthropic

from aeropatch.config import PRICES
from aeropatch.models.base import Generation

FALLBACK_BETA = "server-side-fallback-2026-07-01"


def _cost(model: str, usage: dict) -> float:
    inp, out = PRICES.get(model, (0.0, 0.0))
    cached = usage.get("cache_read_input_tokens") or 0
    written = usage.get("cache_creation_input_tokens") or 0
    return round((usage.get("input_tokens", 0) * inp + written * inp * 1.25 + cached * inp * 0.1
                  + usage.get("output_tokens", 0) * out) / 1e6, 6)


def generate(messages: list[dict], system: str, cfg: dict, temperature: float,
             client: anthropic.Anthropic | None = None) -> Generation:
    # Sampling parameters are not accepted on current models; `temperature` is unused here.
    model = cfg["frontier_model"]
    client = client or anthropic.Anthropic()
    kwargs = {
        "model": model,
        "max_tokens": cfg["max_tokens_frontier"],
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": messages,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": cfg["frontier_effort"]},
    }
    start = time.monotonic()
    try:
        if cfg.get("server_side_fallbacks"):
            with client.beta.messages.stream(betas=[FALLBACK_BETA], extra_body={"fallbacks": "default"},
                                             **kwargs) as stream:
                msg = stream.get_final_message()
        else:
            with client.messages.stream(**kwargs) as stream:
                msg = stream.get_final_message()
    except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError) as e:
        # The SDK already retried twice with backoff.
        return Generation(text="", model=model, error=f"PROVIDER_ERROR: {type(e).__name__}",
                          latency_s=time.monotonic() - start)
    except anthropic.APIStatusError as e:
        return Generation(text="", model=model, error=f"PROVIDER_ERROR: HTTP {e.status_code}: {e.message[:300]}",
                          latency_s=time.monotonic() - start)
    latency = time.monotonic() - start
    u = msg.usage
    usage = {
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
        "served_by": msg.model,
    }
    gen = Generation(text="", model=model, usage=usage, latency_s=latency, cost_usd=_cost(msg.model, usage))
    if msg.stop_reason == "refusal":
        details = getattr(msg, "stop_details", None)
        gen.refusal = {
            "provider": "anthropic",
            "model": msg.model,
            "category": getattr(details, "category", None),
            "explanation": (getattr(details, "explanation", None) or "")[:300],
        }
        return gen
    gen.text = "".join(b.text for b in msg.content if b.type == "text")
    return gen
