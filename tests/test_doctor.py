"""`aeropatch doctor` (doc 17 part 2 §4): every probe is monkeypatched; no Docker, Ollama or network."""

import subprocess

import pytest

from aeropatch import doctor
from aeropatch.doctor import GB, LEVELS, Check

CFG = {"local_host": "http://localhost:11434", "local_model": "qwen3.5:4b"}
MEASURED = "2a654d98e6fb" + "0" * 52
REBUILT = "ffffffffffff" + "1" * 52
# The unpatched probes, kept before the autouse fixture replaces them.
REAL = {n: getattr(doctor, n) for n in ("probe_ollama_update", "probe_docker", "probe_ollama_version",
                                        "probe_ollama_models")}

# app-1.log on the laptop, trimmed: 0.40.3 starts, downloads 0.40.7, then installs it.
LOG_STAGED = r"""time=2026-10-21T09:50:12.334+05:30 level=INFO source=app_windows.go:281 msg="starting Ollama" app=C:\Users\vardh\AppData\Local\Programs\Ollama version=0.40.3 OS=Windows/10.0.26300
time=2026-10-21T09:50:12.420+05:30 level=INFO source=app.go:285 msg="starting ui server" port=50090
time=2026-10-21T09:50:12.389+05:30 level=INFO source=app.go:253 msg="starting ollama server"
time=2026-10-21T09:50:15.870+05:30 level=INFO source=updater.go:373 msg="beginning update checker" interval=1h0m0s
time=2026-10-21T09:50:17.567+05:30 level=INFO source=updater.go:133 msg="New update available at https://github.com/ollama/ollama/releases/download/v0.40.7/OllamaSetup.exe"
time=2026-10-21T09:54:08.888+05:30 level=INFO source=updater.go:242 msg="new update downloaded C:\\Users\\vardh\\AppData\\Local\\Ollama\\updates_v2\\5e8eb517\\OllamaSetup.exe"
"""
# The next hourly check after an app restart, while the bundle is still waiting.
LOG_ALREADY = r"""time=2026-10-21T10:50:12.389+05:30 level=INFO source=app.go:253 msg="starting ollama server"
time=2026-10-21T10:50:17.693+05:30 level=INFO source=updater.go:198 msg="update already downloaded" bundle=C:\Users\vardh\AppData\Local\Ollama\updates_v2\5e8eb517\OllamaSetup.exe
"""
# app.log after the upgrade: 0.40.7 started, nothing waiting.
LOG_AFTER_UPGRADE = r"""time=2026-10-21T11:46:50.031+05:30 level=INFO source=app_windows.go:281 msg="starting Ollama" app=C:\Users\vardh\AppData\Local\Programs\Ollama version=0.40.7 OS=Windows/10.0.26300
time=2026-10-21T11:46:50.195+05:30 level=INFO source=app.go:253 msg="starting ollama server"
time=2026-10-21T11:46:53.196+05:30 level=INFO source=updater.go:373 msg="beginning update checker" interval=1h0m0s
time=2026-10-21T11:47:31.497+05:30 level=INFO source=ui.go:246 msg=site.serveHTTP http.d=507.9µs version=0.40.7
"""


@pytest.fixture(autouse=True)
def green(monkeypatch):
    """A healthy laptop: every probe answers as if all is installed and running."""
    monkeypatch.setattr(doctor, "probe_opengrep", lambda: r"F:\AeroPatch\.tools\opengrep.exe")
    monkeypatch.setattr(doctor, "probe_ollama_version", lambda host: "0.40.7")
    monkeypatch.setattr(doctor, "probe_ollama_models", lambda host: [{"name": "qwen3.5:4b", "digest": MEASURED}])
    monkeypatch.setattr(doctor, "probe_ollama_update", lambda: False)
    monkeypatch.setattr(doctor, "probe_gpu", lambda: "NVIDIA GeForce RTX 3050 Laptop GPU, 4096 MiB")
    monkeypatch.setattr(doctor, "probe_docker", lambda: ("running", "29.1.3", 8 * GB))
    monkeypatch.setattr(doctor, "probe_free_disk", lambda: 120 * GB)
    monkeypatch.setattr(doctor, "probe_claude", lambda: "2.1.296 (Claude Code)")


