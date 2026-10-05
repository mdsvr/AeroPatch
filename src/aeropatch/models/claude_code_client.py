"""Frontier reference via headless Claude Code (`claude -p`) on the user's subscription.

Same contract as fallback_client: context in, edit text out, no tools. The CLI runs with every
built-in tool disabled, AeroPatch's own system prompt (not Claude Code's), no settings, MCP
servers or session files, in an empty temp dir. The model sees the API route's prompt plus a small
fixed prefix Claude Code adds (~250 tokens, measured 2026-09-29); dev-split attempts total ~0.9k.
`cost_usd` is the CLI's API-equivalent estimate; nothing is billed per token on a subscription.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from aeropatch.models.base import Generation

TIMEOUT_S = 300


def _prompt(messages: list[dict]) -> str:
    # ponytail: repair turns are flattened into one prompt; claude -p takes a single user message.
    if len(messages) == 1:
        return messages[0]["content"]
    return "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)


def generate(messages: list[dict], system: str, cfg: dict, temperature: float,
             run=subprocess.run) -> Generation:
    model = cfg["frontier_model"]
    exe = shutil.which("claude")
    if not exe:
        return Generation(text="", model=model, error="PROVIDER_ERROR: claude CLI not found on PATH")
    # Subscription auth only: an API key in the environment would take precedence and bill it.
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "CLAUDECODE")}
    start = time.monotonic()
    # Windows: claude.exe can still hold the dir briefly after exit; a leftover empty dir is harmless.
    with tempfile.TemporaryDirectory(prefix="aeropatch-cc-", ignore_cleanup_errors=True) as tmp:
        sys_file = Path(tmp) / "system.txt"
        sys_file.write_text(system, encoding="utf-8")
        cmd = [exe, "-p", "--model", model, "--effort", cfg["frontier_effort"],
               "--output-format", "json", "--tools", "", "--system-prompt-file", str(sys_file),
               "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence",
               "--disable-slash-commands"]
        try:
            proc = run(cmd, input=_prompt(messages), capture_output=True, text=True, encoding="utf-8",
                       cwd=tmp, env=env, timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return Generation(text="", model=model, error=f"PROVIDER_ERROR: claude -p timed out after {TIMEOUT_S}s",
                              latency_s=time.monotonic() - start)
    latency = time.monotonic() - start
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        detail = (proc.stderr or proc.stdout or "").strip()[:300]
        return Generation(text="", model=model, error=f"PROVIDER_ERROR: exit {proc.returncode}: {detail}",
                          latency_s=latency)
    u = out.get("usage") or {}
    # modelUsage also lists the CLI's own side calls (a small Haiku call comes first since
    # 2026-10-01), so look the requested model up; the first key was logged as served_by before.
    by_model = out.get("modelUsage") or {}
    served = next((m for m in by_model if m.startswith(model)), next(iter(by_model), model))
    usage = {
        "input_tokens": u.get("input_tokens", 0),
        "output_tokens": u.get("output_tokens", 0),
        "cache_read_input_tokens": u.get("cache_read_input_tokens", 0),
        "cache_creation_input_tokens": u.get("cache_creation_input_tokens", 0),
        "served_by": served,
        "model_usage": by_model,  # per model, with costUSD: cost_usd below is the total of all of them
        "billing": "claude-code-subscription",
    }
    gen = Generation(text="", model=model, usage=usage, latency_s=latency,
                     cost_usd=round(out.get("total_cost_usd") or 0.0, 6))
    if out.get("stop_reason") == "refusal":
        gen.refusal = {"provider": "claude-code", "model": served, "category": None,
                       "explanation": str(out.get("result") or "")[:300]}
        return gen
    if out.get("is_error"):
        gen.error = f"PROVIDER_ERROR: {out.get('subtype')}: {str(out.get('result') or '')[:300]}"
        return gen
    gen.text = out.get("result") or ""
    return gen
