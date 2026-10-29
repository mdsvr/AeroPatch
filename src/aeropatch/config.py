"""Single source of truth for defaults (doc 08 part 2, §8; doc 04, §9).

Every run copies the resolved config into its JSONL header. Changing any value means a new
config name: results are only compared within a config.
"""

from __future__ import annotations

import copy
import os
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
    # Layers offloaded to GPU. Ollama's own estimate put qwen3.5:4b 54% on CPU (9 tok/s);
    # all layers fit the 3050's 4 GB at 8k ctx (3.64 GB peak, 48 tok/s; measured 2026-09-28).
    "local_num_gpu": 99,
    "local_think": False,
    # Opus 5.5 since 2026-10-19 (Week 4's reference); Weeks 1 and 2 ran claude-opus-5, as their
    # run headers record.
    "frontier_model": "claude-opus-5-5",
    "frontier_effort": "medium",
    "server_side_fallbacks": True,
    "max_tokens_local": 1024,
    "max_tokens_frontier": 4096,
    "temperature_first": 0.2,
    "temperature_repair": 0.4,
    "stuck_retry_temperature": 0.8,
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
    # Doc 17 part 2 §2. The defaults are today's behaviour, so every earlier config keeps its meaning.
    # hidden_suites: suites still run (their results stay in the record) but are kept out of the
    # model's prompt and out of the stop rule. rescan_feedback: tell the model when the finding's
    # rule still fires. run_tests: False skips the sandbox (gates and re-scan only, nothing runs).
    "hidden_suites": [],
    "rescan_feedback": False,
    "run_tests": True,
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
    # Same model through headless Claude Code on a subscription instead of an API key.
    "baseline-claude-code": {"mode": "frontier", "attempt_plan": ["claude-code"]},
    # Harness self-check: replays each scenario's reference fix. Must resolve 100%.
    "oracle": {"mode": "oracle", "attempt_plan": ["oracle"]},
    "repair-local": {"attempt_plan": ["local", "local", "local"]},
    # D19 diagnosis of the fine-tune: `repair-local` with the start of the answer written for the
    # model. "plan" leaves the RATIONALE to the model. "finding" puts the finding's message there
    # and opens the first block, which is how every target of dataset v1 begins.
    "prefill-plan": {"attempt_plan": ["local", "local", "local"], "local_prefill": "RATIONALE:"},
    "prefill-finding": {"attempt_plan": ["local", "local", "local"],
                        "local_prefill": "RATIONALE: {message}\n<<<<<<< SEARCH"},
    # One attempt, opened with the RATIONALE the untuned control wrote for the same scenario:
    # does a tuned checkpoint write the blocks as well once it is handed that plan?
    "prefill-control-plan": {"attempt_plan": ["local"],
                             "local_prefill": "RATIONALE: {plan}\n<<<<<<< SEARCH",
                             "local_prefill_plans": "training/d19_control_plans.json"},
    # pass@k (doc 12 §2): one attempt, sampled hotter, run n times under separate run ids.
    "sample-local": {"attempt_plan": ["local"], "temperature_first": 0.7},
    # Thinking ablation (doc 11 §7): the thinking shares the token budget with the answer, so the
    # budget and the wall clock are raised; the client reads message.content, not the thinking.
    "repair-local-think": {"attempt_plan": ["local", "local", "local"], "local_think": True,
                           "max_tokens_local": 4096, "scenario_wallclock_s": 1800},
    # Quant ablation, Q8_0 (4.48 GB): 25 layers on the GPU peak at 3,771 MiB with a 4,508-token
    # prompt at 8k context, 26 reach 3,913 (2026-10-16). The rest runs on the CPU at about
    # 14.5 tok/s, so the wall clock is raised and speed is reported apart from accuracy.
    "repair-local-q8": {"attempt_plan": ["local", "local", "local"], "local_num_gpu": 25,
                        "scenario_wallclock_s": 1800},
    "repair-claude-code": {"mode": "frontier", "attempt_plan": ["claude-code", "claude-code", "claude-code"]},
    # ponytail: escalation is the fixed plan below. With 2 local entries it equals doc 04 §5
    # triggers 1-3; add triggers 4-5 (context over local_ctx_budget, multi-file tag) when a
    # scenario's context exceeds ~6k tokens. Today's largest is ~115.
    "cascade": {"mode": "cascade", "attempt_plan": ["local", "local", "frontier"]},
    "cascade-claude-code": {"mode": "cascade", "attempt_plan": ["local", "local", "claude-code"]},
    # Label measurement (doc 17 part 2 §1): V1 is a user with good tests (the PoC is hidden), V2 a
    # user with none (both suites hidden). Each attempt still records the hidden suites as truth.
    "repair-local-v1": {"attempt_plan": ["local", "local", "local"], "hidden_suites": ["poc"],
                        "rescan_feedback": True},
    "repair-local-v2": {"attempt_plan": ["local", "local", "local"], "hidden_suites": ["poc", "regression"],
                        "rescan_feedback": True},
    # Phase D2 (reports/Real bug detection and model mix.md): V1 plus an abstract fix pattern in the
    # first message for CWE-22, 328 and 918 (prompts.FIX_RECIPES). Compared with repair-local-v1 on test.
    "repair-local-v1-recipes": {"attempt_plan": ["local", "local", "local"], "hidden_suites": ["poc"],
                                "rescan_feedback": True, "fix_recipes": True},
    # Doc 17 part 4 §1: the product config of `fix` at the Test level. It is V1's loop, so V1's
    # label precision is what users get; the folder path is checked against V1 on the benchmark.
    "fix-local": {"attempt_plan": ["local", "local", "local"], "hidden_suites": ["poc"], "rescan_feedback": True},
    # The Suggest level: V2's loop with no sandbox, so a user without Docker gets V2's numbers.
    "suggest-local": {"attempt_plan": ["local", "local", "local"], "hidden_suites": ["poc", "regression"],
                      "rescan_feedback": True, "run_tests": False},
    # The `ui` page (docs/17-ui-page-plan.html). "Show thinking": the same loops with the model's
    # thinking on, and repair-local-think's budget, since the thinking shares it with the answer.
    # Their label hit rates were not measured (thinking on fixed 41 vs 38 of 54 on test).
    "fix-local-think": {"attempt_plan": ["local", "local", "local"], "hidden_suites": ["poc"],
                        "rescan_feedback": True, "local_think": True, "max_tokens_local": 4096,
                        "scenario_wallclock_s": 1800},
    "suggest-local-think": {"attempt_plan": ["local", "local", "local"], "hidden_suites": ["poc", "regression"],
                            "rescan_feedback": True, "run_tests": False, "local_think": True,
                            "max_tokens_local": 4096, "scenario_wallclock_s": 1800},
    # A hand-off after the local model gave up: one try by the model the user picks (the page sets
    # attempt_plan and the model), continuing the local tries' conversation.
    "handoff-test": {"mode": "frontier", "attempt_plan": ["claude-code"], "hidden_suites": ["poc"],
                     "rescan_feedback": True},
    "handoff-suggest": {"mode": "frontier", "attempt_plan": ["claude-code"], "hidden_suites": ["poc", "regression"],
                        "rescan_feedback": True, "run_tests": False},
}

# USD per 1M tokens: input, output, cache read (doc 04 §2; platform.claude.com pricing page,
# checked 2026-10-19). Cache reads are 0.1x input except Opus 5.5 (0.05x) and Fable 5.1 (0.025x).
PRICES = {
    "claude-opus-5": (5.00, 25.00, 0.50),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5": (2.00, 10.00, 0.20),
    "claude-haiku-4-5": (1.00, 5.00, 0.10),
    "claude-fable-5-1": (10.00, 50.00, 0.25),
}


def load_config(name: str = "baseline-qwen3.5-4b", **overrides) -> dict:
    if name not in CONFIGS:
        raise KeyError(f"unknown config {name!r}; known: {sorted(CONFIGS)}")
    cfg = copy.deepcopy(DEFAULTS)
    cfg.update(copy.deepcopy(CONFIGS[name]))
    if os.environ.get("OLLAMA_HOST") and "local_host" not in overrides:
        cfg["local_host"] = os.environ["OLLAMA_HOST"]
    cfg.update({k: v for k, v in overrides.items() if v is not None})
    cfg["name"] = name
    return cfg
