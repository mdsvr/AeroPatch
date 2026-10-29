"""Fix a folder (doc 17 part 4, Phase 1b): a Task from a finding, the folder sandbox image, the
user's own tests run twice for a baseline, and `fix`, `apply`, `undo`.

Nothing here writes inside the user's folder except `apply` and `undo`. Everything else goes to
runs/folders/<name>-<hash8>/ (the same folder `check` uses):
    context/   the staged copy the image is built from (never the folder itself)
    fixes/<n>/ fix.json, the diff, and each changed file as it would be after `apply`
    backups/   one folder per `apply`, with the original files and a manifest
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from packaging.specifiers import InvalidSpecifier, SpecifierSet

from aeropatch import check, config
from aeropatch.contracts import Finding, Task
from aeropatch.sandbox import sandbox
from aeropatch.tools.git_ops import Workspace

PYTHON = "3.12"  # the base image's Python
MAX_STAGED_BYTES = 400 * 1024 * 1024
TEST_GLOBS = ("tests/**/*.py", "test/**/*.py", "**/test_*.py", "**/*_test.py", "**/conftest.py")
# Build-log text -> apt packages for one retry (doc 17 part 4 §2 step 4; grows from the failure log).
NATIVE = {"pg_config": "libpq-dev gcc", "mysql_config": "default-libmysqlclient-dev gcc pkg-config",
          "libxml/xmlversion.h": "libxml2-dev libxslt1-dev",
          # From criterion 2's failure log (2026-10-27): old pins with no wheel for 3.12 compile C.
          "No such file or directory: 'gcc'": "gcc"}
MESSAGES = {
    "PYTHON_VERSION": "This project needs Python {detail}. AeroPatch's test sandbox has 3.12, so it can only scan "
                      "and suggest.",
    "NATIVE_PACKAGE": "A package needs extra system software AeroPatch could not install ({detail}). Scanning "
                      "still works.",
    "DEPENDENCY_CONFLICT": "Your requirements contradict each other, so they cannot all be installed.",
    "OLD_PACKAGES": "Some pinned packages are older than Python 3.12 allows (they use a module 3.12 removed). "
                    "Scanning still works.",
    "PRIVATE_INDEX": "Some packages come from a private server; AeroPatch does not send passwords into the sandbox.",
    "MISSING_TEST_PACKAGES": "Your tests need packages your project files do not list ({detail}), so AeroPatch "
                             "cannot run them. Adding them to a requirements file fixes this.",
    "NO_TESTS": "No tests found, so AeroPatch can check the warning but not your app's behaviour.",
    "NO_PASSING_TESTS": "None of your tests passed before any change, so AeroPatch cannot tell whether a change "
                        "breaks something.",
    "NEEDS_SERVICE": "Your tests need a database or other server; the sandbox has none.",
    "NEEDS_SETTINGS": "Your tests need settings that are in your environment, not the code.",
    "TOO_SLOW": "Your tests took longer than the sandbox allows (4 minutes).",
    "TOO_BIG": "This folder is too big to copy into the sandbox (over 400 MB without virtual environments).",
    "BUILD_FAILED": "AeroPatch could not install this project's dependencies in its sandbox. Scanning still works.",
    "NO_DOCKER": "Docker is not running, so AeroPatch cannot run your tests. It can still suggest a change.",
    "NOT_UTF8": "This file is not saved as UTF-8, so AeroPatch will not edit it. The warning still stands.",
}


class FolderError(RuntimeError):
    def __init__(self, kind: str, detail: str = ""):
        self.kind, self.detail = kind, detail
        super().__init__(MESSAGES[kind].format(detail=detail))


@dataclass
class Prepared:
    image: str
    pass_set: list[str]
    flaky: list[str] = field(default_factory=list)
    level: str = "test"  # test | suggest
    note: str = ""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_dir(folder: Path) -> Path:
    return check._run_dir(Path(folder).resolve())


# --------------------------------------------------------------------------- staging


def _skip(name: str) -> bool:
    return check._tool_dir(name) or name.startswith(".env") or name in ("__pycache__",) or name.endswith(".pyc")


def stage(folder: Path, dest: Path) -> Path:
    """Copy the folder without virtual environments, build output, caches, VCS data or .env files."""
    folder = Path(folder).resolve()
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(folder, dest, ignore=lambda d, names: [n for n in names if _skip(n)], symlinks=False)
    size = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
    if size > MAX_STAGED_BYTES:
        raise FolderError("TOO_BIG")
    return dest


def python_check(repo: Path) -> None:
    """Doc 17 part 4 §2 step 2: .python-version, then requires-python, then runtime.txt."""
    pv = repo / ".python-version"
    if pv.is_file():
        want = pv.read_text(encoding="utf-8").split()[0] if pv.read_text(encoding="utf-8").split() else ""
        if want and not (want == PYTHON or want.startswith(PYTHON + ".")):
            raise FolderError("PYTHON_VERSION", want)
        return
    pp = repo / "pyproject.toml"
    if pp.is_file():
        try:
            spec = tomllib.loads(pp.read_text(encoding="utf-8")).get("project", {}).get("requires-python")
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            spec = None
        if spec:
            try:
                if not SpecifierSet(spec).contains(PYTHON + ".0"):
                    raise FolderError("PYTHON_VERSION", spec)
            except InvalidSpecifier:
                pass
            return
    rt = repo / "runtime.txt"
    if rt.is_file():
        m = re.search(r"(\d+\.\d+)", rt.read_text(encoding="utf-8"))
        if m and m[1] != PYTHON:
            raise FolderError("PYTHON_VERSION", m[1])


LOCAL_LINE = re.compile(r"^\s*(-e\b|--editable\b|\.\.?(/|$)|file:)")


def dependency_plan(repo: Path, deps: Path) -> dict:
    """Doc 17 part 4 §2 step 3, first match wins. Writes deps/all.txt (and the files it includes);
    returns {"source": ..., "editable": bool}. Local and editable lines are dropped: the project
    is not in the image yet at that layer. A project file means the project itself is installed
    after the copy, with its usual test extras: on 2026-10-27 cookiecutter's conftest needed its
    package metadata, and buku's tests needed `hypothesis` from its `tests` extra."""
    plan = _dependency_files(repo, deps)
    project = (repo / "pyproject.toml").is_file() or (repo / "setup.py").is_file()
    return {**plan, "editable": project}


