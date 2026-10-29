"""Model providers for the `ui` page's Models section and hand-off (docs/17-ui-page-plan.html, part 3).

Almost every provider, hosted or local, now serves the OpenAI-compatible chat API, so one client
(models/openai_client.py) and the table below cover them. Ollama, Claude Code and Anthropic's own
API keep their existing clients.

Keys live in AeroPatch's .env (git-ignored), are sent only to their own provider's address, and
never go back to the page: it sees the last 4 characters.
"""

from __future__ import annotations

import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import httpx

from aeropatch import config

ENV_FILE = config.ROOT / ".env"
TIMEOUT_S = 4
CUSTOM_BASE = "AEROPATCH_CUSTOM_BASE_URL"
CLAUDE_MODELS = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-fable-5-1"]

# kind: local (free, on this laptop) | subscription | paid (per token, needs a key) | custom
PROVIDERS: dict[str, dict] = {
    "ollama": {"name": "Ollama", "kind": "local", "api": "ollama", "base": "http://localhost:11434",
               "note": "The default for every first try. Any model you have pulled; Ollama's cloud models are "
                       "left out, since they run on Ollama's servers."},
    "claude-code": {"name": "Claude Code", "kind": "subscription", "api": "claude-code",
                    "note": "Your Claude subscription through the claude CLI. No API key, no per-token charge."},
    "anthropic": {"name": "Anthropic API", "kind": "paid", "api": "anthropic", "base": "https://api.anthropic.com/v1",
                  "key": "ANTHROPIC_API_KEY", "keys_url": "https://console.anthropic.com/settings/keys"},
    "openai": {"name": "OpenAI", "kind": "paid", "api": "openai", "base": "https://api.openai.com/v1",
               "key": "OPENAI_API_KEY", "keys_url": "https://platform.openai.com/api-keys", "reasoning_style": True},
    "gemini": {"name": "Google Gemini", "kind": "paid", "api": "openai",
               "base": "https://generativelanguage.googleapis.com/v1beta/openai",
               "key": "GEMINI_API_KEY", "keys_url": "https://aistudio.google.com/apikey", "note": "Has a free tier."},
    "mistral": {"name": "Mistral", "kind": "paid", "api": "openai", "base": "https://api.mistral.ai/v1",
                "key": "MISTRAL_API_KEY", "keys_url": "https://console.mistral.ai/api-keys"},
    "deepseek": {"name": "DeepSeek", "kind": "paid", "api": "openai", "base": "https://api.deepseek.com/v1",
                 "key": "DEEPSEEK_API_KEY", "keys_url": "https://platform.deepseek.com/api_keys"},
    "xai": {"name": "xAI", "kind": "paid", "api": "openai", "base": "https://api.x.ai/v1",
            "key": "XAI_API_KEY", "keys_url": "https://console.x.ai"},
    "groq": {"name": "Groq", "kind": "paid", "api": "openai", "base": "https://api.groq.com/openai/v1",
             "key": "GROQ_API_KEY", "keys_url": "https://console.groq.com/keys",
             "note": "Open models on fast hardware. Has a free tier."},
    "together": {"name": "Together AI", "kind": "paid", "api": "openai", "base": "https://api.together.xyz/v1",
                 "key": "TOGETHER_API_KEY", "keys_url": "https://api.together.ai/settings/api-keys",
                 "note": "Open models."},
    "openrouter": {"name": "OpenRouter", "kind": "paid", "api": "openai", "base": "https://openrouter.ai/api/v1",
                   "key": "OPENROUTER_API_KEY", "keys_url": "https://openrouter.ai/keys",
                   "note": "Hundreds of paid and open models behind one key; some are free."},
    "huggingface": {"name": "Hugging Face", "kind": "paid", "api": "openai", "base": "https://router.huggingface.co/v1",
                    "key": "HF_TOKEN", "keys_url": "https://huggingface.co/settings/tokens",
                    "note": "Open models from many hosts behind one token."},
    "lmstudio": {"name": "LM Studio", "kind": "local", "api": "openai", "base": "http://localhost:1234/v1"},
    "llamacpp": {"name": "llama.cpp server", "kind": "local", "api": "openai", "base": "http://localhost:8080/v1"},
    "vllm": {"name": "vLLM", "kind": "local", "api": "openai", "base": "http://localhost:8000/v1"},
    "jan": {"name": "Jan", "kind": "local", "api": "openai", "base": "http://localhost:1337/v1"},
    "custom": {"name": "Other OpenAI-compatible server", "kind": "custom", "api": "openai",
               "key": "AEROPATCH_CUSTOM_API_KEY", "note": "Any address that serves /chat/completions."},
}
_KEY_RE = re.compile(r"^[\x21-\x7e]{8,500}$")  # printable, no spaces or newlines: one .env line


def _read_env() -> dict[str, str]:
    out = {}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and not name.lstrip().startswith("#"):
                out[name.strip()] = value.strip().strip('"').strip("'")
    return out


