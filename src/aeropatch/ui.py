"""`aeropatch ui`: a local page to check a folder or a public git repo, fix the problems you tick
while watching each try live, hand a stuck one to another model, and apply or undo the result
(doc 17 part 5 §1b; the approved plan is docs/17-ui-page-plan.html).

Stdlib only. Bound to 127.0.0.1. Every request needs the per-launch token and a Host of
127.0.0.1:<port> or localhost:<port>, and a request carrying any other Origin is refused, so a web
page the user visits cannot drive it (CSRF, DNS rebinding). One job runs at a time.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from aeropatch import check, config, labels, providers

PAGE = Path(__file__).with_name("ui.html")
# https only, no user@, query or fragment: rules out ext::, file://, ssh and option-like "-u..." input.
GIT_URL = re.compile(r"^https://[A-Za-z0-9.-]+(:\d{1,5})?(/[A-Za-z0-9._~-]+)+/?$")
MODEL_RE = re.compile(r"^[\w.:/@+-]{1,200}$")
CLONE_TIMEOUT_S = 300
# What the status strip says for a ready level: the check that decides it.
LEVEL_AREA = {"Check": "Opengrep", "Suggest": "Model downloaded", "Test": "Docker running"}
# How often each label was right on AeroPatch's benchmark, local model, two runs pooled (README,
# "Without the exploit test", 2026-10-24). Shown as N of M, never as a percentage (doc 17 part 1).
PRECISION = {labels.QUIET_TESTS_PASS: "On AeroPatch's benchmark this label was right 25 of 34 times.",
             labels.QUIET_NOT_TESTED: "On AeroPatch's benchmark this label was right 23 of 43 times.",
             labels.TESTS_PASS_NO_RESCAN: "On AeroPatch's benchmark this label was right 8 of 14 times."}
_DIALOG_LOCK = threading.Lock()


def git_url_ok(text: str) -> bool:
    return bool(GIT_URL.match(text))


def clones_dir() -> Path:
    return config.RUNS_DIR / "ui-clones"


def _rmtree(path: Path) -> None:
    def writable(fn, p, _exc):  # git marks pack files read-only, which stops rmtree on Windows
        os.chmod(p, stat.S_IWRITE)
        fn(p)
    shutil.rmtree(path, onexc=writable)


def clone(url: str) -> Path:
    """A fresh shallow copy under runs/ui-clones/. Never prompts for a password: a private repo fails."""
    name = re.sub(r"\.git$", "", url.rstrip("/").rsplit("/", 1)[-1]) or "repo"
    dest = clones_dir() / f"{name}-{hashlib.sha256(url.encode()).hexdigest()[:8]}"
    if dest.exists():
        _rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["git", "-c", "protocol.ext.allow=never", "-c", "protocol.file.allow=never", "-c", "credential.helper=",
         "clone", "--depth", "1", "--", url, str(dest)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=CLONE_TIMEOUT_S, check=False,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"})
    if r.returncode != 0:
        last = (r.stderr.strip().splitlines() or ["no message"])[-1]
        raise RuntimeError(f"Could not download the repo. It may be private or the link may be wrong. Git said: {last}")
    return dest


def is_clone(folder: Path) -> bool:
    """A downloaded copy of a link: Apply makes no sense there, so the page offers a .patch instead."""
    return clones_dir().resolve() in Path(folder).resolve().parents


def choose_folder() -> str:
    """Windows' own folder dialog, in front of the browser. '' when the user cancels."""
    import tkinter
    from tkinter import filedialog

    with _DIALOG_LOCK:  # one dialog at a time; Tk lives and dies in this thread
        root = tkinter.Tk()
        try:
            root.withdraw()
            root.attributes("-topmost", True)
            chosen = filedialog.askdirectory(parent=root, mustexist=True,
                                             title="Choose a folder for AeroPatch to check")
        finally:
            root.destroy()
    return str(Path(chosen)) if chosen else ""