def _dependency_files(repo: Path, deps: Path) -> dict:
    deps.mkdir(parents=True, exist_ok=True)
    if (repo / "uv.lock").is_file():
        out = subprocess.run(["uv", "export", "--frozen", "--no-emit-project", "--format", "requirements-txt"],
                             cwd=repo, capture_output=True, text=True, encoding="utf-8", check=False)
        if out.returncode == 0:  # workspace members come out as `-e ./member`: not in the image yet
            kept = [line for line in out.stdout.splitlines() if not LOCAL_LINE.match(line)]
            (deps / "all.txt").write_text("\n".join(kept) + "\n", encoding="utf-8")
            return {"source": "uv.lock", "editable": False}
    if (repo / "Pipfile.lock").is_file():
        data = json.loads((repo / "Pipfile.lock").read_text(encoding="utf-8"))
        lines = [f"{name}{meta['version']}" for section in ("default", "develop")
                 for name, meta in data.get(section, {}).items() if isinstance(meta, dict) and meta.get("version")]
        (deps / "all.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {"source": "Pipfile.lock"}
    files = sorted(repo.glob("requirements*.txt")) + sorted((repo / "requirements").glob("*.txt"))
    if files:
        for f in files:  # keep relative paths, so `-r other.txt` inside them still resolves
            rel = f.relative_to(repo)
            (deps / rel).parent.mkdir(parents=True, exist_ok=True)
            kept = [line for line in f.read_text(encoding="utf-8", errors="replace").splitlines()
                    if not LOCAL_LINE.match(line)]
            (deps / rel).write_text("\n".join(kept) + "\n", encoding="utf-8")
        top = [f for f in files if f.parent == repo] or files
        (deps / "all.txt").write_text("".join(f"-r {f.relative_to(repo).as_posix()}\n" for f in top), encoding="utf-8")
        return {"source": ", ".join(f.relative_to(repo).as_posix() for f in files)}
    (deps / "all.txt").write_text("", encoding="utf-8")
    if (repo / "pyproject.toml").is_file() or (repo / "setup.py").is_file():
        return {"source": "the project's own metadata"}
    return {"source": "none"}


# --------------------------------------------------------------------------- image


def _classify_build(log: str) -> FolderError:
    if re.search(r"No module named '(imp|distutils|asynchat|asyncore|smtpd)'", log):
        return FolderError("OLD_PACKAGES")
    if "ResolutionImpossible" in log or "conflicting dependencies" in log:
        return FolderError("DEPENDENCY_CONFLICT")
    if re.search(r"\b(401|403)\b", log) and re.search(r"index-url|Unauthorized|Forbidden", log, re.IGNORECASE):
        return FolderError("PRIVATE_INDEX")
    native = next((k for k in NATIVE if k in log), None)
    if native:
        return FolderError("NATIVE_PACKAGE", native)
    return FolderError("BUILD_FAILED")


def _build(context: Path, tag: str, log: Path, args: dict) -> None:
    from aeropatch.config import BASE_IMAGE

    if not sandbox.image_exists(BASE_IMAGE):
        sandbox.build_base(config.RUNS_DIR / "builds" / "base.log")
    cmd = sandbox._build_cmd(config.DOCKER_DIR / "folder.Dockerfile", context, tag, {"BASE": BASE_IMAGE, **args})
    try:
        sandbox._run_build(cmd, log)
    except RuntimeError:
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        apt = " ".join(dict.fromkeys(NATIVE[k] for k in NATIVE if k in text))
        if not apt or args.get("APT"):
            raise _classify_build(text) from None
        _build(context, tag, log, {**args, "APT": apt})  # one retry with the native packages


def image_tag(folder: Path) -> str:
    return f"aeropatch-folder:{run_dir(folder).name.lower()}"


def _outcomes(logs: str) -> dict[str, str]:
    sec = sandbox.split_sections(logs).get("OUTCOMES", "")
    out = {}
    for line in sec.splitlines():
        outcome, _, nodeid = line.partition("\t")
        if nodeid:
            out[nodeid] = "failed" if out.get(nodeid) == "failed" else outcome
    return out


def _baseline_failure(logs: str) -> FolderError | None:
    s = sandbox.split_sections(logs)
    rc = s.get("RC-regression", "").strip()
    log = s.get("LOG-regression", "")
    if rc == "124":
        return FolderError("TOO_SLOW")
    if re.search(r"Connection refused|could not connect to server", log) and re.search(r"5432|3306|6379|27017", log):
        return FolderError("NEEDS_SERVICE")
    if re.search(r"KeyError: '[A-Z_]+'|ImproperlyConfigured", log):
        return FolderError("NEEDS_SETTINGS")
    missing = sorted(set(re.findall(r"ModuleNotFoundError: No module named '([\w.]+)'", log)))
    if missing:  # buku's tests need hypothesis and flask, listed only in tox.ini (2026-10-27)
        return FolderError("MISSING_TEST_PACKAGES", ", ".join(m.split(".")[0] for m in missing[:5]))
    if rc == "5":
        return FolderError("NO_TESTS")
    return None


def prepare(folder: Path, extra: dict[str, Path] | None = None, rebuild: bool = False) -> Prepared:
    """Stage, build the image, run the user's tests twice on the pristine code, and bake the tests
    that passed both times into the image. `extra` adds files under /opt/scenario (the scenario
    check's hidden PoC suite). Raises FolderError with a plain message."""
    folder = Path(folder).resolve()
    if not sandbox_available():
        raise FolderError("NO_DOCKER")
    base = run_dir(folder)
    ctx = base / "context"
    tag = image_tag(folder)
    state = base / "prepared.json"
    if not rebuild and state.is_file() and sandbox.image_exists(tag):
        data = json.loads(state.read_text(encoding="utf-8"))
        if data.get("source_hash") == _tree_hash(folder):
            return Prepared(**data["prepared"])
    if ctx.exists():
        shutil.rmtree(ctx)
    repo = stage(folder, ctx / "repo")
    python_check(repo)
    plan = dependency_plan(repo, ctx / "deps")
    (ctx / "extra").mkdir(parents=True, exist_ok=True)
    for name, src in (extra or {}).items():
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, ctx / "extra" / name)
    for f in ("folder_run.sh", "folder_runner.py"):
        shutil.copy2(config.DOCKER_DIR / f, ctx / f)
    args = {"EDITABLE": "1"} if plan["editable"] else {}
    _build(ctx, tag, base / "build.log", args)

    runs = []
    for i in range(2):  # doc 17 part 4 §3: baseline twice, before any edit
        with Workspace(repo) as ws:
            _, logs, timed_out, _ = sandbox.run_container(tag, None, ws.src)
        (base / f"baseline-{i + 1}.log").write_text(logs, encoding="utf-8")
        if timed_out:
            raise FolderError("TOO_SLOW")
        runs.append(logs)
    first, second = (_outcomes(x) for x in runs)
    passed = sorted(n for n in first if first[n] == "passed" and second.get(n) == "passed")
    flaky = sorted(n for n in set(first) | set(second) if first.get(n) != second.get(n))
    if not passed:
        err = _baseline_failure(runs[0])
        raise err or FolderError("NO_PASSING_TESTS")
    (ctx / "extra" / "pass_set.txt").write_text("\n".join(passed) + "\n", encoding="utf-8")
    _build(ctx, tag, base / "build.log", args)  # only the last layers change
    prepared = Prepared(image=tag, pass_set=passed, flaky=flaky,
                        note=f"dependencies from {plan['source']}; {len(passed)} tests passed twice"
                             + (f", {len(flaky)} changed between runs and are left out" if flaky else ""))
    state.write_text(json.dumps({"source_hash": _tree_hash(folder), "prepared": prepared.__dict__}, indent=2),
                     encoding="utf-8")
    return prepared


