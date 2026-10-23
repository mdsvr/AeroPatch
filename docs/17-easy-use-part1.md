# 17 — Easy Use for Non-Experts, Part 1: Goal, Gaps and Decisions

Written 2026-10-22, after the deep research in
[reports/AeroPatch for non technical users.md](../reports/AeroPatch%20for%20non%20technical%20users.md)
(five notes in `research_notes/AeroPatch for non technical users/`). The citations live there; this
plan links to them instead of copying them. Back to the index: [00-overall-plan.md](00-overall-plan.md)

Parts: **1** goal, gaps, labels, phases, decisions (this file) ·
[2](17-easy-use-part2.md) Phase 0, measure first · [3](17-easy-use-part3.md) Phase 1a, check a folder ·
[4](17-easy-use-part4.md) Phase 1b, fix a folder · [5](17-easy-use-part5.md) Phases 2 and 3, no
terminal and stronger labels.

Times are estimates unless they say "measured". Nothing here has been built or run yet.

**Progress page:** <https://claude.ai/artifact/U1xagY57byquQgFDFEvAsA> (private to you) shows every stage,
its tasks and checks, overall progress, and the decisions waiting on you. Its source is
[17-easy-use-progress.html](17-easy-use-progress.html); the progress itself is stored with the page and
updated as work moves along.

**Recheck (2026-10-22, same day).** Every claim about AeroPatch's code and run files was checked
against them. Claims from the research were not re-checked: Docker's Windows requirements, tkinter in
uv's Python, the Opengrep Windows asset, the CPU speed and Ollama's `app.log` lines. Each is marked
"check" where the plan relies on it. These changes followed:
- **No CWE classes are skipped any more.** The untuned model fixed C-022-01 and C-328-01 in both
  Tier C runs. The "never fixed" claim rested on one test scenario each.
- **Docker is optional.** "Check" and "suggest" work without it (§1), and Phase 0's V2 run measures
  the suggest mode exactly.
- **Phase 1 is split.** The read-only `check` (1a) needs nothing from Phase 0 and can start now.
- **Three Phase 0 fixes:**
  - the model must not see the hidden suites' labels ([loop.py:154-156](../src/aeropatch/agent/loop.py#L154-L156));
  - the re-scan must match the one finding, not any hit of the rule in the file;
  - the re-scan must cover only the changed file.
- **Two apply fixes:** keep CRLF line endings and the BOM, and refuse files that are not UTF-8.
- **Phase 1's ground-truth check** keeps the hidden PoC, so truth is still recorded.

## 1. Goal

A person who builds Python apps with AI tools, a student, or a small-business owner with a script
should be able to:

1. install AeroPatch with one line and see a plain "everything is ready" check;
2. point it at their own folder and get at most five findings, each explained in their terms;
3. accept or skip one suggested change at a time, see what was and was not checked, and undo it.

It stays free and local by default. Code leaves the laptop only when the user presses "Ask Claude"
on one finding, through their own Claude Code subscription, after seeing exactly what is sent.

**Three install levels.** Docker Desktop is the hardest prerequisite (admin rights, WSL, sometimes a
firmware switch and a restart), so it is the last step, not the first:

| Level | Needs | The user gets | Best label possible |
|---|---|---|---|
| Check | uv and Opengrep; no admin; ~2 minutes | Up to five explained findings | — |
| Suggest | + Ollama and the model (~3 GB, no admin) | A suggested change per finding; nothing of theirs runs | "Scanner quiet, not tested" |
| Test | + Docker Desktop | The change checked against their own tests in the sandbox | "Scanner quiet, your tests still pass" |

