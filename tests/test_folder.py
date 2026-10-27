"""Phase 1b host-side parts (doc 17 part 4): staging, the dependency plan, the Python check, error
classes, and apply/undo (exit criterion 3: byte-identical undo, CRLF and BOM included, nothing
written before apply). No Docker: the Suggest level must never start a container (criterion 4)."""

import hashlib

import pytest

from aeropatch import config, folder
from aeropatch.contracts import Edit, Finding


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path / "runs")


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


CRLF_BOM = "﻿import sqlite3\r\n\r\ndef find(c, name):\r\n    return c.execute(f\"SELECT * WHERE n = '{name}'\")\r\n"


@pytest.fixture
def proj(tmp_path):
    d = tmp_path / "proj"
    (d / "app").mkdir(parents=True)
    (d / "app" / "db.py").write_bytes(CRLF_BOM.encode("utf-8"))
    (d / "app" / "plain.py").write_bytes(b"x = 1\n")
    return d


def make_fix(proj, n=1):
    out = folder.run_dir(proj) / "fixes" / str(n)
    repo = folder.stage(proj, folder.run_dir(proj) / "context" / "repo")
    edit = Edit(path="app/db.py", search="    return c.execute(f\"SELECT * WHERE n = '{name}'\")",
                replace="    return c.execute(\"SELECT * WHERE n = ?\", (name,))")
    record = {"n": n, "diff": "(diff)", "files": {}, "label": "Scanner quiet, not tested"}
    return folder.save_fix(proj, repo, out, record, [edit])


def test_fix_keeps_crlf_and_bom_and_writes_nothing_in_the_folder(proj):
    before = snapshot(proj)
    rec = make_fix(proj)
    assert snapshot(proj) == before  # nothing written before apply
    after = (folder.run_dir(proj) / "fixes" / "1" / "after" / "app" / "db.py").read_bytes()
    assert after.startswith(b"\xef\xbb\xbf") and after.count(b"\r\n") == 4 and b"\n" not in after.replace(b"\r\n", b"")
    assert b"WHERE n = ?\", (name,))\r\n" in after
    assert list(rec["files"]) == ["app/db.py"]


def test_apply_then_undo_is_byte_identical(proj):
    original = (proj / "app" / "db.py").read_bytes()
    make_fix(proj)
    backup = folder.apply(proj, 1)
    assert (proj / "app" / "db.py").read_bytes() != original
    assert (backup / "app" / "db.py").read_bytes() == original
    folder.undo(proj, 1)
    assert (proj / "app" / "db.py").read_bytes() == original
    with pytest.raises(FileNotFoundError):
        folder.undo(proj, 1)  # nothing left to undo


def test_apply_refuses_a_file_changed_since_the_fix(proj):
    make_fix(proj)
    (proj / "app" / "db.py").write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="changed since the fix"):
        folder.apply(proj, 1)
    assert (proj / "app" / "db.py").read_bytes() == b"changed\n"


def test_undo_refuses_when_the_file_changed_after_apply(proj):
    make_fix(proj)
    folder.apply(proj, 1)
    (proj / "app" / "db.py").write_bytes(b"edited by hand\n")
    with pytest.raises(ValueError, match="nothing was undone"):
        folder.undo(proj, 1)
    assert (proj / "app" / "db.py").read_bytes() == b"edited by hand\n"


def test_stage_leaves_out_environments_caches_and_env_files(tmp_path, proj):
    for p in (".venv/lib/x.py", "venv/x.py", "node_modules/a.js", ".env", ".env.local", "build/x.py",
              "pkg.egg-info/PKG-INFO", "app/__pycache__/x.pyc", ".git/HEAD", ".venv-notebook/y.py"):
        (proj / p).parent.mkdir(parents=True, exist_ok=True)
        (proj / p).write_text("x")
    staged = folder.stage(proj, tmp_path / "staged")
    assert sorted(snapshot(staged)) == ["app/db.py", "app/plain.py"]


@pytest.mark.parametrize(("files", "source", "editable"), [
    ({"requirements.txt": "flask==3.0\n-e .\n./local\n", "requirements-dev.txt": "pytest\n"},
     "requirements-dev.txt, requirements.txt", False),
    ({"requirements/base.txt": "flask\n"}, "requirements/base.txt", False),
    ({"Pipfile.lock": '{"default": {"flask": {"version": "==3.0.0"}}, "develop": {}}'}, "Pipfile.lock", False),
    ({"pyproject.toml": "[project]\nname='x'\n"}, "the project's own metadata", True),
    ({"pyproject.toml": "[project]\nname='x'\n", "requirements.txt": "flask==3.0\n"}, "requirements.txt", True),
    ({}, "none", False),
])
def test_dependency_plan(tmp_path, files, source, editable):
    repo = tmp_path / "repo"
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    repo.mkdir(exist_ok=True)
    plan = folder.dependency_plan(repo, tmp_path / "deps")
    assert plan == {"source": source, "editable": editable}
    if "requirements-dev.txt" in files:
        assert (tmp_path / "deps" / "requirements.txt").read_text().split() == ["flask==3.0"]  # local lines dropped
        assert (tmp_path / "deps" / "all.txt").read_text().split("\n")[:2] == ["-r requirements-dev.txt",
                                                                               "-r requirements.txt"]
    if source == "Pipfile.lock":
        assert (tmp_path / "deps" / "all.txt").read_text().strip() == "flask==3.0.0"