def _tree_hash(folder: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder)
        if p.is_file() and not any(_skip(part) for part in rel.parts):
            h.update(rel.as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def sandbox_available() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:  # noqa: BLE001 - any failure means no Docker
        return False


def prune_images() -> int:
    import docker

    client = docker.from_env()
    images = [i for i in client.images.list() if any(t.startswith("aeropatch-folder:") for t in i.tags)]
    for i in images:
        client.images.remove(i.id, force=True)
    return len(images)


# --------------------------------------------------------------------------- task


def discover_tests(repo: Path) -> list[str]:
    found = {p.relative_to(repo).as_posix() for g in TEST_GLOBS for p in repo.glob(g) if p.is_file()}
    return sorted(found)


def folder_task(repo: Path, finding: Finding, description: str, image: str = "", task_id: str = "") -> Task:
    """Doc 17 part 4 §1. `repo` is the staged copy; `task_id` may be a scenario ID (the oracle
    route then finds its reference fix)."""
    from aeropatch.tools.context import get_context

    ctx = get_context(repo, finding.path, finding.line)
    return Task(id=task_id or f"{repo.parent.parent.name}-{(finding.fingerprint or 'x')[:8]}", repo_path=repo,
                cwe=finding.cwe, finding=finding, description=description, allowed_paths=[finding.path],
                poc_tests=[], regression_tests=discover_tests(repo), image=image, target_function=ctx.target)


# --------------------------------------------------------------------------- fix, apply, undo


def fix(folder: Path, n: int, level: str = "auto", extra_rules: bool = False, cfg_name: str = "",
        on_event=None, think: bool = False, route: dict | None = None, history: list[dict] | None = None) -> dict:
    """Make a fix for shown card n of the check and keep it under runs/; the folder is not touched.
    level: "test" (needs Docker), "suggest" (no tests run) or "auto" (test when it can).
    For the `ui` page: `on_event` gets each step (loop.run), `think` picks the "-think" configs, and
    `route` (providers.route_cfg) sends one try to another model, continuing `history`."""
    from aeropatch.agent import loop, router

    emit = on_event or (lambda _kind, _data: None)
    folder = Path(folder).resolve()
    res = check.check_folder(folder, offline=True, extra_rules=extra_rules)
    if not 1 <= n <= len(res.shown):
        raise IndexError(f"the check shows {len(res.shown)} problems, so there is no number {n}")
    card = res.shown[n - 1]
    if card.kind == "secret":
        raise ValueError("a password or key is fixed by changing it at the provider; its card says how")
    try:
        (folder / card.finding.path).read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise FolderError("NOT_UTF8") from None
    base = run_dir(folder)
    notes, image = [], ""
    if level in ("auto", "test"):
        emit("prepare", {"state": "start", "text": "Getting the test sandbox ready. The first time for a project "
                         "this builds it and runs your tests twice, which can take several minutes."})
        try:
            prep = prepare(folder)
            image = prep.image
            notes.append(prep.note)
            emit("prepare", {"state": "done", "text": f"Sandbox ready: {prep.note}."})
        except FolderError as e:
            if level == "test":
                raise
            notes.append(str(e))
            emit("prepare", {"state": "suggest", "text": f"{e} So this is a suggestion: nothing of your project runs."})
    if not image:
        repo = stage(folder, base / "context" / "repo")
    else:
        repo = base / "context" / "repo"
    if route:
        cfg = config.load_config("handoff-test" if image else "handoff-suggest", **route)
    else:
        cfg = config.load_config(cfg_name or ("fix-local" if image else "suggest-local") + ("-think" if think else ""))
    task = folder_task(repo, card.finding, card.what_could_happen, image)
    out = base / "fixes" / str(n)
    if out.exists():
        shutil.rmtree(out)
    result = loop.run(task, cfg, out / "run", on_event=on_event, history=history)
    record = {"n": n, "finding": card.finding.to_dict(), "headline": card.headline, "config": cfg["name"],
              "model": router.model_name(cfg["attempt_plan"][0], cfg),
              "level": "test" if image else "suggest", "label": result.user_label, "diff": result.final_diff,
              "notes": notes, "files": {}, "time": datetime.now(UTC).isoformat()}
    offered = result.attempts[-1].proposal.edits if result.final_diff and result.attempts[-1].proposal else []
    return save_fix(folder, repo, out, record, offered)


def save_fix(folder: Path, repo: Path, out: Path, record: dict, edits: list) -> dict:
    """Keep each changed file as it will be after `apply`: the offered attempt's edits, applied to
    a fresh copy of the staged files exactly as the loop applied them. Not through the diff: git's
    text output drops the CR of CRLF lines. Workspace.write keeps each file's line ends, and a
    UTF-8 BOM stays the first character of the text."""
    from aeropatch.agent import edits as edit_engine

    if edits:
        with Workspace(repo) as ws:
            paths = sorted({e.path for e in edits})
            ws.write(edit_engine.apply_edits(ws.read_many(paths), edits))
            for rel in ws.changed_paths():
                after = (ws.repo / rel).read_bytes()
                (out / "after" / rel).parent.mkdir(parents=True, exist_ok=True)
                (out / "after" / rel).write_bytes(after)
                record["files"][rel] = {"before": _sha((folder / rel).read_bytes()), "after": _sha(after)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "fix.json").write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
    return record


def _fix_record(folder: Path, n: int) -> tuple[Path, dict]:
    d = run_dir(folder) / "fixes" / str(n)
    if not (d / "fix.json").is_file():
        raise FileNotFoundError(f"there is no fix for problem {n}; run `aeropatch fix` first")
    return d, json.loads((d / "fix.json").read_text(encoding="utf-8"))


def apply(folder: Path, n: int) -> Path:
    """Write fix n into the folder, after backing up each file it changes. Refuses when a file
    changed since the fix was made. Returns the backup folder."""
    folder = Path(folder).resolve()
    d, rec = _fix_record(folder, n)
    if not rec["files"]:
        raise ValueError("this fix changes nothing (the warning was not fixed)")
    for rel, h in rec["files"].items():
        if _sha((folder / rel).read_bytes()) != h["before"]:
            raise ValueError(f"{rel} changed since the fix was made; run `aeropatch fix` again")
    backup = run_dir(folder) / "backups" / f"{n}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}"
    manifest = []
    for rel, h in rec["files"].items():
        target = folder / PurePosixPath(rel)
        (backup / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup / rel)
        manifest.append({"path": rel, **h})
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for rel in rec["files"]:
        (folder / PurePosixPath(rel)).write_bytes((d / "after" / rel).read_bytes())
    return backup


def undo(folder: Path, n: int) -> Path:
    """Put back the files of the last `apply` of fix n, only if they are still as applied.
    Otherwise change nothing and say where the backup is."""
    folder = Path(folder).resolve()
    backups = [b for b in sorted((run_dir(folder) / "backups").glob(f"{n}-*")) if not (b / "undone.txt").exists()]
    if not backups:
        raise FileNotFoundError(f"fix {n} is not applied, so there is nothing to undo")
    backup = backups[-1]
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    changed = [m["path"] for m in manifest if _sha((folder / m["path"]).read_bytes()) != m["after"]]
    if changed:
        raise ValueError(f"{', '.join(changed)} changed after the fix was applied, so nothing was undone. "
                         f"The original files are in {backup}")
    for m in manifest:
        (folder / PurePosixPath(m["path"])).write_bytes((backup / m["path"]).read_bytes())
    (backup / "undone.txt").write_text(datetime.now(UTC).isoformat() + "\n", encoding="utf-8")
    return backup


# --------------------------------------------------------------------------- the benchmark through the folder path


def scenario_folder(sid: str) -> Path:
    """Doc 17 part 4 §5, criterion 1: a test scenario laid out as a user's folder. Its regression
    tests become tests/, its lock file becomes requirements.txt; the PoC goes into the image only."""
    from aeropatch import scenario

    d = scenario.scenario_dir(sid)
    dest = config.RUNS_DIR / "scenario-folders" / sid
    if not dest.exists():
        shutil.copytree(d / "repo", dest)
        shutil.copytree(d / "tests_regression", dest / "tests")
        shutil.copy2(d / "requirements.lock", dest / "requirements.txt")
    return dest


def scenario_task(sid: str) -> Task:
    """The scenario's own Task (description, allowed paths, imports), run through the folder path:
    staged copy, folder image, baseline pass set, PoC hidden in the image."""
    import dataclasses

    from aeropatch import scenario

    task = scenario.load(sid)
    folder = scenario_folder(sid)
    prep = prepare(folder, extra={"tests_poc": scenario.scenario_dir(sid) / "tests_poc"})
    repo = run_dir(folder) / "context" / "repo"
    return dataclasses.replace(task, repo_path=repo, image=prep.image, regression_tests=discover_tests(repo))
