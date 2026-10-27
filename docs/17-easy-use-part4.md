# 17 — Easy Use for Non-Experts, Part 4: Phase 1b, Fix a Folder

Back to [Part 1](17-easy-use-part1.md) · Phase 0: [Part 2](17-easy-use-part2.md) · Phase 1a:
[Part 3](17-easy-use-part3.md) · index: [00-overall-plan.md](00-overall-plan.md)

1b adds `fix`, `apply` and `undo` (commands in [Part 3 §1](17-easy-use-part3.md#1-commands)). It
needs Phase 0's loop changes: the visible label, the re-scan of one finding, `run_tests`, and the
`scenario_dir` guard ([Part 2 §2](17-easy-use-part2.md#2-code-changes-small-in-order)). Estimate: ~5 days.

## 1. A Task from a finding

New `folder_task(folder, finding)` beside `scenario.load` ([scenario.py:35](../src/aeropatch/scenario.py#L35)), ~30 lines:

| Task field | From |
|---|---|
| `id` | `<folder name>-<fingerprint[:8]>`, from the fingerprint `scanners.py` already computes. The scenario ID can be passed instead, for §5's ground-truth check |
| `repo_path` | the folder |
| `cwe`, `finding` | the scanner finding (Opengrep rule metadata or Bandit `issue_cwe`) |
| `description` | the card's "what could happen" text ([Part 3 §2](17-easy-use-part3.md#2-triage-and-cards)), never model-written |
| `allowed_paths` | `[finding.path]` |
| `poc_tests` | `[]` (Phase 3 fills it) |
| `regression_tests` | the discovered test files |
| `image` | the folder image tag (§2) |
| `target_function` | the enclosing function from `get_context` (tree-sitter) |
| `baseline_pass` (new field) | test IDs that passed both baseline runs (§3) |

Two product configs:
- `fix-local`: `repair-local` with `hidden_suites: ["poc"]` and `rescan_feedback: True`. This is the
  V1 loop, so V1's precision is the precision users get.
- `suggest-local`: the same with `run_tests: False`. This is the V2 loop without a sandbox.

Neither config adds anything else. On the benchmark, every regression test passes on the vulnerable
code (validator check 1, [scenario.py:121](../src/aeropatch/scenario.py#L121)), so "the baseline pass
set still passes" and "the regression suite passes" are the same rule there. That is why V1 carries
over to folders.

The only finding type that skips the model is secrets ([Part 3 §3](17-easy-use-part3.md#3-secrets-card-no-model-call)).

Fixes may use only the standard library and packages the project already installs. Dependency files
are forbidden paths ([config.py:21-25](../src/aeropatch/config.py#L21-L25)), so a fix that needs
`defusedxml` or `argon2` ends as "Not fixed", and its card names the package to add by hand.

## 2. The folder sandbox image

Deterministic only; no model in the setup path. The evidence on small models planning installs is
poor ([Part 1 §7](17-easy-use-part1.md#7-deliberately-deferred)). One new `docker/folder.Dockerfile`,
built from a staged copy, never from the folder itself.

1. **Stage the folder** into `runs/folders/<id>/context/`.
   - Leave out `.git`, `.venv`, `venv`, `env`, `node_modules`, `__pycache__`, `.tox`, `.mypy_cache`,
     `.pytest_cache`, `dist`, `build`, `*.egg-info` and `.env*`.
   - Add the same list to the Workspace ignore patterns ([git_ops.py:29](../src/aeropatch/tools/git_ops.py#L29)),
     which also keeps the 512 MB tmpfs from overflowing.
   - Keep the paths short, to stay under Windows' 260-character limit.
2. **Python version.** The base image is Python 3.12 ([sandbox-base.Dockerfile](../docker/sandbox-base.Dockerfile)).
   Read `.python-version`, then `requires-python`, then `runtime.txt`. If 3.12 is excluded, stop with
   the PYTHON_VERSION message (§4). Other versions need a base image each, deferred.
3. **Dependencies, first match wins:**
   1. `uv.lock`: `uv export --frozen --no-emit-project --format requirements-txt` on the host, with
      hashes, so pip checks them.
   2. `Pipfile.lock`: convert to `name==version` lines with stdlib JSON, ~10 lines.
   3. Every `requirements*.txt` and `requirements/*.txt`.
   4. Otherwise `pip install -e .[test]`, falling back to `pip install -e .`.

   No guessing from imports: pipreqs built only 6% of repos in Repo2Run.
4. **Native packages.** On a build error, retry once with apt packages from a small table:
   - `pg_config` → `libpq-dev gcc`
   - `mysql_config` → `default-libmysqlclient-dev gcc pkg-config`
   - `libxml/xmlversion.h` → `libxml2-dev libxslt1-dev`

   The table grows only from Phase 1's failure log.
5. **Layers.** Dependencies first, tagged `aeropatch-folder:<hash of dependency files>`. Then the
   pristine project, copied read-only to `/opt/scenario/repo`, so an edit to the code rebuilds only the
   last layer. The `pip install -e .` route needs the code, so it installs after the copy and rebuilds
   each time. The build is the only step with network. It runs the project's own build code, so it gets
   no host mounts and no secrets, as the scenario build does today.
6. **Cleanup.** `aeropatch prune --images` removes folder images (each about 1-1.5 GB).

Build before loading the model, one at a time, given the laptop's memory history.

## 3. Running the user's tests

`run.sh` gets a folder mode, used when `/opt/scenario/tests_regression` is absent:

- **Pristine tests.** Copy `/src/repo` to `/work/repo`, then copy the pristine tests and test settings
  back over it from `/opt/scenario/repo` (`tests/**`, `test_*.py`, `*_test.py`, `conftest.py`,
  `pyproject.toml`, `setup.cfg`, `pytest.ini`, `tox.ini`). The gates already forbid editing them; this
  makes sure the tests that run are the user's own, unchanged.
- **Run pytest** from `/work/repo` with the project's own config and plugin autoload **on**, since the
  plugins came from the project's dependencies.
  - Keep `python -I`, `--timeout=30`, `timeout 240` and the JUnit output.
  - Drop the explicit `-p pytest_timeout`, which autoload already loads, and check it is not registered
    twice.
  - Run `/opt/scenario/tests_poc` whenever it exists: §5's baked PoC (hidden by `fix-local`) or
    Phase 3's witness test (shown by `fix-local-witness`). Otherwise emit no PoC section, which the
    hidden `poc` suite ignores.
- **pytest version.** A project that pins its own pytest may replace the harness's 8.4.2 while
  installing, so the JUnit parsing must also work with pytest 7.

**Baseline, twice, before any edit.**
- Tests that pass in both runs form the pass-to-pass set. Tests whose result changes are dropped as
  flaky and counted on the card.
- `junit.parse` returns passing test IDs as well as failures.
- "Your tests still pass" then means the pass-to-pass set still passes, not exit code 0.
- pytest exit 5 means no tests, so the label can be at most "Scanner quiet, not tested". With no tests,
  add `python -m compileall` plus an import of each changed module as a smoke check.

## 4. Apply, undo, and plain error messages

**Apply.** `apply` refuses if the file's hash differs from the one at `check` time ("this file changed
since the check; run check again"). It copies the original into the backup folder with a manifest
(path, before and after hashes), then writes. The scratch copy works in LF without a BOM
([git_ops.py:50](../src/aeropatch/tools/git_ops.py#L50), [git_ops.py:65](../src/aeropatch/tools/git_ops.py#L65)),
so `apply` restores the original file's line endings (CRLF is common on Windows) and any UTF-8 BOM.
Otherwise every line would change.

**Undo.** `undo` restores only if the file still has the after-hash. Otherwise it says where the backup
is and changes nothing.

| Class | Detected by | The user reads |
|---|---|---|
| PYTHON_VERSION | §2 step 2 | "This project needs Python X. AeroPatch's test sandbox has 3.12, so it can only scan and suggest." |
| NATIVE_PACKAGE | build log after the apt retry | "Package Y needs extra system software AeroPatch could not install. Scanning still works." |
| DEPENDENCY_CONFLICT | `ResolutionImpossible` | "Your requirements contradict each other (A needs B<2, C needs B>=2)." |
| PRIVATE_INDEX | `--index-url` lines, 401/403 | "Some packages come from a private server; AeroPatch does not send passwords into the sandbox." |
| NO_TESTS | pytest exit 5 | "No tests found, so AeroPatch can check the warning but not your app's behaviour." |
| NEEDS_SERVICE | connection refused on 5432, 3306, 6379 | "Your tests need a database server; the sandbox has none." |
| NEEDS_SETTINGS | `KeyError` on `os.environ`, Django `ImproperlyConfigured` | "Your tests need settings that are in your environment, not the code." |
| TOO_SLOW, TOO_BIG | timeout 240 s; "No space left on device"; staged copy over 400 MB | Plain sentence plus what still worked |
| NOT_UTF8 | the finding's file fails to decode as UTF-8 | "This file is not saved as UTF-8, so AeroPatch will not edit it. The warning still stands." |

Every failure leaves the lower levels working: the user still gets the cards, and a suggestion when
Ollama is there.

## 5. Exit criteria (all must hold)

1. **Same results on known ground.** Copy each test scenario as a folder:
   - its `tests_regression/` becomes `tests/`;
   - its `tests_poc/` is baked into the folder image's PoC slot as a hidden suite, so truth is still
     recorded;
   - the Task keeps the scenario ID, so the oracle route finds its reference fix.

   Then the oracle replay gets the same label through both paths on 27 of 27, and `fix-local` resolves
   within 4 of 54 of V1, with the two alternated on the same day.
2. **Real projects, setup.** On 1a's 10 repos, the build-and-collect rate and the failure classes are
   published.
3. **Undo integrity.** In every scripted case, `undo` restores byte-identical files, including CRLF and
   BOM files, and nothing is written before `apply`.
4. **Suggest level.** `suggest-local` runs with Docker stopped and never starts a container.
5. **Review test, 6 people.**
   - Two groups of three: people who build with AI tools, and students.
   - A 45-minute think-aloud on the HTML page ([Part 3 §1](17-easy-use-part3.md#1-commands)). The
     outputs are replayed from a recording, so no model runs on their machine.
   - The material is a small Flask app written fresh for the test and kept out of the benchmark. It
     contains a good fix, a plausible-but-wrong fix that quiets the scanner but breaks a feature, a
     "not fixed" case and the secrets card.
   - Pass: at least 5 reject the wrong fix, 5 choose to apply the good one, and 5 restate a risk in one
     sentence. Also record confidence against correctness.
   - The page is read-only, so whether participants can undo is tested on the Phase 2 page.