def doctor_data() -> dict:
    """The status strip: one entry per level (Check, Suggest, Test), plus the warnings."""
    from aeropatch import doctor

    checks = doctor.run_checks()
    ready = doctor.ready_levels(checks)
    by_area = {c.area: c for c in checks}
    levels = []
    for i, name in enumerate(doctor.LEVELS):
        missing = doctor._blocked(checks, name)
        if name in ready:
            c = by_area.get(LEVEL_AREA[name])
            levels.append({"name": name, "state": "warn" if c and not c.ok else "ok",
                           "says": c.message if c else "ready", "fix": c.fix if c and not c.ok else ""})
        elif missing:
            levels.append({"name": name, "state": "bad", "says": missing[0].message, "fix": missing[0].fix})
        else:
            levels.append({"name": name, "state": "bad", "says": f"Needs {doctor.LEVELS[i - 1]} first.", "fix": ""})
    warnings = [{"area": c.area, "says": c.message, "fix": c.fix} for c in checks
                if c.level == "warning" and not c.ok and c.area not in LEVEL_AREA.values()]
    return {"levels": levels, "warnings": warnings}


def handoff_preview(history: list[dict], pid: str, model: str) -> dict:
    """Exactly what a hand-off sends (the instructions and every earlier try), whether the secrets
    check lets it go, and what it may cost."""
    from aeropatch.agent import prompts
    from aeropatch.models import claude_code_client

    text = prompts.SYSTEM_PROMPT + "\n\n" + claude_code_client._prompt(history)
    tokens = len(text) // 4
    blocked = prompts._secret_reason(text)
    p = providers.PROVIDERS.get(pid, {})
    cost = ""
    if model in config.PRICES:
        inp, out, _ = config.PRICES[model]
        most = config.DEFAULTS["max_tokens_frontier"]
        cost = (f"About ${tokens * inp / 1e6:.3f} to send, and at most ${most * out / 1e6:.3f} more for the answer "
                f"at API prices.")
        if pid == "claude-code":
            cost += " Through Claude Code it counts against your plan instead."
    elif p.get("kind") == "paid":
        cost = f"Priced by {p['name']}: see their pricing page. One request, at most " \
               f"{config.DEFAULTS['max_tokens_frontier']} tokens of answer."
    elif p.get("kind") == "local":
        cost = "Free: it runs on this computer."
    return {"text": text, "chars": len(text), "tokens": tokens, "blocked": f"Blocked: {blocked}" if blocked else "",
            "cost": cost, "leaves": p.get("kind") in ("paid", "subscription", "custom") or pid == "any"}


class Job:
    """A check of a folder or a link."""

    kind = "check"

    def __init__(self, source: str, lookup: bool):
        self.id = secrets.token_hex(4)
        self.source, self.lookup = source, lookup
        self.events: list[dict] = []
        self.status = "running"  # running, done, failed
        self.result: dict | None = None
        self.report = ""
        self.folder = ""
        self.started = time.monotonic()

    def say(self, step: str, text: str) -> None:
        self.events.append({"t": round(time.monotonic() - self.started, 1), "step": step, "text": text})

    def run(self, cloner=clone) -> None:
        try:
            src = self.source.strip().strip('"')
            if src.startswith(("http://", "https://", "git@", "ssh://", "ext::", "file://")):
                if not git_url_ok(src):
                    raise ValueError("Only public https links are supported, like https://github.com/owner/repo")
                self.say("code", f"Downloading {src} (a shallow copy, only the latest version).")
                folder = cloner(src)
                self.say("code", f"Downloaded to {folder}.")
            else:
                folder = Path(src)
                if not folder.is_dir():
                    raise ValueError(f"There is no folder at {folder}. Check the path and try again.")
            self.say("code", f"Checking {folder.resolve()}. Nothing in it is changed.")
            result = check.check_folder(folder, offline=not self.lookup, progress=self.say)
            self.result = check.page_data(result)
            self.result["link"] = is_clone(result.folder)
            self.report = check.render_html(result)
            check.write_html(result)
            self.folder = str(result.folder)
            self.say("report", f"Done. The report is also saved in {result.run_dir}.")
            self.status = "done"
        except Exception as e:  # noqa: BLE001 - shown to the user as a sentence, never a traceback
            self.say("error", f"Stopped: {e}")
            self.status = "failed"


