"""`aeropatch doctor`: is everything AeroPatch needs installed and running? (doc 17 part 2 §4)

Shape copied from `flutter doctor`: one line per area, a plain fix under each problem, and the
levels that are ready at the end (Check, Suggest, Test; doc 17 part 1 §1). Plain ASCII only, since
a Windows console may not be UTF-8. Every probe has a timeout and never raises, so a broken
install prints a report, not a traceback.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from aeropatch import config
from aeropatch.tools import scanners

TIMEOUT_S = 10
LEVELS = ("Check", "Suggest", "Test")
GB = 2**30
MIN_DOCKER_MEM = 4 * GB
MIN_FREE_DISK = 10 * GB
LOG_TAIL_BYTES = 64 * 1024
# Build prefixes (the digest /api/tags reports) that AeroPatch has benchmarked, per model tag.
# The library qwen3.5:4b runs of Weeks 1 and 2 used 2a654d98e6fb. `ollama pull` now gives
# d8b0f5e9760c, which Phase 0 measured on 2026-10-24 against the export aeropatch-control
# (81771ad1e5cf): 38 and 38 of 54 on test, alternated, Ollama 0.40.10 (doc 17 part 2 §3).
MEASURED_DIGESTS: dict[str, tuple[str, ...]] = {"qwen3.5:4b": ("2a654d98e6fb", "d8b0f5e9760c"),
                                                "aeropatch-control": ("81771ad1e5cf",)}
MARKERS = {"blocking": "[x]", "warning": "[!]", "info": "[-]"}
_START = re.compile(r"starting ollama server", re.IGNORECASE)
_STAGED = re.compile(r"update (already )?downloaded", re.IGNORECASE)


@dataclass
class Check:
    area: str
    level: str  # "blocking" | "warning" | "info"
    ok: bool
    message: str
    fix: str = ""
    gates: tuple[str, ...] = ()  # the levels this check blocks when it fails


# --- probes: each small, each with a timeout, none raises -------------------------------------

def _run(*cmd: str) -> tuple[int, str] | None:
    """(exit code, stdout), or None when the program is not installed."""
    exe = shutil.which(cmd[0])  # resolves Windows shims such as claude.cmd
    if not exe:
        return None
    try:
        proc = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=TIMEOUT_S, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return proc.returncode, proc.stdout.strip()


def _get_json(url: str) -> dict | None:
    # No proxy: Windows' system proxy settings would otherwise apply to localhost too.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=TIMEOUT_S) as r:
            data = json.load(r)
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001 - any failure means "not answering"
        return None


def probe_opengrep() -> str | None:
    return scanners.opengrep_binary()


def probe_docker() -> tuple[str, str, int]:
    """("missing" | "stopped" | "running", server version, memory in bytes or 0 if unknown)."""
    # ponytail: one `docker info` serves both Docker checks, so a hung engine costs one timeout.
    r = _run("docker", "info", "--format", "{{.ServerVersion}} {{.MemTotal}}")
    if r is None:
        return "missing", "", 0
    code, out = r
    parts = out.split()
    if code != 0 or not parts:
        return "stopped", "", 0
    mem = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return "running", parts[0], mem


def probe_ollama_version(host: str) -> str | None:
    data = _get_json(f"{host.rstrip('/')}/api/version")
    return str(data.get("version", "")) if data is not None else None


def probe_ollama_models(host: str) -> list[dict]:
    data = _get_json(f"{host.rstrip('/')}/api/tags") or {}
    models = data.get("models")
    return [m for m in models if isinstance(m, dict)] if isinstance(models, list) else []


def read_log_tail(path: Path | None) -> str:
    """The last LOG_TAIL_BYTES of a file, or "" when it is missing or unreadable."""
    if path is None:
        return ""
    try:
        with open(path, "rb") as f:
            f.seek(max(0, f.seek(0, os.SEEK_END) - LOG_TAIL_BYTES))
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def update_staged(log_text: str) -> bool:
    """True when the app log has an "update downloaded" line after the last server start.

    The lines come from the laptop's app.log and app-1.log (Ollama 0.40.3 and 0.40.7, read on
    2026-10-23): `msg="starting ollama server"`, `msg="new update downloaded ...OllamaSetup.exe"`
    and, an hour later, `msg="update already downloaded"`. File order is used, not the timestamps,
    which are not always in order. An unknown format matches no line, so it gives no warning.
    """
    staged = False
    for line in log_text.splitlines():
        if _START.search(line):
            staged = False
        elif _STAGED.search(line):
            staged = True
    return staged


def probe_ollama_update() -> bool:
    base = os.environ.get("LOCALAPPDATA")
    return update_staged(read_log_tail(Path(base) / "Ollama" / "app.log" if base else None))


def probe_gpu() -> str:
    """The first GPU's "name, memory", or "" when there is no NVIDIA GPU."""
    r = _run("nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader")
    return r[1].splitlines()[0].strip() if r and r[0] == 0 and r[1] else ""


def probe_free_disk() -> int | None:
    try:
        return shutil.disk_usage(config.RUNS_DIR.anchor).free  # runs/ may not exist yet
    except OSError:
        return None


def probe_claude() -> str:
    r = _run("claude", "--version")
    return r[1].splitlines()[0].strip() if r and r[0] == 0 and r[1] else ""


# --- checks ------------------------------------------------------------------------------------