def _staged_log(monkeypatch, tmp_path):
    (tmp_path / "Ollama").mkdir()
    (tmp_path / "Ollama" / "app.log").write_text(LOG_STAGED, encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(doctor, "probe_ollama_update", REAL["probe_ollama_update"])


# (fault, set it up, failing area, its level, ready levels)
FAULTS = [
    ("docker stopped", lambda mp, tmp: mp.setattr(doctor, "probe_docker", lambda: ("stopped", "", 0)),
     "Docker running", "blocking", ["Check", "Suggest"]),
    ("docker missing", lambda mp, tmp: mp.setattr(doctor, "probe_docker", lambda: ("missing", "", 0)),
     "Docker running", "blocking", ["Check", "Suggest"]),
    ("ollama down", lambda mp, tmp: mp.setattr(doctor, "probe_ollama_version", lambda host: None),
     "Ollama answering", "blocking", ["Check"]),
    ("model missing", lambda mp, tmp: mp.setattr(doctor, "probe_ollama_models", lambda host: []),
     "Model downloaded", "blocking", ["Check"]),
    ("other digest", lambda mp, tmp: mp.setattr(doctor, "probe_ollama_models",
                                                lambda host: [{"name": "qwen3.5:4b", "digest": REBUILT}]),
     "Model build", "warning", list(LEVELS)),
    ("update staged", _staged_log, "Ollama update", "warning", list(LEVELS)),
    ("opengrep missing", lambda mp, tmp: mp.setattr(doctor, "probe_opengrep", lambda: None),
     "Opengrep", "warning", list(LEVELS)),
    ("low disk", lambda mp, tmp: mp.setattr(doctor, "probe_free_disk", lambda: 3 * GB),
     "Disk space", "warning", list(LEVELS)),
    ("low docker memory", lambda mp, tmp: mp.setattr(doctor, "probe_docker", lambda: ("running", "29.1.3", 2 * GB)),
     "Docker memory", "warning", list(LEVELS)),
    ("no gpu", lambda mp, tmp: mp.setattr(doctor, "probe_gpu", lambda: ""), "GPU", "warning", list(LEVELS)),
]


def test_all_green(capsys):
    checks = doctor.run_checks(CFG)
    assert all(c.ok for c in checks)
    assert doctor.ready_levels(checks) == ["Check", "Suggest", "Test"]
    assert {c.area for c in checks} == {"Opengrep", "Ollama answering", "Model downloaded", "Model build",
                                        "Ollama update", "GPU", "Docker running", "Docker memory",
                                        "Disk space", "Claude Code"}
    report = doctor.format_report(checks)
    assert report.splitlines()[-1] == "No problems found."
    assert all(line.startswith("[ok] ") for line in report.splitlines()[:-1])
    assert doctor.main() == 0
    assert capsys.readouterr().out.strip().endswith("No problems found.")


@pytest.mark.parametrize("fault, setup, area, level, ready", FAULTS, ids=[f[0] for f in FAULTS])
def test_seeded_fault_is_named(fault, setup, area, level, ready, monkeypatch, tmp_path, capsys):
    setup(monkeypatch, tmp_path)
    checks = doctor.run_checks(CFG)
    failing = [c for c in checks if not c.ok]
    assert [(c.area, c.level) for c in failing] == [(area, level)]
    assert failing[0].fix
    assert doctor.ready_levels(checks) == ready
    report = doctor.format_report(checks)
    assert report.isascii()
    lines = report.splitlines()
    i = next(i for i, line in enumerate(lines) if line.startswith(f"{doctor.MARKERS[level]} {area}: "))
    assert lines[i + 1].startswith("     ") and lines[i + 1].strip()  # the fix, indented under it
    assert doctor.main() == (1 if level == "blocking" else 0)
    capsys.readouterr()


def test_fault_wording(monkeypatch):
    def failing(**probes):
        with monkeypatch.context() as mp:
            for name, fn in probes.items():
                mp.setattr(doctor, name, fn)
            return {c.area: c for c in doctor.run_checks(CFG) if not c.ok}

    assert "installed but not running" in failing(probe_docker=lambda: ("stopped", "", 0))["Docker running"].message
    assert '"Engine running"' in failing(probe_docker=lambda: ("stopped", "", 0))["Docker running"].fix
    assert "not installed" in failing(probe_docker=lambda: ("missing", "", 0))["Docker running"].message
    down = failing(probe_ollama_version=lambda host: None)["Ollama answering"]
    assert "not answering at http://localhost:11434" in down.message and "tray" in down.fix
    assert failing(probe_ollama_models=lambda host: [])["Model downloaded"].fix == \
        "Run: ollama pull qwen3.5:4b (about 3 GB)"
    build = failing(probe_ollama_models=lambda host: [{"name": "qwen3.5:4b", "digest": REBUILT}])["Model build"]
    assert "ffffffffffff has not been tested" in build.message
    assert "Only Bandit will run" in failing(probe_opengrep=lambda: None)["Opengrep"].message
    assert "1-1.5 GB" in failing(probe_free_disk=lambda: 3 * GB)["Disk space"].fix


def test_dependent_checks_are_skipped(monkeypatch):
    monkeypatch.setattr(doctor, "probe_ollama_version", lambda host: None)
    monkeypatch.setattr(doctor, "probe_docker", lambda: ("stopped", "", 0))
    areas = {c.area for c in doctor.run_checks(CFG)}
    assert not areas & {"Model downloaded", "Model build", "Docker memory"}


def test_untagged_model_matches_latest(monkeypatch):
    monkeypatch.setattr(doctor, "probe_ollama_models", lambda host: [{"name": "mymodel:latest", "digest": "abc"}])
    checks = {c.area: c for c in doctor.run_checks({**CFG, "local_model": "mymodel"})}
    assert checks["Model downloaded"].ok
    assert not checks["Model build"].ok  # no measured build for an unknown tag


def test_levels_build_on_each_other(monkeypatch):
    monkeypatch.setattr(doctor, "probe_ollama_version", lambda host: None)  # Docker still runs
    checks = doctor.run_checks(CFG)
    assert doctor.ready_levels(checks) == ["Check"]
    assert doctor.format_report(checks).splitlines()[-1] == \
        "Ready for: Check. Suggest needs Ollama answering. Test needs Suggest first."
    monkeypatch.setattr(doctor, "probe_docker", lambda: ("stopped", "", 0))
    assert doctor.format_report(doctor.run_checks(CFG)).splitlines()[-1] == \
        "Ready for: Check. Suggest needs Ollama answering. Test needs Docker running."


def test_report_markers_and_ready_line():
    checks = [
        Check("Opengrep", "warning", False, "not found.", "Install it."),
        Check("Ollama answering", "blocking", True, "version 0.40.7", gates=("Suggest",)),
        Check("Docker running", "blocking", False, "Docker Desktop is installed but not running.",
              "Open Docker Desktop.", gates=("Test",)),
        Check("Claude Code", "info", False, "not installed.", "Only for Ask Claude."),
    ]
    assert doctor.format_report(checks).splitlines() == [
        "[!] Opengrep: not found.",
        "     Install it.",
        "[ok] Ollama answering: version 0.40.7",
        "[x] Docker running: Docker Desktop is installed but not running.",
        "     Open Docker Desktop.",
        "[-] Claude Code: not installed.",
        "     Only for Ask Claude.",
        "Ready for: Check, Suggest. Test needs Docker running.",
    ]
    assert doctor.ready_levels(checks) == ["Check", "Suggest"]


def test_missing_claude_is_not_a_problem(monkeypatch, capsys):
    monkeypatch.setattr(doctor, "probe_claude", lambda: "")
    checks = doctor.run_checks(CFG)
    report = doctor.format_report(checks)
    assert "[-] Claude Code: not installed." in report
    assert report.splitlines()[-1] == "No problems found."
    assert doctor.ready_levels(checks) == list(LEVELS)
    assert doctor.main() == 0
    capsys.readouterr()


def test_warnings_only_still_ready():
    checks = [Check("GPU", "warning", False, "no NVIDIA GPU found.", "Nothing to fix.")]
    assert doctor.format_report(checks).splitlines()[-1] == "Ready for: Check, Suggest, Test."


# --- the app.log parser -------------------------------------------------------------------------

def test_update_staged_parser():
    assert doctor.update_staged(LOG_STAGED)
    assert doctor.update_staged(LOG_ALREADY)
    assert not doctor.update_staged(LOG_AFTER_UPGRADE)
    assert not doctor.update_staged(LOG_STAGED + LOG_AFTER_UPGRADE)  # restarted since: installed
    assert not doctor.update_staged("")
    assert not doctor.update_staged("some other log format\nwith no matching lines\n")


def test_update_probe_on_files(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "probe_ollama_update", REAL["probe_ollama_update"])
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert not doctor.probe_ollama_update()  # missing file
    (tmp_path / "Ollama").mkdir()
    log = tmp_path / "Ollama" / "app.log"
    log.write_bytes(b"")
    assert not doctor.probe_ollama_update()  # empty file
    log.write_text(LOG_STAGED, encoding="utf-8")
    assert doctor.probe_ollama_update()
    log.write_bytes(b"\xff\xfe not utf-8 \x80\n")
    assert not doctor.probe_ollama_update()
    monkeypatch.delenv("LOCALAPPDATA")
    assert not doctor.probe_ollama_update()


def test_read_log_tail_reads_only_the_end(tmp_path):
    log = tmp_path / "app.log"
    log.write_bytes(b"update downloaded\n" + b"x" * (2 * doctor.LOG_TAIL_BYTES) + b"\nend\n")
    tail = doctor.read_log_tail(log)
    assert len(tail) == doctor.LOG_TAIL_BYTES and tail.endswith("end\n")
    assert "update downloaded" not in tail
    assert doctor.read_log_tail(tmp_path / "missing.log") == ""
    assert doctor.read_log_tail(tmp_path) == ""  # a directory: unreadable, no crash


# --- the probes themselves never raise -----------------------------------------------------------

def test_run_tells_missing_from_failing(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    assert doctor._run("docker", "info") is None
    monkeypatch.setattr(doctor.shutil, "which", lambda name: name)

    def hang(*a, **k):
        raise subprocess.TimeoutExpired("docker", doctor.TIMEOUT_S)
    monkeypatch.setattr(doctor.subprocess, "run", hang)
    assert doctor._run("docker", "info") == (1, "")


@pytest.mark.parametrize("result, expected", [
    (None, ("missing", "", 0)),
    ((1, ""), ("stopped", "", 0)),
    ((0, ""), ("stopped", "", 0)),
    ((0, "29.1.3 8327405568"), ("running", "29.1.3", 8327405568)),
    ((0, "29.1.3"), ("running", "29.1.3", 0)),
])
def test_probe_docker(monkeypatch, result, expected):
    monkeypatch.setattr(doctor, "_run", lambda *cmd: result)
    assert REAL["probe_docker"]() == expected


def test_ollama_probes_survive_bad_answers(monkeypatch):
    real_version, real_models = REAL["probe_ollama_version"], REAL["probe_ollama_models"]
    monkeypatch.setattr(doctor, "_get_json", lambda url: None)
    assert real_version(CFG["local_host"]) is None
    assert real_models(CFG["local_host"]) == []
    monkeypatch.setattr(doctor, "_get_json", lambda url: {"models": "junk"})
    assert real_models(CFG["local_host"]) == []


def test_get_json_never_raises(monkeypatch):
    class Opener:
        def open(self, url, timeout):
            raise ConnectionRefusedError(10061, "refused")
    monkeypatch.setattr(doctor.urllib.request, "build_opener", lambda *a: Opener())
    assert doctor._get_json("http://localhost:11434/api/version") is None