@pytest.mark.parametrize(("name", "text", "excluded"), [
    (".python-version", "3.11.4\n", True), (".python-version", "3.12\n", False),
    ("pyproject.toml", "[project]\nrequires-python = '>=3.13'\n", True),
    ("pyproject.toml", "[project]\nrequires-python = '>=3.9'\n", False),
    ("runtime.txt", "python-3.10.12\n", True), ("runtime.txt", "python-3.12.1\n", False),
])
def test_python_version_check(tmp_path, name, text, excluded):
    (tmp_path / name).write_text(text)
    if excluded:
        with pytest.raises(folder.FolderError) as e:
            folder.python_check(tmp_path)
        assert e.value.kind == "PYTHON_VERSION"
    else:
        folder.python_check(tmp_path)


@pytest.mark.parametrize(("log", "kind"), [
    ("ERROR: ResolutionImpossible: ...", "DEPENDENCY_CONFLICT"),
    ("--index-url https://pkgs.corp/simple ... 401 Unauthorized", "PRIVATE_INDEX"),
    ("Error: pg_config executable not found.", "NATIVE_PACKAGE"),
    ("ModuleNotFoundError: No module named 'imp'", "OLD_PACKAGES"),
    ("error: [Errno 2] No such file or directory: 'gcc'", "NATIVE_PACKAGE"),
    ("something else broke", "BUILD_FAILED"),
])
def test_build_failures_are_named(log, kind):
    assert folder._classify_build(log).kind == kind


@pytest.mark.parametrize(("rc", "log", "kind"), [
    ("5", "no tests ran", "NO_TESTS"), ("124", "", "TOO_SLOW"),
    ("1", "psycopg2.OperationalError: could not connect to server: Connection refused ... port 5432", "NEEDS_SERVICE"),
    ("1", "KeyError: 'DATABASE_URL'", "NEEDS_SETTINGS"),
    ("2", "E   ModuleNotFoundError: No module named 'hypothesis'", "MISSING_TEST_PACKAGES"),
])
def test_baseline_failures_are_named(rc, log, kind):
    logs = f"===AEROPATCH-RC-regression===\n{rc}\n===AEROPATCH-LOG-regression===\n{log}\n===AEROPATCH-END===\n"
    assert folder._baseline_failure(logs).kind == kind


def test_outcomes_keep_a_failure_over_a_pass():
    logs = "===AEROPATCH-OUTCOMES===\npassed\ttests/test_a.py::t\nfailed\ttests/test_a.py::t\npassed\tt2\n"
    assert folder._outcomes(logs) == {"tests/test_a.py::t": "failed", "t2": "passed"}


def test_suggest_level_never_starts_a_container(proj, monkeypatch):
    """Exit criterion 4: Docker stopped, `fix` still suggests, and no container is started."""
    from aeropatch.models.base import Generation
    from aeropatch.sandbox import sandbox

    def no_container(*a, **k):
        raise AssertionError("a container was started")
    monkeypatch.setattr(sandbox, "run_container", no_container)
    monkeypatch.setattr(folder, "sandbox_available", lambda: False)
    finding = Finding(tool="opengrep", rule_id="aeropatch.python.sqli-string-query", path="app/db.py", line=4,
                      cwe="CWE-89", severity="high", message="SQL", fingerprint="abcdef0123456789")
    from aeropatch import check

    monkeypatch.setattr(check, "check_folder", lambda *a, **k: check.triage(proj, [finding]))
    answer = ("<<<<<<< SEARCH app/db.py\n    return c.execute(f\"SELECT * WHERE n = '{name}'\")\n=======\n"
              "    return c.execute(\"SELECT * WHERE n = ?\", (name,))\n>>>>>>> REPLACE\n")
    from aeropatch.agent import router

    monkeypatch.setattr(router, "generate", lambda *a, **k: Generation(text=answer, model="stub"))
    before = snapshot(proj)
    rec = folder.fix(proj, 1)
    assert rec["level"] == "suggest" and rec["config"] == "suggest-local"
    assert rec["notes"] == [folder.MESSAGES["NO_DOCKER"]]
    assert rec["label"] == "Scanner quiet, not tested"
    assert snapshot(proj) == before and list(rec["files"]) == ["app/db.py"]
