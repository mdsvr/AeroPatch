"""Refusal handling and usage capture in the Claude client, with a mocked SDK (no API calls)."""

from types import SimpleNamespace

from aeropatch.config import load_config
from aeropatch.models import fallback_client


class FakeStream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.msg


def fake_client(msg, seen):
    def stream(**kw):
        seen.update(kw)
        return FakeStream(msg)

    beta = SimpleNamespace(messages=SimpleNamespace(stream=stream))
    return SimpleNamespace(beta=beta, messages=SimpleNamespace(stream=stream))


def usage(**kw):
    base = {"input_tokens": 1000, "output_tokens": 200, "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0}
    return SimpleNamespace(**{**base, **kw})


def test_refusal_is_reported_not_raised():
    msg = SimpleNamespace(stop_reason="refusal", model="claude-opus-5", content=[], usage=usage(),
                          stop_details=SimpleNamespace(category="cyber", explanation="declined"))
    seen = {}
    gen = fallback_client.generate([{"role": "user", "content": "x"}], "sys", load_config("baseline-frontier"),
                                   0.2, client=fake_client(msg, seen))
    assert gen.refusal == {"provider": "anthropic", "model": "claude-opus-5", "category": "cyber",
                           "explanation": "declined"}
    assert gen.text == ""
    assert seen["betas"] == [fallback_client.FALLBACK_BETA]
    assert seen["extra_body"] == {"fallbacks": "default"}
    assert seen["thinking"] == {"type": "adaptive"} and seen["output_config"] == {"effort": "medium"}
    assert "temperature" not in seen and "budget_tokens" not in str(seen)
    assert seen["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_text_usage_and_cost():
    msg = SimpleNamespace(stop_reason="end_turn", model="claude-opus-5", stop_details=None,
                          content=[SimpleNamespace(type="thinking", thinking=""),
                                   SimpleNamespace(type="text", text="RATIONALE: x")],
                          usage=usage(cache_read_input_tokens=500))
    gen = fallback_client.generate([], "sys", load_config("baseline-frontier"), 0.2, client=fake_client(msg, {}))
    assert gen.text == "RATIONALE: x"
    assert gen.usage["cache_read_input_tokens"] == 500
    # 1000*5 + 500*0.5 + 200*25 per 1M tokens
    assert abs(gen.cost_usd - (5000 + 250 + 5000) / 1e6) < 1e-9
