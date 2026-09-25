import httpx
import pytest

from aeropatch.config import load_config
from aeropatch.models import local_client
from aeropatch.models.base import LocalServerDown


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


def test_server_down_fails_fast(monkeypatch):
    def post(*a, **k):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(LocalServerDown):
        local_client.generate([], "sys", load_config(), 0.2)
