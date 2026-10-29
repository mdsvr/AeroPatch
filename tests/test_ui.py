"""`aeropatch ui` (doc 17 part 5 §1b; docs/17-ui-page-plan.html): link rules, refused requests, the
status strip, the folder dialog, a check end to end, fixing with live events, hand-off, model keys,
and apply and patch."""

import http.client
import json
import threading
import time
from pathlib import Path

import pytest

from aeropatch import check, config, doctor, providers, ui
from aeropatch import folder as fp
from aeropatch.models import openai_client


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(check, "CARDS_PATH", tmp_path / "no-cards.json")
    srv = ui.Server(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv
    srv.shutdown()
    srv.server_close()


def request(srv, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=30)
    h = {"X-Token": srv.token, **(headers or {})}
    conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
    r = conn.getresponse()
    return r.status, r.read().decode()


@pytest.mark.parametrize("url", ["ext::sh -c x", "-uX", "file:///c", "http://github.com/a/b", "git@github.com:a/b",
                                 "https://user@github.com/a/b", "https://github.com/a/b?x=1", "https://github.com"])
def test_rejected_links(url):
    assert not ui.git_url_ok(url)


def test_accepted_links():
    assert ui.git_url_ok("https://github.com/mdsvr/AeroPatch")
    assert ui.git_url_ok("https://gitlab.com/group/sub/repo.git")


def test_refuses_without_token_foreign_origin_or_host(server):
    assert request(server, "GET", "/", headers={"X-Token": "wrong"})[0] == 403
    assert request(server, "POST", "/api/check", {"source": "."}, {"Origin": "https://evil.example"})[0] == 403
    assert request(server, "GET", "/", headers={"Host": f"evil.example:{server.server_port}"})[0] == 403
    assert request(server, "GET", "/")[0] == 200


def test_check_job_reaches_done_with_steps_and_cards(server, tmp_path):
    folder = tmp_path / "app"
    folder.mkdir()
    (folder / "app.py").write_text("import subprocess\n\ndef run(cmd):\n    subprocess.call(cmd, shell=True)\n")
    status, body = request(server, "POST", "/api/check", {"source": str(folder), "lookup": False})
    assert status == 200
    job_id = json.loads(body)["id"]
    for _ in range(240):
        job = json.loads(request(server, "GET", f"/api/job/{job_id}")[1])
        if job["status"] != "running":
            break
        time.sleep(0.5)
    texts = [e["text"] for e in job["events"]]
    assert job["status"] == "done", texts
    assert {"code", "files", "scan", "sort", "report"} <= {e["step"] for e in job["events"]}
    assert "lookup" not in {e["step"] for e in job["events"]}  # the box was unticked: no network
    assert any(c["path"] == "app.py" for c in job["result"]["cards"])
    status, report = request(server, "GET", f"/api/report/{job_id}")
    assert status == 200 and "<html" in report


def test_second_check_while_one_runs_is_refused(server, monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(ui.Job, "run", lambda self: gate.wait(10))
    assert request(server, "POST", "/api/check", {"source": "."})[0] == 200
    assert request(server, "POST", "/api/check", {"source": "."})[0] == 409
    gate.set()


def test_bad_source_fails_in_words(tmp_path):
    job = ui.Job(str(tmp_path / "missing"), lookup=False)
    job.run()
    assert job.status == "failed" and "There is no folder" in job.events[-1]["text"]
    job = ui.Job("git@github.com:a/b", lookup=False)
    job.run(cloner=lambda url: pytest.fail("must not clone"))
    assert job.status == "failed" and "https" in job.events[-1]["text"]


def test_secret_card_carries_no_code(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path / "runs")
    folder = tmp_path / "app"
    folder.mkdir()
    (folder / "settings.py").write_text('password = "Zq8vR2xpL9wTk4"\n')
    data = check.page_data(check.check_folder(folder, offline=True))
    assert "Zq8vR2xpL9wTk4" not in json.dumps(data)


def test_status_strip(server, monkeypatch):
    checks = [doctor.Check("Opengrep", "warning", False, "not found.", "Put opengrep.exe in .tools."),
              doctor.Check("Ollama answering", "blocking", True, "version 0.40.10", gates=("Suggest",)),
              doctor.Check("Model downloaded", "blocking", True, "qwen3.5:4b is downloaded", gates=("Suggest",)),
              doctor.Check("GPU", "warning", False, "no NVIDIA GPU found.", "Nothing to fix."),
              doctor.Check("Docker running", "blocking", False, "Docker Desktop is installed but not running.",
                           "Open Docker Desktop.", gates=("Test",))]
    monkeypatch.setattr(doctor, "run_checks", lambda: checks)
    d = json.loads(request(server, "GET", "/api/doctor")[1])
    assert [lv["state"] for lv in d["levels"]] == ["warn", "ok", "bad"]
    assert d["levels"][2]["fix"] == "Open Docker Desktop."
    assert [w["area"] for w in d["warnings"]] == ["GPU"]


def test_folder_dialog(server, monkeypatch):
    monkeypatch.setattr(ui, "choose_folder", lambda: r"F:\projects\app")
    assert json.loads(request(server, "POST", "/api/choose-folder", {})[1]) == {"folder": r"F:\projects\app"}

    def broken():
        raise ImportError("no tkinter")
    monkeypatch.setattr(ui, "choose_folder", broken)
    status, body = request(server, "POST", "/api/choose-folder", {})
    assert status == 501 and "Paste the path" in json.loads(body)["error"]


# --------------------------------------------------------------------------- fix, hand-off, models, apply


def checked_folder(server, folder):
    """A finished check of `folder`, as the page would have run it first."""
    job = ui.Job(str(folder), lookup=False)
    job.status, job.folder = "done", str(folder.resolve())
    server.jobs[job.id] = job
    return job.folder


def wait_done(server, job_id):
    for _ in range(240):
        job = json.loads(request(server, "GET", f"/api/job/{job_id}")[1])
        if job["status"] != "running":
            return job
        time.sleep(0.25)
    raise AssertionError("job did not finish")


def fake_fix(calls):
    def fix(folder, n, on_event=None, think=False, route=None, history=None, **_):
        calls.append({"n": n, "think": think, "route": route, "history": history})
        for kind, data in [("prepare", {"state": "done", "text": "Sandbox ready."}),
                           ("try", {"route": "local", "model": "qwen3.5:4b", "prompt": "SYSTEM\n\nFinding: ..."}),
                           ("token", {"text": "RATIONALE: x"}), ("answer", {"text": "RATIONALE: x", "rationale": "x"}),
                           ("gates", {"ok": True, "violations": [], "details": []}), ("diff", {"diff": "-a\n+b"}),
                           ("sandbox", {"state": "start"}), ("test", {"outcome": "passed", "name": "tests/t.py::a"}),
                           ("sandbox", {"state": "done", "total": 1, "failures": []}), ("rescan", {"still": True}),
                           ("result", {"user_label": "Not fixed, warning kept", "offered": False}),
                           ("end", {"user_label": "Not fixed, warning kept", "diff": "",
                                    "messages": [{"role": "user", "content": "first"}]})]:
            on_event(kind, data)
        return {"label": "Not fixed, warning kept", "diff": "", "level": "test", "model": "qwen3.5:4b", "notes": []}
    return fix


def test_fix_streams_every_step_and_keeps_the_conversation_for_a_handoff(server, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(fp, "fix", fake_fix(calls))
    folder = checked_folder(server, tmp_path)
    status, body = request(server, "POST", "/api/fix", {"folder": folder, "numbers": [1], "think": True})
    assert status == 200
    job = wait_done(server, json.loads(body)["id"])
    kinds = [e["kind"] for e in job["events"]]
    assert kinds[0] == "problem" and kinds[-1] == "problem" and "test" in kinds and "gates" in kinds
    assert all("messages" not in e for e in job["events"])  # the conversation stays on the server
    assert calls[0]["think"] is True and server.histories[(folder, 1)] == [{"role": "user", "content": "first"}]

    pv = json.loads(request(server, "GET", f"/api/handoff?folder={folder}&n=1&provider=any&model=")[1])
    assert pv["text"].endswith("first") and not pv["blocked"] and pv["leaves"]

    status, body = request(server, "POST", "/api/handoff", {"folder": folder, "n": 1, "provider": "any",
                                                            "pasted": "RATIONALE: y"})
    assert status == 200
    wait_done(server, json.loads(body)["id"])
    assert calls[1]["route"] == {"attempt_plan": ["pasted"], "pasted_text": "RATIONALE: y"}
    assert calls[1]["history"] == [{"role": "user", "content": "first"}]


def test_state_lets_a_reloaded_page_draw_itself_again(server, tmp_path, monkeypatch):
    assert json.loads(request(server, "GET", "/api/state")[1]) == {}
    monkeypatch.setattr(fp, "fix", fake_fix([]))
    folder = checked_folder(server, tmp_path)
    wait_done(server, json.loads(request(server, "POST", "/api/fix", {"folder": folder, "numbers": [1]})[1])["id"])
    state = json.loads(request(server, "GET", "/api/state")[1])
    assert state["check"]["status"] == "done" and len(state["fixes"]) == 1
    assert state["fixes"][0]["events"][-1]["state"] == "done"


def test_fix_and_handoff_refuse_what_was_not_checked(server, tmp_path):
    assert request(server, "POST", "/api/fix", {"folder": str(tmp_path), "numbers": [1]})[0] == 400
    folder = checked_folder(server, tmp_path)
    assert request(server, "POST", "/api/fix", {"folder": folder, "numbers": []})[0] == 400
    assert request(server, "POST", "/api/handoff", {"folder": folder, "n": 1, "provider": "any",
                                                    "pasted": "x"})[0] == 400


def test_handoff_preview_flags_a_secret(server, tmp_path):
    folder = checked_folder(server, tmp_path)
    server.histories[(folder, 1)] = [{"role": "user", "content": 'api_key = "sk-ant-' + "a1B2c3D4" * 4 + '"'}]
    pv = json.loads(request(server, "GET", f"/api/handoff?folder={folder}&n=1&provider=claude-code"
                                           "&model=claude-opus-5-5")[1])
    assert pv["blocked"].startswith("Blocked") and "plan" in pv["cost"]


def test_pasted_answer_runs_the_real_loop_gates_and_rescan(tmp_path, monkeypatch):
    """No model and no Docker: an answer pasted from another tool goes through the same edit
    parser, 8 gates and re-scan as any try, at the Suggest level."""
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(check, "CARDS_PATH", tmp_path / "no-cards.json")
    monkeypatch.setattr(fp, "sandbox_available", lambda: False)
    folder = tmp_path / "app"
    folder.mkdir()
    (folder / "app.py").write_text("import subprocess\n\n\ndef run(cmd):\n    subprocess.call(cmd, shell=True)\n")
    events = []
    answer = ("RATIONALE: run it without a shell.\n<<<<<<< SEARCH app.py\n    subprocess.call(cmd, shell=True)\n"
              "=======\n    subprocess.call(cmd.split())\n>>>>>>> REPLACE")
    rec = fp.fix(folder, 1, route={"attempt_plan": ["pasted"], "pasted_text": answer},
                 on_event=lambda kind, data: events.append((kind, data)))
    kinds = [k for k, _ in events]
    assert kinds[:2] == ["prepare", "prepare"] and "gates" in kinds and kinds[-1] == "end"
    assert dict(events)["gates"]["ok"] and dict(events)["sandbox"]["state"] == "skipped"
    assert rec["level"] == "suggest" and rec["model"] == "pasted answer"
    assert rec["label"] == "Scanner quiet, not tested" and "cmd.split()" in rec["diff"]
    assert (folder / "app.py").read_text().count("shell=True") == 1  # the folder is untouched


def test_keys_go_to_env_and_never_back_to_the_page(server, tmp_path, monkeypatch):
    monkeypatch.setattr(providers, "ENV_FILE", tmp_path / ".env")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    (tmp_path / ".env").write_text("OLLAMA_HOST=http://localhost:11434\n")
    key = "gsk_" + "Abc123" * 6
    status, body = request(server, "POST", "/api/models/key", {"provider": "groq", "key": key})
    assert status == 200 and json.loads(body) == {"key_end": key[-4:]}
    assert (tmp_path / ".env").read_text().splitlines() == ["OLLAMA_HOST=http://localhost:11434", f"GROQ_API_KEY={key}"]
    monkeypatch.setattr(providers, "list_models", lambda pid: [])  # no local servers contacted here
    assert key not in request(server, "GET", "/api/models")[1]
    assert request(server, "POST", "/api/models/key", {"provider": "groq", "key": "has space in it"})[0] == 400
    request(server, "POST", "/api/models/forget", {"provider": "groq"})
    assert "GROQ_API_KEY" not in (tmp_path / ".env").read_text()


def test_ollama_cloud_models_are_not_listed_as_local(monkeypatch):
    class Resp:
        status_code = 200

        def json(self):
            return {"models": [{"name": "qwen3.5:4b"}, {"name": "kimi-k2.6:cloud"}, {"name": "gpt-oss:120b-cloud"}]}

    monkeypatch.setattr(providers.httpx, "get", lambda url, timeout: Resp())
    assert providers.list_models("ollama") == ["qwen3.5:4b"]


def test_handoff_refuses_an_ollama_cloud_model(server, tmp_path, monkeypatch):
    folder = checked_folder(server, tmp_path)
    server.histories[(folder, 1)] = [{"role": "user", "content": "first"}]
    monkeypatch.setattr(providers, "list_models", lambda pid: ["qwen3.5:4b"])
    status, body = request(server, "POST", "/api/handoff", {"folder": folder, "n": 1, "provider": "ollama",
                                                            "model": "kimi-k2.6:cloud"})
    assert status == 400 and "this computer" in json.loads(body)["error"]


def test_custom_server_address_rules():
    assert providers.base_ok("https://llm.example.com/v1") and providers.base_ok("http://localhost:9000/v1")
    assert not providers.base_ok("http://llm.example.com/v1") and not providers.base_ok("https://u:p@x.com")
    assert not providers.base_ok("file:///etc/passwd")


def test_openai_compatible_request_shape(monkeypatch):
    seen = {}

    class Resp:
        status_code, text = 200, ""

        def json(self):
            return {"choices": [{"message": {"content": "RATIONALE: ok"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 3}}

    def post(url, json, headers, timeout):
        seen.update(url=url, body=json, headers=headers)
        return Resp()

    monkeypatch.setattr(openai_client.httpx, "post", post)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123456789")
    cfg = config.load_config("handoff-test", **providers.route_cfg("openai", "gpt-x"))
    gen = openai_client.generate([{"role": "user", "content": "u"}], "sys", cfg, 0.4)
    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["headers"] == {"Authorization": "Bearer sk-test-123456789"}
    assert "temperature" not in seen["body"] and seen["body"]["max_completion_tokens"] == 4096
    assert gen.text == "RATIONALE: ok" and gen.usage["output_tokens"] == 3
    cfg = config.load_config("handoff-test", **providers.route_cfg("groq", "llama-x"))
    openai_client.generate([{"role": "user", "content": "u"}], "sys", cfg, 0.4)
    assert seen["body"]["temperature"] == 0.4 and "max_tokens" in seen["body"]


def test_live_tests_report_only_the_first_suite():
    """The sandbox watcher reports each finished test once, skips the time before any test ends,
    and stops when a hidden PoC suite rewrites the outcomes file."""
    from types import SimpleNamespace

    import requests

    from aeropatch.sandbox import sandbox

    outputs = [(1, b"cat: /tmp/outcomes.txt: No such file"), (0, b"passed\ta\n"), (0, b"passed\ta\nfailed\tb\n"),
               (0, b"passed\tpoc_1\n"), (0, b"passed\tpoc_1\npassed\tpoc_2\n")]

    class Container:
        waits = 0

        def wait(self, timeout):
            self.waits += 1
            if self.waits <= len(outputs):
                raise requests.exceptions.ReadTimeout()
            return {"StatusCode": 0}

        def exec_run(self, cmd, user):
            code, out = outputs[self.waits - 1]
            return SimpleNamespace(exit_code=code, output=out)

    seen = []
    assert sandbox._wait_watching(Container(), 60, lambda outcome, name: seen.append((outcome, name))) == 0
    assert seen == [("passed", "a"), ("failed", "b")]


def test_apply_and_patch(server, tmp_path, monkeypatch):
    folder = checked_folder(server, tmp_path)
    monkeypatch.setattr(fp, "apply", lambda f, n: tmp_path / "backup")
    assert json.loads(request(server, "POST", "/api/apply", {"folder": folder, "n": 1})[1]) == \
        {"backup": str(tmp_path / "backup")}
    rec = fp.run_dir(Path(folder)) / "fixes" / "1" / "fix.json"
    rec.parent.mkdir(parents=True)
    rec.write_text(json.dumps({"diff": "--- a\n+++ b\n"}))
    status, body = request(server, "GET", f"/api/patch?folder={folder}&n=1")
    assert status == 200 and body.startswith("--- a")
    clone = ui.clones_dir() / "repo-1"
    clone.mkdir(parents=True)
    cfolder = checked_folder(server, clone)
    assert request(server, "POST", "/api/apply", {"folder": cfolder, "n": 1})[0] == 400
