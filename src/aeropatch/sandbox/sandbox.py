"""Ephemeral hardened Docker sandbox (doc 07).

Build phase (network on, once per scenario): `docker build` via the CLI (BuildKit secrets).
Run phase (network off, every attempt): docker SDK with the hardening flags from doc 07 §4.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

import docker
from aeropatch.config import BASE_IMAGE, DEFAULTS, DOCKER_DIR, ROOT
from aeropatch.contracts import SandboxResult
from aeropatch.sandbox import junit

LABELS = {"aeropatch": "1"}
LOG_CAP = 2_000_000
MARKER = "===AEROPATCH-"


# --------------------------------------------------------------------------- build phase


def _build_cmd(dockerfile: Path, context: Path, tag: str, build_args: dict | None = None) -> list[str]:
    cmd = ["docker", "build", "-f", str(dockerfile), "-t", tag, "--label", "aeropatch=1"]
    for k, v in (build_args or {}).items():
        cmd += ["--build-arg", f"{k}={v}"]
    # Optional corporate/agent proxy support. Proxy build args are not persisted in the image.
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        cmd += ["--build-arg", f"HTTPS_PROXY={proxy}"]
        if urlparse(proxy).hostname in ("127.0.0.1", "localhost"):
            cmd += ["--network", "host"]
    ca = os.environ.get("AEROPATCH_BUILD_CA")
    if ca:
        cmd += ["--secret", f"id=ca,src={ca}"]
    return cmd + [str(context)]


def _run_build(cmd: list[str], log_path: Path | None) -> None:
    env = {**os.environ, "DOCKER_BUILDKIT": "1"}
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(proc.stdout + proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"docker build failed ({cmd[-1]}):\n{proc.stderr[-3000:]}")


def build_base(log_path: Path | None = None) -> str:
    _run_build(_build_cmd(DOCKER_DIR / "sandbox-base.Dockerfile", ROOT, BASE_IMAGE), log_path)
    return image_id(BASE_IMAGE)


def build_scenario(scenario_dir: Path, tag: str, log_path: Path | None = None) -> str:
    cmd = _build_cmd(DOCKER_DIR / "scenario.Dockerfile", scenario_dir, tag, {"BASE": BASE_IMAGE})
    _run_build(cmd, log_path)
    return image_id(tag)


def image_id(tag: str) -> str:
    return docker.from_env().images.get(tag).id


def image_exists(tag: str) -> bool:
    try:
        docker.from_env().images.get(tag)
        return True
    except docker.errors.ImageNotFound:
        return False


# --------------------------------------------------------------------------- run phase


def hardened_kwargs(cfg: dict | None = None) -> dict:
    cfg = {**DEFAULTS, **(cfg or {})}
    return {
        "network_mode": "none",
        "read_only": True,
        "tmpfs": {"/work": "rw,exec,size=512m", "/tmp": "rw,size=256m"},
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges"],
        "pids_limit": cfg["sandbox_pids"],
        "mem_limit": cfg["sandbox_memory"],
        "memswap_limit": cfg["sandbox_memory"],
        "nano_cpus": int(cfg["sandbox_cpus"] * 1e9),
        "user": "10001:10001",
        "ulimits": [docker.types.Ulimit(name="nofile", soft=1024, hard=1024)],
        "stop_signal": "SIGKILL",
        # Explicit, minimal environment: nothing from the host process leaks in.
        "environment": {"PYTHONDONTWRITEBYTECODE": "1", "HOME": "/tmp"},
        "labels": LABELS,
        "detach": True,
    }


def run_container(image: str, command: list[str] | str | None = None, src_dir: Path | None = None,
                  timeout_s: float | None = None, cfg: dict | None = None) -> tuple[int | None, str, bool, float]:
    """Run one hardened container. Returns (exit_code, logs, timed_out, duration_s).

    The container is always removed, even if the harness crashes mid-run.
    """
    cfg = {**DEFAULTS, **(cfg or {})}
    timeout_s = timeout_s or cfg["sandbox_timeout_s"]
    client = docker.from_env()
    volumes = {str(src_dir.resolve()): {"bind": "/src", "mode": "ro"}} if src_dir else {}
    container = None
    start = time.monotonic()
    timed_out = False
    code: int | None = None
    try:
        container = client.containers.run(image, command, volumes=volumes, **hardened_kwargs(cfg))
        try:
            code = container.wait(timeout=timeout_s).get("StatusCode")
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            timed_out = True
            container.kill()
        logs = container.logs(stdout=True, stderr=True)[:LOG_CAP].decode("utf-8", "replace")
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except docker.errors.NotFound:
                pass
    return code, logs, timed_out, time.monotonic() - start


def prune_leftovers() -> int:
    """Remove containers left behind by a crashed harness (label aeropatch=1)."""
    client = docker.from_env()
    leftovers = client.containers.list(all=True, filters={"label": "aeropatch=1"})
    for c in leftovers:
        c.remove(force=True)
    return len(leftovers)


def split_sections(logs: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in logs.splitlines():
        if line.startswith(MARKER) and line.endswith("==="):
            if current:
                sections[current] = "\n".join(buf)
            current = line[len(MARKER):-3]
            buf = []
        elif current:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf)
    return sections


def run_tests(image: str, src_dir: Path, cfg: dict | None = None,
              raw_log: Path | None = None) -> SandboxResult:
    """Run PoC + regression tests (+ lint and re-scan of changed files) on a prepared workspace."""
    _, logs, timed_out, duration = run_container(image, None, src_dir, cfg=cfg)
    if raw_log:
        raw_log.parent.mkdir(parents=True, exist_ok=True)
        raw_log.write_text(logs)
    return parse_logs(logs, timed_out, duration)


def parse_logs(logs: str, timed_out: bool = False, duration: float = 0.0) -> SandboxResult:
    s = split_sections(logs)
    res = SandboxResult(applied=True, duration_s=round(duration, 2), timed_out=timed_out)
    labels = []
    for suite in ("poc", "regression"):
        total, failures = junit.parse(s.get(f"JUNIT-{suite}", ""))
        rc = s.get(f"RC-{suite}", "").strip()
        passed = rc == "0" and total > 0 and not failures
        if suite == "poc":
            res.poc_total, res.poc_passed = total, passed
        else:
            res.regression_total, res.regressions_passed = total, passed
        if not passed:
            if total == 0 and not failures:
                tail = junit.clean(s.get(f"LOG-{suite}", ""))[-1500:]
                failures = [junit.Failure(test_id=f"<{suite}>", kind="error",
                                          message=f"no tests ran (pytest exit {rc or '?'})", trace=tail)]
            res.failures.extend(failures)
            labels.append(junit.classify(failures) or ("POC_FAIL" if suite == "poc" else "REGRESSION"))

    ruff = s.get("RUFF")
    if ruff:
        try:
            issues = json.loads(ruff or "[]")
            res.lint_ok = not any((i.get("code") or "").startswith("E9") or i.get("code") is None
                                  for i in issues)
        except json.JSONDecodeError:
            res.lint_ok = False
    bandit = s.get("BANDIT")
    if bandit:
        try:
            findings = json.loads(bandit).get("results", [])
            res.rescan_clean = not any(f.get("issue_severity") in ("MEDIUM", "HIGH") for f in findings)
        except json.JSONDecodeError:
            res.rescan_clean = None

    if timed_out:
        res.label = "TIMEOUT"
    elif "END" not in s:
        res.label = "SANDBOX_ERROR"
    elif res.poc_passed and res.regressions_passed:
        res.label = "RESOLVED"
    else:
        specific = [lab for lab in labels if lab not in ("POC_FAIL", "REGRESSION")]
        res.label = specific[0] if specific else ("REGRESSION" if "REGRESSION" in labels else "POC_FAIL")
    return res