def _write_env(name: str, value: str | None) -> None:
    """Set (or with None remove) one line of .env, keeping every other line as it was."""
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.is_file() else []
    lines = [ln for ln in lines if ln.partition("=")[0].strip() != name]
    if value is not None:
        lines.append(f"{name}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value  # the Anthropic SDK reads its key from the environment


def get_key(name: str) -> str:
    return os.environ.get(name) or _read_env().get(name, "")


def base_url(pid: str) -> str:
    p = PROVIDERS[pid]
    return (get_key(CUSTOM_BASE) if pid == "custom" else p.get("base", "")).rstrip("/")


def base_ok(url: str) -> bool:
    """A custom address must be https, or plain http on this computer."""
    u = urlparse(url)
    local = u.hostname in ("localhost", "127.0.0.1", "::1")
    return bool(u.hostname) and (u.scheme == "https" or (u.scheme == "http" and local)) and not u.username


def save_key(pid: str, key: str) -> str:
    p = PROVIDERS[pid]
    if "key" not in p:
        raise ValueError(f"{p['name']} needs no key")
    if not _KEY_RE.match(key):
        raise ValueError("That does not look like a key: 8 to 500 characters, no spaces")
    _write_env(p["key"], key)
    return key[-4:]


def forget_key(pid: str) -> None:
    _write_env(PROVIDERS[pid]["key"], None)


def save_custom_base(url: str) -> None:
    url = url.strip().rstrip("/")
    if not base_ok(url):
        raise ValueError("Use an https address, or http://localhost for a server on this computer")
    _write_env(CUSTOM_BASE, url)


def headers(pid: str) -> dict:
    p = PROVIDERS[pid]
    key = get_key(p["key"]) if "key" in p else ""
    if p["api"] == "anthropic":
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}
    return {"Authorization": f"Bearer {key}"} if key else {}


def list_models(pid: str) -> list[str]:
    """The provider's own model list; [] when it does not answer."""
    p = PROVIDERS[pid]
    if p["api"] == "claude-code":
        return CLAUDE_MODELS
    base = base_url(pid)
    if not base:
        return []
    try:
        if p["api"] == "ollama":
            r = httpx.get(f"{base}/api/tags", timeout=TIMEOUT_S)
            # Ollama's cloud models (name:cloud, name-cloud) run on ollama.com, so they are not
            # "on this computer" and are left out of the local list.
            return sorted(m["name"] for m in r.json().get("models", [])
                          if not re.search(r"[:-]cloud$", m["name"])) if r.status_code == 200 else []
        r = httpx.get(f"{base}/models", headers=headers(pid), timeout=TIMEOUT_S)
        if r.status_code != 200:
            return []
        return sorted(str(m.get("id", "")) for m in r.json().get("data", []) if m.get("id"))
    except (httpx.HTTPError, ValueError):
        return []


def status(pid: str) -> dict:
    """What the Models section shows for one provider. Hosted providers are not contacted here."""
    p = PROVIDERS[pid]
    out = {"id": pid, "name": p["name"], "kind": p["kind"], "note": p.get("note", ""),
           "keys_url": p.get("keys_url", ""), "needs_key": "key" in p, "base": base_url(pid)}
    key = get_key(p["key"]) if "key" in p else ""
    out["key_end"] = key[-4:] if key else ""
    if p["api"] == "claude-code":
        out["ready"], out["says"] = bool(shutil.which("claude")), (
            "claude CLI found" if shutil.which("claude") else "Claude Code is not installed")
    elif p["kind"] == "paid":
        out["ready"], out["says"] = bool(key), (f"key saved, ends in {key[-4:]}" if key else "no key yet")
    else:  # local or custom: is a server answering?
        if not out["base"]:
            out["ready"], out["says"] = False, "no address set"
        else:
            models = list_models(pid)
            out["ready"] = bool(models)
            out["models"] = models
            out["says"] = (f"answering, {len(models)} model{'s' if len(models) != 1 else ''}" if models
                           else "not answering at " + out["base"])
    return out


def all_status() -> list[dict]:
    with ThreadPoolExecutor(max_workers=8) as pool:  # local servers that are off each wait out a timeout
        return list(pool.map(status, PROVIDERS))


def route_cfg(pid: str, model: str) -> dict:
    """The config overrides that send one try to `model` at provider `pid`."""
    api = PROVIDERS[pid]["api"]
    if api == "ollama":
        return {"attempt_plan": ["local"], "local_model": model}
    if api == "claude-code":
        return {"attempt_plan": ["claude-code"], "frontier_model": model}
    if api == "anthropic":
        return {"attempt_plan": ["frontier"], "frontier_model": model}
    return {"attempt_plan": ["openai"], "api_provider": pid, "api_model": model}


def needs_preview_cost(pid: str) -> bool:
    return PROVIDERS[pid]["kind"] in ("paid", "subscription", "custom")
