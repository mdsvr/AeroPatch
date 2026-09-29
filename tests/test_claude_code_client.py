"""Headless Claude Code client with a mocked subprocess (no CLI calls)."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from aeropatch.config import load_config
from aeropatch.models import claude_code_client as cc


@pytest.fixture(autouse=True)
def fake_cli(monkeypatch):
    monkeypatch.setattr(cc.shutil, "which", lambda name: "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")


def runner(payload: dict, seen: dict):
    def run(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        seen["system"] = open(cmd[cmd.index("--system-prompt-file") + 1], encoding="utf-8").read()
        return SimpleNamespace(stdout=json.dumps(payload), stderr="", returncode=0)
    return run


def ok(**kw):
    return {"is_error": False, "stop_reason": "end_turn", "subtype": "success", "result": "RATIONALE: x",
            "total_cost_usd": 0.0421, "usage": {"input_tokens": 3000, "output_tokens": 900},
            "modelUsage": {"claude-opus-5": {}}, **kw}


def test_success_is_tool_less_and_subscription_billed():
    seen = {}
    gen = cc.generate([{"role": "user", "content": "fix it"}], "SYSTEM", load_config("baseline-claude-code"),
                      0.2, run=runner(ok(), seen))
    assert gen.text == "RATIONALE: x" and not gen.error and gen.refusal is None
    assert gen.cost_usd == 0.0421 and gen.usage["input_tokens"] == 3000 and gen.usage["served_by"] == "claude-opus-5"
    cmd = seen["cmd"]
    assert cmd[cmd.index("--tools") + 1] == "" and cmd[cmd.index("--model") + 1] == "claude-opus-5"
    assert seen["system"] == "SYSTEM" and seen["input"] == "fix it"
    assert "ANTHROPIC_API_KEY" not in seen["env"]  # never bill an API key by accident


def test_refusal_is_reported_not_raised():
    gen = cc.generate([{"role": "user", "content": "x"}], "S", load_config("baseline-claude-code"), 0.2,
                      run=runner(ok(stop_reason="refusal", result="declined"), {}))
    assert gen.refusal["provider"] == "claude-code" and gen.text == ""


def test_cli_error_and_timeout_become_provider_errors():
    cfg = load_config("baseline-claude-code")
    gen = cc.generate([{"role": "user", "content": "x"}], "S", cfg, 0.2,
                      run=runner(ok(is_error=True, subtype="error_during_execution", result="boom"), {}))
    assert gen.error.startswith("PROVIDER_ERROR: error_during_execution")

    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 1)
    assert "timed out" in cc.generate([{"role": "user", "content": "x"}], "S", cfg, 0.2, run=slow).error


def test_repair_history_is_flattened_in_order():
    seen = {}
    msgs = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}, {"role": "user", "content": "c"}]
    cc.generate(msgs, "S", load_config("baseline-claude-code"), 0.2, run=runner(ok(), seen))
    assert seen["input"].index("[user]\na") < seen["input"].index("[assistant]\nb") < seen["input"].index("[user]\nc")
