"""Single source of truth for defaults (doc 08 part 2, §8; doc 04, §9).

Every run copies the resolved config into its JSONL header. Changing any value means a new
config name: results are only compared within a config.
"""

from __future__ import annotations

import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = ROOT / "evaluations" / "scenarios"
RULES_DIR = ROOT / "rules"
RUNS_DIR = ROOT / "runs"
DOCKER_DIR = ROOT / "docker"

BASE_IMAGE = "aeropatch-sandbox-base:latest"

FORBIDDEN_GLOBS = [
    "tests/**", "test_*.py", "*_test.py", "conftest.py", ".github/**", ".gitlab-ci.yml",
    "Dockerfile*", "docker-compose*", "pyproject.toml", "setup.py", "setup.cfg",
    "requirements*.txt", "*.lock", ".env*",
]
# Matched on dotted prefixes: "urllib.request" is risky, "urllib.parse" is not.
RISKY_MODULES = ["subprocess", "socket", "requests", "urllib.request", "urllib3", "http.client", "ctypes",
                 "pickle", "marshal", "httpx"]
RISKY_CALLS = ["os.system", "os.popen", "eval", "exec", "__import__"]

DEFAULTS: dict = {
    "mode": "local",
    "attempt_plan": ["local"],
    "local_model": "qwen3.5:4b",
    "local_host": "http://localhost:11434",
    "local_num_ctx": 8192,
    "local_think": False,
    "frontier_model": "claude-opus-5",
    "frontier_effort": "medium",
    "server_side_fallbacks": True,
    "max_tokens_local": 1024,
    "max_tokens_frontier": 4096,
    "temperature_first": 0.2,
    "temperature_repair": 0.4,
    "max_usd_per_scenario": 0.50,
    "local_ctx_budget": 6000,
    "max_changed_lines": 60,
    "max_files": 3,
    "feedback_token_cap": 1500,
    "sandbox_timeout_s": 300,
    "sandbox_memory": "2g",
    "sandbox_cpus": 2.0,
    "sandbox_pids": 256,
    "scenario_wallclock_s": 600,
    "localization": "oracle",
    "forbidden_globs": FORBIDDEN_GLOBS,
    "risky_modules": RISKY_MODULES,
    "risky_calls": RISKY_CALLS,
}

# Named configs. The Week 1 baseline is single-attempt with oracle localization (doc 14, D6).
CONFIGS: dict[str, dict] = {
    "baseline-qwen3.5-4b": {"attempt_plan": ["local"], "local_model": "qwen3.5:4b"},
    "baseline-qwen2.5-coder-3b": {
        "attempt_plan": ["local"], "local_model": "qwen2.5-coder:3b-instruct-q4_K_M",
    },
    "baseline-frontier": {"mode": "frontier", "attempt_plan": ["frontier"]},
    # Harness self-check: replays each scenario's reference fix. Must resolve 100%.
    "oracle": {"mode": "oracle", "attempt_plan": ["oracle"]},
    "repair-local": {"attempt_plan": ["local", "local", "local"]},
    "cascade": {"mode": "cascade", "attempt_plan": ["local", "local", "frontier"]},
}

# USD per 1M tokens (doc 04 §2; Anthropic table cached 2026-06-24). Re-check before publishing.
PRICES = {
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-fable-5-1": (10.00, 50.00),
}


def load_config(name: str = "baseline-qwen3.5-4b", **overrides) -> dict:
    if name not in CONFIGS:
        raise KeyError(f"unknown config {name!r}; known: {sorted(CONFIGS)}")
    cfg = copy.deepcopy(DEFAULTS)
    cfg.update(copy.deepcopy(CONFIGS[name]))
    cfg.update({k: v for k, v in overrides.items() if v is not None})
    cfg["name"] = name
    return cfg
