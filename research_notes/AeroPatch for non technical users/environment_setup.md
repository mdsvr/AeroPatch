# Automatic environment setup and test running for an arbitrary Python repo in a Docker sandbox

Notes as of 2026-10-22. Sources are arXiv HTML versions and official docs read on that date unless marked "(search snippet only)". Every success rate below is tagged with its **criterion** and **sample size**, because the papers measure very different things. "Pytest collects" (Repo2Run) is not comparable to "Pyright finds no missing imports on hand-picked hard repos" (EnvBench) or "the fail-to-pass test flips" (SWE-Factory, Multi-Docker-Eval).

## 1. What do 2024-2026 research systems and benchmarks report about automatic environment setup?

### Takeaway
Success rates split sharply by benchmark type:
- **Popular repos that already have tests, graded by build / collect / most-tests-pass:** about 55-96%. Repo2Run reaches 86% (pytest runs) and RepoLaunch 81% (most tests pass). BootstrapAgent's 95.9% is graded against its own self-generated "minimal verify", a lower bar than "most tests pass".
- **Repos chosen for difficulty, or graded by fail-to-pass:** about 7-54%. EnvBench's best method got 6.69%, and even GPT-5 got only 43/329 at pass@5. SWE-rebench found a recipe for 31% of repos, Multi-Docker-Eval topped out at 37.7%, and SWE-Factory reached about 54% on Python.

