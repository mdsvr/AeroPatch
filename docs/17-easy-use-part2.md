# 17 — Easy Use for Non-Experts, Part 2: Phase 0, Measure First

Back to [Part 1](17-easy-use-part1.md) (goal, labels, decisions) · index: [00-overall-plan.md](00-overall-plan.md)

Phase 0 builds almost nothing a user sees. It finds out how often each label from Part 1 §4 would be
right on code without an exploit test, using the benchmark AeroPatch already has, and it adds
`aeropatch doctor`. Without these numbers, Phase 1 would be showing labels nobody has checked.

## 1. Why the benchmark can answer this

Every benchmark scenario still runs its PoC and regression suites in the sandbox on every attempt
([run.sh:16](../docker/run.sh#L16)). Phase 0 hides some suites from the loop (feedback and the stop
rule) but keeps their results in `sandbox.json` and the run file. So each attempt carries the label a
user would have seen *and* the truth from the hand-written tests, at no extra sandbox cost.

- **V1, "the user has good tests":** hide the PoC suite. The loop sees regression failures and a
  re-scan line, and stops when the label would be "Scanner quiet, your tests still pass" (or "the
  scanner could not re-check this" on Tier B, whose findings are advisories).
- **V2, "the user has no tests":** hide both suites. The loop sees only the re-scan line and stops
  at "Scanner quiet, not tested".
- **Truth:** `poc_passed and regressions_passed` of the stopping attempt, exactly today's RESOLVED.

V2 matters more than it looks. The benchmark's regression tests were written to catch broken fixes,
and they are far stronger than most users' tests, so V1 alone would flatter the label most users get.
V1 and V2 bracket what users will see: one with strong tests, one with none.

**V2 also measures the Suggest level exactly** (Part 1 §1). With both suites hidden, the model sees what
it would see with no sandbox at all: format errors, gate rejections and the re-scan line. So V2's
numbers are the numbers for users without Docker.

## 2. Code changes (small, in order)

| # | Change | Where | Size |
|---|---|---|---|
| 1 | Tag each `Failure` with its suite: add `suite: str = ""`, set it in the parse loop | [contracts.py:79](../src/aeropatch/contracts.py#L79), [sandbox.py:177-191](../src/aeropatch/sandbox/sandbox.py#L177-L191) | ~3 lines |
| 2 | Only call `scenario_dir` when the plan has an oracle route (`sdir = scenario_dir(task.id) if "oracle" in cfg["attempt_plan"] else None`) | [loop.py:44](../src/aeropatch/agent/loop.py#L44) | 1 line; Phase 1 needs it too |
| 3 | New config keys with today's behaviour as defaults: `hidden_suites: []`, `rescan_feedback: False`, `run_tests: True` | [config.py:31](../src/aeropatch/config.py#L31) | 3 lines |
| 4 | **Two labels, beside the true one.** `att.label` stays the true sandbox label for the records. A new `model_label` is what `older` and `repair_message` show the model. It uses today's vocabulary (REGRESSION, SYNTAX_ERROR, …) computed from the visible suites only, plus one new value, SCANNER_STILL_FLAGS, for "visible checks pass, rule still present". With `hidden_suites: []` and `rescan_feedback: False` it equals `att.label`, so existing configs are unchanged. A new `Attempt.user_label` (change 7) is for display and the stop rule only. Without this, the model would read POC_FAIL in a V1 run, or be told RESOLVED while the loop goes on | [loop.py:147-156](../src/aeropatch/agent/loop.py#L147-L156), [contracts.py](../src/aeropatch/contracts.py) | ~10 lines |
| 5 | **Feedback.** Drop failures from hidden suites before `junit.summarize`. If `rescan_feedback` is on and the finding is still present, add "The scanner still reports {rule_id} at {path}:{line}." | [loop.py:148](../src/aeropatch/agent/loop.py#L148) | ~6 lines |
| 6 | **Re-scan the one finding.** Count the rule's hits in the finding's file at task start; "still present" means the count did not fall. Scan only that file, not the whole repository. A file with one hit gives the same answer as today. **Built 2026-10-23, with a change:** a host-side count found 43 scenarios with one hit, 15 advisories with no re-scan, and two with several (A-079-02 has 4 hits, A-328-02 has 2). There a partial fix would read differently, so only configs with `rescan_feedback` use the count, and every earlier config keeps the any-hit answer. An oracle run on `test` before and after must still give identical values | [scanners.py](../src/aeropatch/tools/scanners.py) | ~10 lines |
| 7 | `user_label(sandbox, gate_ok, hidden)` returns one of the Part 1 §4 labels. A pure function over the recorded fields | new `src/aeropatch/labels.py` | ~30 lines |
| 8 | **Stop rule.** When `hidden_suites` is set, stop on the target label, not on RESOLVED; set `final_diff` at that stop | [loop.py:151-153](../src/aeropatch/agent/loop.py#L151-L153) | ~5 lines |
| 9 | **`run_tests: False`** skips the sandbox but keeps the gates and the re-scan: the Suggest level. Nothing of the user's runs | [loop.py:143](../src/aeropatch/agent/loop.py#L143) | ~4 lines |
| 10 | Configs `repair-local-v1` (`hidden_suites: ["poc"]`) and `repair-local-v2` (`["poc", "regression"]`). Both have `rescan_feedback: True` and the plan `local, local, local` | [config.py:68](../src/aeropatch/config.py#L68) | 4 lines |
| 11 | **Label table** in the report. Per label: the N tasks that stopped on it, the M of them truly resolved, a 95% Wilson interval, and the yield (N out of all tasks). CSV like the others | [metrics.py](../src/aeropatch/metrics.py) | ~30 lines |
| 12 | `aeropatch doctor` (§4) | [cli.py](../src/aeropatch/cli.py), new `src/aeropatch/doctor.py` | ~90 lines |

The existing configs keep `hidden_suites: []` and `rescan_feedback: False`, so every earlier run file
still means what it meant. One side effect: `bench` resumes a killed run only if the stored config
matches exactly, and the new keys are in every resolved config, so a run killed before this change
cannot be resumed after it. None was pending on 2026-10-23. The product's folder configs (Part 4 §1) turn `rescan_feedback` on; V1 and V2
must use exactly that loop, or their precision belongs to a different loop.

**Checks left behind** (one each, per the project's habit): `tests/test_labels.py`, a table of
sandbox results → expected label, including `original_rule_present=None` never counting as quiet;
`tests/test_doctor.py`, the six seeded faults in §4; one loop test that neither a hidden suite's
failure text nor its label (POC_FAIL, IMPORT_ERROR from that suite) reaches the repair prompt, since
either would leak the answer into the measurement; one re-scan test with two hits of a rule in one file.
Two prompt checks guard the claims this plan rests on:
- a recorded `repair-local` attempt produces a byte-identical repair prompt before and after
  these changes, so existing configs keep their meaning;
- V2 and `suggest-local` produce identical prompts for the same attempt, which is what "V2 measures
  Suggest exactly" (§1) depends on.

## 3. The runs

Estimated from measured run times (a `repair-local` run takes about 11 minutes on `test` and 6 on
`test_b`, D20); the V runs may be shorter because they stop earlier. All use `--local-model
aeropatch-control`, the benchmarked export, like Week 4.

| Run | Config | Split | Runs | Estimate |
|---|---|---|---|---|
| Oracle replay through the labeller | `oracle` | test, test_b | 1 each, plus one on test before change 6 | ~15 min, no model |
| V1 | `repair-local-v1` | test | 2 (alternated with V2) | ~22 min |
| V1 | `repair-local-v1` | test_b | 2 | ~12 min |
| V2 | `repair-local-v2` | test | 2 | ~22 min |
| Library model against the export | `repair-local`, `--local-model qwen3.5:4b` and `aeropatch-control`, alternated | test | 2 each | ~45 min |
| Scanner check on the 10 pristine Tier B repos | `aeropatch scan` per repo | test_b | 1 | ~5 min |

**About 2 hours of attended runs.** Before starting: grep `%LOCALAPPDATA%\Ollama\app.log` for "update
downloaded"; check free space on `F:` (the library model is about 3.3 GB more); close other heavy
programs; give every run a `--run-id` so it resumes; alternate models between runs to keep the
model server's memory bounded. Name runs like the Week 4 ones: `<date>-v1a-repair-local-v1-test`.

**What the oracle replay shows:** the other direction of error. Reference fixes are correct by
construction, so any that come out "Not fixed, warning kept" (the scanner still flags the line) show
how often a correct fix would be hidden from the user.

**What the scanner check shows:** for each Tier B repo, how many findings Opengrep and Bandit report and
whether any lands within 3 lines of the advisory's location (`scenario.json` `finding`). It answers
"would AeroPatch have found these real bugs at all?", which nobody has measured yet.

## 4. `aeropatch doctor`

Shape copied from `flutter doctor`: one line per area, a plain fix under each problem, "No problems
found" at the end. Each line is **blocking** (nothing works without it) or a **warning**. Plain ASCII
markers (`[ok]`, `[!]`, `[x]`), since a Windows console may not be UTF-8. Stdlib only.

| Check | How | If it fails, the user reads |
|---|---|---|
| Docker running (blocking) | `docker info`, 10 s timeout | "Docker Desktop is installed but not running. Open it from the Start menu and wait for 'Engine running'." Different text if `docker` is not found at all |
| Docker memory (warning) | `docker info --format {{.MemTotal}}` | Under 4 GB: "Builds may fail. Docker Desktop → Settings → Resources" |
| Ollama answering (blocking) | `GET {local_host}/api/version` | "Ollama is not answering." A known Windows bug leaves the tray icon up with no server |
| Model present (blocking) | `GET /api/tags` has `local_model` | "Run `ollama pull qwen3.5:4b` (about 3 GB)." |
| Model digest (warning) | digest in `/api/tags` against the measured one(s) | "This model build has not been tested with AeroPatch; results may differ." |
| Ollama update staged (warning) | An "update downloaded" line in `%LOCALAPPDATA%\Ollama\app.log` after the last server start (check the exact log lines on the laptop first) | "Ollama will restart itself to update. Install the update now, before a long check." |
| GPU (warning) | `nvidia-smi --query-gpu=name,memory.total` | No NVIDIA GPU: "Suggestions will take about 4-6 times longer." The ratio comes from one guide's 8-12 tokens a second on a 4-core CPU, against the 46.5 measured here; measure it before quoting it |
| Opengrep (warning) | `scanners.opengrep_binary()` | "Only Bandit will run, which reports many more false alarms." |
| Disk (warning) | `shutil.disk_usage` on the runs drive | Under 10 GB: each project's sandbox image is about 1-1.5 GB |
| Claude Code (info) | `claude --version` | Only for "Ask Claude"; never blocking |

The last line names the levels that are ready: "Ready for: Check, Suggest. Test needs Docker
running." A missing Docker blocks only the Test level, never Check or Suggest.

Seeded-fault test: Docker stopped, Ollama not answering, model missing or a different digest, a staged
update, Opengrep missing, low disk. The doctor must name each correctly, with probes monkeypatched in
`tests/test_doctor.py` and once by hand on the laptop.

## 5. Exit criteria (all must hold)

1. Per-label precision and yield published as N of M with 95% Wilson intervals, from V1 on test and
   test_b and V2 on test, two runs each, in the README and `docs/results/labels/`. Oracle runs before
   and after change 6 give identical `original_rule_present` values, so the benchmark keeps its meaning.
2. The oracle replay's label counts published: how many correct reference fixes each label misreads.
3. The library model's resolved count within 4 of 54 of the export's (the project's pre-set bar),
   same day, alternated. Otherwise the doctor warns on every digest except the export's, and decision 3
   in Part 1 §6 becomes urgent.
4. Tier B scan results published: findings per repo, and advisories with a finding within 3 lines.
5. The doctor names all six seeded faults.
6. `NOTES.md` and `runs/INDEX.md` list every run with its Ollama version.

## 6. What could change the plan

- **V2's "Scanner quiet, not tested" is right only a minority of the time.** Then, for users without
  tests, AeroPatch is an explainer that offers suggestions, not a fixer: Phase 1 shows the change as
  "a suggestion to review" and puts Phase 3's attack tests first.
- **V1's resolve rate falls far below 70%.** That rate, not 70% or 35%, is the one to quote to users.
- **Tier B scans find almost none of the advisories.** Detection, not repair, is the bottleneck on
  real code: triage and rules (Part 3 §2) move ahead of model work.
- **The library digest loses by 4 or more.** Users must get the export (decision 3 (b)) or a warning.

At 27 and 10 scenarios the intervals span 20-40 points, so these are coarse readings. Differences under
the pre-set bar are ties.