def run_checks(cfg: dict | None = None) -> list[Check]:
    cfg = cfg or config.load_config("repair-local")
    host, model = cfg["local_host"], cfg["local_model"]
    checks: list[Check] = []
    add = checks.append

    opengrep = probe_opengrep()
    add(Check("Opengrep", "warning", bool(opengrep),
              f"found ({opengrep})" if opengrep else
              "not found. Only Bandit will run, which reports many more false alarms.",
              "" if opengrep else "Put opengrep.exe in AeroPatch's .tools folder, or set AEROPATCH_OPENGREP "
              "to its path. Downloads: https://github.com/opengrep/opengrep/releases"))

    version = probe_ollama_version(host)
    add(Check("Ollama answering", "blocking", version is not None,
              f"version {version or 'unknown'} at {host}" if version is not None else
              f"Ollama is not answering at {host}.",
              "" if version is not None else
              "Start Ollama from the Start menu. If its icon is already in the tray, right-click it,\n"
              "choose Quit Ollama and start it again: on Windows the icon can stay up with no server\n"
              "behind it. Not installed? Get it from https://ollama.com/download",
              gates=("Suggest",)))
    if version is not None:
        names = {model} if ":" in model else {model, f"{model}:latest"}
        entry = next((m for m in probe_ollama_models(host) if m.get("name") in names), None)
        add(Check("Model downloaded", "blocking", entry is not None,
                  f"{model} is downloaded" if entry else f"{model} is not downloaded.",
                  "" if entry else f"Run: ollama pull {model}" + (" (about 3 GB)" if model == "qwen3.5:4b" else ""),
                  gates=("Suggest",)))
        if entry:
            digest = str(entry.get("digest", ""))
            tested = any(digest.startswith(p) for p in MEASURED_DIGESTS.get(model, ()))
            add(Check("Model build", "warning", tested,
                      f"build {digest[:12]} is the one AeroPatch measured" if tested else
                      f"build {digest[:12] or 'unknown'} has not been tested with AeroPatch; results may differ.",
                      "" if tested else "Nothing to do; read the published success rates as a rough guide."))

    staged = probe_ollama_update()
    add(Check("Ollama update", "warning", not staged,
              "an update is downloaded and waiting." if staged else "no update waiting",
              "Ollama will restart itself to install it, which stops a check midway. Install it now,\n"
              'before a long check: right-click its tray icon and choose "Restart to update".' if staged else ""))

    gpu = probe_gpu()
    add(Check("GPU", "warning", bool(gpu),
              gpu or "no NVIDIA GPU found: suggestions take about 4-6 times longer (an estimate).",
              "" if gpu else "Nothing to fix: everything still works, only slower."))

    docker, server, mem = probe_docker()
    add(Check("Docker running", "blocking", docker == "running",
              {"running": f"engine {server}",
               "stopped": "Docker Desktop is installed but not running.",
               "missing": "Docker Desktop is not installed."}[docker],
              {"running": "",
               "stopped": 'Open Docker Desktop from the Start menu and wait for "Engine running".',
               "missing": "Only the Test level needs it. Get it from "
                          "https://www.docker.com/products/docker-desktop/"}[docker],
              gates=("Test",)))
    if docker == "running" and mem:
        add(Check("Docker memory", "warning", mem >= MIN_DOCKER_MEM,
                  f"{mem / GB:.1f} GB" + ("" if mem >= MIN_DOCKER_MEM else ": builds may fail."),
                  "" if mem >= MIN_DOCKER_MEM else
                  "Give Docker at least 4 GB: Docker Desktop -> Settings -> Resources (with the WSL 2\n"
                  "backend, set memory=4GB under [wsl2] in .wslconfig in your user folder)."))

    free = probe_free_disk()
    if free is not None:
        where = config.RUNS_DIR.anchor
        add(Check("Disk space", "warning", free >= MIN_FREE_DISK,
                  f"{free / GB:.0f} GB free on {where}" if free >= MIN_FREE_DISK else
                  f"only {free / GB:.1f} GB free on {where}.",
                  "" if free >= MIN_FREE_DISK else
                  "Free up at least 10 GB: each project's test box takes about 1-1.5 GB."))

    claude = probe_claude()
    add(Check("Claude Code", "info", bool(claude), claude or "not installed.",
              "" if claude else 'Only needed for the optional "Ask Claude" button.'))
    return checks


def _blocked(checks: list[Check], level: str) -> list[Check]:
    return [c for c in checks if c.level == "blocking" and not c.ok and level in c.gates]


def ready_levels(checks: list[Check]) -> list[str]:
    """The levels whose blocking checks all pass. Levels build on each other (Suggest is Check
    plus Ollama, Test is Suggest plus Docker), so the first level that is not ready ends the list."""
    ready = []
    for level in LEVELS:
        if _blocked(checks, level):
            break
        ready.append(level)
    return ready


def format_report(checks: list[Check]) -> str:
    lines = []
    for c in checks:
        lines.append(f"{'[ok]' if c.ok else MARKERS[c.level]} {c.area}: {c.message}")
        if not c.ok and c.fix:
            lines += [f"     {fix_line}" for fix_line in c.fix.splitlines()]
    if all(c.ok for c in checks if c.level != "info"):
        lines.append("No problems found.")
        return "\n".join(lines)
    ready = ready_levels(checks)
    last = [f"Ready for: {', '.join(ready)}."]
    for level in LEVELS[len(ready):]:
        missing = _blocked(checks, level)
        if missing:
            last.append(f"{level} needs {' and '.join(c.area for c in missing)}.")
        else:
            last.append(f"{level} needs {LEVELS[LEVELS.index(level) - 1]} first.")
    lines.append(" ".join(last))
    return "\n".join(lines)


def main() -> int:
    checks = run_checks()
    print(format_report(checks))
    return 0 if all(c.ok for c in checks if c.level == "blocking") else 1