Agents that combine evidence gathering, an execute-observe-repair loop, verification in a clean container and reuse of past setups do best (BootstrapAgent 95.9% on Repo2Run's 122-repo Python subset, May 2026). Small models are weak as planners: Qwen3-8B single-shot configured 8 of 329 EnvBench repos against GPT-4o's 29. No published numbers exist for 4B-class models.

### Cited Findings
**Python-focused agents and benchmarks (oldest first)**
- **ExecutionAgent** (ISSTA 2025, arXiv Dec 2024): ran the test suites of 33 of 50 projects (66%) across 14 languages. Its results deviate from ground-truth test runs by 7.5%, a 6.6x gain over the previous best technique. Average cost was 74 minutes and USD 0.16 of LLM spend per project — [arXiv 2412.10133](https://arxiv.org/abs/2412.10133v2) (search snippet only; the v1 abstract says "33/55", which looks like a typo).
- **Installamatic / "Beyond pip install"** (KAIST, Dec 2024): a benchmark of 40 Python repos with ground-truth installs. The agent reads the project's own docs and installed 55% of repos at least once in 10 attempts — [arXiv 2412.06294](https://arxiv.org/html/2412.06294v1) (search snippet only).
- **Repo2Run** (arXiv Feb 2025, NeurIPS 2025): built 361 of 420 Python repos (86.0%). The repos were created in 2024, have more than 100 stars and have unit tests. **Criterion:** the synthesized Dockerfile builds and pytest runs in it; whether tests pass is not counted. Model was gpt-4o-2024-05-13 at temperature 0.2. Baselines: pipreqs 6.0%, a one-shot LLM Dockerfile generator 22.1%, SWE-agent 9.0% — [Repo2Run](https://arxiv.org/html/2502.13681v3).
- Repo2Run's design: the default base image is python:3.10, and the agent may switch images. A dual environment separates an inner container for installs and tests from an outer terminal. The agent takes a `docker commit` snapshot before each command and rolls back on failure. pip and apt installs go through a waiting list and a conflict list, and pipdeptree inspects dependencies. A synthesizer turns the successful command sequence into a Dockerfile with pinned versions — [Repo2Run](https://arxiv.org/html/2502.13681v3).
- **EnvBench** (JetBrains, ICLR 2025 DL4Code workshop): 329 Python and 665 JVM repos, deliberately chosen to be hard. **Criterion for Python:** the setup script exits 0 and Pyright reports zero `reportMissingImports` errors; tests are not run. The best method configured 6.69% of Python repos (GPT-4o / GPT-4o-mini, zero-shot plus two agentic workflows) — [EnvBench](https://arxiv.org/html/2503.14443).
- **SetupBench** (arXiv Jul 2025, repo microsoft/SetupBench): 93 tasks that start from a bare Linux sandbox. OpenHands scored 38.9-57.4% on repo setup and 20.0-53.3% on local database configuration. 38-89% of its actions were unnecessary compared with optimal human behavior — [arXiv 2507.09063](https://arxiv.org/abs/2507.09063v1) (search snippet only).
- **SWE-rebench** (Nebius, May 2025, v2 Nov 2025): Qwen2.5-72B-Instruct writes up to 3 JSON "recipes" per task from up to 10 selected files (README, setup.py, requirements.txt). Each recipe holds the Python version, install command, test command, pre-install steps and pip packages, and the model refines it from the error logs. **Criterion:** fail-to-pass and pass-to-pass validation. A working recipe was found for at least one task in **31% of repositories**. On an 18-task SWE-bench check, the agentless approach configured 6/18 with 1 candidate, 8/18 with 3 and 9/18 with 10, and an interactive agent configured 8/18 — [SWE-rebench](https://arxiv.org/html/2505.20411).
- **SWE-smith** (SWE-bench team, Apr 2025, NeurIPS 2025): SWE-agent with claude-3-5-sonnet-20241022 installs each repo at its latest commit (at most 100 steps), averaging about 17 steps, about $0.72 and usually under 2 minutes. A human then reviews the trajectory (3-20 minutes) and extracts the install steps (about 7 minutes). The repo is kept only if more than 80% of existing tests pass. The author gave up on 17 repos during review and kept 128, for about 18 human hours and about $160 of LLM cost — [SWE-smith](https://arxiv.org/html/2504.21798).
- **SWE-Factory / SWE-Builder** (arXiv Jun 2025, v3 Jan 2026): a multi-agent system with repair loops and a memory pool of past Dockerfiles and test scripts. **Criterion:** the fail-to-pass test flips after the gold patch, manually verified. On 198 Python issues: GPT-4.1-mini 54.0%, Kimi-K2 54.0%, DeepSeek-V3-0324 54.5%. Overall on 671 issues: 42.0-50.2% — [SWE-Factory](https://arxiv.org/html/2506.10954).
- **PIPer** (JetBrains, Sep 2025): single-turn, zero-shot generation of a setup script, scored as pass@5 successes.

  | Model | EnvBench-Python (329 repos; script exits 0 and Pyright finds no missing imports) | Repo2Run (420 repos; script exits 0 and pytest collects without error) |
  |---|---|---|
  | GPT-5 | 43 | 106 |
  | GPT-4o | 29 | 67 |
  | GPT-4o-mini | 15 | 84 |
  | Qwen3-32B | 29 | 71 |
  | Qwen3-14B | 17 | 64 |
  | Qwen3-8B | 8 | 32 |
  | PIPer (Qwen3-8B after SFT and RL) | 27 | 103 |

  PIPer brings an 8B model to GPT-4o level — [PIPer](https://arxiv.org/html/2509.25455).
- **Multi-Docker-Eval** (Dec 2025): 334 issues from 40 repos in 9 languages. 20.06% of instances are "Easy" (they build with something like `pip install -r requirements.txt`). **Criterion:** fail-to-pass rate. The best overall score was 37.72% (DeepSeek-v3.1). On Python, SWE-Builder scored 47.86% with DeepSeek-v3.1, 49.57% with Kimi-K2-thinking, 41.88% with Claude-Sonnet-4, 15.38% with GPT-OSS-20B and 21.37% with Qwen3-235B-A22B. RepoLaunch averaged only 8.85% F2P here, against 30.58% for SWE-Builder. The paper finds that "model size and reasoning length are not decisive factors" — [Multi-Docker-Eval](https://arxiv.org/html/2512.06915).
- **HerAgent** (Feb 2026): uses a hierarchical "test pyramid" for verification and reports pass@k on a 122-repo Repo2Run subset — [arXiv 2602.07871](https://arxiv.org/pdf/2602.07871) (search snippet only). On that subset, HerAgent built 104 of 122 repos according to [BootstrapAgent](https://arxiv.org/html/2605.15815). A search snippet of HerAgent's own paper says Repo2Run succeeds on 109 of 122 under pass@5 and HerAgent on 110 under pass@3. **The two sources do not agree.**
- **EvoConfig** (Jan 2026): 88.1% on Repo2Run's 420-repo benchmark, against 86.0% for Repo2Run with GPT-4o — [arXiv 2601.16489](https://arxiv.org/pdf/2601.16489) (search snippet only).
- **BootstrapAgent** (May 2026): writes a reusable `.bootstrap` contract containing setup.sh, doctor.sh, verify.sh and repair notes. It runs five stages: discovery over README, metadata, lockfiles and CI workflows; evidence-linked planning; contract generation; verification in Docker (a warm loop, then a clean replay in a fresh container); and trace-driven minimal repair. **Criterion:** setup, doctor and minimal verify all pass in a fresh container. Results: Repo2Run Python subset 117/122 (95.9%), Installamatic 38/40 (95%), ExecutionAgent 42/50, using DeepSeek-V4-Flash. **Ablations:** without trace-driven repair, Repo2Run falls to 26.2% and Installamatic to 40%; without the discovery step, Repo2Run falls to 76.2% — [BootstrapAgent](https://arxiv.org/html/2605.15815).
- **EnvPilot** (Sep 2026): SWE-agent plus a memory of 667 problem/solution/action experiences distilled from Multi-SWE-bench trajectories. On AES-Bench (112 instances, 9 languages; the native test suite must run to completion), DeepSeek-V3 scored 75.0% against 62.5% without memory. GPT-4o-mini scored 46.4%. On the 12 Python instances, EnvPilot and Repo2Run both scored 8/12 with DeepSeek-V3, and Repo2Run scored 3/12 with GPT-4o-mini. Cost was about $0.034-0.063 per task — [EnvPilot](https://arxiv.org/html/2609.07357).
- **RepoLaunch** (the pipeline behind SWE-bench-Live; v3 dated 3 Oct 2026): a Preparation agent picks the base image; a Setup agent works with bash and web search; a Verify agent checks for hallucinated success; an Organize agent writes minimal rebuild commands, the test command and a per-test log parser. **Criterion:** most tests pass. Python build success was 81.0% (34/42), against 59.5% (25/42) for Repo2Run under the same stricter rule. An older version built 76.2% (528/693) of SWE-bench-Live Python instances. Success by backbone: Claude-Sonnet-5 90.8%, DeepSeek-v4-Pro 84.9%, GPT-5-medium 79.6% (all languages, n=152). Cost was about $0.66 per Python instance — [RepoLaunch](https://arxiv.org/html/2603.05026).
- **Deployment-oriented benchmarks** (DeployBench Jun 2026, FDE-Bench Sep 2026) also appeared. FDE-Bench has 136 Docker, Compose and Kubernetes tasks, and its best model resolves 75.0% — [FDE-Bench](https://arxiv.org/html/2609.27571v1) (search snippet only).

### Inferences
- **The "deterministic first, LLM repair second" design is supported by the data.** Every top system (BootstrapAgent, RepoLaunch, SWE-Factory) puts verification and repair loops around evidence it gathers from config files. Repair is the single biggest factor: removing it drops BootstrapAgent from 95.9% to 26.2%.
- **For a local 4B model, use it as a log-reading repairer under strict guardrails, not as the planner.** The closest data is single-turn and 8B, so this is an inference. At single-turn pass@5, Qwen3-8B succeeded on 2.4% of EnvBench (8/329) and 7.6% of Repo2Run (32/420), while GPT-4o got 29 and 67. Its EnvBench avg@5 is 2.6 successes, under 1%.
- **The two RepoLaunch figures are not comparable, not contradictory.**
  - 81% is build success with most tests passing, from v3 with GPT-5 on 42 Python repos.
  - 8.85% is the fail-to-pass rate on Multi-Docker-Eval issue instances, likely with an earlier RepoLaunch version and other models. RL fine-tuning, as in PIPer, closes that gap but is a training project of its own.
- **Reuse is cheap and effective.** SWE-Factory's memory pool adds about 5.2 points, EnvPilot's memory adds 12.5 points and BootstrapAgent's contract cuts build time by 22.3%. AeroPatch should persist a per-repo "recipe" (Python version, install commands, test command, flaky list) after the first success.
- **AeroPatch needs a "verify, don't trust" step.** Multi-Docker-Eval shows models over-committing: Claude-Sonnet-4 declared success on 47.41% of runs but achieved 35.53% F2P. Silent false passes accounted for 12.70% of failures. RepoLaunch added a separate Verify agent for the same reason.

### Gaps
- No published results for Qwen3.5-4B (or any 4B model) on any environment-setup benchmark, agentic or single-turn.
- I did not read SWE-Gym's or Multi-SWE-bench's environment-construction details. Both are believed to rely mainly on manual or semi-manual setup; this is unverified in this pass.
- Results are not directly comparable across papers (different criteria, repo selection, pass@k). No head-to-head on a "typical small user project" exists.
- The ExecutionAgent, Installamatic, SetupBench, HerAgent, EvoConfig and FDE-Bench numbers come from search snippets or abstracts; I did not read the full texts.

## 2. Which deterministic tools and heuristics exist, and which order of attempts gives the best coverage cheaply?

### Takeaway
On benchmarks built to be hard, deterministic scripts alone cover about 6-20% of repos. They are still the right first step because they cost seconds, not LLM calls, and they collect the evidence the repair loop needs. uv covers Python-version selection (`.python-version`, then `requires-python`), lockfile installs and fast cached installs. Railpack and repo2docker publish a precedence order of config files to copy.

### Cited Findings
- **Deterministic coverage, per benchmark:**
  - EnvBench's deterministic script detects Conda, uv or Poetry, creates a venv and installs from requirements.txt, setup.py, pyproject.toml, setup.cfg or Pipfile. It configured **62 of 391 candidate Python repos (15.9%)**, which were then excluded from the benchmark. The paper's 329 final count does not quite reconcile with 391 - 62 - 3 = 326 — [EnvBench](https://arxiv.org/html/2503.14443).
  - pipreqs (inferring requirements from imports) alone: **6.0%** on Repo2Run's 420 repos — [Repo2Run](https://arxiv.org/html/2502.13681v3).
  - Multi-Docker-Eval: **20.06%** of instances build with simple commands such as `pip install -r requirements.txt` — [Multi-Docker-Eval](https://arxiv.org/html/2512.06915).
- **EnvBench's base image** (a good model for a "fat" setup image): ubuntu:22.04 with pyenv (Python 3.8-3.13), Poetry, uv, pyright, pipenv and conda/miniconda preinstalled — [EnvBench](https://arxiv.org/html/2503.14443).
- **uv's Python-version discovery:**
  - `--python` is an explicit override.
  - uv looks for `.python-version` in the working directory and its parents. A `.python-versions` file can list several versions.
  - uv respects `requires-python` from pyproject.toml; "The first Python version that is compatible with the requirement will be used, unless a version is otherwise requested."
  - Managed versions are preferred newest-first; for system installs, uv takes the first compatible one.
  - uv downloads python-build-standalone CPython builds automatically, but the list of available versions is frozen per uv release — [uv Python versions](https://docs.astral.sh/uv/concepts/python-versions/).
- **Railpack's Python-version priority:** `RAILPACK_PYTHON_VERSION`, then `.python-version` / `.tool-versions` / `mise.toml`, then `runtime.txt`, then `Pipfile`, then a default of 3.13.2. Only non-EOL Python 3.10+ is supported, and `requires-python` is not mentioned. Railpack detects Python from `requirements.txt`, `pyproject.toml`, `Pipfile` or root `main.py` / `app.py` etc., and supports pip, poetry, pdm, uv and pipenv through their lockfiles. It also maps common packages to apt packages: pycairo to libcairo2-dev, PostgreSQL drivers to libpq-dev / libpq5, MySQL to default-libmysqlclient-dev, pydub to ffmpeg, pdf2image to poppler-utils — [Railpack Python](https://railpack.com/languages/python).
- **repo2docker's config files, "roughly in the order of build priority":** environment.yml, install.R, DESCRIPTION, Project.toml; then Pipfile / Pipfile.lock, requirements.txt, pyproject.toml, setup.py; system-wide: apt.txt, runtime.txt, default.nix, Dockerfile; post-build: postBuild, start — [repo2docker config](https://repo2docker.readthedocs.io/en/latest/configuration/index.html).
- **The recipe SWE-rebench's LLM produces:** Python version (it chose 3.9 as a "safe middle-ground" from a supported 3.6-3.10 range), `pip install -e .[dev]`, and a pytest test command. Environments are grouped and reused by `git tag` major.minor version, which covers about 95% of tasks — [SWE-rebench](https://arxiv.org/html/2505.20411).
- **uv lockfile installs:** `uv sync --locked` asserts the lockfile is current; `uv sync --frozen --no-install-project` installs dependencies only. `UV_NO_DEV=1` drops dev dependencies, so a test sandbox should **not** set it — [uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/).

### Inferences
**Proposed attempt order for AeroPatch** (cheap first; each step is a candidate install script, and the first one that passes the health check in Q3 wins):

1. **Pick the Python version.** Check `.python-version`, then `requires-python` (let uv choose the first compatible version), then `runtime.txt`, then `Pipfile` `python_version`, then classifiers in setup.py / setup.cfg (unsourced heuristic). Default to 3.12, or the newest version the base image has. Install it with `uv python install`. This order combines the uv and Railpack orders; Railpack's 3.10+ floor shows that old projects need an older interpreter, so keep 3.8/3.9 available, as EnvBench's image does.
2. **Install by lockfile, if present:**
   - `uv.lock` → `uv sync --locked` (dev groups included).
   - `poetry.lock` → `poetry install`.
   - `pdm.lock` → `pdm install`.
   - `Pipfile.lock` → `pipenv install --dev`.
   - `environment.yml` → conda/mamba (repo2docker ranks it first).
3. **Otherwise use requirements files:** `uv pip install -r` every `requirements*.txt` and `requirements/*.txt`, test or dev files included. The glob is a heuristic, not sourced.
4. **Then install the project itself:** `uv pip install -e ".[test,tests,dev]"`, falling back to plain `-e .` if those extras do not exist. The extras names are a heuristic; SWE-rebench's recipe uses `.[dev]`.
5. **Then the test runner:** `uv pip install pytest` if it is missing.
6. **Map native packages to apt packages first.** If the install fails on a native build, apply a Railpack-style table (libpq-dev, libcairo2-dev, ffmpeg and so on) before calling any LLM.
7. **Only then run the LLM repair loop.** Give the model the error log, the file tree, README / CONTRIBUTING / CI-workflow excerpts and the current script, and allow N rounds, as in SWE-rebench and BootstrapAgent. Restrict the model to editing the install script (pip / uv / apt / env lines) and log each delta.
8. **Last resort:** pipreqs, which alone covers only 6% of repos.
9. **Persist** the winning script as the repo's recipe.

### Gaps
- No source measures deterministic coverage on *ordinary* (not hand-picked-hard) user repos. EnvBench and Multi-Docker-Eval both select for difficulty, so 6-20% is a floor, not an estimate.
- I did not read the nixpacks docs (Railpack is its successor), or the tox/nox, PDM, Hatch or pip-tools docs, in this pass.
- No source compares "uv pip install" against "pip install" success rates on legacy setup.py projects.
- No sourced rule exists for reading Python-version classifiers from setup.py / setup.cfg.

## 3. How should a tool detect and run the test suite, and decide the baseline is healthy before applying a fix?

### Takeaway
Use pytest as the universal runner (it runs unittest suites too), with Django `manage.py test` as the main exception, and get per-test status from structured output. Call the baseline "healthy" only if tests are collected, most of them pass, and repeated runs agree. Exclude tests that flip between runs as flaky, and judge the fix by fail-to-pass plus pass-to-pass.

### Cited Findings
- **pytest runs unittest suites:** "pytest supports running Python unittest-based tests out of the box" and "will automatically collect unittest.TestCase subclasses and their test methods in test_*.py or *_test.py files". The load_tests protocol is not supported — [pytest unittest](https://docs.pytest.org/en/stable/how-to/unittest.html).
- **Django:** tests run via `./manage.py test`, which uses unittest discovery of `test*.py` files. A separate blank test database is created. With SQLite it is in-memory by default; with PostgreSQL the configured `USER` must be able to create databases and read the `postgres` database, so a server must be reachable — [Django testing](https://docs.djangoproject.com/en/stable/topics/testing/overview/).
- **pytest exit codes:**

  | Code | Meaning |
  |---|---|
  | 0 | All tests passed |
  | 1 | Some tests failed |
  | 2 | Interrupted |
  | 3 | Internal error |
  | 4 | Usage error |
  | 5 | **No tests were collected** |
  | 6 | Max warnings exceeded |

  [pytest exit codes](https://docs.pytest.org/en/stable/reference/exit-codes.html)
- **Health criteria used in practice:**
  - Repo2Run: pytest runs. PIPer's Repo2Run check: pytest collection without errors — [Repo2Run](https://arxiv.org/html/2502.13681v3), [PIPer](https://arxiv.org/html/2509.25455).
  - RepoLaunch: most tests pass, including core and integration tests — [RepoLaunch](https://arxiv.org/html/2603.05026).
  - SWE-smith: more than 80% of existing tests pass — [SWE-smith](https://arxiv.org/html/2504.21798).
- **Per-test status:** RepoLaunch's Organize agent "prefers test commands that produce structured output (e.g., JSON or XML)". It generates a parser that maps test names to pass, fail or skip, and its main management failures are "fail to parse test log" and "fail to print test status separately" — [RepoLaunch](https://arxiv.org/html/2603.05026).
- **Exit-code grading is simple and nearly as good:** SWE-Factory prints `rc=$?` behind a unique marker and treats 0 as pass. Against manual labels it reached F1 0.991 over 1,201 instances. Its 16 false negatives came from script bugs, such as a misspelled marker or `set -e` exiting early — [SWE-Factory](https://arxiv.org/html/2506.10954).
- **Flakiness:** SWE-rebench runs tests multiple times and excludes any instance that fails in at least one run. It also freezes dependency versions after setup, because unpinned dependencies otherwise rot — [SWE-rebench](https://arxiv.org/html/2505.20411).
- **The SWE-bench-style validation rule:** at least one test fails before the fix, those tests pass after it (FAIL_TO_PASS), and previously passing tests still pass (PASS_TO_PASS) — [SWE-rebench](https://arxiv.org/html/2505.20411), [RepoLaunch](https://arxiv.org/html/2603.05026).
- **Timeouts dominate test-phase failure:** SWE-smith caps test runtime at 2 minutes. In Repo2Run, 40.7% of failed repos failed on a test-run timeout — [SWE-smith](https://arxiv.org/html/2504.21798), [Repo2Run](https://arxiv.org/html/2502.13681v3).

### Inferences
**Proposed test detection and baseline procedure:**

1. **Pick the runner.**
   - If `manage.py` exists and Django is installed, use `python manage.py test`.
   - Otherwise use `python -m pytest -p no:cacheprovider -rA --junitxml=/out/base.xml`. pytest also covers unittest-only repos.
   - tox.ini / noxfile.py are hints for the right extras and the test command, not runners to invoke: tox/nox would try to create new venvs and reach the network. This is an unsourced inference.
2. **Collect first.** `pytest --collect-only -q` is a cheap health gate, matching the PIPer/Repo2Run criterion. Exit 5 means "no tests" (see Q6); exit 2, 3 or 4, or collection errors, mean the environment is broken, so feed the error to the repair loop.
3. **Run the baseline twice**, offline (`--network none`), with a per-run timeout, and record per-test status from JUnit XML. Tests that differ between runs are flaky; exclude them from verdicts. A third run is affordable when the suite is fast. This follows the SWE-rebench practice; the run count is a judgment call.
4. **Healthy if** collection succeeds and at least about 50% of non-flaky tests pass. RepoLaunch uses "more than half" and SWE-smith "more than 80%". Below that threshold, report "environment partially working" and still proceed, using only the passing tests as the PASS_TO_PASS set.
5. **After the fix,** require that every baseline-passing non-flaky test still passes and that the AeroPatch PoC/security test flips from fail to pass. Exit code alone is acceptable only as a fallback (SWE-Factory F1 0.991).

### Gaps
- Not read: tox/nox docs, pytest-rerunfailures, pytest-randomly, or any study measuring how many reruns catch most flaky Python tests.
- No source gives a recommended "healthy" pass threshold beyond the 50% and 80% choices above.

## 4. How do you safely build with network access for installs and then run untrusted code without network, and what Docker Desktop on Windows quirks matter?

### Takeaway
Build a dependency image with network, then run all project code, including tests, in a container started with `--network none`. Installing is itself code execution: setup.py and build backends run during `pip install`. So the install stage must be treated as untrusted too: no host mounts, no secrets left in layers, resource limits. On Windows, copy the repo into the build context or the WSL filesystem rather than bind-mounting from NTFS, force LF on shell scripts, and watch MAX_PATH.

### Cited Findings
- **`--network none`:** "Within the container, only the loopback device is created"; use `docker run --network none`. No IPv6 loopback is configured — [Docker none driver](https://docs.docker.com/engine/network/drivers/none/).
- **Per-step network control at build time:** `RUN --network=none` means "The command is run with no network access". `--network=host` needs the `network.host` entitlement — [Dockerfile reference](https://docs.docker.com/reference/dockerfile/).
- **Cache mounts:** `RUN --mount=type=cache,target=...` persists between builds without invalidating the instruction cache, and is "stored in the builder's local storage". Cache mounts are not included in exported build cache (`--cache-to`). `sharing=locked` serializes writers — [Dockerfile reference](https://docs.docker.com/reference/dockerfile/).
- **Secrets for private indexes:** `RUN --mount=type=secret` gives access "without baking them into the image". The secret is mounted at `/run/secrets/<id>` by default, or exposed as an env var — [Dockerfile reference](https://docs.docker.com/reference/dockerfile/).
- **Installs execute project code:** pip delegates sdist builds to "build backends". setuptools' backend "closely mimics directly executing `setup.py`", and building wheels may compile C/C++ extensions. Build isolation installs build-time dependencies into a temporary environment — [pip build system](https://pip.pypa.io/en/stable/reference/build-system/).
- **Offline install pattern:** `python -m pip download --destination-directory DIR -r requirements.txt`, then `python -m pip install --no-index --find-links=DIR -r requirements.txt`. `pip wheel --wheel-dir DIR` builds wheels for packages that publish only sdists — [pip user guide](https://pip.pypa.io/en/stable/user_guide/).
- **uv in Docker:**
  - Copy pinned binaries with `COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/`.
  - Install dependencies before copying the project: `uv sync --frozen --no-install-project` with the lockfile bind-mounted, then copy the project and `uv sync --locked`.
  - Set `UV_LINK_MODE=copy` with cache mounts, `UV_COMPILE_BYTECODE=1` optionally, and `UV_PYTHON_DOWNLOADS=0` to force the system Python.
  - Multi-stage: copy only `/app/.venv` into the final stage.

  [uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/)
- **Docker Desktop with the WSL2 backend:**
  - "Performance is much higher when files are bind-mounted from the Linux filesystem". Avoid `/mnt/c` mounts and keep source in the WSL home directory.
  - inotify works only for files on the Linux filesystem.
  - Limit the WSL VM's memory and CPU via `.wslconfig`. Older WSL versions let `vmmem.exe` eat all memory.
  - Minimum WSL 2.1.5; Enhanced Container Isolation needs WSL 2.6+.

  [Docker WSL best practices](https://docs.docker.com/desktop/features/wsl/best-practices/)
- **Line endings:** the `text` attribute normalizes files to LF in the index, and on checkout "may be converted from LF to CRLF depending on the eol attribute, the Git config, and the platform". The documented fix for scripts is `*.sh text eol=lf` in .gitattributes — [gitattributes](https://git-scm.com/docs/gitattributes).
- **Path length:** Windows MAX_PATH is 260 characters, and you "may hit this limitation if you are cloning a git repo that has long file names into a folder that itself has a long name". Lifting it needs the `LongPathsEnabled` registry value set to 1 **and** an app manifest that opts in, so not all tools benefit — [Microsoft MAX_PATH](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation).

### Inferences
**Proposed two-stage flow for AeroPatch:**

1. **Stage A, the deps image (network on).**
   - Build context is a temp copy of the repo. Clone or copy it inside the WSL filesystem or straight into the build context, never bind-mounted from NTFS.
   - Use a fixed base image with uv and several Python versions preinstalled, as in EnvBench.
   - `RUN --mount=type=cache,target=/root/.cache/uv` plus the install script from Q2.
   - Private-index tokens, if the user supplies any, go only via `--mount=type=secret` and never into ENV or ARG.
   - Run as a non-root user, with CPU, memory and time limits.
   - Tag the image `aeropatch-env:<repo-hash>-<lockfile-hash>`.
2. **Stage B, the test runs (network off).**
   - `docker run --network none` on the Stage A image, plus AeroPatch's existing hardening (read-only root, dropped capabilities, tmpfs for /tmp).
   - Copy in the current (baseline or patched) source and run the Q3 procedure.
   - No package installs are possible here, which is the point.
3. **If a fix adds a new dependency** (rare for security fixes, but version bumps happen), rebuild Stage A with the new constraint. Never open the network in Stage B.
4. **Treat Stage A as hostile:** it runs setup.py with internet access. Do not mount the host Docker socket or user directories into it. Consider `--network=none` on steps that need no network (for example the `-e .` install after a `pip download`). The download-then-`--no-index` pattern is only **partly** offline:
- The project's own build can run offline, but only if its `[build-system] requires` packages (setuptools, hatchling etc.) are also pre-downloaded into the find-links directory. Otherwise an isolated offline build fails.
- `pip download` "does the same resolution and downloading as `pip install`" and has build-isolation options for sdists ([pip download](https://pip.pypa.io/en/stable/cli/pip_download/)). So dependency sdists very likely still execute build code during the networked download step.
- `--only-binary :all:` avoids that, but it fails for packages without wheels.
5. **Windows hygiene:**
   - Normalize CRLF to LF on any generated shell script before COPY.
   - Keep the work dir short, e.g. a short root folder under F:\AeroPatch, to stay under MAX_PATH.
   - Cap the WSL VM's memory in `.wslconfig`, given the 16 GB laptop and Ollama running alongside.

### Gaps
- No source measured the bind-mount slowdown on NTFS in numbers for 2026 Docker Desktop.
- I found no first-party doc stating that `docker build` from a Windows path (context sent over the WSL boundary) is slow or fast; only bind mounts are covered.
- `core.autocrlf` defaults in Git for Windows and `git config core.longpaths` were not verified from a primary source in this pass.
- No source in this pass quantified how often setup.py-time network access or malicious install hooks occur in the wild.
- The pip docs read here do not state explicitly that `pip download` prepares metadata, and so runs build backends, for sdists. That it does is inferred from its "same resolution as pip install" wording and its build-isolation options.

## 5. What are common failure causes, and how do tools handle or report them?

### Takeaway
Most failures fall into a few groups:
- timeouts and hardware limits;
- toolchain and Python-version mismatches;
- missing system or native libraries;
- obsolete or unpinned dependencies;
- external services (databases);
- tokens and secrets;
- agents hallucinating success.

Good tools classify the failure, retry the fixable classes and report the rest plainly instead of pretending.

### Cited Findings
- **Repo2Run**, 59 failed repos:

  | Cause | Repos | Share |
  |---|---|---|
  | Test-run timeout | 24 | 40.7% |
  | Hardware insufficiency | 21 | 35.6% |
  | Dependency-install timeout | 8 | 13.5% |
  | Repository defects | 5 | 8.5% |
  | Missing token | 1 | 1.7% |

  [Repo2Run](https://arxiv.org/html/2502.13681v3)
- **EnvBench (Python):**
  - missing system dependencies;
  - Python version mismatch (the project needs an older or newer Python);
  - LLM scripts that call tools not installed;
  - agents repeating the same failing action;
  - even expert setups failing on obsolete dependencies and dynamic imports.

  [EnvBench](https://arxiv.org/html/2503.14443)
- **EnvPilot**, 25 failures in its best trial:

  | Cause | Share |
  |---|---|
  | Toolchain/runtime (version constraints, PATH and shell activation) | 60% |
  | Platform/system constraints (e.g. headless Chrome needing a no-sandbox flag) | 16% |
  | Native dependency (BLAS/ABI mismatch) | 16% |
  | Repo-config mismatch | 8% |

  [EnvPilot](https://arxiv.org/html/2609.07357)
- **Multi-Docker-Eval** (SWE-Builder failures): Docker build errors 36.09%, missing or non-executable test scripts 18.12%, silent false passes 12.70%; failures after a successful build were rare (2.63%). Peak memory was 7.4-7.7 GB — [Multi-Docker-Eval](https://arxiv.org/html/2512.06915).
- **RepoLaunch:** command timeout or OOM, failed regression tests, failed dependency resolution, repos "not ready for production", unparseable test logs and hallucinated build success. Each bash command has a 30-minute timeout and the Setup agent is capped at 60 steps on Linux — [RepoLaunch](https://arxiv.org/html/2603.05026).
- **SWE-rebench:** flaky tests, installs that need interactive troubleshooting, and unpinned or obsolete dependencies, handled by freezing versions after setup — [SWE-rebench](https://arxiv.org/html/2505.20411).
- **SetupBench:** database configuration succeeded only 20.0-53.3% of the time. Common agent failures were incomplete dev tooling, invented task constraints and environment changes that did not persist — [arXiv 2507.09063](https://arxiv.org/abs/2507.09063v1) (search snippet only).
- **BootstrapAgent** explicitly excludes CI features that need secrets, services or special hardware, and recommends maintainer review of the generated contract. Its sanity check caught 5/122 and 4/50 cases where repairs had weakened verification — [BootstrapAgent](https://arxiv.org/html/2605.15815).
- **Railpack** handles common native packages deterministically with a fixed table that maps Python packages to apt packages (libpq, cairo, ffmpeg, MySQL client, poppler) — [Railpack Python](https://railpack.com/languages/python).
- **Services:** Django test runs against PostgreSQL need a reachable server and a user who can create databases; SQLite needs none — [Django testing](https://docs.djangoproject.com/en/stable/topics/testing/overview/).

### Inferences
**Proposed failure classes for AeroPatch's report** (one plain-language line each for a non-technical user):

| Class | Detected by | What AeroPatch does or tells the user |
|---|---|---|
| `python-version` | "requires a different python" errors | Retry with another interpreter |
| `native-build` | missing headers or compiler | Apply the apt map, then retry |
| `dependency-conflict` | resolver errors | Hand to the LLM repair loop |
| `private-package` | 401/403 or "no matching distribution" for a name not on PyPI | Ask the user for an index URL/token |
| `needs-service` | connection refused to localhost:5432 / 6379, or DATABASES settings | Report "needs a database", or optionally start a sidecar on an internal network |
| `needs-secret` | KeyError on an env var, missing .env | Ask the user or set dummy values |
| `timeout/oom` | time or memory limit hit | Run a subset or raise the limit |
| `no-tests` | pytest exit 5 | Go to Q6 |
| `broken-at-head` | tests fail for reasons unrelated to setup | Report it |

- **Never let the repair loop weaken the check.** Following BootstrapAgent's sanity check, reject repairs that delete tests, add `|| true`, or narrow the test selection.
- **Sidecars and the sandbox:** service containers (Postgres, Redis) can be attached to a Docker `--internal` network so tests still cannot reach the internet. This is an inference; I did not read the Docker internal-network docs in this pass.

### Gaps
- No quantitative breakdown found of how many real-world Python repos need external services or secrets to run tests.
- Not read in this pass: how SWE-bench / SWE-Gym handle services, or the Docker `--internal` network docs.

## 6. What should happen when a repo has no tests at all?

### Takeaway
No source offers a standard answer for security-fix verification. The evidence points to a fallback ladder:
1. An environment smoke check (pytest exit 5 detected, imports resolve, the code compiles).
2. AeroPatch's own generated PoC or regression test as the fail-to-pass test.
3. A clear "partially verified" label in the report.

### Cited Findings
- pytest returns exit code 5 when "No tests were collected", so a tool can detect "no tests" reliably and separately from failure — [pytest exit codes](https://docs.pytest.org/en/stable/reference/exit-codes.html).
- EnvBench measures setup success without running tests: Pyright `reportMissingImports` errors must be zero. That is a precedent for an "imports resolve" health check on test-less repos — [EnvBench](https://arxiv.org/html/2503.14443).
- Generating test scripts is itself a measured agent skill, and a common failure: missing or non-executable test scripts caused 18.12% of SWE-Builder failures. Multi-Docker-Eval criticizes earlier benchmarks for not testing whether agents can generate test scripts — [Multi-Docker-Eval](https://arxiv.org/html/2512.06915).
- Repo2Run, SWE-smith and RepoLaunch all select repos that already have tests, so they give no guidance for test-less repos — [Repo2Run](https://arxiv.org/html/2502.13681v3), [SWE-smith](https://arxiv.org/html/2504.21798), [RepoLaunch](https://arxiv.org/html/2603.05026).

### Inferences
**For a repo with no tests, AeroPatch should:**
1. Still build the environment.
2. Run `python -m compileall` plus an import of every top-level module, offline, as the baseline health check. A Pyright missing-imports scan, as in EnvBench, is a heavier option.
3. Run its vulnerability-specific PoC test (which must fail before the fix and pass after) as the only behavioral check.
4. Report "fix proven against the exploit; no project tests exist, so regressions elsewhere are unchecked".
5. Optionally keep the generated PoC test in the PR, so the user's repo gains its first test.

Making an LLM write a broad regression suite is out of scope and unreliable: generating test scripts is a known failure mode, per Multi-Docker-Eval.

### Gaps
- I found no paper or tool doc that defines best practice for verifying a code change in a repo with zero tests.
- No data found on how common test-less repos are among the small personal projects that non-technical users would bring.

## 7. How long do builds typically take, how big are images, and what caching makes repeated runs fast on a laptop?

### Takeaway
A first-time agentic setup takes about 15-30 minutes per repo on average, with a long tail past an hour. A reused recipe or cached image cuts later runs to minutes. Per-repo images are about 1-1.5 GB. Caching (BuildKit cache mounts for uv/pip, dependency layers before source layers, one environment image reused per repo) is what makes a laptop workable. The 16 GB RAM limit is real: Multi-Docker-Eval reports 7.4-7.7 GB peak memory per SWE-Builder run, and it is not stated whether that covers the agent, the build or both.

### Cited Findings
- **Time per repo:**
  - Repo2Run: average 29.03 minutes per successful build, against 21.33 minutes for a manual build in its developer study — [Repo2Run](https://arxiv.org/html/2502.13681v3).
  - ExecutionAgent: 74 minutes and $0.16 per project — [arXiv 2412.10133](https://arxiv.org/abs/2412.10133v2) (search snippet only).
  - SWE-Factory, Python: 16.2-26.5 minutes and $0.030-0.051 per instance — [SWE-Factory](https://arxiv.org/html/2506.10954).
  - SWE-smith's install agent: usually under 2 minutes, about 17 steps and about $0.72 — [SWE-smith](https://arxiv.org/html/2504.21798).
  - BootstrapAgent: median 24.6 minutes and 43.8K tokens; 90th percentile 79.0 minutes and 169.2K tokens — [BootstrapAgent](https://arxiv.org/html/2605.15815).
- **Reuse pays:**
  - BootstrapAgent's contract cut downstream build time by 22.3% and tokens by 25.9%. Median wall time fell from 285.2s to 112.0s on ExecutionAgent and from 391.9s to 309.8s on Repo2Run.
  - Disabling the warm repair loop would add about 4,840 minutes over the Repo2Run set.

  [BootstrapAgent](https://arxiv.org/html/2605.15815)
- **Image sizes and resources:**
  - Multi-Docker-Eval: SWE-Builder images were 0.9-1.2 GB, with 600-750 CPU-seconds and 7.4-7.7 GB peak memory. RepoLaunch images averaged 1.42 GB, with about 10x the CPU time — [Multi-Docker-Eval](https://arxiv.org/html/2512.06915).
  - SWE-smith: about 295 GB for 128 repo images (one image per repo, shared by all tasks). Other corpora: SWE-Gym about 6 TB, R2E-Gym subset about 4 TB. The paper estimates SWE-bench-style per-instance images at 50-150 TB for 50k tasks — [SWE-smith](https://arxiv.org/html/2504.21798).
- **SWE-bench harness:**
  - Images come in three tiers: base, then about 60 environment images, then per-instance images.
  - Disk needed by cache level: `env` (default) about 100 GB, `instance` about 2,000 GB, `none`/`base` about 120 GB during a run.
  - Docker Desktop needs at least 120 GB of disk, 16 GB RAM and 8 CPUs, and fewer than min(0.75 x CPUs, 24) workers.

  [SWE-bench Docker setup](https://www.swebench.com/SWE-bench/guides/docker_setup/)
- **Caching mechanics:**
  - uv recommends a cache mount (`/root/.cache/uv`) with `UV_LINK_MODE=copy`, and installing dependencies (`--no-install-project`) before copying the source so source edits do not invalidate the dependency layer.
  - `UV_PYTHON_CACHE_DIR=/root/.cache/uv/python` lets managed Pythons use the cache mount.
  - `--no-cache` shrinks images when no cache mount is used.

  [uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/)
- BuildKit cache mounts live in the builder's local storage and are not exported with `--cache-to` — fine for a single laptop, useless for CI cache sharing — [Dockerfile reference](https://docs.docker.com/reference/dockerfile/).
- **Repo-level reuse:** SWE-rebench groups tasks by `git tag` major.minor so one environment serves many tasks (about 95% coverage) — [SWE-rebench](https://arxiv.org/html/2505.20411). SWE-Factory's memory pool reuses the Dockerfile from the same repo and a nearby version; removing it costs about 5.2 F2P points — [SWE-Factory](https://arxiv.org/html/2506.10954).

### Inferences
**Laptop budget for AeroPatch:**
- A deterministic-path build of a typical small project (uv, warm cache) should take a few minutes. The 15-30 minute figures are for agentic loops on hard repos.
- Plan for about 1-1.5 GB per environment image. Keep one image per repo and lockfile hash, and prune least-recently-used images past a disk cap stored on F: or D:.
- Never rebuild per fix: the fix only changes source copied into the Stage B container.
- Run one build at a time. With Ollama holding about 4B model weights and Multi-Docker-Eval's 7.4-7.7 GB peak memory per SWE-Builder run, parallel builds risk the same memory exhaustion AeroPatch already hit with heavy jobs.

**Fast-path order on repeat runs:**
1. Recipe file exists and the image tag matches: skip the build.
2. Lockfile unchanged but the image is missing: rebuild from the recipe with the warm uv cache, no LLM.
3. Otherwise run the full Q2 ladder.

### Gaps
- No source gives build times for the purely deterministic uv path on typical small repos, or measures uv against pip install time in Docker for 2026 versions. The uv docs make only qualitative claims.
- No Windows- or Docker-Desktop-specific build-time measurements found.
- Not verified: Docker Desktop's default disk-image size and how to move it to another drive (relevant to the "never C:" constraint).
