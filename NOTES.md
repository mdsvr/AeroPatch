# AeroPatch working notes

## Week 1 status (2026-09-29): complete

D1–D5 were built in a Linux cloud container (2026-09-25). Everything was re-verified on the laptop
(RTX 3050 4 GB, Docker Desktop 29.8, Ollama 0.34.4) on 2026-09-29, where D6 and D7 were run.

| Plan item (doc 14) | State |
|---|---|
| D1 repo skeleton, config, `.env` handling | Done. `src/aeropatch/` package with an `aeropatch` CLI |
| D2 sandbox + 6 security tests | Done. All 6 pass on Docker Desktop too |
| D3 scenario format, validator, first 5 scenarios | Done. CWE-89, 78, 22, 502, 918 |
| D4 context extraction, scanners, 5 more scenarios | Done. CWE-79, 601, 1333, 328, 209; 10-rule Opengrep ruleset |
| D5 edit engine, gates, prompt v1, local + fallback clients | Done. All 8 gates. Frontier end-to-end: 9/10 resolved (D6) |
| D6 single-attempt baseline, 2 local models + frontier | Done. Table below |
| D7 bake-off decision | Done. **Qwen3.5-4B** is the primary SLM |

**Week 1 exit criteria**
- [x] One command runs a scenario end-to-end: `aeropatch remediate A-089-01 --config
  baseline-qwen3.5-4b` resolved CWE-89 with a parameterized query in 13 s.
- [x] 10 validated dev scenarios, split recorded in `evaluations/scenarios/split.json`.
  `validate --all`: 10/10 pass all 4 checks on the laptop, after the 2026-09-28 PoC loosening.
- [x] Baseline table for 2 local models and 1 frontier model (below).
- [x] Sandbox security tests pass on Docker Desktop. Every prompt passes `check_no_secrets` before
  any route (local, API or Claude Code) sees it.

Laptop checks (2026-09-29): `build-base`, `validate --all` 10/10, `pytest -q -rs` 93 passed, 0
skipped (scenario rules run through `.tools\opengrep.exe` via `AEROPATCH_OPENGREP`), oracle bench
10/10.

## D6 baseline (10 dev scenarios, 1 attempt, oracle localization, temp 0.2)

Runs: `runs/20260929-*-dev.jsonl` (local, gitignored). 95% Wilson intervals at n = 10.

| Model | Apply | PoC fixed | Resolved (95% CI) | p50 s | tok/s | Peak VRAM | Cost / run |
|---|---|---|---|---|---|---|---|
| Qwen3.5-4B Q4 (Ollama) | 80% | 50% | **5/10** (24–76%) | 4.4 | 48 | 3,787 MiB (3,643 over idle) | $0 |
| Qwen2.5-Coder-3B Q4 | 60% | 10% | 0/10 (0–28%) | 1.4 | 75 | 2,440 MiB (2,295 over idle) | $0 |
| Claude Opus 5 (Claude Code) | 100% | 100% | **9/10** (60–98%) | 8.7 (incl. CLI startup) | - | n/a | $0.18 API-equivalent |
| oracle (reference fix replay) | 100% | 100% | 10/10 | 0.0 | - | - | - |

- **Run-to-run variance.** Qwen3.5-4B resolved the *same* 5 scenarios on 2026-09-28 and 09-29
  (A-022, 079, 089, 1333, 209). Its apply rate moved 100% → 80% and Coder-3B's 80% → 60%. Every
  swing is `SEARCH_NOT_FOUND` (SEARCH text not copied verbatim), not a parse failure.
- **Where Qwen3.5-4B fails:** A-078 and A-918 regress (the fix breaks behaviour), A-601 leaves the
  PoC failing, A-328 and A-502 alternate between regression and SEARCH mismatch.
- **A-502 regresses for every model, Opus included.** Check in Week 2 that its regression test
  doesn't reject valid fixes before counting it against models.
- Idle GPU use is ~145 MiB (display). Peak is sampled every 0.5 s with `nvidia-smi` during the run.

## D7 decision: Qwen3.5-4B

Doc 03 §5 rule: among models with apply ≥ 80% and p50 < 30 s, pick the highest resolved
(PoC-fixed ∧ regression-free) rate.
1. Filter: Qwen3.5-4B passes (80–100% apply, 4.4 s). Coder-3B fails today (60%) and scored 0%
   resolved either way.