class FixJob:
    """Fixes for the ticked problems, one after another, or one hand-off try. Every step of the
    loop becomes an event the page draws as it arrives."""

    kind = "fix"

    def __init__(self, folder: str, numbers: list[int], think: bool = False, route: dict | None = None,
                 histories: dict | None = None):
        self.id = secrets.token_hex(4)
        self.folder, self.numbers, self.think, self.route = folder, numbers, think, route
        self.histories = histories if histories is not None else {}  # (folder, n) -> conversation
        self.events: list[dict] = []
        self.status = "running"
        self.result = None
        self.report = ""
        self.current = 0
        self.started = time.monotonic()

    def emit(self, kind: str, data: dict) -> None:
        if kind == "end":  # the conversation stays here for a hand-off; the page gets the rest
            self.histories[(self.folder, self.current)] = data["messages"]
            data = {k: v for k, v in data.items() if k != "messages"}
        self.events.append({"t": round(time.monotonic() - self.started, 1), "kind": kind, "n": self.current, **data})

    def run(self) -> None:
        from aeropatch import folder as fp
        from aeropatch.models.base import LocalServerDown

        for n in self.numbers:
            self.current = n
            self.emit("problem", {"state": "start", "handoff": bool(self.route)})
            try:
                rec = fp.fix(Path(self.folder), n, on_event=self.emit, think=self.think, route=self.route,
                             history=self.histories.get((self.folder, n)) if self.route else None)
                self.emit("problem", {"state": "done", "label": rec["label"], "offered": bool(rec["diff"]),
                                      "diff": rec["diff"], "level": rec["level"], "model": rec["model"],
                                      "notes": rec["notes"], "precision": PRECISION.get(rec["label"], "")
                                      if rec["model"] in ("qwen3.5:4b", "aeropatch-control") else ""})
            except LocalServerDown:
                self.emit("problem", {"state": "error", "text": "The local model is not running. Start Ollama "
                                      "(the status strip at the top says how) and try again."})
            except Exception as e:  # noqa: BLE001 - one problem's failure must not stop the next
                self.emit("problem", {"state": "error", "text": str(e) or type(e).__name__})
        self.status = "done"


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int = 0):
        super().__init__(("127.0.0.1", port), Handler)
        self.token = secrets.token_urlsafe(24)
        self.jobs: dict[str, Job | FixJob] = {}
        self.histories: dict = {}
        self.lock = threading.Lock()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_port}/?t={self.token}"

    def start(self, job: Job | FixJob) -> bool:
        with self.lock:  # one job at a time: the laptop runs Ollama and Docker beside it
            if any(j.status == "running" for j in self.jobs.values()):
                return False
            self.jobs[job.id] = job
        threading.Thread(target=job.run, daemon=True).start()
        return True

    def start_job(self, source: str, lookup: bool) -> Job | None:
        job = Job(source, lookup)
        return job if self.start(job) else None

    def state(self) -> dict:
        """The latest check and every fix of its folder, as events, so a reloaded page draws
        itself again (and picks up a job that is still running)."""
        checks = [j for j in self.jobs.values() if isinstance(j, Job)]
        if not checks:
            return {}
        last = checks[-1]
        fixes = [j for j in self.jobs.values() if isinstance(j, FixJob) and last.folder and j.folder == last.folder]
        return {"check": {"id": last.id, "status": last.status, "lookup": last.lookup, "source": last.source,
                          "events": last.events, "result": last.result},
                "fixes": [{"id": j.id, "status": j.status, "events": j.events} for j in fixes]}

    def checked(self, folder: str) -> str | None:
        """The folder exactly as a finished check here resolved it; nothing else may be fixed."""
        return next((j.folder for j in self.jobs.values()
                     if isinstance(j, Job) and j.status == "done" and j.folder == folder), None)