Machine guidance is to be measured in Phase 2's install test. As an estimate: Check runs anywhere;
Suggest needs about 8 GB of RAM, and without a GPU it is about 4-6 times slower; Test needs 16 GB
(Docker's own minimum is 8 GB).

**What success looks like:** most findings on real code will end as "not fixed" or "not proven".
That is fine if the tool says so plainly. A wrong "fixed" is worse than an honest "could not check".

## 2. What blocks it today (checked in the code on 2026-10-22)

| Gap | Where | Why it matters |
|---|---|---|
| `remediate` and the MCP `remediate` take only a benchmark scenario ID | [cli.py:62](../src/aeropatch/cli.py#L62), [scenario.py:35](../src/aeropatch/scenario.py#L35) | A user's folder has no `scenario.json`, PoC tests, `requirements.lock` or reference fix |
| `loop.run` calls `scenario_dir(task.id)` on every route | [loop.py:44](../src/aeropatch/agent/loop.py#L44) | Raises for any Task that is not a scenario; only the oracle route needs it |
| RESOLVED needs a passing PoC suite with at least one test | [sandbox.py:180](../src/aeropatch/sandbox/sandbox.py#L180), [sandbox.py:213](../src/aeropatch/sandbox/sandbox.py#L213) | On a folder with no PoC, every attempt reads as a failure |
| Only test failures reach the next prompt | [loop.py:148](../src/aeropatch/agent/loop.py#L148) | `original_rule_present` and lint are recorded but only printed in the report ([loop.py:186](../src/aeropatch/agent/loop.py#L186)); without a PoC the model never hears the scanner still flags the line |
| The loop stops only on RESOLVED | [loop.py:151](../src/aeropatch/agent/loop.py#L151) | Needs a second stop rule for folders |
| The runner is built for baked scenario tests | [run.sh:16](../docker/run.sh#L16) | `-c /dev/null`, plugin autoload off and `/opt/scenario/tests_*` paths: a user's own suite (pyproject settings, conftest plugins, pytest-django) will often not collect |
| Workspace copies everything but `.git` and caches | [git_ops.py:29](../src/aeropatch/tools/git_ops.py#L29) | A `.venv` or `node_modules` overflows the 512 MB `/work` tmpfs ([sandbox.py:89](../src/aeropatch/sandbox/sandbox.py#L89)) |
| The secret filter runs on the local route too | [loop.py:73](../src/aeropatch/agent/loop.py#L73) | A real API key next to the finding ends the run as SECRET_BLOCKED; the benchmark used `"changeme"` on purpose |
| The re-scan counts any hit of the rule in the same file | [scanners.py:106](../src/aeropatch/tools/scanners.py#L106) | Real files often have two hits of one rule; fixing one would never read as "scanner quiet" |
| The re-scan scans the whole repository on every attempt | [scanners.py:98-101](../src/aeropatch/tools/scanners.py#L98-L101) | Fine for 50-line scenarios; slow on a real project |
| Files are read as UTF-8 and written back with LF | [git_ops.py:50](../src/aeropatch/tools/git_ops.py#L50), [git_ops.py:65](../src/aeropatch/tools/git_ops.py#L65) | Applying a fix to a Windows CRLF file would rewrite every line; a cp1252 file crashes the read |
| `ROOT = parents[2]`, and the wheel holds only `src/aeropatch` | [config.py:13](../src/aeropatch/config.py#L13) | `uv tool install git+…` would lose `rules/`, `docker/` and Opengrep |
| The MCP server only reads `evaluations/scenarios/` | [mcp_server.py:60](../src/aeropatch/mcp_server.py#L60) | Widening it sends scan results and diffs into a hosted chat (Claude Desktop, Cursor) |
| All 10 Tier B findings are `tool: advisory` | `evaluations/scenarios/B-*/scenario.json` | Whether Opengrep or Bandit would find the real CVEs has never been measured |
| Users will pull the library `qwen3.5:4b`, rebuilt as `d8b0f5e9760c` | [README, Model](../README.md#model) | That build has not been benchmarked |

## 3. Principles

- **Evidence, not verdicts.** Every status line names the check that ran and the one that did not.
  "Secure", "safe", "fixed", "verified" and "guaranteed" never appear in a status line.
- **Measure before showing.** A label ships only with its measured hit rate from AeroPatch's own
  benchmark, written as "N of M", not a percentage (Part 2).
- **Deterministic first.** Triage, the cards, the secrets advice and the environment build use no model.
  The 4B writes code edits only, as today.
- **One finding at a time.** No "fix all". Nothing is written before Apply. Apply backs up first, and
  `undo` restores byte-identical files. Nothing in AeroPatch commits, pushes or opens a pull request.
- **Local by default.** The check and the local page work without an account. "Ask Claude" is per
  finding, opt-in, previewed, and goes through the existing `claude-code` route, never the paid API.
  No telemetry. Run folders that hold the user's code can be deleted with one command.
- **Each level works alone.** A user who never installs Docker still gets the Check and Suggest levels.
- **Reuse.** The loop, the 8 gates, the sandbox, the scanners and the secret filter stay as they are.
  Changes are new config keys, so the benchmark configs keep their meaning
  ([config.py:3-4](../src/aeropatch/config.py#L3-L4): changing a value means a new config name).

## 4. The labels a user sees

Every label also requires all 8 gates to pass (FORBIDDEN_PATH, OUT_OF_SCOPE, TOO_LARGE,
SUPPRESSES_CHECKS, DELETES_SYMBOL, RISKY_IMPORT, SYNTAX_ERROR, NO_CHANGE; [gates.py](../src/aeropatch/agent/gates.py)).

| Label | What must hold | The card says this was not checked |
|---|---|---|
| **Attack test now blocked** (Phase 3, only if measured better than the next row) | A witness test written and frozen before any edit failed on the original for the security reason and passes after; baseline tests still pass; the rule is gone | "AeroPatch wrote this attack test itself"; other ways in; behaviour your tests do not cover |
| **Scanner quiet, your tests still pass** | `original_rule_present` is False; every test that passed twice at baseline still passes | Whether an attack is really blocked; behaviour your tests do not cover |
| **Your tests still pass; the scanner could not re-check this** | Baseline tests still pass; `original_rule_present` is None. None never counts as quiet. In the product this happens only when the re-scan itself fails; on the benchmark it is every Tier B (advisory) finding | Whether the flaw is gone; behaviour your tests do not cover |
| **Scanner quiet, not tested** | Rule gone; at the Suggest level (no Docker), or the project has no tests, or none ran (pytest exit 5) | Everything about behaviour |
| **Not fixed, warning kept** | A check failed and the attempts are used up | Shown with the failing check and a next step |
| **Probably not a real problem** (collapsed) | Triage parked it (Part 3 §2) | Kept, never deleted; one click to show |

Each label will carry a measured hit rate in the form "fixes with this label were right N of M times".
Where the number comes from is part of the wording:
- if the label occurred on the real-CVE tier, the number is from there: "on 10 real bugs";
- otherwise it is from the hand-built tier: "on 27 small practice apps".

"Scanner quiet, not tested" can only be measured on practice apps, and the card says so. The 35%
real-CVE rate is **never** shown as the chance a fix is right. It was earned with the finding handed
over and an exploit test feeding every repair.

## 5. Phases on one page

| Phase | User gets | Size (estimate) | Exit, in short (full criteria in Parts 2-5) |
|---|---|---|---|
| **0. Measure first** | `aeropatch doctor` | ~2 days of code, ~2 h of attended runs | Per-label precision and yield as N of M with Wilson intervals; library model within 4 of 54 of the export or a doctor warning; Tier B scan results; doctor names 6 seeded faults |
| **1a. Check a folder** (can start now, beside Phase 0) | `check` and `dismiss`: up to five cards in the terminal and an HTML page | ~3 days (37 cards to write) | The scenario finding is in the top five on 25 of 27; ≥50% precision of shown findings on 10 public repos |
| **1b. Fix a folder (CLI)** | `fix`, `apply`, `undo`, with or without Docker | ~5 days | Folder path matches the scenario path on the benchmark; build-and-collect rate on the 10 repos; undo byte-identical; review test with 6 people |
| **2. No terminal** | One install line; a desktop shortcut to a local page | ~4 days | Fresh Windows 11 Home reaches all-green; 2 of 3 unaided installs; SUS ≥ 68 |
| **3. Stronger labels, opt-in help** | "Attack test now blocked" on some findings; "Ask Claude" with a preview | ~5 days | Label 1 beats label 2 or does not ship; injection split still 0 of 4 |

About 19 working days in all, as an estimate.

Order rules:
- 1a needs nothing from Phase 0.
- 1b needs Phase 0's labels.
- Phase 2 wraps Phase 1's commands.
- Phase 3 is optional.

1a's read-only check is worth shipping even if the fix rate on real code turns out low.

## 6. Only you can decide these

1. **The pass bars.** ≥50% precision of shown findings, ≥25 of 27 in the top five, ≥5 of 6 in the
   review test, ≥2 of 3 unaided installs, SUS ≥ 68. The report writer proposed them; no source sets
   them. Change them before Phase 0's runs, not after.
2. **Undo style.** Default: a backup copy in `.aeropatch/backup/<timestamp>/` plus `aeropatch undo`,
   which keeps "nothing commits". The other option: apply onto a new git branch, one commit per fix.
3. **Which model users get.** (a) Library `qwen3.5:4b` plus a doctor warning on any unmeasured digest
   (no publishing). (b) Publish the measured Q4_K_M export to Hugging Face and pull it with
   `ollama pull hf.co/<you>/<repo>:Q4_K_M`, so every user gets the benchmarked weights. (b) is
   publishing, and whether Ollama applies the same renderer to an `hf.co` pull must be checked first.
4. **Phase 0's runs.** About 10 benchmark runs, ~2 hours. They will not start without your go-ahead.
   When they run: check Ollama's `app.log` for a staged update, use `--run-id`, nothing heavy beside them.
5. **People.** Phase 1 and 2 tests need 6 + 3 participants (two groups of three for each test).
6. **Release.** Phase 2 needs a tag and a release zip on GitHub, which is outward-facing.
7. **Claude Desktop / MCP for folders.** Deferred until after the local page, because the chat itself
   runs on a hosted model. Say if you want it sooner.

## 7. Deliberately deferred

| Deferred | Why not now | Revisit when |
|---|---|---|
| A model-driven repair loop for environment setup | Qwen3-8B configured 8 of 329 hard repos single-shot; memory beside Docker | Phase 1's failure classes show install conflicts dominate |
| Database or Redis sidecars, private package indexes, required secrets | Each adds a moving part | "Needs a database" is the top Phase 1 blocker |
| Hypothesis differential tests on harmless inputs | Unmeasured on security patches | V2 shows "Scanner quiet, not tested" is the weakest label in use |
| Pixee's codemodder as a deterministic first pass | New dependency; coverage of AeroPatch's rules unchecked | A class the 4B never fixes has a matching codemod |
| Claude Desktop `.mcpb`, Cursor, wider MCP allowlist | Hosted chat; uv and free-plan support unconfirmed | After Phase 2, with redacted outputs and configs limited to local and `claude-code` |
| A signed `.exe`, MSIX, winget manifest | SmartScreen blocks unsigned apps; individual signing is US/Canada only | The one-line install fails Phase 2's bar |
| PR bots, a GitHub Action, pre-commit hook, Explorer menu entry | Server or paid GPU runners, or a signed package; not on the non-expert path | — |
| Podman, macOS, Linux; a 2B or CPU-only model; fine-tuning | Untested, or measured to lose or tie | A benchmark run on that platform or model |
| Multi-file and dependency-upgrade fixes | Gates cap edits at 3 files and 60 lines; dependency files are forbidden paths, so a fix needing a new package (defusedxml, argon2) cannot be made | Labels hold on single-function fixes |
| A larger community Opengrep ruleset | Licences differ (Semgrep's registry rules are not open source; check before use); more rules also mean more noise | Phase 0's scan finds few of the 10 real advisories |
| Python versions other than 3.12 in the sandbox | One base image per version | PYTHON_VERSION is a common Phase 1 failure |