2. VRAM: Qwen3.5-4B peaks at 3,787 MiB total, only 309 MiB below the card's 4,096 MiB. Doc 03
   says "under 3.8 GB"; read here as GiB (3,891 MiB), the unit the "4 GB" card is labelled in.
   Read as decimal GB (3,624 MiB) the peak is over the limit. Either way the remedy would be a
   smaller `num_ctx`, not a different model. Keep `num_ctx` at 8192; a bigger context needs
   re-measuring.
3. Choice: **Qwen3.5-4B** (Apache-2.0), 5/10 vs 0/10. It stays the fine-tuning target for Week 3.
   Coder-3B stays only as the documented fallback if Qwen3.5 tooling fails.

The gap to Opus (5/10 vs 9/10) is the headroom fine-tuning and the repair loop are meant to
close. With n = 10 the intervals overlap heavily; the frozen 40–50 scenario set (Week 2) is what
makes deltas meaningful.

## Frontier reference via Claude Code (deviation)

No API key is set up, so the frontier baseline runs `claude-opus-5` through headless Claude Code
on the user's subscription: `aeropatch bench --config baseline-claude-code`. The client
(`models/claude_code_client.py`) keeps the model a pure function: every built-in tool disabled
(`--tools ""`), AeroPatch's system prompt replacing Claude Code's, no settings/MCP/session files,
empty temp working dir, and `ANTHROPIC_API_KEY` stripped from its environment so a key is never
billed by accident. The model gets the API route's prompt plus a small fixed prefix that Claude
Code adds (~250 tokens; `--exclude-dynamic-system-prompt-sections` doesn't remove it). D6
attempts used 860–1,010 input tokens each, which confirms no tool definitions or Claude Code
system prompt got in. Repair turns are flattened into one prompt. `cost_usd` is the CLI's API-equivalent estimate. The API client (`baseline-frontier`)
is unchanged and remains the production route once a key exists.

Checked 2026-09-29 against the model table cached 2026-09-25: `claude-opus-5` ($5/$25) and the
`server-side-fallback-2026-07-01` beta are still current. `claude-opus-5-5` ($4/$20) is newer and
cheaper; decide at D13 whether the frontier reference moves to it. Ollama cloud is not an option:
`glm-5.1:cloud` and `qwen3.5:cloud` were retired on 2026-09-25, and Kimi/MiniMax need paid credits.

## Model check (against the current Claude model table, cached 2026-06-24)

- Doc 04's IDs and prices are current. `claude-opus-5` stays the default frontier model;
  `claude-sonnet-5` / `claude-haiku-4-5` remain your cost choice after D6.
- The Claude client uses adaptive thinking + `output_config.effort` (no `budget_tokens`, no
  `temperature`, both rejected on current models), streams, checks `stop_reason == "refusal"`
  before reading content, and turns on server-side fallbacks (`fallbacks: "default"`, beta
  `server-side-fallback-2026-07-01`; cyber refusals are rerouted by Anthropic).
- The Ollama tags in `config.py` (`qwen3.5:4b`, `qwen2.5-coder:3b-instruct-q4_K_M`) match
  `ollama list` on the laptop.

## Deviations from the docs (and why)

- **Patches are applied host-side, not with `git apply` in the sandbox.** The scratch copy
  (with the patch already applied) is mounted read-only at `/src`; the image has no git. This is
  doc 07 §5's "scratch copy" design; it removed an apt dependency and keeps the image smaller.
  Tests still come from the image, never from `/src`.
- **Package path:** `src/aeropatch/{agent,models,sandbox,tools}` instead of `src/agent` etc., so
  `uv run aeropatch ...` works as an installed script.
- **tmpfs mounts need `mode=1777`**, otherwise the non-root sandbox user cannot write to
  `/work`. `/tmp` is also `noexec` now.
- **`RISKY_IMPORT` matches dotted prefixes.** `urllib` as a whole was too broad (the open-redirect
  fix needs `urllib.parse`); the list now names `urllib.request`, `http.client`, `urllib3` etc.
- **Scenarios are stdlib-only** for Week 1 (sqlite3 instead of Flask), so builds need no network
  beyond the base image. Flask/FastAPI scenarios can add a hash-pinned `requirements.lock`.
- **The ReDoS PoC runs the check in a child process** with a 5 s timeout: a regex stuck in
  backtracking can't be interrupted in-process by pytest-timeout.
- **Rules were first tested with Semgrep 1.178** in the cloud container; on the laptop they pass
  with `.tools\opengrep.exe`. In a git worktree, point `AEROPATCH_OPENGREP` at
  `F:\AeroPatch\.tools\opengrep.exe`, since `.tools/` is gitignored and not copied.
- **Frontier baseline via Claude Code**, not the API (section above).

## Week 2, D8–D10 start (2026-10-01): repair loop, gates, router modes, 3 larger scenarios

**13 dev scenarios** (the Week 1 ten plus A-022-02, A-078-02, A-089-02), oracle localization.
Every run below was made on **uncommitted changes on top of `f65332f`** (each header says
`dirty: true`), so re-run them on the commit before quoting a number anywhere. Runs are local
(`runs/` is gitignored). `pytest -q`: 142 passed.

| Config | Plan | Resolved (95% CI) | Run | Notes |
|---|---|---|---|---|
| `repair-local` | local ×3 | 10/13 (50–92%) | `20261001-181502` | 7 on attempt 1, 3 by repair |
| `repair-local` | local ×3 | 8/13 (36–82%) | `20261001-182050` | 7 on attempt 1, 1 by repair |
| `repair-claude-code` | Claude Opus 5 ×3 | **13/13** (77–100%) | `20261001-182615` | All on attempt 1; $0.14 API-equivalent |
| `cascade-claude-code` | local, local, Claude Opus 5 | **13/13** (77–100%) | `20261001-180638` | 8 local, 5 escalated; $0.26 API-equivalent. **Older state**, see below |

The first three rows share one state of the code and scenarios. The cascade row is one step
older: it ran before A-022-02's PoC test was corrected (item 10 below), and its re-run failed
fast with `LocalServerDown` because the Ollama server had stopped. That run escalated A-022-02,
which the local model resolved on attempt 1 in both later runs, so its 8 local / 5 escalated
split is likely to shift. **Re-run it.**

- **D8 check met:** a fix that fails attempt 1 and lands on attempt 2 is in
  `runs/20261001-181502-repair-local-dev/A-918-01/`; two more land on attempt 3 (A-078-01,
  A-601). Opus has one in an earlier run (`20261001-180131`): its first A-328 edit added
  `# noqa`, the `SUPPRESSES_CHECKS` gate rejected it, and attempt 2 resolved.
- **D9 check met:** every dev scenario ran through all three modes (local, frontier, cascade).
- **Attempt 1 is more stable than repair.** The same seven resolve on attempt 1 in both
  `repair-local` runs (A-022-01, 022-02, 078-02, 079, 089-01, 1333, 209); A-502 also resolves
  on attempt 1 in some runs, the cascade run among them. Repairs added 3 in one run and 1 in the
  other, and not the same scenarios. Across all of today's local-route runs, including those
  made before the fixes below (16 per Week 1 scenario): A-328 never resolved locally, A-918
  once, A-078-01 and A-601 four times each, A-502 nine times. With n = 13 none of the run-to-run
  differences is significant.
- **Not comparable with D6:** the context, the loop and one Week 1 test changed (below), and
  dev grew.
- **Decode speed fell** from ~48 tok/s to 38 and 43 tok/s (run medians) in the last two local
  runs, after about an hour of back-to-back benchmarks. Earlier in the session (during run
  `175545`) the GPU read 78 °C with 3,947 MiB in use. Thermal throttling (risk R10) and VRAM
  pressure are the candidates; neither was checked.

**What the first repair run showed (it added nothing: 5/10 on the Week 1 ten), and what changed:**

1. *Fragment headers leaked into edits.* The model copied `# lines 6-8` into SEARCH and spanned
   non-adjacent fragments (A-328, A-502; the D6 baseline outputs for the same two show it too).
   **A file of ≤ 60 lines is now shown whole and verbatim** (`context.py`). Attempt-1 apply rate
   went 70% → 100%, and no model output since contains a `# lines` header (every saved
   `raw_output.txt` searched).
2. *A-502 was a context problem, not a test problem.* Its test is valid. The fix has to change
   `dump_prefs` too, which the fragment context hid, so every model (Opus included) broke it.
   Fixed by (1).
3. *`FORMAT_FAIL` feedback was not actionable.* A-601 produced the same marker-less output three
   times. The feedback now repeats the format example.
4. *Repairs written on top of the failed edit.* 6 of 8 `SEARCH_NOT_FOUND` repair attempts quoted
   the model's own previous REPLACE text instead of the file. `edits.rebase` retargets such an
   edit at the original lines, so edits still always apply to the original file.
5. *Identical-edit detection* (doc 08 part 1 §7) is wired in: one retry at 0.8, then `STUCK`.
   It fired on real runs (A-502, A-328, A-078-01). Edits are rebased before they are hashed.
6. *Secret filter false positives on sandbox feedback.* pytest tracebacks print locals
   (`password = 's3cret!'` from A-328's own tests) and long temp paths ending in a credential
   word (`.../ticket-1/secret.txt`, A-022-02). Both blocked the next prompt. Sandbox feedback is
   now redacted (`prompts.redact`) before it enters a prompt; the filter itself is unchanged, and
   `test_scenarios.py` checks every scenario's first prompt against it.
7. *A-078-01's regression test rejected a valid fix.* It required `CalledProcessError` for a
   missing file; Opus's fix (open the file, pipe it to `wc`) raises `FileNotFoundError`. The test
   now accepts either. Re-validated: 4/4 checks.
8. *Missing file path with two editable files.* On A-089-02 the model left the path off the
   SEARCH line or wrote it as the block's first line: `FORMAT_FAIL` on all three attempts, in
   both runs. The parser now infers the file (a first line that names one, else the one file
   containing the SEARCH text). After that its edits applied and were judged by the sandbox.
9. *Call sites.* A method named `read` matched its own `f.read()` as a "call site"; the target
   function's own lines are now skipped.
10. *A-022-02's first PoC test rejected a valid fix.* It demanded `PermissionError` or
    `ValueError`. The local model's `os.path.basename(name)` fix makes the traversal harmless
    but ends in `FileNotFoundError`. The PoC now asserts that no content from outside the ticket
    comes back. Re-validated: 4/4 checks.

**Larger scenarios (64–84-line target files, fragment context):** A-022-02 (class method; the
fix can reuse an existing `_safe_name`), A-078-02 (one of seven functions shells out to `du`),
A-089-02 (two files: the SQL is assembled in `filters.py`, executed in `store.py`). All pass the
4-check validator and the rule test. No `# lines` header leaked into SEARCH on any of them, so
the 60-line threshold stays. They are in **dev**, not test, because the context and the parser
were checked against them. `bench` headers now record `dirty`, and `make_reference_patch.py`
writes LF (a CRLF patch failed `git apply` in the rule test on Windows).

**Still failing locally, and why (guides the Week 3 data mix):**
- A-328 (weak hash): never finds salted hashing; by attempt 3 it reasons in circles inside
  RATIONALE until the 1,024-token limit and emits no blocks. The same runaway shows on A-502.
  A grammar (Week 4 ablation) or fine-tuning on short rationales targets this.
- A-918 (SSRF): wrong logic in the attempts read (it fetches the private address it has just
  detected). Resolved locally once in 16 runs.
- A-601 (open redirect): misses `//host` and `/\host` on attempt 1; a repair sometimes lands.
- A-078-01: does not replace the shell's `<` redirection correctly; a repair sometimes lands.
- A-089-02 (two-file): resolved locally in 3 of 10 runs; its first attempts keep formatting
  values into the SQL text.

**"Resolved" is behavioural, and one resolve shows the limit of that.** A-089-02's local fix in
run `182050` doubles the quotes in each value instead of binding parameters. On SQLite that does
stop the injection, so the PoC and regression tests pass, and the run counts as resolved. The
report line says `original rule still present`. Doc 12's scanner-clean rate is the metric that
keeps fixes like this visible; report it next to the resolve rate in Week 4.

`cascade` and `baseline-frontier` still use the API route and need a key; the `-claude-code`
configs are the ones that run today.

## Next (Week 2, doc 14)

1. Re-run `cascade-claude-code` on dev, and all four configs once this work is committed.
   Today's server was started with `OLLAMA_MODELS=F:\.ollama\models` set for that process: the
   user-level variable points at `D:\ollama_models`, which does not exist. Whether the tray app
   finds the models with that variable was not tested; check `ollama list` before a long run.
2. D10–D11: the remaining scenarios (13 exist, all dev; target 40–50) with 50–150-line apps,
   all into **test**, then freeze `split.json`. New CWEs each need an Opengrep rule; a CWE-798
   scenario must use a placeholder credential or the secret filter blocks its prompt; check XXE
   is really exploitable on Python 3.12 before building on it. PoC tests should assert the
   outcome (nothing leaked, nothing run), not one exception type (items 7 and 10).
3. D12: `metrics.py` (Wilson CIs, McNemar), concurrency 2, thin MCP wrapper.
4. D13: full baselines with repair, run on a clean commit. Decide first whether the frontier
   reference moves to `claude-opus-5-5`.
5. The architecture pages (`docs/architecture*.html`) still carry a "What's blocking D6?" prompt.
