"""Containment tests for the sandbox itself (doc 07 §11). Run twice to check cleanup."""

import os

import docker
import pytest

from aeropatch.config import BASE_IMAGE
from aeropatch.sandbox import sandbox


def _docker_ready() -> bool:
    try:
        docker.from_env().images.get(BASE_IMAGE)
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = [pytest.mark.docker,
              pytest.mark.skipif(not _docker_ready(), reason="Docker or sandbox base image unavailable")]


def py(code: str, timeout: float = 60):
    return sandbox.run_container(BASE_IMAGE, ["python", "-c", code], timeout_s=timeout)


def count_ours() -> int:
    return len(docker.from_env().containers.list(all=True, filters={"label": "aeropatch=1"}))


def test_no_network():
    code, logs, _, _ = py(
        "import socket\n"
        "try:\n socket.create_connection(('1.1.1.1', 53), timeout=3); print('CONNECTED')\n"
        "except OSError as e: print('BLOCKED', e)")
    assert "BLOCKED" in logs and "CONNECTED" not in logs


def test_readonly_root_and_tmp_size_cap():
    code, logs, _, _ = py(
        "import os\n"
        "for p in ('/usr/x', '/x'):\n"
        "  try: open(p, 'w').write('x'); print('WROTE', p)\n"
        "  except OSError: print('RO', p)\n"
        "try:\n"
        "  with open('/tmp/big', 'wb') as f:\n"
        "    for _ in range(300): f.write(b'0' * 1024 * 1024)\n"
        "  print('BIG-OK')\n"
        "except OSError: print('CAPPED')")
    assert "WROTE" not in logs and logs.count("RO ") == 2
    assert "CAPPED" in logs and "BIG-OK" not in logs


def test_process_count_is_limited():
    # Tries to start far more processes than pids_limit allows; the limit must stop it.
    code, logs, timed_out, _ = py(
        "import subprocess\n"
        "procs = []\n"
        "try:\n"
        "  for _ in range(400): procs.append(subprocess.Popen(['sleep', '5']))\n"
        "  print('STARTED-ALL')\n"
        "except OSError: print('LIMITED', len(procs))", timeout=60)
    assert "LIMITED" in logs and "STARTED-ALL" not in logs


def test_infinite_loop_is_killed_at_timeout():
    code, logs, timed_out, dur = py("while True: pass", timeout=5)
    assert timed_out and dur < 30


def test_no_secrets_in_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-never-reach-the-sandbox")
    code, logs, _, _ = py("import os; print(sorted(os.environ)); print(any('sk-ant' in v for v in os.environ.values()))")
    assert "ANTHROPIC_API_KEY" not in logs and logs.strip().endswith("False")
    assert os.environ["ANTHROPIC_API_KEY"]  # still set on the host side


def test_cleanup_after_crash(monkeypatch):
    before = count_ours()

    def boom(self, **kw):
        raise RuntimeError("simulated harness crash")

    monkeypatch.setattr(docker.models.containers.Container, "logs", boom)
    with pytest.raises(RuntimeError):
        py("print('hi')")
    assert count_ours() == before == 0