class Handler(BaseHTTPRequestHandler):
    server: Server

    def log_message(self, *args) -> None:  # keep the terminal quiet
        pass

    def _allowed(self, query: dict) -> bool:
        port = self.server.server_port
        if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
            return False
        token = self.headers.get("X-Token") or query.get("t", [""])[0]
        return secrets.compare_digest(token.encode(), self.server.token.encode())

    def _send(self, code: int, body: str, ctype: str = "application/json", extra: dict | None = None) -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")  # the token is in the page's URL
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj))

    def _error(self, code: int, text: str) -> None:
        self._json(code, {"error": text})

    def do_GET(self) -> None:
        u = urlparse(self.path)
        q = parse_qs(u.query)
        arg = lambda name: q.get(name, [""])[0]
        if not self._allowed(q):
            return self._send(403, "Forbidden", "text/plain")
        if u.path == "/":
            return self._send(200, PAGE.read_text(encoding="utf-8"), "text/html")
        if u.path == "/api/doctor":
            return self._json(200, doctor_data())
        if u.path == "/api/state":
            return self._json(200, self.server.state())
        if u.path == "/api/models":
            return self._json(200, {"providers": providers.all_status()})
        if u.path == "/api/models/list":
            pid = arg("provider")
            if pid not in providers.PROVIDERS:
                return self._error(404, "Unknown provider.")
            return self._json(200, {"models": providers.list_models(pid)})
        if u.path == "/api/handoff":
            folder, n, pid, model = self.server.checked(arg("folder")), arg("n"), arg("provider"), arg("model")
            history = self.server.histories.get((folder, int(n))) if folder and n.isdigit() else None
            if not history:
                return self._error(404, "Run the local fix for this problem first; the hand-off continues from it.")
            return self._json(200, handoff_preview(history, pid, model))
        if u.path == "/api/patch":
            from aeropatch import folder as fp

            folder, n = self.server.checked(arg("folder")), arg("n")
            path = fp.run_dir(Path(folder)) / "fixes" / n / "fix.json" if folder and n.isdigit() else None
            if not path or not path.is_file():
                return self._error(404, "There is no fix for this problem yet.")
            diff = json.loads(path.read_text(encoding="utf-8")).get("diff", "")
            return self._send(200, diff, "text/x-diff",
                              {"Content-Disposition": f'attachment; filename="aeropatch-fix-{n}.patch"'})
        parts = u.path.strip("/").split("/")  # /api/job/<id> and /api/report/<id>
        job = self.server.jobs.get(parts[2]) if len(parts) == 3 and parts[0] == "api" else None
        if job and parts[1] == "job":
            status, n = job.status, len(job.events)  # status first: a "done" reply then carries every event
            since = arg("since")
            return self._json(200, {"status": status, "kind": job.kind, "lookup": getattr(job, "lookup", None),
                                    "next": n, "events": job.events[int(since) if since.isdigit() else 0:n],
                                    "result": job.result if status == "done" else None})
        if job and parts[1] == "report" and job.report:
            return self._send(200, job.report, "text/html")
        self._send(404, "Not found", "text/plain")

    def do_POST(self) -> None:
        u = urlparse(self.path)
        # Read the body before any refusal: closing with it unread resets the connection on Windows.
        raw = self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 200_000))
        if not self._allowed(parse_qs(u.query)):
            return self._send(403, "Forbidden", "text/plain")
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            return self._error(400, "The request was not valid JSON.")
        route = {"/api/choose-folder": self._choose, "/api/check": self._check, "/api/fix": self._fix,
                 "/api/handoff": self._handoff, "/api/apply": self._apply, "/api/undo": self._apply,
                 "/api/models/key": self._models, "/api/models/forget": self._models,
                 "/api/models/custom": self._models, "/api/models/test": self._model_test}.get(u.path)
        if not route:
            return self._send(404, "Not found", "text/plain")
        route(u.path, body)

    def _choose(self, _path: str, _body: dict) -> None:
        try:
            self._json(200, {"folder": choose_folder()})
        except Exception:  # noqa: BLE001 - no tkinter, or no desktop to show it on
            self._error(501, "The folder dialog is not available here. Paste the path instead.")

    def _check(self, _path: str, body: dict) -> None:
        source = str(body.get("source", "")).strip()
        if not source:
            return self._error(400, "Paste a folder path or a git link first.")
        job = self.server.start_job(source, lookup=bool(body.get("lookup", True)))
        if job is None:
            return self._error(409, "Something is already running. Wait for it to finish.")
        self._json(200, {"id": job.id})

    def _fix(self, _path: str, body: dict) -> None:
        folder = self.server.checked(str(body.get("folder", "")))
        numbers = body.get("numbers")
        if not folder:
            return self._error(400, "Check this folder first.")
        if not isinstance(numbers, list) or not numbers or not all(isinstance(n, int) and 0 < n < 100 for n in numbers):
            return self._error(400, "Tick at least one problem.")
        job = FixJob(folder, sorted(set(numbers)), think=bool(body.get("think")), histories=self.server.histories)
        if not self.server.start(job):
            return self._error(409, "Something is already running. Wait for it to finish.")
        self._json(200, {"id": job.id})

    def _handoff(self, _path: str, body: dict) -> None:
        folder, n = self.server.checked(str(body.get("folder", ""))), body.get("n")
        pid, model, pasted = str(body.get("provider", "")), str(body.get("model", "")), body.get("pasted")
        if not folder or not isinstance(n, int) or (folder, n) not in self.server.histories:
            return self._error(400, "Run the local fix for this problem first.")
        if pid == "any":
            if not isinstance(pasted, str) or not pasted.strip():
                return self._error(400, "Paste the other tool's answer first.")
            route = {"attempt_plan": ["pasted"], "pasted_text": pasted[:100_000]}
        else:
            if pid not in providers.PROVIDERS or not MODEL_RE.match(model):
                return self._error(400, "Pick a model first.")
            st = providers.status(pid)
            if not st["ready"]:
                return self._error(400, f"{st['name']} is not ready: {st['says']}.")
            if pid == "ollama" and model not in st["models"]:  # its cloud models would leave the computer
                return self._error(400, "Pick a model that runs on this computer.")
            route = providers.route_cfg(pid, model)
        job = FixJob(folder, [n], route=route, histories=self.server.histories)
        if not self.server.start(job):
            return self._error(409, "Something is already running. Wait for it to finish.")
        self._json(200, {"id": job.id})

    def _apply(self, path: str, body: dict) -> None:
        from aeropatch import folder as fp

        folder, n = self.server.checked(str(body.get("folder", ""))), body.get("n")
        if not folder or not isinstance(n, int):
            return self._error(400, "Check this folder first.")
        if is_clone(Path(folder)):
            return self._error(400, "This is AeroPatch's copy of a link. Save the .patch and apply it in your own copy.")
        try:
            backup = (fp.apply if path == "/api/apply" else fp.undo)(Path(folder), n)
        except (FileNotFoundError, ValueError) as e:
            return self._error(400, str(e))
        self._json(200, {"backup": str(backup)})

    def _models(self, path: str, body: dict) -> None:
        pid = str(body.get("provider", ""))
        if pid not in providers.PROVIDERS:
            return self._error(404, "Unknown provider.")
        try:
            if path == "/api/models/key":
                return self._json(200, {"key_end": providers.save_key(pid, str(body.get("key", "")).strip())})
            if path == "/api/models/forget":
                providers.forget_key(pid)
            else:
                providers.save_custom_base(str(body.get("base", "")))
        except (ValueError, KeyError) as e:
            return self._error(400, str(e))
        self._json(200, providers.status(pid))

    def _model_test(self, _path: str, body: dict) -> None:
        """One tiny request, so the user sees a provider and model answer before relying on them."""
        from aeropatch.agent import router
        from aeropatch.models.base import LocalServerDown

        pid, model = str(body.get("provider", "")), str(body.get("model", ""))
        if pid not in providers.PROVIDERS or not MODEL_RE.match(model):
            return self._error(400, "Pick a model first.")
        cfg = config.load_config("handoff-suggest", max_tokens_local=64, **providers.route_cfg(pid, model))
        try:
            gen = router.generate(cfg["attempt_plan"][0], [{"role": "user", "content": "Reply with the word OK."}],
                                  "Answer in one word.", cfg, 0.0)
        except LocalServerDown as e:
            return self._json(200, {"ok": False, "says": f"Not answering: {e}"})
        if gen.error or gen.refusal:
            return self._json(200, {"ok": False, "says": gen.error or "It refused."})
        self._json(200, {"ok": True, "says": f"Answered in {gen.latency_s:.1f} s: {gen.text.strip()[:60]!r}"})


def main(port: int = 0, open_browser: bool = True) -> int:
    srv = Server(port)
    print(f"AeroPatch is running at {srv.url}\nKeep this window open; press Ctrl+C to stop.", flush=True)
    if open_browser:
        webbrowser.open(srv.url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        srv.server_close()
    return 0
