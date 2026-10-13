import httpx
import pytest

from aeropatch import scenario
from aeropatch.agent import prompts
from aeropatch.config import load_config
from aeropatch.models import local_client
from aeropatch.models.base import LocalServerDown
from aeropatch.tools.context import get_context


class Resp:
    status_code = 200
    text = ""

    def json(self):
        return {"message": {"content": "RATIONALE: x"}, "prompt_eval_count": 900, "eval_count": 120,
                "eval_duration": 4_000_000_000}


def test_request_shape_and_usage(monkeypatch):
    seen = {}

    def post(url, json, timeout):
        seen.update(url=url, body=json)
        return Resp()

    monkeypatch.setattr(httpx, "post", post)
    gen = local_client.generate([{"role": "user", "content": "u"}], "sys", load_config(), 0.2)
    assert seen["url"].endswith("/api/chat")
    assert seen["body"]["think"] is False and seen["body"]["stream"] is False
    assert seen["body"]["messages"][0] == {"role": "system", "content": "sys"}
    assert seen["body"]["options"]["num_predict"] == 1024 and seen["body"]["options"]["temperature"] == 0.2
    assert gen.text == "RATIONALE: x"
    assert gen.usage == {"input_tokens": 900, "output_tokens": 120, "decode_tok_s": 30.0}


def test_prefill_is_sent_as_the_answer_start_and_kept_in_the_text(monkeypatch):
    seen = {}
    monkeypatch.setattr(httpx, "post", lambda url, json, timeout: seen.update(body=json) or Resp())
    user = {"role": "user", "content": "Finding: CWE-79 at a.py:1.\n\nMessage: Unescaped HTML.\n\ncode"}
    gen = local_client.generate([user], "sys", load_config("prefill-finding"), 0.2)
    start = "RATIONALE: Unescaped HTML.\n<<<<<<< SEARCH"
    assert seen["body"]["messages"][-1] == {"role": "assistant", "content": start}
    assert gen.text == start + "RATIONALE: x"


def test_plan_prefill_has_a_line_for_every_dev_scenario(monkeypatch):
    seen = {}
    monkeypatch.setattr(httpx, "post", lambda url, json, timeout: seen.update(body=json) or Resp())
    cfg = load_config("prefill-control-plan")
    for sid in scenario.list_ids("dev"):
        task = scenario.load(sid)
        ctx = get_context(task.repo_path, task.finding.path, task.finding.line, task.allowed_paths)
        user = prompts.first_user_message(task, ctx)
        local_client.generate([{"role": "user", "content": user}], "sys", cfg, 0.2)
        start = seen["body"]["messages"][-1]["content"]
        assert start.startswith("RATIONALE: ") and start.endswith("\n<<<<<<< SEARCH") and "{" not in start


def test_server_down_fails_fast(monkeypatch):
    def post(*a, **k):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(LocalServerDown):
        local_client.generate([], "sys", load_config(), 0.2)
