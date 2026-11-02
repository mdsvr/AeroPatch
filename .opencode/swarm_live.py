"""Live state server for the AeroPatch model-swarm dashboard.

Reads opencode's SQLite database read-only and serves:
  /            -> swarm.html
  /api/state   -> JSON snapshot of the current session tree

Run:  .venv\\Scripts\\python.exe .opencode\\swarm_live.py [port]
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.expanduser(r"~\.local\share\opencode\opencode.db")
PROJECT_DIR = os.path.dirname(HERE).replace("\\", "/")

ACTIVE_MS = 8000       # a session is "running" if touched this recently
FEED_LIMIT = 14


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DATA}?mode=ro", uri=True, timeout=2.0)
    con.row_factory = sqlite3.Row
    return con


def parse_model(raw: str | None) -> str:
    if not raw:
        return "?"
    try:
        m = json.loads(raw)
    except ValueError:
        return raw
    model = m.get("id") or m.get("modelID") or "?"
    provider = m.get("providerID") or ""
    return f"{provider}/{model}" if provider else model


def frontmatter(path: str) -> dict:
    """Read the top-level scalar keys of a markdown file's YAML frontmatter."""
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    out = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip()
    return out


def configured_models() -> dict:
    """Which model each role is set to, read from the files that define it."""
    agents = {}
    adir = os.path.join(HERE, "agent")
    if os.path.isdir(adir):
        for name in sorted(os.listdir(adir)):
            if name.endswith(".md"):
                fm = frontmatter(os.path.join(adir, name))
                if fm.get("model"):
                    agents[name[:-3]] = fm["model"]
    lead = "?"
    cfg_path = os.path.join(os.path.dirname(HERE), "opencode.json")
    try:
        with open(cfg_path, encoding="utf-8") as fh:
            lead = json.load(fh).get("model", "?")
    except (OSError, ValueError):
        pass
    return {"lead": lead, "agents": agents}


def content_summary(data: str | None) -> tuple[str, str]:
    """Return (kind, text) for one message: a tool call or a text snippet."""
    if not data:
        return ("", "")
    try:
        msg = json.loads(data)
    except ValueError:
        return ("", (data or "")[:80])
    # opencode 1.18 stores one part per row; older builds nested them in "content"
    for item in msg.get("content") or [msg]:
        kind = item.get("type")
        if kind == "tool":
            name = item.get("tool") or item.get("name") or "tool"
            state = (item.get("state") or {})
            status = state.get("status") or ""
            return ("tool", f"{name} - {status}" if status else name)
        if kind == "text":
            text = (item.get("text") or "").strip().replace("\n", " ")
            if text:
                return ("text", text[:110])
    return ("", "")


def build_state() -> dict:
    con = connect()
    try:
        root = con.execute(
            "select * from session where parent_id is null and directory like ? "
            "order by time_updated desc limit 1",
            (PROJECT_DIR + "%",),
        ).fetchone()
        if root is None:
            root = con.execute(
                "select * from session where parent_id is null "
                "order by time_updated desc limit 1"
            ).fetchone()
        if root is None:
            return {"now": int(time.time() * 1000), "empty": True, "config": configured_models()}

        children = con.execute(
            "select * from session where parent_id = ? order by time_created asc",
            (root["id"],),
        ).fetchall()

        now = int(time.time() * 1000)

        def session_row(r) -> dict:
            updated = r["time_updated"] or 0
            running = (now - updated) < ACTIVE_MS
            return {
                "id": r["id"],
                "agent": r["agent"] or "?",
                "model": parse_model(r["model"]),
                "title": r["title"] or "",
                "status": "running" if running else "idle",
                "cost": round(r["cost"] or 0.0, 6),
                "tokens_in": r["tokens_input"] or 0,
                "tokens_out": r["tokens_output"] or 0,
                "age_ms": now - updated,
                "elapsed_ms": now - (r["time_created"] or now),
            }

        feed = []
        ids = [root["id"]] + [c["id"] for c in children]
        marks = ",".join("?" * len(ids))
        rows = con.execute(
            f"select session_id, time_created, data from part "
            f"where session_id in ({marks}) order by time_created desc limit 60",
            ids,
        ).fetchall()
        by_id = {r["id"]: (r["agent"] or "?") for r in [root] + list(children)}
        for r in rows:
            kind, text = content_summary(r["data"])
            if not text:
                continue
            feed.append({
                "t": r["time_created"],
                "who": by_id.get(r["session_id"], "?"),
                "kind": kind,
                "text": text,
            })
            if len(feed) >= FEED_LIMIT:
                break

        total_cost = sum((r["cost"] or 0) for r in [root] + list(children))
        total_in = sum((r["tokens_input"] or 0) for r in [root] + list(children))
        total_out = sum((r["tokens_output"] or 0) for r in [root] + list(children))

        return {
            "now": now,
            "project": PROJECT_DIR,
            "config": configured_models(),
            "root": session_row(root),
            "agents": [session_row(c) for c in children],
            "totals": {
                "cost": round(total_cost, 6),
                "tokens_in": total_in,
                "tokens_out": total_out,
                "sessions": 1 + len(children),
            },
            "feed": list(reversed(feed)),
        }
    finally:
        con.close()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/state":
            try:
                body = json.dumps(build_state()).encode("utf-8")
                code = 200
            except Exception as exc:  # noqa: BLE001
                body = json.dumps({"error": str(exc)}).encode("utf-8")
                code = 500
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.split("?")[0] in ("/", "/index.html"):
            self.path = "/swarm.html"
        super().do_GET()

    def log_message(self, *a):
        pass


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"swarm dashboard on http://127.0.0.1:{port}/", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
