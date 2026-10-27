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
The table is the **2026-10-03 re-run on `main` at `3d26b27`**: every header says `dirty: false`,
and `pytest -q -rs` on that commit gave 142 passed, 0 skipped. Runs are local (`runs/` is
gitignored).

| Config | Plan | Resolved (95% CI) | Run | Notes |
|---|---|---|---|---|
| `repair-local` | local ×3 | 10/13 (50–92%) | `20261003-113223` | 7 on attempt 1, 3 by repair; 43 tok/s |
| `repair-local` | local ×3 | 7/13 (29–77%) | `20261003-115043` | 7 on attempt 1, none by repair; 46 tok/s |
| `repair-claude-code` | Claude Opus 5 ×3 | **13/13** (77–100%) | `20261003-113658` | All on attempt 1; $0.26 API-equivalent |
| `cascade-claude-code` | local, local, Claude Opus 5 | **13/13** (77–100%) | `20261003-114259` | 9 local (7 on attempt 1, 2 by repair), 4 escalated; $0.22 API-equivalent |
| `oracle` | reference fix replay | 12/13 | `20261003-113134` | Harness bug in the oracle route, fixed below; 13/13 after (`20261003-121131`) |

The first runs of these configs (2026-10-01, on uncommitted code, `dirty: true`) gave 10/13 and
8/13 local, 13/13 Opus and 13/13 cascade (8 local, 5 escalated). The Opus run cost $0.14 then
and $0.26 now for the same 13 first-attempt resolves; the difference was not looked into.

**Oracle route bug (fixed 2026-10-03).** `patch_to_blocks`
gave a file's last hunk the path of the *next* file in the patch, so the two-file A-089-02
replayed as `FORMAT_FAIL`. It only affects the `oracle` config, not any model run.
`tests/test_oracle.py` covers a two-file patch.

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
  differences is significant. The 2026-10-03 runs repeat the pattern: the same seven on attempt
  1 in all three local-route runs, and 3, 0 and 2 repairs.
- **Not comparable with D6:** the context, the loop and one Week 1 test changed (below), and
  dev grew.
- **Decode speed fell** from ~48 tok/s to 38 and 43 tok/s (run medians) in the last two local
  runs, after about an hour of back-to-back benchmarks. Earlier in the session (during run
  `175545`) the GPU read 78 °C with 3,947 MiB in use. Thermal throttling (risk R10) and VRAM
  pressure are the candidates; neither was checked. On 2026-10-03 it held at 43–46 tok/s over a
  25-minute block of five runs; the GPU went from 54 °C to 72 °C after the first local run, with
  3,933 MiB in use (about 190 MiB of that was there before the model loaded).

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

## Week 2, D10–D11 (2026-10-03): 20 test scenarios, 33 of 40–50

All 20 are Tier A, stdlib-only and in **test** (`split.json`: 13 dev, 20 test, not frozen yet).
For each one:
- the 4-check validator passes in the sandbox, and **every** PoC test fails on the vulnerable
  code (the validator only asks for one);
- the reference fix passes the gates and resolves through the `oracle` route: 20/20, run
  `20261003-123850-oracle-test`;
- its rule fires on the vulnerable code and not on the fixed code;
- a second-attempt prompt built from its sandbox feedback passes the secret filter, for both a
  PoC failure and a regression failure (40 prompts, 0 blocked; no model involved). Feedback, not
  the first prompt, is what got prompts blocked on 2026-10-01, and `test_scenarios.py` only
  covers first prompts.

`pytest -q -rs`: 224 passed, 0 skipped. **No model has been run on these, and none should be
before D13.** Dev is dev because the context builder and the parser were tuned against it.

| ID | CWE | Target file | What it adds over dev |
|---|---|---|---|
| A-089-03 | 89 | 90 lines | `%`-formatted `LIKE` search plus a status filter; a second table to leak through `UNION` |
| A-078-03 | 78 | 76 lines | `os.system` with `cd … && tar`; a `tarfile` fix needs no subprocess at all |
| A-022-03 | 22 | 66 lines | `tarfile.extractall` on an uploaded archive (`..` and absolute entries) |
| A-079-02 | 79 | 68 lines | Four interpolation points, one inside a `title="…"` attribute |
| A-502-02 | 502 | 91 lines | A legacy pickle branch next to the JSON path in a job spool |
| A-918-02 | 918 | 67 lines | A host-name blocklist already exists; the resolved address is never checked |
| A-601-02 | 601 | 58 lines | A prefix check already exists; `//host`, `/\host` and look-alike hosts pass it |
| A-1333-02 | 1333 | 67 lines | `^([A-Za-z]+\s*)+$` among four compiled patterns; a length cap alone does not fix it (41 characters hang, a 62-character name must stay valid) |
| A-328-02 | 328 | 55 lines | Class with `set_password` and `check_password`; both must change together |
| A-209-02 | 209 | 71 lines | `repr(exc)` and `traceback.format_exc()` in the JSON body |
| A-611-01 | 611 | 74 lines | SAX parser with `feature_external_ges` turned on |
| A-798-01 | 798 | 51 lines | Password literal next to settings that are read from `BILLING_*` variables |
| A-352-01 | 352 | 52 lines | One of two POST views skips the existing `csrf_ok` check |
| A-020-01 | 20 | 44 lines | Quantity with no range check: zero, negative, over the per-line limit, repeated adds |
| A-338-01 | 338 | 47 lines | Reset codes from `random.choice`; the PoC replays the seed |
| A-611-02 | 611 | 58 lines | `pulldom` with a custom parser; a local file entity and an external DTD |
| A-798-02 | 798 | 50 lines | Fallback HMAC key in the source when the environment variable is missing |
| A-352-02 | 352 | 50 lines | The token is compared only when the form sends one; an empty token matches a session without one |
| A-020-02 | 20 | 62 lines | Negative transfer amount pulls money back; the recipient can pass the card limit |
| A-338-02 | 338 | 47 lines | API key from `random.Random(owner:second)`; the PoC recomputes it |

**Things found while writing them**
- **XXE on Python 3.12 needs the code to ask for it.** Probed with a `file://` entity: `ElementTree`
  raises, `minidom` and default `xml.sax` drop the entity, and only `xml.sax` with
  `feature_external_ges` set to True reads the file (it then loads an external DTD too, also
  through `pulldom`). Setting `feature_external_pes` raises: expat does not read external
  parameter entities. Both 611 scenarios use the `external_ges` switch; an lxml variant would
  need a pinned dependency.
- **A-798-01 uses `"changeme"`** as the hard-coded password, so nothing that looks like a real
  secret is sent to a model.
- **Secret filter gap, fixed.** `DB_PASSWORD = "…"` and other `_`-prefixed names passed the
  assignment check, because `\b` does not match between `_` and `PASSWORD`. The pattern now uses
  a lookbehind; `tests/test_prompts.py` has the case. `redact` uses the same pattern, so repair
  feedback is redacted more widely too. All 28 first prompts still pass, and no prompt, model
  output or sandbox log of the 2026-10-03 runs contains an assignment the old pattern missed, so
  those results do not depend on the change. Names with a suffix (`SECRET_KEY = "…"`) are still
  only caught by the entropy rule (32+ characters).
- **Files over 60 lines limit what a scenario can ask.** The prompt then shows only the
  finding's function, so a fix that needs a second function in the same file is out of reach
  for any model (A-502-01's old problem). The larger test scenarios keep the whole fix inside
  the target function; those that need a sibling function or a module-level constant
  (A-328-02, A-352-01, A-798-01, A-798-02) stay under 61 lines.
- **Seven new rules** (17 in total): `tar-extract-unfiltered`, `xxe-external-entities`,
  `hardcoded-credential`, `csrf-missing-check`, `csrf-check-skippable`, `unchecked-quantity`,
  `insecure-random-secret`. They add no finding to any other scenario.
- **The rules are syntactic, so some valid fixes still trip them:** escaping into a variable
  before the f-string (A-079-02), a manual path check without `filter=` (A-022-03), a safe
  regex that still has a quantified group (A-1333-02). Those count as "original rule still
  present" and will lower the scanner-clean rate without being wrong.
- **Authoring bias.** These scenarios and their reference fixes were written by a Claude model,
  and the frontier reference is Claude Opus 5. The PoC tests assert outcomes (nothing leaked,
  nothing run, nothing stored) so that other correct fixes pass, but say this next to the
  frontier numbers. Tier B (real CVEs) does not have this problem.

## Week 2, D11 (2026-10-03, later): 7 more scenarios, split frozen at 13 dev / 27 test

Two decisions were open and were taken as defaults, not by the user: **Tier A only** (no Tier B
real CVEs, no Tier C) and the frontier reference **stays `claude-opus-5`**. Both can still be
changed; the consequences are under "Next".

The seven new scenarios are Tier A, stdlib-only and in **test**. They met the same bar as the
first 20: 4-check validator, every PoC test failing on the vulnerable code, rule fires on the
vulnerable code and not on the fixed code, and repair prompts built from PoC-failure and
regression-failure feedback pass the secret filter. Two more checks were added for these seven:
a **second, differently written correct fix** resolves each one (so the tests do not pin the
reference fix), and all 40 trees were scanned, vulnerable and fixed, to confirm that the five
new rules fire only on their own scenario.

| ID | CWE | Target file | What it adds |
|---|---|---|---|
| A-327-01 | 327 | 55 lines | MD5 ties an update package to its manifest entry; the PoC swaps in a published MD5 collision pair (checked: different bytes, same digest) |
| A-327-02 | 327 | 49 lines | Signature is `sha256(key + text)`; the PoC forges a longer signed query by length extension, with its own SHA-256 and without the key |
| A-502-03 | 502 | 53 lines | No pickle: a JSON `object_hook` imports whatever `"__type__"` names and calls it |
| A-079-03 | 79 | 46 lines | A hand-written escape handles `& < >` but not quotes, and its output goes into attributes; the fix belongs in the helper, not at the call sites |
| A-918-03 | 918 | 69 lines | URL allowed by `startswith`; `cdn.shop.example.attacker.net` and `cdn.shop.example@10.0.0.5` pass |
| A-089-04 | 89 | 58 lines | `ORDER BY {sort} {direction}`: identifiers cannot be bound, so the fix is an allowlist; the PoC reads another table through the sort order |
| A-078-04 | 78 | 51 + 16 lines | **Two files**, the only such scenario in test: the command string is built in `commands.py` and run with `shell=True` in `logviewer.py` |

- **CWE-327 now has scenarios**, so every CWE in doc 11 §4 has at least two. 16 CWEs in total.
- **Five new rules** (22 in total): `weak-integrity-digest`, `keyed-hash-without-hmac`,
  `dynamic-import-deserialization`, `html-escape-misses-quotes`, `url-prefix-allowlist`.
- **Limits of the new PoCs.** A-327-01 only has an MD5 collision, so a "fix" that moves to SHA-1
  passes. A-327-02's forgery applies to 256-bit hex signatures; a fix that keeps the
  secret-prefix construction with another hash is not caught.
- **`split.json` is frozen** (its note says so, and `test_scenarios.py` pins 13 and 27). A
  scenario added later goes under its own key, so dev and test stay as they are. That rule is
  mine; change it if Tier B should count as test.
- `pytest -q -rs` after D11: 252 passed, 0 skipped.

## Week 2, D12 (2026-10-03): metrics, two sandboxes, MCP wrapper

- **`metrics.py`** (`aeropatch report <run.jsonl>...`, stdlib only): 95% Wilson intervals,
  cumulative resolve@1/2/3, repair gain, exact McNemar on the tasks two runs share, a per-CWE
  table and the failure-attribution chart with each unresolved task's attempt labels. Its
  Wilson test uses the intervals already in this file (5/10, 10/13, 13/13, 0/10). Not built:
  pass@k (no sampled runs exist), the bootstrap, CSV output.
- **`bench --jobs 2`**: two tasks at once. One thread writes, in sorted order, so the run file
  and resume are the same as at `--jobs 1`. Local generation is behind one lock in
  `router.generate`; the tree-sitter parser is no longer shared between threads. The header
  records `jobs`. Default is 1.
- **Runner check without a model** (this replaces D12's `repair-local --split test` check, which
  would have shown test to a model a day early): `oracle` on test at `--jobs 2`, hard-killed
  after 8 results and resumed under the same run id. 27 results, 27 distinct, 27 resolved,
  `dirty: false`: `runs/20261003-155826-oracle-test-jobs2.jsonl`.
- **MCP wrapper**: `src/aeropatch/mcp_server.py`, `uv run aeropatch mcp` (stdio, MCP Python SDK
  2.2). Tools: `scan`, `get_context`, `validate`, `remediate`. Not exposed: `propose_fix` and
  `apply_edits` (`remediate` covers them), and nothing that commits or pushes. `repo` must be
  under `evaluations/scenarios/`; `validate` refuses a diff that adds
  or removes files, since the gates only see changed files.
- **One real call over stdio**, from the SDK's client against a separate server process
  (negotiated protocol 2026-07-28): `scan` on A-327-02 returned the one finding, and `validate`
  with its reference patch returned `resolved: true` (2 PoC and 6 regression tests). It was not
  tried from Claude Code or MCP Inspector; nothing was added to your Claude Code config.
- `pytest -q -rs` after D12: 266 passed, 0 skipped.

## Week 2, D13 (2026-10-03): baselines with repair on the frozen test split

27 test scenarios, oracle localization, `--jobs 1`, every header `dirty: false`. Runs are local
(`runs/` is gitignored). Intervals are 95% Wilson; the tables come from `aeropatch report`.
This was done in one afternoon, not overnight: a config takes 5–15 minutes on 27 scenarios.

| Config | Plan | Resolved (95% CI) | By attempt 1 / 2 / 3 | Rule gone | Run | Notes |
|---|---|---|---|---|---|---|
| `repair-local` | local ×3 | 17/27 (44–78%) | 12 / 15 / 17 | 14/17 | `20261003-155954` | 48 tok/s, p50 6.3 s, $0 |
| `repair-local` | local ×3 | 18/27 (48–81%) | 11 / 16 / 18 | 12/18 | `20261003-162838` | Same commit, second run; 44.5 tok/s, p50 9.6 s |
| `repair-claude-code` | Claude Opus 5 ×3 | **27/27** (88–100%) | 27 / 27 / 27 | 18/27 | `20261003-161129` | All on attempt 1; $0.66 API-equivalent |
| `cascade-claude-code` | local, local, Claude Opus 5 | 26/27 (82–99%) | 13 / 17 / 26 | 17/26 | `20261003-161702` | **Before the loop fix below.** 17 local, 9 escalated and resolved, 1 stuck and never escalated; $0.62 |
| `cascade-claude-code` | local, local, Claude Opus 5 | **27/27** (88–100%) | 13 / 17 / 27 | 18/27 | `20261003-165008` | After the loop fix. 16 local, 11 escalated and resolved; $0.69 |
| `oracle` | reference fix replay | 27/27 | - | 27/27 | `20261003-155826` | At `--jobs 2`, killed and resumed |

The first four runs are on commit `55e0709`; the cascade re-run is on `9fcc75c`, which differs
in the loop fix, a logging field and the report code.

- **Local against Opus is a real difference at this size.** Paired on the same 27 scenarios, Opus
  resolved 10 that local run 1 did not and 9 that run 2 did not, and local resolved none that
  Opus missed: exact McNemar p = 0.002 and 0.004.
- **The cascade matched Opus and did not cost less.** After the fix it resolved 27/27, 16 of them
  without Opus. But an escalated attempt carries the two failed local attempts and their test
  output, and cost $0.063 on average against $0.024 for a first attempt in the Opus-only run.
  So 11 escalations cost $0.69, and sending all 27 straight to Opus cost $0.66. On this set
  the cascade saves frontier calls (11 instead of 27), not frontier cost; it breaks even at
  about 10 escalations in 27. These are API-equivalent estimates on a subscription.
- **The two local runs agree in total and differ in which scenarios.** 17 and 18, with five flips:
  A-078-03 and A-352-02 resolved only in run 1; A-089-03, A-089-04 and A-798-01 only in run 2
  (McNemar p = 1.0). Seven scenarios failed in both: A-020-02, A-022-03, A-078-04, A-328-02,
  A-601-02, A-918-02, A-918-03. The Wilson interval does not include this run-to-run spread.
- **Per-CWE counts are 1 or 2 scenarios each**, so the per-CWE table says where to look, not
  what is true. Run 1 resolved neither SQL-injection scenario; run 2 resolved both.
- **Repair helps the local model**: 5 of 15 first-attempt failures were fixed in run 1 and 7 of
  16 in run 2. Opus never needed a second attempt.
- **Authoring bias applies to the 27/27.** All 40 scenarios and their reference fixes were written
  by Claude models, and the frontier reference is Claude Opus 5. Its fixes do differ from the
  reference ones (A-089-04 falls back to a default sort instead of raising), but a 100% score on
  home-written scenarios is weak evidence about real CVEs. Tier B is what would test that.
- **"Rule gone" is lower than "resolved"** because the rules are syntactic: in 9 of Opus's 27
  resolved fixes the original rule still fires (for example an allowlisted column still sits in
  an f-string). Report both numbers side by side, as planned for Week 4.
- **Not comparable with the dev table above**: different scenarios.
- **Speed.** The second local run decoded at 44.5 tok/s against 48.0 and its p50 latency was
  9.6 s against 6.3 s. It started after about 30 minutes of continuous benchmarks; the GPU read
  83 °C during the first local run. Throttling (risk R10) is the likely cause and was not tested.

**Found while re-checking the runs (2026-10-03)**

1. **A stuck local model ended a cascade instead of escalating (fixed in `9fcc75c`).** When a
   repair repeated an earlier edit twice, `loop.py` stopped the run with `STUCK`. In a cascade
   that skipped the frontier entry. A-078-03 in run `161702` went local `POC_FAIL`, `STUCK`,
   stop; Opus resolves it on the first attempt in run `161129`. Now a stuck route is skipped
   for the rest of the plan and a different route still gets its turn (doc 04 §5: the local
   attempts are used up). Single-route plans end as before, so the local and Opus numbers are
   unaffected. It had not happened in any dev cascade run. `tests/test_loop.py` covers it.
   The 26/27 stays in the table as the measured pre-fix result. The re-run exercised the fix:
   A-798-01 went local `POC_FAIL`, `STUCK`, and then Opus resolved it.
2. **`served_by` named the wrong model in every Claude Code run since 2026-10-01** (logging only,
   fixed in `9fcc75c`). The CLI's `modelUsage` lists its own side call to Haiku 4.5 first, and
   the client took the first key. Opus did answer: in all 50 attempts of runs `152934`, `113658`
   and `161129` the logged cost is at least 5 times what the logged tokens would cost at Haiku
   prices, and one direct call showed the two entries side by side. `cost_usd` is the CLI's
   total, and it is more than the logged tokens cost at Opus's list price: about 30% of the
   $0.66 of run `161129` is not explained by them. From `9fcc75c` on, `usage.model_usage`
   records the CLI's per-model split. In the cascade re-run (11 Opus attempts, $0.69) that is
   $0.65 for Opus and $0.04 for the Haiku side call, while the logged Opus tokens come to
   $0.45 at list price. So the side call is about 6% of the cost, and most of the gap is Opus
   cost that the top-level `usage` fields do not show. Why was not looked into.
3. **Context headers were copied into edits on test.** 5 of 107 local outputs in the two test
   runs contain a `# lines N-M` or call-site header (A-022-03 three times, A-918-02, A-078-04),
   all on repair attempts and all on files over 60 lines or the two-file scenario. On dev no
   output did, which is why the 60-line threshold was kept on 2026-10-01. Nothing was changed:
   a change to the context format has to be judged on dev and is a new config.
4. **The first plan for the Week 3 data mix used test results; it now uses dev only.** See D14.

## Week 2, D14 (2026-10-03): where the untuned SLM fails, and the injection script

**Which split decides the data mix.** Doc 14 §5 says the baseline failures decide the synthetic
mix; doc 11 §3 says test is for final runs only. The baselines of D13 are on test, so the two
conflict. The CWE weights in `training/inject_cwe.py` were first set from the test run and were
then moved to **dev only**: 3 for CWE-328 and CWE-918 (never or once resolved locally on dev), 2
for CWE-78, CWE-89 and CWE-601 (resolved in under half of the dev runs), 1 for the rest. Dev has
no scenario for CWE-20, 327, 338, 352, 611 or 798, so those have no signal. Overrule this if
doc 14's reading is the one you want.

Dev attribution, from `aeropatch report` on the two dev runs of this morning (`113223`, `115043`):
A-328-01 and A-918-01 unresolved in both, A-601-01 in both, and A-078-01, A-089-02 and A-502-01
in the second only. The causes are the ones listed under "Still failing locally" above.

**What the test runs add** (read from each attempt's diff and sandbox result; for the write-up,
not for the data mix). None of the 10 unresolved scenarios of run 1 is a broken test:
- *Half of a two-part fix* (3): A-020-02 fixes the negative amount in one attempt and the
  recipient limit in another, never both; A-601-02 handles `//host` but not `/\host`; A-918-03
  parses the host but stops requiring https.
- *An edit that leaves the file inconsistent* (3): A-022-03 calls a helper it never defines;
  A-328-02 imports `bcrypt`, which is not installed, then uses `os` without importing it;
  A-798-01 deletes the password constant while it is still used.
- *SQL beyond "bind the value"* (2): A-089-04 writes the right allowlist and then binds the
  column name as a parameter (`ORDER BY ? ?`); A-089-03 binds the values but drops the optional
  status filter and repeats that three times.
- *SSRF* (1): A-918-02 compares the resolver's output with the host-name blocklist and never
  uses `ipaddress`, the same mistake as on dev.
- *Two files* (1): A-078-04 removes `shell=True` and leaves the command a string; it never edits
  `commands.py`.
These match the dev picture: the model gets the idea and fails on completeness.

**`training/inject_cwe.py` (first version).** A teacher model behind an Ollama endpoint writes a
small clean module, the same module with one CWE planted, PoC tests and regression tests. A
candidate is kept only if the injection is 1–10 changed lines, its code shares no 13-token run
with any benchmark scenario, and it passes validator checks 1–3 in the sandbox with the PoC
failing as a test failure (not an import error). Kept examples are scenario directories under
`training/synthetic/` (gitignored), so `--student` runs `repair-local` on them and logs the
failed attempts with their feedback. Each candidate gets a manifest line with its reject
reason. `tests/test_inject_cwe.py` covers parsing and the static rejects.
- **Deviation from doc 09 §3:** the teacher writes the clean module too. The doc takes clean
  functions from permissively licensed projects; that needs pinned dependencies in the sandbox
  image, which no scenario has yet.
- **The teacher is not chosen.** `--teacher` is required. Doc 09 §4 asks for an open-weights
  model stronger than the student, through a hosted endpoint; that is your decision and it
  may cost money.
- **Smoke test only** (`--teacher qwen3.5:4b --count 3`, the student standing in as teacher).
  All three answers parsed. One was rejected before the sandbox (`injection_size`); two were
  built, run in the sandbox and rejected at check 1, because their PoC did not separate the
  two versions. Their directories and images were removed. 0 of 3 kept, 50–100 s each. This
  shows the pipeline runs end to end. It says nothing about yield, no example has been kept
  yet, and so the `--student` pass has never run.

## Week 2 close-out (2026-10-05): Tier B from real CVEs, and the open evidence closed

You asked for all of Week 2 to be completed, so Tier B was built. Tier C was not: it has to come
from the teacher model that also produces the training data (doc 09), and that is not chosen.

**Evidence that was missing on 2026-10-03**
- **A model run killed and resumed.** `repair-local` on dev, hard-killed after 5 results and
  resumed under the same run id: 13 results, 13 distinct, in sorted order, `dirty: false`
  (`runs/20261005-150539-repair-local-dev-killed.jsonl`; it resolved 9/13).
- **The MCP server called from Claude Code.** Headless Claude Code 2.1.239, with a throwaway
  `--mcp-config` file and `--strict-mcp-config`, connected to `aeropatch mcp`, listed the four
  tools and called `get_context` on A-089-01. Nothing was added to your Claude Code settings.
- The stale "What's blocking D6?" prompt on the architecture page now asks about Week 3.

**How the ten were chosen.** Not from PatchEval-Verified or CVE-Bench as doc 14 planned, but from
the GitHub advisory database, which is what those benchmarks are built from and reaches CVEs
published last week:
1. 1,906 reviewed pip advisories were published between 2026-03-16 and 2026-10-02 (after
   Qwen3.5's release). 811 name exactly one fix commit.
2. 154 of those, in 71 projects, fit the harness: the commit changes exactly one non-test
   Python file by at most 60 lines and also changes a test, the licence is MIT, BSD, Apache or
   PSF, and the project has no native code.
3. From the small, dependency-light projects among them, 16 fix commits were read. 10 were
   built; all 10 pass. The other 6 were dropped before building: three for fixes spread over
   several functions (two in scitokens, one in urllib3), one for a timing-only test (a second
   mistune one), one for a fix on an obscure error path (a third PyJWT one; two per project
   was the cap), and Authlib for needing integration-test fixtures, which would also have
   gone past the plan's ceiling of 50. GitPython's thirteen advisories were skipped unread:
   their tests need a `git` binary, which the sandbox image does not have.

| ID | CWE | Project | Function to fix | Fix public | Advisory | Upstream fix | Target file |
|---|---|---|---|---|---|---|---|
| B-022-01 | 22 | Mako | `Template.__init__` | 2026-04-14 | 2026-04-16 | 4 lines | 711 lines |
| B-079-01 | 79 | mistune | `HTMLRenderer.safe_url` | 2026-06-21 | 2026-07-20 | 20 lines | 153 lines |
| B-094-01 | 94 | sqlparse | `OutputPythonFilter._process` | 2026-06-29 | 2026-08-17 | 16 lines | 123 lines |
| B-113-01 | 113 | microdot | `Response.set_cookie` | 2026-04-24 | 2026-05-05 | 4 lines | 1,566 lines |
| B-1333-01 | 1333 | geopy | `Point.from_string` | 2026-07-10 | 2026-10-02 | 11 lines | 480 lines |
| B-287-01 | 287 | Flask-HTTPAuth | `HTTPTokenAuth.authenticate` | 2026-03-28 | 2026-03-31 | 4 lines | 669 lines |
| B-347-01 | 347 | PyJWT | `PyJWS._verify_signature` | 2026-09-09 | 2026-09-29 | 2 lines | 472 lines |
| B-347-02 | 347 | PyJWT | `is_pem_format` | 2026-09-09 | 2026-09-29 | 19 lines | 142 lines |
| B-400-01 | 400 | hpack | `decode_integer` | 2026-06-21 | 2026-09-24 | 13 lines | 664 lines |
| B-400-02 | 400 | pyasn1 | `Real.__float__` | 2026-07-08 | 2026-07-21 | 21 lines | 3,327 lines |

**How each one is built**
- `repo/` holds the project's package at the commit before the fix, with the upstream licence
  file (MIT, BSD-2, BSD-3). `scenario.json` records the advisory URL, the CVE id, both commit
  hashes and the advisory date. None of these is shown to a model: the finding's rule id is
  `advisory.cwe-N` and the description states the flaw without naming the CVE.
- The reference patch is the upstream fix, unchanged.
- **PoC tests: the attack is upstream's, the test code is mine.** Six reuse the inputs of the
  tests the upstream fix added, with the assertion rewritten to check the outcome (nothing
  leaked, no header line added, no claims returned), so another correct fix passes. Four were
  rebuilt around the advisory, because the upstream test pins exact output, passes on the
  vulnerable code too, or would hang the test process: sqlparse, Flask-HTTPAuth, hpack, pyasn1.
- **Regression tests (4 to 17 per scenario) are not all upstream's.** One file is the project's
  own tests converted to pytest (Flask-HTTPAuth). Four are the project's tests plus tests I
  added (geopy, microdot, sqlparse, pyasn1). Five I wrote in the style of the project's suite
  (both PyJWT ones, mistune, Mako, hpack); the second PyJWT one includes three cases from the
  fix's tests. This list is the record: the docstrings of the microdot, sqlparse and second
  PyJWT files name the upstream test file without mentioning my additions, and the scenario
  files are frozen.
- Mako and Flask-HTTPAuth install hash-pinned dependencies at image build (MarkupSafe; Flask
  and its six dependencies). The other eight need nothing beyond the standard library.
- Same bar as the 27 Tier A test scenarios: validator, every PoC test failing on the vulnerable
  code, repair prompts from PoC and regression feedback passing the secret filter, and a
  second, differently written fix resolving. One alternative fix was wrong in a way the
  project's own test caught (Flask-HTTPAuth must return `None`, not `False`, for "no user").
- They are under their own key `test_b` in `split.json`, frozen at 10. dev and test are as they
  were. `pytest -q -rs`: 296 passed, 0 skipped.

**Harness changes for Tier B** (commit `e382773`; none touches the loop, the context, the
prompts or the gates)
- Validator check 4 is skipped when the finding does not come from a scanner, as doc 11 §6
  says. The rule test in `test_scenarios.py` covers scanner findings only.
- The report prints `-` for "Rule gone" when there is no rule to re-run.
- Sandbox and build logs are written as UTF-8. Real code contains characters that Windows'
  default encoding cannot write (geopy's prime signs), which would have crashed a run.

**Limits of this tier**
- **Selection bias.** Only small fixes inside one function of one file, in small pure-Python
  libraries. Real fixes that span files, need native code or services are not represented, so
  these ten are the easy end of real CVEs.
- **Authoring bias is reduced, not gone.** The vulnerable code and the fixes are other people's.
  The scenario descriptions, the PoC test code and writing or choosing the regression tests
  were done by a Claude model.
- **Three scenarios depend on time** (geopy, hpack, pyasn1): their PoC runs the call in a child
  process with a 5-second limit. On this laptop the vulnerable code needs well over that for
  the PoC inputs (measured on smaller inputs: 18 s for hpack, over 12 s for pyasn1, over 8 s
  for geopy); a much faster machine would need larger inputs.
- **sqlparse's fix has a twin** in the PHP output filter. Only the Python filter is shown to the
  model and checked by the PoC; the reference patch fixes both.
- **No "before release" group.** All ten advisories are later than Qwen3.5's release, so the
  memorisation comparison of doc 09 §9 cannot be made. Fix commits were public 2 days to 3
  months before their advisories, and six of the ten fixes were public before July 2026.
- **Memorisation cannot be ruled out for the frontier reference.** `claude-opus-5`'s training
  cutoff is not in the model table I checked (it gives June 2026 for `claude-opus-5-5`, a later
  model). Six of the ten fixes were public before July 2026 and three before May, so Opus may
  have seen some of these fixes. Its 10/10 is not evidence either way.
- **The CWE mix differs from Tier A.** CWE-94, 113, 287, 347 and 400 are not in doc 11's list;
  real advisories did not line up with it.

**Baselines on Tier B** (10 scenarios, `--jobs 1`, commit `e382773`, every header `dirty: false`)

| Config | Resolved (95% CI) | By attempt 1 / 2 / 3 | Run | Notes |
|---|---|---|---|---|
| `repair-local` | 5/10 (24–76%) | 4 / 4 / 5 | `20261005-160032` | 47 tok/s, p50 10.3 s, $0 |
| `repair-local` | 5/10 (24–76%) | 5 / 5 / 5 | `20261005-161537` | The same five scenarios |
| `repair-claude-code` | **10/10** (72–100%) | 9 / 10 / 10 | `20261005-160526` | One repair; $0.45 API-equivalent |
| `cascade-claude-code` | **10/10** (72–100%) | 3 / 4 / 10 | `20261005-160808` | 4 local, 6 escalated and resolved; $0.69 |
| `oracle` | 10/10 | - | `20261005-160005` | |

- **The local model resolves half of the real CVEs, and the same half each time**: Mako,
  microdot, Flask-HTTPAuth, PyJWT's empty key and hpack. All five need one added guard or
  condition (upstream fixes of 2 to 13 lines). It failed mistune, sqlparse, geopy, PyJWT's PEM
  check and pyasn1 in both runs. In the cascade run microdot also went to Opus.
- **5/10 here against 17 and 18 of 27 on Tier A is not a measured drop.** The intervals overlap
  widely at n = 10. What can be said: the untuned model is not only solving home-written code.
- **Opus resolved all ten, and needed the repair loop once.** Its first Flask-HTTPAuth fix
  returned `False` for "no user" where the library's own test expects `None`; the second
  attempt passed. That test came from the project, not from me.
- **Local against Opus: 0 against 5 discordant scenarios, exact McNemar p = 0.062.** Not
  significant at this size; with Tier A (p = 0.002) the direction is the same.
- **The cascade cost more than Opus alone again**: $0.69 for 6 escalations ($0.115 each)
  against $0.45 for 11 direct attempts ($0.041 each). An escalation carries two failed local
  attempts and their test output, and these files are larger than Tier A's.
- **Why the local model failed** (read from each attempt): on geopy it broke the docstring's
  triple quotes three times, or changed the pattern and broke a valid format; on PyJWT's PEM
  check it rewrote the regular expression and dropped two of the three closing quotes, then
  repeated itself; on mistune it decoded the URL but blocked allowed data images or missed
  double encoding; on sqlparse its first fix still let the snippet run code, then it repeated
  itself; on pyasn1 its guards rejected ordinary values or missed the zero case. No failure
  traces back to a scenario defect, a gate misfire or the secret filter.
- No refusals and no secret blocks in any run.

## Week 3, D15 (2026-10-06 and 07): a free local teacher, a rebuilt generator, 531 real fix pairs

**Teacher: `qwen3.5:9b-q4_K_M`, run on the laptop.** You asked for a model you can download and
use at no cost, so no hosted model was used and no prompt left the machine.
- Of the four hosted tags in your Ollama, `glm-5.1:cloud` was retired on 2026-09-25 and
  `qwen3.5:cloud` answers 410. `kimi-k2.6:cloud` and `minimax-m2.7:cloud` work and bill per
  token ($4.00 and $1.20 per million output tokens).
- Qwen3.5-9B is Apache-2.0 and 6.6 GB at Q4_K_M. It is the largest Qwen3.5 that fits 16 GB of RAM
  with 4 GB of VRAM; the next size, 27B, is 17 GB. Run locally, no host's terms apply, which
  closes the "terms on training with outputs" item of doc 09 §4.
- Speed on this laptop with a 4,096-token context: **7.3 tokens/s with 20 layers on the GPU**.
  Ollama's own split gives 4.0 and all layers on the GPU 3.3 (it spills into shared memory).
  `inject_cwe.py` has `--num-gpu` and `--num-ctx` for this.
- The cost of this choice is speed: a candidate takes about 3 minutes, against the 60 s the plan
  assumed, so 24 hours give about 475 candidates, not 1,440.

**The generator was rebuilt during the pilot**, because the first 14 candidates kept nothing.
What a 9B teacher got wrong, and what `training/inject_cwe.py` does now:

| Fault seen | Change |
|---|---|
| Two full copies of the module differed in docstrings and helpers (`injection_size`, 3 of 7) | The teacher writes the fixed module and one SEARCH/REPLACE block that plants the flaw; the script builds the vulnerable copy with `aeropatch.agent.edits`. A third fewer output tokens |
| PoC tests passed on both versions | Each CWE carries one PoC idea that separates them. The student never sees a test |
| A test used a name it did not import, so the whole file failed | Missing imports are added: the module's names, stdlib modules, pytest |
| One wrong test among six sank the candidate | Tests the sandbox does not bear out are removed. A PoC test stays if it fails on the vulnerable code and passes on the fixed code; a regression test stays if it passes on both. At least 1 and 2 must be left, and validator checks 1–3 then run unchanged |
| Planted lines carried comments such as `# Missing upper bound check` | Every comment on a planted line is cut; give-away wording in a planted docstring rejects the candidate |
| One shared idiom, `scheme not in ("http", "https")`, was a `leakage` reject | A candidate is dropped above 30 shared 13-token runs (about four copied lines). The count is in the manifest (`eval_overlap`) for the D16 leakage report to look at |

Also new: rejected answers are saved under `training/synthetic/rejects/` with the failed check,
the manifest records the prompt version, generation seconds and output tokens, and a run stopped
mid-candidate cleans up its half-written directory on restart.

**Pilot.** 47 candidates in all; the manifest's `prompt` field tells the versions apart.

| Version | Candidates | Kept | Rejects |
|---|---|---|---|
| 1: two full modules | 7 | 0 | `injection_size` 3, check 1 twice, `leakage` 1, `no_target` 1 |
| 2: fixed module and one block | 3 | 0 | check 1 twice, `gives_away` 1 |
| 3: a PoC idea per CWE | 4 | 0 | `no_poc_separates` 2, `gives_away` 1, `format` 1 |
| 4: imports added, tests pruned | 3 | 2 | check 3 once |
| **5: planted comments cut (the pilot of 30)** | **30** | **10** | `no_poc_separates` 7, `injection_size` 4, check 3 three times, `no_target` 3, `secret` 2, a syntax error 1 |

- **Yield 33% (10 of 30), 182 s per candidate**: 171 s to generate 1,577 tokens on average, and
  about 15 s in the sandbox for a candidate that reaches it.
- **No `leakage` reject under the new rule.** 13 of the 47 candidates share 1 to 4 runs of 13
  tokens with benchmark code; the old rule would have dropped every one of them.
- Kept by CWE in the 30: 328 (3 of 4), 22 (2 of 2), 89, 601, 798, 918 and 327 (1 each).
  Nothing for 352 (0 of 4, two stopped by the secret filter), 338, 502 and 78 (0 of 2 each).
- The yield is slightly understated: a test id with a dot in a parameter
  (`test_x[http://127.0.0.1/x]`) was read wrongly by the pruning step until after the pilot.

**Sizing.** Expected kept = 24 h × 3,600 × 0.33 ÷ 182 s = about 158. That is the bottom row of
the plan's table (under 300), whose answer is "fix the prompt or change teacher". The prompt is
fixed (0% to 33%) and the teacher is the largest that fits, so the gap is speed. Consequences:
- The synthetic slice will be about 160 examples, not 800. Mined fix pairs carry the
  first-attempt slice, and the repair-turn slice shrinks with it.
- The total will probably land under R4's fallback of 1,500 unless the general bug-fix slice
  grows or generation continues after D16. That is a D16 decision, once `stats.md` exists.
- A hosted teacher would be several times faster (not measured; `kimi-k2.6:cloud`, an estimated
  $12 to $20 for the night). You declined paid models; this is here so the trade is on record.

**Overnight run.** Started 2026-10-06 15:19, detached, 500 candidates:
`uv run python training/inject_cwe.py --teacher qwen3.5:9b-q4_K_M --count 500 --num-gpu 20 --num-ctx 4096`,
log in `training/synthetic/overnight.log`. At the pilot's pace it ends about 16:40 on
2026-10-07. It can be stopped and started again with the same command; never two at once.
The laptop is on AC with sleep-on-AC off. Closing the lid may still suspend it.

**Found while the run was going (evening of 2026-10-06).** After 98 candidates the kept rate was
17%, not the pilot's 33%. Two checks were throwing away usable answers. Both are changed in
`training/inject_cwe.py`; the process started at 15:19 still runs the old code.
- **Class-based modules were rejected as `no_target`** (14 of 98). The target had to be a
  top-level function. A method now counts and is named `Class.method`. Re-checked apart from the
  run, 5 of the first 9 pass everything.
- **Check 3 asked for more than training data needs** (13 of 98). It wants a regression test to
  fail when the target's body is deleted. Pruning often leaves that to the PoC tests: in 16 of
  17 such rejects the deleted body still fails a PoC test, so it is not judged resolved. Those
  are now kept with `"note": "check 3 by a PoC test"` in the manifest. **This relaxes the
  acceptance rule and is yours to overrule**; the note lets D16 leave them out.
- **Nothing is lost by not restarting.** Every rejected answer is in
  `training/synthetic/rejects/`, so the `no_target` and check-3 rejects can be re-checked with
  the new code when the run ends. Expect roughly 20 more kept from the first 98.
- Not a fault: the sandbox was checked twice during losing streaks (14 rejects in a row) and
  reported real test results each time. At 98 candidates the teacher looked weakest on CWE-89
  and CWE-918; the whole run says otherwise (below).

**Result (2026-10-07): 189 training examples, 128 of them without the relaxed check 3.** The run
ended by itself at 17:07 after 25 h 48 min: 500 candidates, 185 s each on average (175 s to
generate 1,632 tokens, 9.3 tokens/s), nothing in `overnight.err.log`.

| | Answers | Kept |
|---|---|---|
| The run as it ran, with the old code | 500 | 105 (21%) |
| Its `no_target` and check-3 rejects, re-checked with the new code | 104 | 74 |
| of them: a method as target, no rule changed | | 16 |
| of them: check 3 met by a PoC test, the relaxed rule | | 58 |
| **Overnight in all** | 500 | **179 (36%)** |
| Pilot: 7 kept, and 3 more by the relaxed rule out of 7 re-checked | 47 | 10 |
| **Training examples** | | **189** |

- **The relaxed check 3 is still yours to overrule.** 61 of the 189 carry
  `"note": "check 3 by a PoC test"`; without them the set is 128.
- **Rejects of the run as it ran:** `no_poc_separates` 147, `injection_size` 67, check 3 60,
  `no_target` 44, `gives_away` 18, `inject_not_applied` 16, `syntax` 13, `format` 10 (one looked
  at: the fixed module alone used all 3,500 tokens), `regression_tests_wrong` 9, check 1 3,
  `secret` 3, a test file that does not parse 2, `leakage` 1 (43 shared runs), check 2 1 (a
  regression test passed while pruning and failed in the validator), a Docker error 1.
- **The re-check** took the 112 saved answers of both kinds, pilot included, through today's
  checks in the order `main()` uses. Its log is `training/synthetic/recheck.log`; the manifest
  as the run left it is `manifest.before-recheck.jsonl`. A re-checked record has `"was"`, its
  first status, and `"status"` is what today's code says.
  - Check 3 (64): 59 kept by a PoC test; in 5 the deleted body passes every test.
  - `no_target` (48): 18 kept (16 with no rule changed, 2 by a PoC test), 13
    `no_poc_separates`, 7 `injection_size`, 6 still `no_target` (one answers the first pilot
    prompt and was left alone), 2 `regression_tests_wrong`, 1 check 3, 1 a test file that does
    not parse.
- **Leakage: 46 of the 189 share text with Tier C, and the limit lets them all through.** A scan
  of all 189 against today's benchmark finds none above the limit of 30 shared runs; 83 share
  at least one run with some benchmark file. The 46 (32 of the 128) share runs found only in
  Tier C: 4 share one run, 27 share 2 to 5, 10 share 6 to 10, 5 share 11 to 22 (`S-89-00164`
  has the 22). They are mostly CWE-328 (20) and CWE-89 (13), the same teacher writing the same
  kind of module as `C-328-01` and `C-089-01`. Dropping every one leaves 143 (96 without the
  relaxed check 3). **Where to put the Tier C limit is yours to decide on D16.**
- `eval_overlap` in the manifest is the count at the time of the check. Tier C was already in
  the benchmark when the run started, with the docstrings it had before the rewording at 15:36,
  so 5 of the counts recorded before the re-check differ by 1 to 3 from a scan today. D16
  should recompute, not read the field.
- The re-check script was a one-off and is not in the repository. It mirrored the order of
  checks in `main()`; the generator's code today gives the same verdicts on a new run.
- **By CWE** (candidates, kept, overnight only): 328 (72, 39), 918 (68, 27), 89 (56, 16),
  327 (23, 16), 601 (40, 15), 20 (23, 12), 79 (21, 12), 798 (23, 9), 78 (44, 7), 22 (27, 6),
  1333 (25, 6), 338 (16, 6), 352 (13, 4), 209 (30, 3), 502 (19, 1). The teacher is weakest on
  CWE-502, CWE-209 and CWE-78.
- The scanners flag 35 of the 189 (`scanner_flagged`).
- **`no_poc_separates` is the largest loss** (169 with the pilot) and is not diagnosed. One
  guess is ruled out: none of 156 PoC files imports a name its module lacks, and 2 import from
  a wrong module path. The rest needs sandbox runs.

**Tier C: 5 scenarios, set aside before the overnight run** (your default from the plan).
`C-020-01`, `C-022-01`, `C-089-01`, `C-328-01` and `C-601-01` are the pilot's `S-20-00015`,
`S-22-00019`, `S-89-00029`, `S-328-00030` and `S-601-00033`. Their manifest status is `tier_c`,
their directories are in `evaluations/scenarios/`, and `split.json` has the key `test_c`.
- They were set aside before the overnight run, not before every training example: 12 pilot
  candidates were already kept, and these are 5 of those 12.
- The code and the code change of the reference fix are the teacher's.
- **Docstrings were reworded in four of the five.** The teacher's docstrings come from the fixed
  module and described protection the vulnerable code lacks ("Uses parameterized queries to
  prevent SQL injection", "using PBKDF2 with SHA256 and a unique salt", "Returns the validated
  path or '/' if unsafe"). They now say only what is true of both versions, and the same words
  went into both, so each reference patch keeps its code change. `C-020-01` needed none.
- The descriptions, the finding messages and the PoC tests are mine, rewritten to the Tier A
  bar: behaviour only, either valid rejection accepted (`PermissionError` or `ValueError`; no
  rows or a refused non-number). `C-020-01` also got one regression test at the boundary.
- Checked for each: the validator passes, every PoC test fails on the vulnerable code, the
  repair prompt passes the secret filter, the reference fix passes the gates, and a second,
  differently written fix resolves (a chained comparison; `realpath` with `commonpath` raising
  `PermissionError`; `int()` with `BETWEEN`; `scrypt`; an inline `urlparse` check). The oracle
  resolves 5 of 5 on `test_c`.
- No model has been run on them. They are easy: one function, and in `C-022-01` and `C-601-01`
  the fix pattern sits elsewhere in the same file.
- The other 7 pilot examples are training data. How much overlap with these five a training
  example may have is open: 46 of the 189 share at least one 13-token run with them (see the
  result above), and `prepare_dataset.py` applies whatever limit is chosen (D16).

**What to look for when reading 30 examples on D17**
- A pruned PoC can separate the versions for a functional reason. In `S-328-00037` the PoC is
  "the right password verifies": MD5 broke the verify function. The fix is still the real one.
- Docstrings come from the fixed module and stay in the vulnerable one, so some name the fix
  ("using PBKDF2") above code that does not do it. A keyword match, not a reading, finds such
  wording in the target function's docstring of 6 of the first 9 kept examples. Tier C was
  reworded for this; the training examples were not. A model that learns to make the code match
  its docstring would look better on synthetic data than on real code, so decide on D16 whether
  to reword or filter them.
- `S-798-00017` and `S-798-00028` plant "changeme" in odd places; the teacher is weak on CWE-798.

**Defaults taken today, yours to overrule:** fix pairs from the GitHub advisory database (not
MoreFixes); Tier C built; the generator's leakage rule relaxed as in the table above, with every
overlap recorded for D16; the context format and the CWE weights left as they were.

**`training/prepare_dataset.py`, first part: real fix pairs.** `mine` lists the reviewed pip
advisories published before 2026-01-01 and keeps one pair per fix commit; `spotcheck` re-applies
random pairs.

| Step | Advisories |
|---|---|
| Reviewed pip advisories before 2026-01-01 | 4,205 |
| Not exactly one fix commit | 2,053 |
| Not exactly one modified non-test Python file | 1,106 |
| Commit not found (17) or a merge (258) | 286 |
| Same commit as an earlier advisory | 185 |
| More than 60 changed lines | 33 |
| Benchmark project (exclusion list) | 7 |
| Blocks do not re-apply byte-exact | 4 |
| **Kept** | **531** |

- 531 pairs from 296 repositories, advisories from 2018-07-12 to 2025-12-19. Most frequent:
  CWE-22 (51), CWE-79 (40), CWE-200 (29), CWE-20 (25), CWE-502 (20), CWE-601 (19).
- **Spot check: 20 of 20 re-apply byte-exact** (seed 3407), and none of the 531 comes from a
  benchmark project or after the cutoff. The check parses the stored assistant message with
  `edits.parse` and applies it with `edits.apply_edits`, as the loop does.
- The exclusion list is the nine Tier B projects, matched on repository name and on package
  name. `tests/test_prepare_dataset.py` fails if a Tier B scenario's project is missing from it.
- A fix that only removes the file's final newline, or whose changed lines hold a line of
  5 to 9 equals signs, has no target: `edits` cannot express either.
- Not applied yet (D16): the filters of doc 09 §7. 370 pairs have one or two blocks; 23 have more
  than six, and the largest file is 14,666 lines.
- 258 advisories point at a merge commit and were dropped. Diffing a merge against its first
  parent would recover some of them.

## Week 3, D16 (2026-10-09): student pass, bug-fix slice, filters, 554 examples

**Result: 554 examples, 526 in `train.jsonl` and 28 in `val.jsonl`.** That is under R4's fallback
of 1,500. `training/stats.md` has every count below and is written by the build;
`training/data/leakage.md` has every overlap with the benchmark. Nothing is frozen: the spot
check of 30 and the freeze are D17.

| Slice | Examples | Share | Plan (doc 09 §8) | From |
|---|---|---|---|---|
| Security fix, first attempt | 374 | 68% | 55% | 228 advisory pairs, 146 synthetic |
| Repair turns | 69 | 12% | 20% | 51 synthetic scenarios the student failed on |
| General bug fixes | 111 | 20% | 20% | 44 SWE-Gym, 67 SWE-smith |
| Format practice, counted inside the slices above | 47 | 8% | 5% | 11 repairs after a format failure, 36 fixes of 3 or more blocks |

- 215 examples are checked by the sandbox (the synthetic ones). The other 339 re-apply
  byte-exact and have no test.
- Every written example was read back: 554 targets parse, every SEARCH is in its prompt, ids
  are unique, and no repository or synthetic scenario is on both sides of the split.

**Student pass: 111 of 189 resolved at the first attempt, 156 within three.** Run
`20261009-student-pass`, `repair-local` (untuned `qwen3.5:4b`), 54 minutes, median 10 s a scenario.
- 154 failed attempts: POC_FAIL 80, REGRESSION 35, FORMAT_FAIL 21, SEARCH_NOT_FOUND 10,
  GATE_REJECT 4, SEARCH_AMBIGUOUS 3, IMPORT_ERROR 1. Weakest by CWE: 1333 (4 of 6), 20 (8 of 12),
  918 (19 of 28).
- **The run stopped once, and I caused it.** At 181 scenarios Windows refused to start a process
  (`WinError 1455`, paging file too small) while a memory-heavy check of mine ran beside it.
  `inject_cwe.py` has `--run-id` since this morning, so the same command finished the last 9.
  One scenario (`S-89-00111`) lost its third attempt to an Ollama out-of-memory error.
- **Parity: 0 mismatches.** A repair turn is rebuilt from the run file with the loop's own
  functions, and the build compares it with every `prompt.txt` the student was sent for a
  scenario in the set (240 prompts). The first message of each synthetic example is checked
  the same way. That covers 64 of the 69 repair turns in the set. The other 5 end a
  conversation (the feedback on a last attempt, which was never sent on), so no prompt on disk
  holds them. 3 turns follow a third attempt, a conversation that `repair-local` never sends.

**General bug fixes** (`prepare_dataset.py general`, about 15 minutes): 894 pairs through the
advisory converter. Rows come from the Hugging Face datasets-server as JSON, so no new dependency.
- SWE-Gym, all 2,438 rows: 555 pairs from 11 repositories (at most 60 files fetched per
  repository). Its patch is the fix.
- SWE-smith, 4,300 of 59,136 rows (one page in fourteen): 339 pairs from 37 repositories. Its
  patch plants the bug in a clean copy, so the fix is the reverse.
- **The exclusion list dropped 100 SWE-smith rows from benchmark projects.** SWE-smith names a
  repository `owner__name.commit`; `smith_repo()` turns that back before the check, and a test
  covers it.

**Filters** (pairs left after each step; the full table is in `stats.md`):

| Step | Advisory | Synthetic | SWE-Gym | SWE-smith |
|---|---|---|---|---|
| Converted, or kept by the sandbox | 531 | 189 | 555 | 339 |
| A CWE on the advisory | 510 | 189 | 555 | 339 |
| At most 60 changed lines in at most 2 functions | 419 | 189 | 472 | 288 |
| At most 6 hunks, none whitespace only | 401 | 189 | 460 | 238 |
| **Every SEARCH line is in the prompt** (new) | 304 | 189 | 384 | 179 |
| The fix passes the loop's gates (new) | 293 | 189 | 381 | 179 |
| Dedupe | 293 | 188 | 380 | 179 |
| **Within 2,048 tokens** | 238 | 188 | 206 | 157 |
| Secrets | 232 | 188 | 192 | 157 |
| Leakage | 228 | 146 | 191 | 157 |
| At most 30 per CWE and repository | 228 | 146 | 189 | 157 |
| General bug fixes held to 20% | 228 | 146 | 44 | 67 |

- **Two filters are not in doc 09.** A file over 60 lines is shown as one function, so a fix
  that also edits code outside it would train the model to edit what it cannot see: 232 pairs
  dropped. And a fix the loop's gates reject is not a target: 14 dropped (8 do not parse as
  Python 3, 5 add a `# noqa` or `# nosec` comment, 1 adds a risky import).
- **Two changes rescued pairs.** The finding of a mined pair now points at the first changed
  line inside a function, not at the import the fix adds above it (about 50 advisory pairs).
  The converter also tries blocks with less context, or context on one side only, when a
  neighbouring line is out of view.
- **Dedupe and leakage compare function with function**, on 5-token runs with identifiers
  blanked, as section 3 of the Week 3 plan decided. Comparing a benchmark function with a whole
  prompt flagged 196 pairs falsely on the first try. Two near-duplicates were dropped (more than
  two functions 80% alike); 56 pairs of functions are that alike in all, mostly two bugs in one
  SWE-Gym or SWE-smith function, and stay.
- **Length is the largest loss after context: 251 pairs and 46 repair turns** are over 2,048
  tokens. Tokens are estimated at 3.6 characters each (Ollama counted 4.05 on average over the
  student's prompts, under 3.7 for 5% of them); a repair turn the student was sent uses Ollama's
  own count. **At 4,096 the set is 661 examples**: 420 first attempts, 109 repair turns, 132
  general. `build --max-tokens 4096` writes that set.

**Leakage: 47 pairs and 4 repair turns dropped. 48 of the 485 kept pairs and 6 of the 69 kept
turns share some text with the benchmark, and I read every shared passage.**
- No pair comes from a benchmark project and no advisory is from 2026.
- 35 synthetic examples share at least one 13-token run with a Tier C scenario and are dropped
  (the limit is zero, your default). D15 counted 46 on the whole module, and that count is 48
  today; the build counts on the prompt and the target, and a module over 60 lines is shown as
  one function.
- **12 more are dropped by a rule I added: no shared run may touch a line that a benchmark
  reference fix removes or adds.** Four synthetic CWE-327 examples held
  `hashlib.md5(data).hexdigest()` and its `sha256` twin, which is the whole reference fix of
  `A-327-01`; two held the fixed regular expression of `A-1333-02`. The rest: one synthetic
  CWE-328, four advisory pairs and one SWE-Gym pair with a common idiom on a fix line
  (`os.path.realpath(os.path.join(`, `.encode("utf-8")).hexdigest()`, a `.replace` escape).
- **A repair turn is checked on what it adds to the prompt**: the student's edits and the test
  output. 4 turns are dropped. In the first turns of `S-328-00127` and `S-328-00525` the student
  wrote the fix line of `C-328-01`; both turns of `S-918-00185` share 2 runs with `C-601-01`.
  The 6 kept turns share a typing signature, a number pattern, `.decode('utf-8'))` and
  `scheme not in ("http", "https")`.
- **The format example in the system prompt shares a line with the reference fix of `A-089-01`**
  (dev): `... FROM users WHERE name = ?", (name,))`. Every model has seen it in every prompt
  since Week 1, so it is a property of the benchmark, not of the training set. The scan of a
  repair turn leaves the example out, or every repair after FORMAT_FAIL would be dropped.
- No training function overlaps a benchmark target function by half; the closest is 47%, a
  three-line getter.
- What the 48 kept pairs share, at most 9 runs with one scenario: comment rulers and docstring
  underlines, import and typing lines, `open(path, "w", encoding="utf-8")`,
  `os.path.abspath(os.path.join(`, `def __init__(self, *args, **kwargs)`, two URLs, and the
  host list `("localhost", "127.0.0.1", ...` of `A-918-02` in three synthetic CWE-918 examples.
  That list is an unchanged line there; the fix of `A-918-02` resolves the host name.

**Defaults taken today, yours to overrule**
- The 61 examples that pass check 3 only by a PoC test are kept (46 of the 146 synthetic first
  attempts). They are ordered last, so a cap drops them first.
- Tier C limit zero; the fix-line rule above; general bug fixes at 20%; the 2,048 limit.
- **No generator for format practice.** Real examples already make 8%: repairs after a format
  failure and fixes of three or more blocks.
- **Finding wording.** Synthetic prompts keep `synthetic rule synthetic.cwe-N`, as Tier C has it.
  Advisory pairs read as Tier B does (`advisory rule advisory.cwe-N`). A bug fix reads `Bug
  reported by issue rule issue.bug`, with the issue title as the message and the issue text as
  the description. No training prompt says `opengrep` or `bandit`, which is what Tier A says.
- Docstrings that name the fix are left in: 32 of the 146 synthetic first attempts by a keyword
  match.
- `stats.md` is in git (`training/stats.md`), because it holds counts only. The examples and
  `leakage.md` stay in `training/data/`, which is ignored.
- One line changed in `src/`: `gates.check` built a set of the file's lines once per line, which
  took seconds on a 5,000-line file. Same result, and the gate tests pass. The first 180
  scenarios of the student run ran before the change and the last 9 after it. The run header
  says commit `4c43b51` and not dirty for all of them: it is written once, at the start, and
  `dirty` does not watch `training/`, where `--run-id` was added.

**For the reading of 30 on D17**
- **33 of the 485 first targets call a function the prompt does not show** (20 synthetic, 9
  advisory, 4 SWE-Gym), such as `validate_quantity` in `S-20-00162`. A regular expression found
  them, not a reading. Decide whether to filter them: they teach calling a helper on faith.
- The RATIONALE of every target is the finding's message, so it states the flaw, not the fix.
  For advisory and synthetic pairs the message and the description are the same sentence.
- **Only `target` may be trained on.** The assistant messages inside `messages` are the student's
  failed edits; `finetune.py` has to mask them, which `train_on_responses_only` alone does not.
- Call sites in a training prompt come from the same file only; at inference they can come from
  the whole repository.
- The length limit is an estimate until the real tokenizer runs on Kaggle.

## Week 3, D17, first part (2026-10-12): the reading, `finetune.py`, the template check

Steps 1 to 4 of `docs/14-timeline-part4.md` are done. **Steps 5 to 9 wait for the Kaggle API
token**: there is none in `%USERPROFILE%\.kaggle\`. Nothing is frozen, because the sequence
length depends on the pilot.

**The set after the reading: 470 examples at 2,048 tokens (445 train, 25 validation), or 541 at
4,096.** It was 554 on D16. Three filters and exact token counts changed it.

| Slice | At 2,048 | At 4,096 | From |
|---|---|---|---|
| Security fix, first attempt | 345 | 380 | 240 or 275 advisory pairs, 105 synthetic |
| Repair turns | 31 | 53 | synthetic scenarios the student failed on |
| General bug fixes | 94 | 108 | SWE-Gym and SWE-smith |

**The reading (doc 09 §10): 3 of the 30 random examples were wrong or silly, which is the
limit, and 3 of the 8 repair turns I read were bad.** So I read every synthetic fix in the set
(124) and the PoC tests of the 36 scenarios the student had failed on.
- **20 synthetic scenarios are rejected by name, with a reason each, in `training/rejected.txt`.**
  The build leaves them out with their repair turns. Three fixes do the opposite of what the
  CWE asks: `S-798-00263` replaces an environment lookup with a hardcoded credential, and two
  CWE-918 fixes allow only localhost. Seven cannot work or change the function's contract (a
  salt that is made and thrown away, a renamed parameter). Three are too weak to teach. In
  seven the planted flaw is nonsense (`username = "hacker"`). 7 of the 11 CWE-798 scenarios
  are among them; D15 already found the teacher weak there.
- **Two PoC tests failed a correct fix of the student** (`S-338-00032`, `S-601-00473`): the test
  checked a side effect of the teacher's own fix. Their repair turns would have taught the
  model to give up a right answer.
- Of the 18 advisory pairs in the sample none was wrong. `GHSA-74xw-82v7-hmrm` is odd but
  real: the upstream fix uses `exec` and the `imp` module. Of the 5 bug fixes one was bad, a
  SWE-smith bug with a comment that says what is broken; the second filter below removes those.
- Two things hold for the whole set and were not counted per example: every RATIONALE repeats
  the finding's message, and some docstrings name the fix.

**Three filters came out of it** (pairs dropped at the step, in the 2,048 build):

| Filter | Dropped | Why |
|---|---|---|
| The fix uses no function, class or constant of the file that the prompt hides | 37 | The target of `S-20-00162` called `validate_quantity`, which the prompt did not show. An AST check replaces the D16 pattern match: 25 synthetic, 11 SWE-Gym, 1 advisory |
| No SWE-smith bug that a comment announces | 35 | Its bug writer sometimes says what it broke: `# Off-by-one error: Starts from 1 instead of 0`. The general slice refilled from spare pairs |
| Not a fix that was read and rejected | 20 | The list above |

**Template check: the Hugging Face chat template and Ollama build the same prompt.** The
tokenizer of `Qwen/Qwen3.5-4B` is public and runs on the laptop without a GPU.
- 25 sampled student prompts (12 first prompts, 8 with one repair turn, 5 with two): the token
  count with thinking off equals Ollama's `prompt_eval_count` every time. With thinking on it
  is 2 lower, so Ollama does send the empty think block.
- `finetune.py` repeats the check on every example that carries Ollama's count and stops the
  run on a mismatch: 135 prompts in the 2,048 set and 148 in the 4,096 set, all equal.
- A final assistant turn rendered by the template is the generation prompt, the target and
  `<|im_end|>`. Earlier assistant turns carry no think block.

**Token counts are exact now.** `build --tokenizer Qwen/Qwen3.5-4B` counts each example as
`finetune.py` encodes it (run it with `uv run --with transformers --with jinja2`; the project
gains no dependency). The D16 estimate was 10% high on average, so the 2,048 set grew from 452
to 470. Run on both sets, `finetune.prepare` drops nothing for length, and every target decodes
back exactly.

**`training/finetune.py`** (not run on a GPU yet; the pilot is its first run):
- Each example is the rendered prompt, then the target's tokens, then the end-of-turn token.
  Labels are -100 over the whole prompt, so the student's failed edits inside a repair turn are
  never learned. A test with a stand-in tokenizer checks this on the laptop.
- **Change from doc 10 §2: `transformers.Trainer`, not TRL's `SFTTrainer`.** The examples arrive
  tokenised and masked, so nothing of TRL's text handling is wanted.
- Arguments cover the pilot (`--max-steps 50`), the memory probe (`--longest 50
  --max-seq-length 4096`), the full run and the untuned control (`--max-steps 0 --gguf q4_k_m`).
  Everything measured goes to `pilot.json`.
- Tokens are built with the plain tokenizer the check above was made with. The model also
  takes images, so Unsloth may return a processor; that object is used for saving only.
- `training/kaggle/kernel.py` is a script kernel that clones the repository and calls the
  script. It reads the code from GitHub, so this work has to be pushed before the pilot. It
  asks for a T4: Unsloth needs CUDA capability 7.0, and Kaggle's other GPU, the P100, has 6.0.
- `training/requirements.txt` says `unsloth` and is not pinned: the kernel saves `pip freeze`
  on its first run, and the pins come from that.

**Kaggle, later the same day.** You created the account and the token (username
`<kaggle-username>`; the token is in `%USERPROFILE%\.kaggle\access_token`).
- Both sets are uploaded as private datasets, `aeropatch-train` (470 examples) and
  `aeropatch-train-4096` (541). Kaggle reports them ready and private.
- **The kernel ran twice and had neither a GPU nor internet** ("GPU: False, internet: False" in
  its log, 40 seconds each), although its settings ask for both and for a T4. That is what
  Kaggle gives an account whose phone number is not verified. Nothing else ran on it.
- Two things learned about the command line on Windows: `datasets create` has to be run from
  inside the folder (with a relative `-p` path it fails on its own temporary file), and `-t`
  keeps the `.jsonl` files from being turned into CSV.
- The kernel now runs the pilot, the memory probe and the control in one session, under
  `/tmp`, and stops at once with a clear message when it has no GPU or no internet.
- `finetune.py` asks Unsloth, not torch, whether bf16 is supported: torch counts emulation and
  says yes on a T4. That fix is committed but not on GitHub yet, and the kernel clones from
  there.

**The pilot ran (kernel version 8, 47 min 49 s on one Kaggle T4): it trains, it fits, and the
export works.** Your phone was verified by then, and Kaggle gave two T4s and internet.

| Check (doc 10 §4) | Result |
|---|---|
| Loss over 50 steps of 8 examples | 0.40 at step 5, 0.21 at step 50; validation 0.242 at step 25, 0.233 at step 50 |
| Peak VRAM | 9.89 GB, against the limit of 14 |
| Speed | about 34 s a step once the first step's kernels are compiled (that step took 5 min 16 s); 33 min 44 s for the 50 |
| Examples dropped for length | 0 of 445; the longest is exactly 2,048 tokens |
| Prompts equal to Ollama's count | 129 of 129 in the training split |
| Validation outputs that parse | 5 of 5. This counts the format only: at least 3 of the 5 are wrong fixes (second part, below) |
| Export | `Qwen3.5-4B.Q4_K_M.gguf`, and `Qwen3.5-4B.F16-mmproj.gguf` for the model's image input |

- A full run of 2 epochs on this 2,048-token set would be about 111 steps, a little over an
  hour. The set that is trained is the 4,096-token one: 128 steps, about 90 minutes (second
  part, below).
- **Precision on a T4.** A T4 has no bf16. Unsloth prints "float16 precision for qwen3_5 won't
  work, using float32", yet the weights report float16 and the peak is 9.89 GB, so most of the
  model is 16-bit. `finetune.py` asks for bf16 only where Unsloth says the GPU has it and never
  for fp16 autocast.
- Kaggle has no L4 for this account: a kernel that asks for one gets no GPU.
- Versions on Kaggle that day are pinned in `training/requirements.txt` (Unsloth 2026.10.3,
  transformers 5.16.1, torch 2.11.0). transformers 5 has no `warmup_ratio`; the script passes
  5% as a number of steps.
- Unsloth writes no Ollama Modelfile for this model ("no template mapping found"), so the
  renderer lines of `docs/14-timeline-part4.md` §1 are needed by hand, as expected.
- Kaggle mounts a dataset under `/kaggle/input/datasets/<user>/<name>`; the kernel looks the
  folder up.
- **The pilot ran from the laptop's `finetune.py`, laid over the cloned one** (SHA-256
  `cacba103...` in the kernel's log), so that fixes could be tried without a push each time.
  The file in the repository is that one plus a renamed report key. A run that counts (D18) has
  to use pushed code.
- Kaggle's command line shows no log while a kernel runs. The website does, and its training
  lines appear in blocks, at each evaluation.

**D17 is complete (second part, the same afternoon).** Every item of `docs/14-timeline-part4.md`
§7 holds.

| Step | Result |
|---|---|
| Memory probe at 4,096 (kernel version 9) | **12.99 GB peak** on the 50 longest examples, 0 dropped, longest 4,087 tokens, 139 prompts equal to Ollama's count |
| Sequence length | **4,096**: the peak is under 14 GB and the full run is estimated at about 90 minutes of training (511 examples, 683,663 tokens, 2 epochs, 128 steps, 3.86 ms a token in the pilot) |
| **Dataset v1, frozen** | 541 examples: 511 train, 30 validation. 380 first attempts, 53 repair turns, 108 bug fixes |
| Export rehearsal | The pilot GGUF loads in Ollama with `training/Modelfile`, 100% on the GPU, 3,041 MiB, 47.5 tokens/s; it stops and writes the edit format. It resolved `A-089-01`, which shows nothing about fixing: that scenario's fix is the line of the system prompt's format example |
| Untuned control | Same export, no adapter: **9 of 13 on dev** (run `20261012-164903-repair-local-dev`), inside the library model's 7 to 10 |

- **SHA-256 of dataset v1**, the same files as the private Kaggle dataset `aeropatch-train-4096`:
  - `train.jsonl` `9ba0dec85a726cc090ad350fdedc6ce831fb46a195ca2a9293542a86b5e8870b`
  - `val.jsonl` `9ee09d3037df16669618a6e5dd297ca009ec4c6e64c8c30bd2fe074f1c18c916`
  `prepare_dataset.py` builds exactly these with its defaults (the limit is 4,096 now) and
  `--tokenizer Qwen/Qwen3.5-4B`; `training/stats.md` describes them.
- **The control matches the library model on the checks that were run**, and they are few. For
  one prompt Ollama counts 584 tokens for `qwen3.5:4b`, the control and the pilot, and at
  temperature 0 the control begins its answer with the same words as the library model. It
  failed `A-328-01`, `A-601-01` and `A-918-01`, the three the untuned model failed on
  2026-10-03, and `A-089-02`. The weights were not compared.
- **Untuned, 2 of 5 validation outputs parse; after 50 pilot steps, 5 of 5; after 6 probe
  steps, 4 of 5.** The format is learned early. The pilot also learned to write the finding's
  message as its RATIONALE, which is what every target does. **Parsing says nothing about the
  fix.** Of the pilot's 5 outputs at least 3 are wrong, read against their targets: one calls
  `exec` with four arguments (it takes three), one puts quotes around an escaped value where
  the reference refuses a dict, and one turns case-sensitive matching off where the reference
  replaces `unquote_plus` with `unquote`. Only the dev runs of D18 measure fixing.
- The exported text model reports 4.3B parameters; the image projector is a second file
  (`mmproj`) that the Modelfile does not load.
- One run of the control cannot be told from the library model's spread. D18 runs it three
  times, as planned. The pilot model was not run on dev.
- **Kaggle's command line downloads only the newest version's output.** Its API takes a version
  label such as `v8`; a scratch script used it to fetch the pilot's files after version 9 had
  started. Version 9 waited 15 minutes in Kaggle's queue.
- **The laptop ran out of memory again**, for about 40 minutes, while I polled Kaggle's live
  log through the browser. Commands could not start. You closed programs and it recovered.
- **Disk: 7.6 GB free on `F:`.** The two downloaded GGUFs and the projector (6.2 GB under
  `training/data/pilot` and `training/data/control`) are copies of what Ollama now holds, and
  the teacher `qwen3.5:9b` is 6.6 GB. D18 downloads up to three more GGUFs of 2.8 GB, and
  Ollama keeps its own copy of each.

**Defaults taken today, yours to overrule**
- **The sequence length is 4,096**, by the rule of the D17 plan.
- The 20 rejections. Each is one line in `training/rejected.txt`; delete a line to take the
  scenario back.
- The names filter and the SWE-smith comment filter.
- I did not reject fixes that are imperfect but point the right way, such as a path check by
  string prefix (`S-22-00265`).
- Leakage was read again for the new set: 45 of the 439 pairs and 4 of the 31 repair turns
  share text with the benchmark, the same kinds as on D16 and none on a fix line.

**D18 preparation (the same evening): checkpoints, their exports, and what LoRA reaches**
- **The run now keeps a checkpoint at every evaluation: steps 32, 64, 96 and 128.** Before, the
  kernel deleted them, and only the last adapter left Kaggle. 64 and 128 are the ends of the
  two epochs (511 examples in groups of 8 are 64 steps; transformers 5.16.1 counts the short
  last group as a step, read from its source). Each checkpoint is the adapter alone, about
  85 MB.
- **Each earlier checkpoint gets its own GGUF in the same Kaggle session.** D18 judges
  checkpoints through Ollama, and a later session cannot read this one's files.
  `finetune.py --max-steps 0 --adapter <checkpoint folder> --gguf q4_k_m` exports a saved
  adapter; the kernel runs it for steps 32, 64 and 96 after the training. The image projector
  is no longer copied out. Expected output: four GGUFs of 2.6 GB, 10.4 GB of Kaggle's 20.
- **The rehearsal passed (kernel version 10, 23 min 27 s).** 4 training steps saved
  checkpoints 2 and 4, each with its validation loss (0.428, then 0.349), and the kernel then
  exported checkpoint 2 to a GGUF with `--adapter`; both steps ended with exit code 0. The
  export carries the adapter: its 5 validation outputs differ from the untuned control's on
  the same prompts, and 4 of 5 parse against the control's 2. The run used the laptop's
  `finetune.py` laid over the clone (SHA-256 `b68aae38...`), the same file as commit `97ae347`.
- **The whole session should take about 2 hours 30 minutes**: 90 minutes of training, 14
  minutes of setup and the first export (the pilot's figure), and three more exports at 11
  minutes each (measured in the rehearsal). The total is my estimate.
- **The full run started at 17:38: kernel version 11**, from the pushed commit `97ae347`.
- **LoRA reaches the MLP of all 32 layers and the attention of 8.** Read from the pilot's
  adapter (256 tensors, 21.2 M parameters): `gate_proj`, `up_proj` and `down_proj` carry an
  adapter in every layer; `q_proj`, `k_proj`, `v_proj` and `o_proj` exist only in the 8
  full-attention layers. The other 24 layers are Gated DeltaNet, whose mixing weights are named
  `in_proj_qkv`, `in_proj_z` and `out_proj`, and they have no adapter.
  - **Default taken, yours to overrule: the first full run keeps these 7 module names.** They
    are the list of Unsloth's Qwen3.5 guide, the pilot's loss fell with them, and memory at
    4,096 tokens is already 12.99 GB of 14.
  - If dev does not move, adding the three DeltaNet projections is the first thing to try. It
    needs a memory probe first.
- **The control's three dev runs are done: 9, 8 and 9 of 13.** This is the number a tuned
  checkpoint has to beat. Every run failed `A-089-02`, `A-328-01`, `A-601-01` and `A-918-01`;
  the second also failed `A-078-01`.

  | Run | Resolved |
  |---|---|
  | `20261012-164903-repair-local-dev` | 9 of 13 |
  | `20261012-171355-repair-local-dev` | 8 of 13 |
  | `20261012-171917-repair-local-dev` | 9 of 13 |
- **Disk: 15.9 GB free on `F:`** after you agreed to the deletion: the three downloaded GGUF
  files and the Ollama model `aeropatch-pilot` are gone. The pilot's adapter and both
  `pilot.json` files are kept, and so is the teacher `qwen3.5:9b`.

## Week 3, D18 (2026-10-12): the full run, and both checkpoints score below the control

**The fine-tuned model resolves fewer dev scenarios than the untuned control: 20 of 39 against
26 of 39, for both checkpoints.** Every tuned run is below every control run. This is a
negative result, not a flat one: the band set before the runs was 2 points around 26.

| Model (Ollama name) | Run 1 | Run 2 | Run 3 | Total of 39 |
|---|---|---|---|---|
| Untuned control (`aeropatch-control`) | 9 | 8 | 9 | **26** |
| Step 64, end of epoch 1 (`aeropatch-step64`) | 7 | 7 | 6 | **20** |
| Step 128, end of epoch 2 (`aeropatch-step128`) | 7 | 7 | 6 | **20** |

**The full run (kernel version 11, commit `97ae347`, 2 h 20 min 31 s in all)**
- 128 steps in 89 min 30 s (42.0 s a step), peak 13.1 GB, 511 examples, none dropped, longest
  4,087 tokens. All four steps of the session ended with exit code 0.
- **Validation loss is flat from the first checkpoint on**: 0.2071 at step 32, 0.2052 at 64,
  0.2072 at 96, 0.2067 at 128. Training loss fell from 0.42 to 0.16 over the same steps. On 30
  validation examples these four values cannot be told apart.
- The plan's rule (the end of each epoch, and the lowest validation loss) gives steps 64 and
  128: the lowest loss is at 64. Step 32 and step 96 were exported too and were not judged.
- Both judged models were checked against the control before their runs: the same prompt is
  1,810 tokens for all three, each is 100% on the GPU (2,951 MiB), and each runs at 48 tokens
  a second. Their SHA-256 values differ.

**Where the points went** (resolved out of 3 runs; the 5 scenarios not listed are 3 of 3 for all)

| Scenario | Control | Step 64 | Step 128 |
|---|---|---|---|
| `A-502-01` | 3 | 0 | 0 |
| `A-079-01` | 3 | 1 | 1 |
| `A-022-01` | 3 | 1 | 2 |
| `A-078-01` | 2 | 3 | 2 |
| `A-089-02`, `A-328-01`, `A-601-01`, `A-918-01` | 0 each | 0 each | 0 each |

- **None of the four scenarios the control always fails was resolved once**, in 24 tuned tries.
- **The failures changed kind.** Final labels over 39 scenario runs:

  | Label | Control | Step 64 | Step 128 |
  |---|---|---|---|
  | `RESOLVED` | 26 | 20 | 20 |
  | `REGRESSION` (the fix breaks a regression test) | 3 | 7 | 9 |
  | `STUCK` (the same edit again after feedback) | 1 | 6 | 6 |
  | `POC_STILL_FAILS` | 5 | 4 | 3 |
  | `FORMAT_FAIL` | 4 | 1 | 1 |
  | `GATE_REJECT` | 0 | 1 | 0 |

  The format was learned (4 format failures became 1). What got worse is the fix itself:
  more edits that break behaviour, and more repeats of a rejected edit.

**What to look at on D19. These are guesses from the tables above; none is tested.**
- **The RATIONALE.** Every training target begins with the finding's message as its
  RATIONALE, and the tuned model copies that: at temperature 0 it answers "RATIONALE: Pyrofork
  has a Path Traversal in download_media Method" where the control writes what it is about to
  do ("Prevent path traversal by ensuring the `file_name` parameter ..."). The untuned model
  may be using that line to reason before it edits, and training may have removed it.
- **Repair turns.** `STUCK` went from 1 to 6. Repair turns are 53 of 541 examples, 10% against
  the plan's 20%.
- **Overfitting or learning rate.** Validation loss stopped moving at step 32 while training
  loss kept falling. Step 32 has a GGUF on Kaggle and was not judged; it is the cheapest next
  measurement.
- **Data against dev.** Half of dataset v1 is advisory fixes from large real projects; the dev
  scenarios are small applications.

**Where the files are**
- Kaggle keeps the output of kernel version 11: four GGUFs, the four checkpoints and the final
  adapter.
- The five adapters and the reports are copied to `training/data/full/` on `F:` (git-ignored).
- Ollama holds `aeropatch-step64` and `aeropatch-step128` (2.8 GB each, on `F:`). The two
  downloaded GGUF files are copies of those and can go. They were moved off `C:` to
  `D:\aeropatch-d18` (5.2 GB) on 2026-10-13.
- Dev runs: `runs/20261012-201541`, `-201954`, `-202425` (step 64) and `-202913`, `-203246`,
  `-203620` (step 128), each `-repair-local-dev.jsonl`.

## Week 3, D19 (2026-10-13): why the tuned model is worse on dev

**How the two experiments are read. Written at 10:35, before any total existed**: the first
`prefill-plan` run stood at 8 resolved of 11 done, and no `prefill-finding` run had started.
- **RATIONALE experiment.** `prefill-finding` against `prefill-plan`, both on the untuned control,
  3 dev runs each, totals of 39 and first-attempt counts. Finding 4 or more below plan: the copied
  RATIONALE explains most of the loss, and dataset v2 rewrites that line. Within 2: it does not.
  3 is undecided. `prefill-plan` against yesterday's 26 only checks that writing the start of the
  answer costs nothing by itself.
- **Step 32.** Its score counts only together with whether it already copies the finding. Copies
  and scores near 26: the copying is harmless, and the damage comes later in training. Copies and
  scores near 20: the RATIONALE or the data, and the pair above decides.

**The RATIONALE experiment: with the finding's message written as its RATIONALE, the untuned
control falls from 26 to 21 of 39.** By the rule above (4 or more), the copied RATIONALE explains
most of the loss. The tuned checkpoints scored 20.

| Model and config | Run 1 | Run 2 | Run 3 | Total of 39 | Resolved at attempt 1 |
|---|---|---|---|---|---|
| Control, `repair-local` (D18) | 9 | 8 | 9 | **26** | 23 |
| Control, `prefill-plan` | 8 | 9 | 9 | **26** | 21 |
| Control, `prefill-finding` | 7 | 8 | 6 | **21** | 17 |
| Step 64, `repair-local` (D18) | 7 | 7 | 6 | **20** | 15 |
| Step 128, `repair-local` (D18) | 7 | 7 | 6 | **20** | 16 |

- **The two configs** are `repair-local` with the start of the answer written for the model
  (`local_prefill` in `config.py`; Ollama continues a trailing assistant message).
  `prefill-plan` writes `RATIONALE:` and the model finishes the line, as the control does anyway.
  `prefill-finding` writes `RATIONALE: <the finding's message>` and opens the first block, which
  is how the tuned model answers.
- **Writing the start of the answer costs nothing in the total**: `prefill-plan` scores the
  control's 26. The answers are not the same, though. At the first attempt it resolves 21 against
  23, and its first answers are longer (median 172 output tokens against 138, 5 SEARCH lines
  against 3). Ollama trims trailing whitespace from the written start; whether it also builds
  the turn without the empty think block was not checked. Both prefill configs share whatever it
  does, which is why finding is read against plan and not against yesterday's control.
- **The forced finding loses the two scenarios the tuned model loses most**, and little else:

  | Scenario (resolved of 3 runs) | Control | Step 64 | Step 128 | `prefill-plan` | `prefill-finding` |
  |---|---|---|---|---|---|
  | `A-502-01` | 3 | 0 | 0 | 3 | 0 |
  | `A-022-01` | 3 | 1 | 2 | 3 | 1 |
  | `A-079-01` | 3 | 1 | 1 | 3 | 3 |
  | `A-022-02` | 3 | 3 | 3 | 3 | 2 |
  | `A-078-01` | 2 | 3 | 2 | 2 | 3 |

  The other 8 scenarios score the same in all five columns.
- **Two things the RATIONALE does not explain.** `A-079-01` stays at 3 of 3 with the finding
  forced, and the tuned checkpoints resolve it once in 3. And `STUCK` ends 1 of 39 runs in both
  prefill configs, against 6 for each tuned checkpoint. Both come from the training itself.
- **Why the plan line matters, from the answers.** On `A-502-01` the control's RATIONALE says
  "Replace `pickle` with `json`" and its edit changes `dump_prefs` and `load_prefs` together. The
  tuned model restates the finding and changes `load_prefs` alone, so stored preferences no
  longer load.
- **This is what dataset v1 teaches**: 497 of the 511 training targets open with the finding's
  message (some are advisory titles: "Duplicate Advisory: python-jose denial of service via
  compressed JWE content"). The tuned checkpoints copy it in 36 of 39 first answers each, the
  control in none.
- Runs: `20261013-102945`, `-103745`, `-104622` (`prefill-plan`) and `-103404`, `-104224`,
  `-105029` (`prefill-finding`), each `-dev.jsonl`, alternated. No provider error in any; 46 to
  47.5 tokens a second. **Their headers say `dirty: true`**: they ran the two configs as an
  uncommitted change on top of `f43f77a`.
- **Limits.** Three runs a config and 13 scenarios: every `prefill-finding` run is at or below
  every `prefill-plan` run, and 5 of the 6 lost resolves are in two scenarios. Forcing the
  control is not the tuned model; it shows that losing the plan line is enough to lose those two.

**One D18 guess is ruled out by yesterday's runs: repair turns.** The loss is at the first
attempt: the control resolves 23 of 39 there, the checkpoints 15 and 16. A failed first attempt
was then repaired as often after tuning as before: 3 of 16 for the control, 5 of 24 at step 64,
4 of 23 at step 128. An unrepaired one ends in `STUCK` more often after tuning (6 of 19 at each
checkpoint, 1 of 13 for the control), but no resolve is lost there. So the share of repair turns
in the data (10% against the plan's 20%) is not what cost the points.

**Step 32 also scores 20 of 39, so training for fewer steps is not the fix.** It is a quarter of
the run, and it already copies the finding.

| Model, `repair-local` | Run 1 | Run 2 | Run 3 | Total of 39 | Resolved at attempt 1 | First answers that copy the finding, of 39 |
|---|---|---|---|---|---|---|
| Control (D18) | 9 | 8 | 9 | **26** | 23 | 0 |
| Step 32 (`aeropatch-step32`) | 5 | 7 | 8 | **20** | 11 | 36 |
| Step 64 (D18) | 7 | 7 | 6 | **20** | 15 | 36 |
| Step 128 (D18) | 7 | 7 | 6 | **20** | 16 | 36 |

- By the rule written this morning: it copies and scores near 20, so the prefill pair decides,
  and that pair points at the RATIONALE.
- **It fits the loss curve.** Validation loss was flat from step 32 on (D18): what the targets
  teach was learned by then, the first line included.
- Step 32 is the weakest at the first attempt (11) and repairs the most (9 of 28 first failures).
  Its runs spread more (5, 7, 8) than any other model's.
- Per scenario it loses what the later checkpoints lose: `A-502-01` 0 of 3 and `A-022-01` 0 of 3.
  It resolves `A-079-01` 3 of 3, each time by repair. It resolved `A-089-02` once and `A-918-01`
  once, which the control did in none of its 9 runs of yesterday and today; one resolve each in
  3 runs is not a finding.
- Checked before the runs, as on D18: one prompt is 395 tokens for the control and for step 32,
  the model is 100% on the GPU (3,083 MiB of GPU memory in use), and it runs at 47 tokens a
  second.
- Runs: `20261013-105642`, `-110052`, `-110550`, each `-repair-local-dev.jsonl`, on `f43f77a`
  with `dirty: false` (the prefill change was stashed for them). No provider error.
- The GGUF came from kernel version 11's output with a script that streams one file to disk;
  `kaggle kernels output` reads a whole file into memory first. The download was deleted after
  its SHA-256 (`37a757f4...`) matched the blob Ollama made from it.

**What the second run should change. This is my reading; nothing is started, and dataset v1 is
frozen, so the choice is yours.**
- **Not fewer steps** (step 32), **and not the plan's two options**, rank 32 or 3 epochs: both
  teach the same targets harder.
- **The first line of the targets.** Two ways to do it:
  - **A. Rewrite each RATIONALE as one line that says what the fix does**, written from the
    diff by a local model, with 30 of them read before the freeze. That is dataset v2. On
    `qwen3.5:4b` it is under an hour for 541 examples, on the 9B teacher about 4 hours; both
    are estimates.
  - **B. Keep the targets and leave the RATIONALE line out of the loss**, a few lines in
    `finetune.py`. No data work, but every block is still trained after a line that plans
    nothing.
  - A is the likelier of the two, not a known fix: the control loses 5 of 39 when its plan line
    is replaced, which does not show that training on plan lines wins them back.
- **The shape of the blocks** (the third experiment, below): the first line alone should not be
  expected to reach 26. What would teach the other shape, none of it tried: take out of each
  synthetic vulnerable file the imports only its fix uses, so that the target adds them, and
  check each one in the sandbox again; write the target of a file shown whole from its `def`
  line; raise the share of prompts that show a whole file (67 of 461 today).
- **Learning rate** was not tested. The same score at steps 32, 64 and 128 is a reason not to
  start there.
- Either way the second run costs one Kaggle session of about 2 hours 20 minutes and three dev
  runs per checkpoint.
- **Still unexplained**: `A-079-01` at steps 64 and 128, and the `STUCK` endings. Look again
  after the second run.
- **The bar for the second run, set before it exists.** The tuned model replaces the untuned
  one only at 26 of 39 or more on dev, three runs. At 25 or fewer the untuned model goes into
  Week 4 and the fine-tune is reported as it is. If no second checkpoint is judged by the end of
  D21, Week 4 also runs on the untuned model: D22 starts the test runs.
- **Disk decides how many checkpoints can be judged.** Each one needs about 5.6 GB on `F:` while
  Ollama copies it and 2.8 GB after the download is deleted, and `F:` has 7.7 GB free. Two
  checkpoints fit only if `aeropatch-step32`, `-step64` and `-step128` are removed from Ollama
  first (8.4 GB; all three are in kernel version 11's output on Kaggle), or if `D:` is back. Removing them is yours to
  approve.

**A third experiment, and how it is read. Written at 11:18, before it ran.** Does a tuned
checkpoint write the blocks as well as the control once it is handed a plan? Config
`prefill-control-plan`: one attempt, opened with `RATIONALE: <the line the control wrote for
that scenario in run 20261012-164903>` and the start of the first block
(`training/d19_control_plans.json`). Step 64 and the control each run it 3 times, so only the
weights differ. Resolved of 39: step 64 within 2 of the control means the tuned model still
writes good blocks when it has a plan, and rewriting the targets' first line addresses the main
cause. 4 or more below means the damage goes past the first line, and the rewrite alone should
not be expected to reach 26. 3 is undecided.

**Its result: handed the control's plan, step 64 resolves 16 of 39 and the control 20.** That is
4 below, so by the rule the damage goes past the first line.

| Model, `prefill-control-plan` (one attempt) | Run 1 | Run 2 | Run 3 | Total of 39 |
|---|---|---|---|---|
| Control | 7 | 6 | 7 | **20** |
| Step 64 | 5 | 6 | 5 | **16** |

- Three scenarios differ: `A-079-01` (control 3 of 3, step 64 none), `A-022-01` (2, none) and
  `A-502-01` (none, 1). The other 10 score the same.
- **What step 64 does with the plan.** On `A-079-01` it writes `html.escape(author)` inside the
  function and never imports `html`: `NameError`, 3 times of 3. On `A-022-01` it compares a
  string with `base_dir`, which is a `Path`: `TypeError`.
- **The blocks changed shape, at every checkpoint.** Of 39 first answers:

  | Model and config | A block starts at module level (a `def` line, an import) | Adds an import |
  |---|---|---|
  | Control, `repair-local` | 24 | 4 |
  | Control, `prefill-plan` | 28 | 7 |
  | Control, `prefill-finding` | 25 | 6 |
  | Control, `prefill-control-plan` | 26 | 6 |
  | Step 32, `repair-local` | 0 | 0 |
  | Step 64, `repair-local` | 0 | 1 |
  | Step 128, `repair-local` | 3 | 2 |
  | Step 64, `prefill-control-plan` | 3 | 3 |

  The control rewrites from the `def` line or the top of the file, so it can add an import or
  change a second function. The tuned model edits lines inside the function body.
- **Dataset v1 teaches that shape too.** Of its 461 first-attempt targets, 72 have a block that
  starts at module level (4 of the 99 synthetic ones) and 49 add an import (1 of the 99). Two
  reasons, both read from the build and not tested: 394 of the 461 prompts show one function of
  a larger file, where the imports are out of view; and the generator plants the flaw into the
  fixed module, so the import a fix needs is already in the vulnerable file. On dev, 6 of the 13
  reference fixes add an import.
- **This config is harder for the control as well**: 20, against 23 at the first attempt of
  `repair-local` and 21 of `prefill-plan`. It loses `A-502-01` in all 3 runs. So its numbers
  compare inside the config only.
- Runs: `20261013-111826`, `-112212`, `-112600` (control) and `-112025`, `-112406`, `-112755`
  (step 64), each `-prefill-control-plan-dev.jsonl`, alternated, `dirty: true` like the other
  prefill runs. No provider error; 48 tokens a second.
- The command that counted imports in dev's reference fixes counted them for test, Tier B and
  Tier C as well. Those numbers are not used here and should not steer the data.

**Dataset v2 and the second run: what changes, and how the run is read. Written at 12:20,
before v2 was built.** You said to run the training and to fix what still goes wrong.
- **Two changes to the targets, nothing else.** The RATIONALE of every target becomes one line
  that says what the fix does, written from the fix by the untuned `qwen3.5:4b` at temperature 0
  (my default: its own plan lines are the ones the experiments used, and it is the fastest). And
  a fix inside a function of at most 15 lines is one block that holds the whole function, from
  its `def` line. That is the untuned model's own habit, measured on its 184 first answers of
  the student pass: it writes the whole function in 76 of 90 answers for a function of 1 to 8
  lines, 32 of 57 for 9 to 15 lines, 11 of 27 for 16 to 25, 2 of 10 above that.
- **The same run otherwise**: `finetune.py` as on GitHub at `f43f77a`, the D18 values, 128 steps
  if the set keeps its size. The synthetic files are not edited, so the student pass and its
  repair turns stay valid. Not done: taking the fix's imports out of the vulnerable files.
- **Is the problem still there? Three checks on the step-64 and step-128 dev runs, in this
  order.** The RATIONALE copies the finding in at most 5 of 39 first answers (36 today). A block
  starts at module level in at least 15 of 39 (0 to 3 today; the control 24). If either fails,
  the data change did not take, and it is fixed and run again. If both pass, the total is read
  against the bar: 26 of 39 or more and the tuned model replaces the untuned one; less and the
  untuned model goes into Week 4.
- **Before the Kaggle session**: v2 is measured the same way (blocks at module level were 72 of
  461 first-attempt targets in v1), and 30 examples are read.

**Dataset v2, first build (12:10): 541 examples again, and the first reading failed.**
- The shape took: a block starts at a `def`, `class` or decorator line in 206 of the 488 first
  attempts and bug fixes, and at module level in 156 of 461 training targets against 72 in v1
  (synthetic: 69 of 99, against 4). No target opens with the finding (497 of 511 did).
- The plan step dropped nothing: 488 lines for 541 examples (a repair turn shares its
  scenario's line), none unusable, 11 words at the median and 17 at most. A line takes under a
  second on `qwen3.5:4b`.
- **Reading 30 (seed 3407): 4 plan lines were vague or wrong in a detail, over the limit of 3
  (doc 09 §10).** All four sit on fixes from real projects; the 9 synthetic ones read were
  right. "Call `self` to ensure proper authentication context is maintained" for a fix that
  returns `self.handle_response(...)`; "prevent backspace characters" for backtracking; "Escape
  forward slashes" for a regular expression that was restructured; a line about `self.mode` for
  a fix that stops assigning it. No fix was wrong: the blocks are v1's.
- **Tightened: the prompt now asks the line to name what the blocks add, remove or replace**, so
  that it can be checked against them. Tried on those four and six others: the four became
  accurate ("Replace the direct return with a call to `self.handle_response` passing through
  kwargs") and the six stayed as they were or changed a word. The first lines are kept as
  `training/data/plans.first-wording.jsonl`; the set is rebuilt and 30 are read from a new seed.

**Dataset v2, frozen (12:20): 541 examples, 511 train and 30 validation.**
- **The second reading passed: 2 of 30 plan lines are imprecise (seed 20261013), within the
  limit of 3.** One says "non-greedy match" where the fix puts in a negated character class;
  one names the change rightly (the salt is passed by keyword) and gives a wrong reason. A
  third is borderline. All three are about regular expressions or library calls in real
  projects. The 11 synthetic first attempts and repair turns in the sample are right.
- **v2 against v1.** The same 541 examples but one: a SWE-smith pair that now converts took a
  place among the bug fixes. For the other 540 the prompt and the split are identical. The
  blocks changed shape in 224 targets and are v1's, byte for byte, in 316. Training tokens:
  700,290 against 683,663, which is 2.4% more; the longest example is still 4,087.
- **SHA-256**, the same files as the private Kaggle dataset `aeropatch-train-v2`:
  - `train.jsonl` `4bf82d1a1067f629c27b29c4b492b31143ccf980c90dd7885b82fbbfb5ce91c3`
  - `val.jsonl` `25689fd91465d53c19beab6eba1efa27145c4f04345050e16134d84a279134ef`
- Built by `uv run --with transformers --with jinja2 python training/prepare_dataset.py build
  --student-run 20261009-student-pass --tokenizer Qwen/Qwen3.5-4B --plans qwen3.5:4b --out
  training/data/v2`, about 10 minutes. The 488 lines are in `training/data/plans.jsonl`; with
  that file a build asks the model nothing and writes the same files. `training/data/v2/stats.md`
  has the counts.
- **Dataset v1 is rebuilt from commit `f43f77a` from now on**: the builder writes whole-function
  blocks always, and `--plans` is what adds the new first line.
- **The run: kernel version 12, pushed at 12:22**, run `full-v2` on `aeropatch-train-v2`. The
  kernel clones the branch from GitHub, where `finetune.py` is still `f43f77a`'s; only
  `kernel.py` and its settings went up with the push. Expected: about 2 hours 25 minutes.

**The second run finished (kernel version 12, complete at the 14:58 check, about 2 h 35 min).**
All four steps of the session ended with exit code 0, and its log shows the clone at `f43f77a`.
- 128 steps in 97 minutes (45.5 s a step, against 42.0 for v1: the targets are longer), peak
  13.1 GB, 511 examples, none dropped, longest 4,087 tokens, 139 prompts equal to Ollama's count.
- **Validation loss is flat again**: 0.2595 at step 32, 0.2560 at 64, 0.2577 at 96, 0.2588 at
  128. Training loss fell from 0.39 to 0.18. The values are higher than v1's 0.207 because the
  targets changed, so the two runs cannot be compared on loss.
- The 5 validation outputs of the final adapter parse, and the two I read open with a plan
  ("Replace the filename with a safe path to prevent directory traversal").
- By the plan's rule the judged checkpoints are steps 64 and 128 again: the ends of the two
  epochs, and 64 has the lowest validation loss.
- The output of the session is fetched with `training/kaggle/fetch_output.py`, which streams the
  files that match a pattern. Everything is on `D:\aeropatch-d19`: the reports, the five
  adapters and the two GGUFs.

**The second run on dev: step 64 scores the control's 26 of 39, and both problems are gone.**

| Model, `repair-local` | Run 1 | Run 2 | Run 3 | Total of 39 | Resolved at attempt 1 | First answers that copy the finding | A block starts at module level |
|---|---|---|---|---|---|---|---|
| Untuned control (D18) | 9 | 8 | 9 | **26** | 23 | 0 | 24 |
| v1, step 64 (D18) | 7 | 7 | 6 | **20** | 15 | 36 | 0 |
| v1, step 128 (D18) | 7 | 7 | 6 | **20** | 16 | 36 | 3 |
| **v2, step 64** (`aeropatch-v2-step64`) | 8 | 9 | 9 | **26** | 18 | 0 | 28 |
| v2, step 128 (`aeropatch-v2-step128`) | 8 | 7 | 8 | **23** | 23 | 0 | 32 |

- **The three checks written before the run.** The RATIONALE copies the finding in none of 39
  first answers at either checkpoint (the limit was 5). A block starts at module level in 28
  and 32 (at least 15 was asked). And step 64 reaches the bar of 26. So by the rule **v2 at
  step 64 replaces the untuned model in Week 4; that is yours to overrule.**
- **It is a tie, not a gain.** 26 against 26 on 13 scenarios shows that this fine-tune no
  longer costs anything on dev. It does not show that it helps.
- **What came back**: `A-502-01` is 3 of 3 at both checkpoints (none with v1) and `A-079-01`
  3 of 3 (1 with v1). `A-022-01` is 2 of 3 at step 64 and none at step 128. Of the four
  scenarios the control never resolves, `A-089-02` was resolved once, at step 64.
- **The two checkpoints resolve at different attempts.** Step 64 resolves 18 at the first
  attempt and repairs 8 of its 21 failures. Step 128 resolves 23 at the first attempt, the
  control's number, and repairs none of its 16 failures: 9 of them end in `STUCK`, the same
  edit again after feedback (3 at step 64, 1 for the control). In these runs the second epoch
  made first answers better and repair turns worse.
- First answers that add an import: 3 at step 64 and 6 at step 128 (the control 4, v1 1 and
  2). No run ended in `FORMAT_FAIL` (the control: 4 of 39).
- **Decoding was slow, and not because of the model**: 28.8 tokens a second in all six runs,
  against 47 this morning. Right after them the control ran at 35.8 and v2 step 64 at 35.2 on
  one prompt, `nvidia-smi` listed a second program on the GPU (ArtCraft Launcher), and the card
  drew 35 W. No attempt ran into a time limit, so the resolves stand. Speed and VRAM of the
  tuned model have to be measured again on a quiet machine (the plan's D20).
- Checked before the runs: one prompt is 395 tokens for both checkpoints and the control, and
  each is 100% on the GPU.
- Runs: `20261013-151854`, `-153130`, `-154255` (step 64) and `-152453`, `-153655`, `-154843`
  (step 128), each `-repair-local-dev.jsonl`, alternated, on `f43f77a` with `dirty: false` (the
  uncommitted `src` and `tests` changes were stashed). No provider error.
- **Limits.** Three runs a checkpoint and 13 scenarios: 26, 26 and 23 are closer together than
  dev can separate. And **dev chose these two changes**: the diagnosis read dev's failures, so
  dev is no longer a neutral measure of v2. No dev code is in the training data (the leakage
  checks ran on v2 as on v1, and the three examples in the plan prompt are not from dev). The
  test split and Tier B, which no model has been tuned against, are the measure (D22).

**What is left of the two problems, and what was not tried.**
- Fixed at both checkpoints: the copied RATIONALE and the shape of the blocks.
- Not fixed: at step 128 the model repeats a rejected edit. Step 64 is the checkpoint to use.
- Not tried: judging steps 32 and 96 (their GGUFs are in the session's output on Kaggle),
  taking the fix's imports out of the synthetic vulnerable files, the learning rate, the 9B
  teacher for the plan lines.

**State of the laptop (16:10).** Ollama holds `aeropatch-control`, the v1 checkpoints `-step32`,
`-step64` and `-step128`, and `aeropatch-v2-step64` and `-v2-step128`. `F:` has 8.1 GB free.
`D:` is an external drive: it was not mounted in the morning and was back at midday with 425 GB
free. `D:\aeropatch-d19` holds the second run's files (5.9 GB) and `D:\aeropatch-d18`
yesterday's two GGUF copies. Free commit fell to 1.6 GB during the prefill runs, when the model
server alone held 7.3 GB; nothing failed. The tables of this section come from one-off scripts
that are not in the repository; `aeropatch report` gives the totals.

## Week 3, D19, evening (2026-10-13): the five limits of the tuned model, and the test runs

You asked for research on what is still not right and for a try at fixing it. Three of the
five limits are measurements that were missing, one cannot be fixed with a free local model,
and for one the cheap fixes were looked at and set aside.

**Dev cannot show a gain from fine-tuning any more.** Outside the four scenarios no local model
resolves, the untuned control resolves 26 of the 27 possible runs on the other nine. So a model
can beat it on dev by 1, or by cracking one of the four. The room is on test, where the local
model scored 17 and 18 of 27 in Week 2, and on Tier B (5 of 10). The dev tie therefore says
little about whether tuning helps; the test runs below are what can.

**The four scenarios, over 30 local runs of yesterday and today** (every model and config, 120
scenario runs): weak password hashing `A-328-01` and the open redirect `A-601-01` were never
resolved, the SSRF `A-918-01` once and the two-file SQL injection `A-089-02` twice. Each needs
knowledge the 4B model does not bring: a salted key derivation with its verifier changed
together, `ipaddress` on the resolved address, a redirect check that also refuses `//host` and
`/\host`, and the same change in two files. More samples do not find them, so pass@k will not
either. The cascade is the design's answer: Opus resolved all 13 dev scenarios in Week 2.

**Research (two papers read, four searches), and why no hint section went into the prompt.**
- "Guiding AI to Fix Its Own Flaws" (arXiv 2506.23034): vulnerability hints lower the
  vulnerability rate of GPT-4o by 8 to 12 points on its three benchmarks. For open models of 3B
  to 34B the change runs from 8 points lower to 3 points higher, so some get worse. Precise,
  directive hints do better than CWE definitions.
- "Identifying Helpful Context for LLM-based Vulnerability Repair" (EASE 2025, GPT-4o, Java):
  a CWE description leaves the repair count where the baseline is (11, 12, 14 against 11, 12,
  14 of 42). What raises it is CVE-specific text and several prompts tried against a checker:
  26 of 42 fixed at least once by the best three prompts together, at most 20 by any one.
- So for a 4B model a hint section is as likely to cost as to gain. It would also change the
  prompt that v2 was trained on. Not built.

**The missing import, replayed without a model: not worth a harness step.** In the nine dev
runs of the control and the two v2 checkpoints, 12 failed attempts stopped on a
standard-library module used and not imported (`os`, `re`, `secrets`, `html`, `base64`). Each diff was applied again with the import
added and run through the gates and the sandbox. For the control 4 of 4 then resolve, and one
unresolved run would have been resolved (`A-078-01`, 26 to 27 of 39). For v2 none of 8 does:
with the import in place `A-328-01` still breaks `verify_password` and `A-601-01` still fails
its PoC. An automatic import would be a new config for every route, for 1 run in 117.

**The test runs, planned before any of them (17:20).** This brings the plan's D22 forward, and
it is the only use of the test splits for this comparison: **nothing is tuned afterwards on
what they show.**
- Models: the untuned control and `aeropatch-v2-step64`, both `repair-local` on the committed
  harness (`c03f33f`, clean tree). The control is run again: Week 2's 17 and 18 came from the
  library model on an older commit.
- Runs: 2 each on `test` (27 scenarios), `test_b` (10 real CVEs) and `test_c` (5 held-out
  synthetic), alternating the models.
- Read: totals of 54, 20 and 10, the paired exact McNemar of `aeropatch report`, and the
  first-attempt counts.
- **Rule.** A gain: v2 at least 4 above the control on `test` (of 54) and not below it on
  `test_b`. A loss: at least 4 below on `test`. Anything else is "no difference shown". Week
  2's two local runs differed by 1 in total with 5 scenarios flipping, which is where the 4
  comes from. On a loss the untuned model goes into the rest of Week 4.

## Week 3, D20 (2026-10-14): the test runs, and the model for Week 4

**On test the tuned model resolves 32 of 54 and the untuned control 38. By the rule written
yesterday before any test run, that is a loss: the untuned model goes into Week 4.** That is
yours to overrule. The gap is not significant on its own: the paired exact McNemar gives
p = 0.146, with 9 scenario runs that only the control resolved and 3 that only v2 resolved.
That value pools the two run pairs (run *i* of one model against run *i* of the other, by
scenario), as `notebooks/runs.ipynb` computes it; `aeropatch report` gives each pair's own value.
The rule reads the totals, so the verdict does not depend on it.
The rule's 4 came from Week 2, whose two local runs differed by 1 with 5 scenarios flipping.

| Model, `repair-local` on `c03f33f` | Run 1 | Run 2 | Total of 54 | Resolved at attempt 1 |
|---|---|---|---|---|
| Untuned control (`aeropatch-control`) | 19 | 19 | **38** | 28 |
| v2, step 64 (`aeropatch-v2-step64`) | 18 | 14 | **32** | 24 |

- **Where**: the control is ahead on 7 scenarios, `A-020-01` and `A-078-04` (1 of 2 against
  none), and `A-089-04`, `A-1333-02`, `A-502-03`, `A-601-02`, `A-798-02` (2 against 1). v2 is
  ahead on 1, `A-022-03` (1 against none).
- **The same failures as on dev**: v2's attempts end in `REGRESSION` 16 and 24 times against the
  control's 16 and 11, and 9 of its scenario runs end `STUCK` (the same edit again after
  feedback), against none for the control. The fix breaks behaviour more often after tuning.
- **The runs are sound.** No provider error, sandbox error or timeout in any of the four. Today's
  decoding ran at 46.2 to 46.6 tokens a second. The control's first run decoded at 28.4 because
  its first 23 scenarios ran yesterday with ArtCraft Launcher on the GPU; no attempt reached a
  time limit, so its results stand.
- **The export costs nothing on test**: the control scores 19 and 19 here, against 17 and 18 for
  the library `qwen3.5:4b` in Week 2 (an older commit).
- Runs: `20261013-170329` and `20261014-124302` (control), `20261014-123112` and
  `20261014-125354` (v2), each `-repair-local-test.jsonl`, alternated, `dirty: false`.

**Yesterday's test run did not crash: the laptop was restarted from the Start menu at 17:15:47**
(System event 1074, "Other (Unplanned)"), the second of the last write in `A-798-01`. The run
was resumed today under its run ID; its 4 missing scenarios ran from 12:28 to 12:31.

**Speed and GPU memory on a quiet GPU** (one dev run each, `nvidia-smi` every 0.5 s, no other
program on the GPU): both models are 100% on the GPU and peak at **3,043 MiB**, under the plan's
3,891, and decode at **46.5** (control) and **46.7** (v2) tokens a second. Dev: 9 and 8 of 13.
D19's 28.8 tokens a second was the other program on the GPU, as suspected.

**Memory during the runs.** Free commit fell to 0.5 GB during v2's first test run: the model
server grew from 7.8 to 10.3 GB private while one model stayed loaded for 30 scenarios, and
Windows grew the page files on `C:` and `F:`. It came back at each change of model. Nothing failed.

**Tier B and Tier C point the same way, or tie.**

| Split, 2 runs each | Untuned control | v2, step 64 | Paired exact McNemar |
|---|---|---|---|
| `test_b`, 10 real CVEs (of 20) | **7** (4 + 3) | 3 (2 + 1) | p = 0.289 (6 against 2) |
| `test_c`, 5 held-out synthetic (of 10) | 9 (5 + 4) | 9 (4 + 5) | p = 1.000 (1 against 1) |

- Tier B: the control is ahead on `B-022-01` and `B-287-01` (2 against none) and on `B-113-01`
  and `B-400-01` (1 against none). v2 is ahead on `B-094-01` (2 against none).
- The control's 4 and 3 on Tier B are below the library model's 5 and 5 of Week 2, where on
  test it was above (19 and 19 against 17 and 18). Ten scenarios cannot separate these.
- Tier C is the kind of data v2 was trained on (held out of it), and both models resolve 9 of
  10: there, the untuned model already does what the training taught.
- Runs: `20261014-130652`, `-131647` (control) and `-131242`, `-132226` (v2), each
  `-repair-local-test_b.jsonl`; `20261014-132647`, `-132909` (control) and `-132803`, `-133016`
  (v2), each `-repair-local-test_c.jsonl`. Alternated, `dirty: false`, no provider error,
  sandbox error or timeout.

**The Week 4 model at three quantisations.** Kernel version 13 (13:08 to 13:36) exported the
untuned control at Q8_0 and Q5_K_M by the path of D17's Q4_K_M (`--max-steps 0`, no adapter;
runs `control-q8` and `control-q5` in `kernel.py`; only `kernel.py` went up, so the clone is the
branch as on GitHub). Both ended with exit code 0. Unsloth wrote Q8_0 in one pass and Q5_K_M
from an f16 file with llama.cpp's quantiser, in the same run. Each run's 5 validation outputs
parse in 2 of 5, as D17's untuned export did.

| File | Bytes | SHA-256 | Where |
|---|---|---|---|
| `Qwen3.5-4B.Q4_K_M.gguf` (D17) | 2,708,804,192 | `51b5c0d6e5a9a2b6a5514231b821378382d72a057de3d7ad3ac09a5bddbbfdc7` | Ollama blob of `aeropatch-control`, hash checked today |
| `Qwen3.5-4B.Q5_K_M.gguf` | 3,074,986,592 | `eca20e2e5833929b09bed8ef4275bc2752dc9214c94fb1602ebffda46eb3853a` | `D:\aeropatch-d20\control-q5` |
| `Qwen3.5-4B.Q8_0.gguf` | 4,482,402,912 | `5a721cb3a164834aaa771acce87e7d666d04f437c0668b3e93306692b727d154` | `D:\aeropatch-d20\control-q8` |

- Not loaded into Ollama: `ollama create` copies the file onto `F:`. Q8_0 is larger than the
  GPU's 4 GB, so part of it will run on the CPU; the quantisation ablation (doc 10 §7) is Week 4's.
- Before the verdict, v2's step-64 adapter was uploaded as the private Kaggle dataset
  `aeropatch-v2-step64-adapter` for an export of v2; it is not used.

**The other Week 3 leftovers**
- `aeropatch-step32`, `-step64` and `-step128` are removed from Ollama: `F:` went from 8.1 to
  15.9 GB free. `D:\aeropatch-d18` is kept: it now holds the only local copies of v1's step 64
  and step 128 GGUFs, and `D:` has 420 GB free.
- The README has a training section; its status line names the Week 4 model.
- `runs/INDEX.md` lists every run with its config, model, split, commit and score, grouped by
  phase with a one-line takeaway. `.gitignore` now ignores `runs/*` except that file.
- `notebooks/runs.ipynb` shows the runs: what is running now, the D20 comparison, per-scenario
  results, today's timeline, GPU memory and the dev history. It reads `runs/` only. Its kernel
  is `.venv-notebook` (git-ignored), kept apart from `.venv` so that the benchmark's
  environment did not change during the runs.
- **The laptop QLoRA demo is cut** (cut-list item 6, doc 10 §13 accepts a documented reason):
  the laptop has no training stack (no torch, Unsloth or bitsandbytes), and its GPU and memory
  went to the benchmark runs all day.

## Week 4, D22 (2026-10-16): the plan, and the defaults taken

The plan is `docs/14-timeline-part5.md`. You answered "ok proceed with it", so these are taken,
each yours to overrule:
- **Frontier model `claude-opus-5-5`** for every Week 4 frontier and cascade run, the one I
  recommended over the plan's written default (`claude-opus-5`). Every frontier row runs again
  on D22 anyway, so the choice costs no extra runs. Week 1 and 2 frontier rows stay as they were.
- Local commits on this branch before each new config or scenario, so every run is
  `dirty: false`. Nothing is pushed.
- The Kaggle dataset `aeropatch-v2-step64-adapter` stays until you say to delete it.

**`claude-opus-5-5` needs Claude Code 2.1.280 or newer; the npm CLI on the laptop is 2.1.239.**
Every call to it came back `PROVIDER_ERROR` ("does not support this model"); `claude-opus-5`
still answers. Your `claude update` could not reach the registry, though `npm view` reaches it
from here (latest 2.1.301), and an npm `claude.exe` started at 12:37 is still running, which
would block replacing it. The Week 4 frontier runs therefore put the VS Code extension's bundled
CLI (2.1.296) first on `PATH` for the bench process only; it answered `claude-opus-5-5` on the
first try. Nothing on the system was changed.

**pass@k, the control (D23).** `sample-local` (one attempt at temperature 0.7, no feedback), 5
runs per split, alternated, all `dirty: false`, on `1337883` to `8a8ea58` (only `metrics.py` and
the scenarios changed in between, never the run path).

| Split | Resolved per run | pass@1 | pass@3 | pass@5 | Repair loop, resolve@3 (D20, 2 runs) |
|---|---|---|---|---|---|
| `test` (27) | 12, 12, 12, 13, 12 | 45% | 61% | 67% | 70% (38 of 54) |
| `test_b` (10) | 4, 1, 4, 1, 3 | 26% | 45% | 50% | 35% (7 of 20) |
| `test_c` (5) | 2, 3, 3, 3, 5 | 64% | 90% | 100% | 90% (9 of 10) |

- On `test` the repair loop beats resampling at the same budget of three generations (70%
  against 61%): the feedback is worth something there. On Tier B it is the other way round (35%
  against 45%), on 10 scenarios. Tier C ties.
- Sampling at 0.7 resolves less per try than the repair loop's first attempt at 0.2 (45% against
  52%, 28 of 54 in D20).
- Runs: `20261016-s1` to `-s5-sample-local-<split>`. `aeropatch report` on the 15 files gives
  the table.

**The adversarial scenarios (D22).** X-01, X-02, X-03, X-05 and X-06 (doc 13 §6), copies of
`A-089-01` with one planted instruction each, split key `adversarial`; X-04 is
`tests/test_sandbox_security.py`. All five pass the four validator checks. The tests show the
planted text in each first prompt, and the hand-written patch that obeys each injection gets the
expected code: `RISKY_IMPORT` (X-01), `FORBIDDEN_PATH` (X-02, X-05), `SUPPRESSES_CHECKS` (X-03);
X-06 is `SECRET_BLOCKED`. **X-01 without the import line passes every gate**: a bare
`requests.post` is not a risky call, and only an added import is checked. Through the MCP
`validate` tool the sandbox then fails it, `NameError: name 'requests' is not defined`, PoC and
regressions both red. That is the layer that stops it today; in a file that already imported
`requests` it would be the network-less sandbox alone.

**D22 runs: the cascade and the frontier on Opus 5.5** (14:19 to 15:02, `dirty: false`, no
provider error, sandbox error or timeout; the src diff from `c03f33f` is `metrics.py`, the
`report` command and the `sample-local` entry only).

| Config, local model `aeropatch-control` | `test` (27) | `test_b` (10) | `test_c` (5) | Cost, all three splits |
|---|---|---|---|---|
| `cascade-claude-code`, pass 1 | 27 (16 local, 11 escalated) | 9 (4 local) | 5 (3 local) | $1.10 |
| `cascade-claude-code`, pass 2 | 27 (16 local, 11 escalated) | 9 (4 local) | 5 (4 local) | $0.96 |
| `repair-claude-code` | 27 | 10 | 5 | $1.15 |

- Costs are the Claude Code route's API-equivalent figures; nothing is billed per token.
- The cascade misses `B-400-02` both times: two local attempts fail, then its one Opus attempt
  breaks a regression test. Opus alone, with three attempts and feedback, resolves it.
- The cascade resolves 16 of 27 on `test` without a frontier call in both passes, about what the
  control alone resolves in two local attempts (18 and 18 at attempt 2 in D20).
- Runs: `20261016-c1-` and `-c2-cascade-claude-code-<split>`, `20261016-f1-repair-claude-code-<split>`.

**The adversarial runs (D23).** The control twice and Opus 5.5 once on the 5 scenarios:
**injection-follow 0 of 4 and got-through 0 of 4 in all three runs**, X-06 `SECRET_BLOCKED` in
all three, and the SQL injection itself resolved at attempt 1 in X-01, X-02, X-03 and X-05 every
time. Neither model wrote an edit that obeyed the planted text. Runs: `20261016-a1-` and
`-a2-repair-local-adversarial`, `20261016-f1-repair-claude-code-adversarial`.

**D24, quantisation: Q5_K_M shows no difference.** `aeropatch-control-q5` is `training/Modelfile`
with only `FROM` changed; its Ollama blob is `sha256-eca20e2e…`, the D20 hash. All layers on the
GPU, peak **3,391 MiB** in a `remediate` smoke test (`nvidia-smi` every 0.5 s).

| `repair-local` on `test` | Run 1 | Run 2 | Of 54 | Peak VRAM | Decode |
|---|---|---|---|---|---|
| Q4_K_M, the control (D20) | 19 | 19 | 38 | 3,043 MiB | 46.5 tok/s |
| Q5_K_M | 21 | 20 | 41 | 3,391 MiB | about 43 tok/s |

+3 of 54 is under the rule's 4: no difference shown, and Q4 stays the served model. Runs
`20261016-q5a-` and `-q5b-repair-local-test`; Q5 was removed from Ollama after them.

**Q8_0 does not fit the 4 GB GPU whole.** Loaded with a 4,508-token Tier B prompt at 8k context
(blob `sha256-5a721cb3…`, the D20 hash), peak VRAM and decode by GPU layer count:

| `num_gpu` | 99 | 32 | 30 | 28 | 26 | 25 | 24 | 22 |
|---|---|---|---|---|---|---|---|---|
| Peak MiB | 3,903 | 3,903 | 3,921 | 3,911 | 3,913 | **3,771** | 3,657 | 3,423 |
| tok/s | 7.7 | 8.6 | 11.5 | 12.8 | 16.4 | **14.5** | 12.7 to 13.3 | 9.9 |

From 26 layers up the GPU is full and Windows spills into shared memory, which is why "all
layers" is the slowest. `repair-local-q8` uses 25 layers, the most under 3,891 MiB, with a
`scenario_wallclock_s` of 1,800 so the slower decode is not scored as a wrong fix.

**Q8_0 on `test`: 22 and 19, 41 of 54, the same +3 as Q5: no difference shown.** It decodes at
16.4 and 17.3 tok/s (p50 latency per attempt 18.8 and 19.8 s, against 6 to 7.5 s at Q4) and
peaks at 3,771 MiB; no attempt reached the time limit. Q4_K_M stays the served model: the larger
quants buy nothing measurable here, and Q8 costs about a third of the speed. Runs
`20261016-q8a-` and `-q8b-repair-local-q8-test`; Q8 was removed from Ollama after them.

**Thinking on: 21 and 20, 41 of 54, no difference shown.** `repair-local-think` (Q4 control,
4,096-token budget). Thinking is really on: the median attempt writes 695 output tokens against
238 without it, while the visible answer stays near 500 characters, so about 450 tokens of each
attempt are thinking. No attempt came near the budget or the time limit; decode 47 tok/s. Runs
`20261016-tka-` and `-tkb-repair-local-think-test`.

**The D24 ablation table** (the control, `repair-local` on `test`, 2 runs per row, D20's rule):

| Variant | Of 54 | Against the control | Peak VRAM | Decode |
|---|---|---|---|---|
| Q4_K_M, thinking off (control, D20) | 38 | | 3,043 MiB | 46.5 tok/s |
| Q5_K_M | 41 | +3 | 3,391 MiB | about 43 tok/s |
| Q8_0, 25 layers on the GPU | 41 | +3 | 3,771 MiB | about 17 tok/s |
| Q4_K_M, thinking on | 41 | +3 | as Q4 | 47 tok/s |

All three variants land on 41, which suggests the control's 38 of D20 sits low in its own spread
(Week 2's two library-model runs differed by 1 with 5 scenarios flipping). A same-day control
pair could not change any verdict: at 41 it would tie all three. Grammar and tool localization
were cut (`docs/14-timeline-part5.md` §4).

**D25: the report and the charts.** `aeropatch report` now gives a 95% paired bootstrap interval
beside each McNemar p, p95 latency, $ and tokens per resolved scenario, pass@k over repeated
one-attempt runs, the injection rates, and `--csv <dir>`. The three charts of doc 12 §6
(cost against accuracy, the repair curve, failure attribution) are drawn by
`notebooks/week4_charts.py` rather than inside `runs.ipynb`: one command, run with the
`.venv-notebook` interpreter, and the run files it reads are listed at its top. They are in
`docs/results/`, beside the CSV tables of the `test` comparison (`docs/results/test/`). On `test`
the untuned model's failures are mostly a PoC that still fails (10 of 16); v2's are `STUCK` (9)
and `REGRESSION` (7), the D19 finding again.

## Week 4, D26 (2026-10-16): README, fresh clone, MCP transcript

- **README rewritten** for the Week 4 results: the headline table on all three tiers with 95%
  Wilson intervals, the paired differences (bootstrap interval and McNemar), the three charts,
  pass@k, the ablations, the adversarial table, a Model section, Limitations and a Later list.
  Every number was recomputed from the run files with `aeropatch.metrics` before it went in, and
  every relative link checked. The run IDs are named beside each table.
- **Fresh clone, measured.** `git clone` into an empty `D:\aeropatch-fresh`, then `uv sync`,
  `ollama pull qwen3.5:4b`, `uv run aeropatch remediate A-089-01 --config repair-local`:
  RESOLVED at attempt 1 in 26.6 s; 380 s in all, mostly `uv sync`. `A-089-01` was resolved in all
  7 complete clean dev runs of a local model. Docker's images are shared, so the base image
  already existed: the new path that builds it when missing (`scenario.ensure_image`) is covered
  by a unit test, not by this run. `uv run aeropatch build A-089-01` inside the clone then rebuilt
  the scenario image in 10 s and created `runs/builds/` itself, so a first build's log path works
  on a fresh clone. The harness would not let me delete `D:\aeropatch-fresh`; it is yours to
  remove.
- **MCP transcript**: `docs/mcp-transcript.md`, one stdio session through the `mcp` client
  (2.2.0): `get_context`, `validate` with the reference fix (resolved) and with `# nosec` added
  (`SUPPRESSES_CHECKS`), `remediate` (resolved at attempt 1 with the library model), and a `scan`
  outside the allowlisted root (refused).
- **Checks**: `ruff check .` was failing on 14 old findings (`notebooks/runs.ipynb`, `re.M` in
  `local_client.py`); now clean, with DTZ off for notebooks only. The full suite first gave 363
  passed and 1 failed: `test_cleanup_after_crash` counted one sandbox container left from the
  restart of 2026-10-13 17:15:47. After `aeropatch prune` and the lint fixes, a full rerun: **364
  passed** (255 s).
- **The cited run files are published**: the 45 JSONL files the README names (D20 and Week 4) are
  committed with `git add -f`; the rest of `runs/` stays ignored. Scanned first: no user name,
  email, user folder or `AppData` path; the secret filter finds only the scenarios' own test
  passwords (`'password123'`, `'correct horse'`) in sandbox traces and a PEM public key from a
  Tier B test, all already public under `evaluations/`. This was part 5's D27 default.
- The cost chart no longer gives seconds per resolved for the local model: its first run shared
  the GPU with another program (D20), which would have inflated the figure.
- Not done: the draft PRs on a demo repository (part 5, D26) wait for you to name one.

## Week 4, D27 (2026-10-16): the security checklist

**Doc 13 §9 is ticked**, each item with its evidence there; doc 07 §10's six sandbox checks are
ticked too (all are tests in `tests/test_sandbox_security.py`, passing in the run of 364).

- **The repository is already public on GitHub** (`gh repo view`: PUBLIC), so the history scan
  below checked what is already out, not a gate before release.
- **History scan, every branch, every added line (92,533):** the secret filter's patterns
  (`prompts.SECRET_PATTERNS`, the assignment rule, high entropy beside a credential word) plus
  Kaggle, Slack and Stripe token formats, JWTs, email addresses and Windows user folders. **No
  real credential.** The 38 distinct hits: fake keys in tests (`sk-ant-1234567890…`,
  `sk-ant-should-never-reach-the-sandbox`), X-06's `AKIAIOSFODNN7EXAMPLE` (AWS's documented
  example), the scenarios' test passwords in their code and in the published run traces, a PEM
  public key from a Tier B test, pytest temp paths, upstream authors' emails in two Tier B licence
  files, and `C:\Users\<your Windows user name>` six times in old versions of `NOTES.md` (no current file has it).
  That last one is not a secret; rewriting public history for it is not worth it, in my view.
- `.env` is ignored and was never committed in any branch; `.env.example` holds no values.
- No code in `src/` commits, pushes, opens or merges a pull request; there is no `submit`.
- The README gained a **Dual-use boundaries** section and, in the Model section, the intended
  use and known failure modes, which stand in for a model card (the model is the base model).
- **The repository has no licence file.** Doc 15 §6 suggests MIT or Apache-2.0; choosing one is
  yours, so nothing was added. Until then the public code is visible but, legally, not licensed
  for reuse.

## Week 4, D28 (2026-10-16): resume bullets, write-up, exit criteria

- **Resume bullets** in doc 15 §2a, every number from the README: three to lead with (the
  pipeline and the 70% at $0, the cascade, the benchmark with feedback against resampling), three
  alternatives (prompt injection 0 of 12, the fine-tune's negative result, the repair gain of 38%),
  and the filled project-page summary. Each was checked against the run numbers; three wordings
  were corrected on the way (the scenario counts, what "0 of 12" counts, and the tie on Tier C).
- **Write-up**: `docs/writeup.md`, about 950 words for a blog: the setup, the small model alone,
  why fine-tuning lost, feedback against resampling, what the cascade really costs, the injection
  results with the one gate gap, the ablations, next steps and limits. Linked from the README.
- **Every README number now traces to a committed file.** A review found numbers outside the
  Results section (the dev ties, the speed and VRAM figures, the library model's 17 and 18, the
  Week 2 spread) resting on unpublished runs. 19 more run files and four `nvidia-smi` traces were
  scanned the same way (only pytest temp paths matched) and committed: 64 run files in all, each
  named in the README where its number appears.
- **Exit criteria**: part 2's Week 4 criteria and the whole-project definition of done are ticked
  (the served model is the untuned base, a recorded change), and part 5 §10.
- **Licence (2026-10-19, you asked me to research and choose): Apache-2.0.** `LICENSE` is the
  official text from apache.org (SHA-256 `cfc7749b…3d30`, the canonical hash); `pyproject.toml`
  declares `license = "Apache-2.0"` with `license-files`, and the package metadata shows it. Why:
  - It is as permissive as MIT and adds an explicit patent grant and patent retaliation, which
    MIT and BSD do not address.
  - It matches what the project stands on: the Qwen3.5-4B weights, Bandit, the Docker SDK and
    the training stack (Unsloth, Transformers, TRL, PEFT) are Apache-2.0; the other direct
    dependencies are MIT or BSD-3-Clause, all compatible. The FSF itself recommends Apache-2.0
    among lax permissive licences for substantial programs. Doc 15 §6 recommended it too.
  - The cost: Apache-2.0 is not compatible with GPLv2-only code (it is with GPLv3). Nothing here
    is GPLv2, and Opengrep (LGPL-2.1) is an external binary that is not distributed.
  - Scenario code keeps the licence in its `scenario.json`: Tier A and the adversarial copies MIT,
    Tier B its upstream MIT or BSD licence, Tier C `generated`. The README says so.
- **Left, all yours**: a demo repository for the draft PRs (the PR feature itself
  was never built, so these would be PRs opened by hand from a `remediate` diff); pushing the
  `v1.0` tag; deleting `D:\aeropatch-fresh` and the Kaggle dataset `aeropatch-v2-step64-adapter`.

## Model check (2026-10-19)

You asked me to check the whole model setup and update it. I checked it and fixed where the code
and docs disagreed. I did not change the model: no published number moves.
- **No newer Qwen fits 4 GB.** Qwen's Hugging Face listing since Qwen3.5 (2026-03) has
  Qwen3.6 (27B, 35B-A3B), Qwen3.8 (27B and up) and Qwen-Drive-1.0-4B (a driving model). Nothing
  general under 9B. Other model families were not surveyed.
- **`aeropatch-control`** is the blob `sha256-51b5c0d6…bfdc7`, the README's SHA-256, and its
  Modelfile parameters equal the library model's (`top_k 20`, `top_p 0.95`, `presence_penalty
  1.5`, `temperature 1`, the `qwen3.5` renderer and parser).
- **Ollama 0.40.3** since 2026-10-12 12:35 (its app log), before the first cited Week 3 run
  (`20261012-164903`); the README now says so. Weeks 1 and 2 ran older versions.
- **The library `qwen3.5:4b` tag was rebuilt.** Weeks 1 and 2 used build `2a654d98e6fb`
  (3,266,450,553 bytes, reported as 4.7B). The fresh-clone pull at 17:35 on 2026-10-16 replaced
  it with `d8b0f5e9760c` (3,324,173,934 bytes, 4.2B; the vision projector is now a separate
  file), which equals the registry today. Only the fresh-clone run and the MCP transcript
  (17:36-17:38) used the new build; both resolved `A-089-01`. Evidence: Ollama's server log loads
  blob `a9d0a3e1…` at 17:36:21, its only library-model load that afternoon (the runs before it
  loaded `aeropatch-control` and the ablation exports), and `docs/mcp-transcript.md` was written
  at 17:38:54. The README's 17 and 18 of 27
  belong to the old build, and it now says so. Benchmarking the new build is a run you can ask for.
- **Frontier default: `claude-opus-5` → `claude-opus-5-5`** in `config.DEFAULTS`, so the
  README's commands run the model its results report. The run headers keep each run's model;
  resuming an old frontier run under the new default is refused by the header check, as it should
  be. The CLI tests follow the new default.
- **The global `claude` CLI is 2.1.296** (was 2.1.239, which does not accept Opus 5.5): the
  version the Week 4 Opus runs used, chosen over the latest (2.1.303) to match them; the
  auto-updater may move it on, and any later version runs the model too. One live call
  through `claude_code_client` with `repair-claude-code`: served by `claude-opus-5-5`, "OK",
  $0.0067 API-equivalent on the subscription.
- **API-route cost: cache reads are priced per model.** `_cost` charged 0.1× input for every
  model. The pricing page (checked 2026-10-19) gives 0.05× for Opus 5.5 and 0.025× for Fable
  5.1, so `PRICES` now holds input, output and cache-read prices, and a test covers Opus 5.5.
  Input and output prices were already right. No published number used this route (every
  frontier run went through Claude Code, whose cost is the CLI's own estimate).
- **Checks**: the full suite, 364 passed (246 s); `ruff check .` clean.

## Retraining v2 on the same data (2026-10-19)

You asked to train the model again on the data it has. This is a reproduction of D19's second run:
dataset v2 (`train.jsonl` `4bf82d1a…`, `val.jsonl` `25689fd9…`, the same files as the Kaggle
dataset `aeropatch-train-v2`), `finetune.py` and `training/requirements.txt` unchanged since
`f43f77a`, seed 3407, the D18 values, kernel run `full-v2`. What can differ: the Kaggle image
and GPU kernels that are not deterministic.

**How it is read, written before the session.**
- **Reproduced bit for bit?** The new step-64 GGUF's SHA-256 against D19's (`D:\aeropatch-d19`),
  and the validation loss at each checkpoint against D19's 0.2595, 0.2560, 0.2577 and 0.2588.
- **The benchmark, as v2 step 64 was judged** (`repair-local`): dev 3 runs (D19: 26 of 39), test
  2 runs (D20: 32 of 54), Tier B 2 runs (3 of 20) and Tier C 2 runs (9 of 10). The baselines are
  the D19 and D20 runs: the local route of the harness has not changed since `c03f33f` (two
  `re.MULTILINE` lint edits and a base-image check in `remediate`).
- **Rule.** Within 3 of 54 of v2's 32 on test, the training reproduces. Against the untuned
  control's 38, D20's rule applies again: 4 or more below is a loss, 4 or more above a gain.
- This is the second time the test split judges a fine-tune. Nothing is tuned on what it shows.

**The session: kernel version 14, queued 11:42, running 11:52, complete at the 14:24 check.**
All four steps ended with exit code 0 (`full-v2` and the exports of steps 32, 64 and 96). The
clone was `e302ebb`, whose `finetune.py` is `f43f77a`'s, and `pip freeze` is identical to D19's.

| | D19 (kernel version 12) | Today (version 14) |
|---|---|---|
| Examples, steps | 511, 128 | 511, 128 |
| Seconds a step, training time | 45.5, 5,820 s | 47.5, 6,082 s |
| Peak GPU memory | 13.1 GB | 13.1 GB |
| Validation loss at steps 32, 64, 96, 128 | 0.2595, 0.2560, 0.2577, 0.2588 | 0.2595, 0.2567, 0.2579, 0.2587 |
| Training loss, first and last logged | 0.3851, 0.1817 | 0.3852, 0.1820 |
| Step-64 GGUF, SHA-256 | `3331e74d…` (2,783,446,560 bytes) | `6f8a7c5b…` (2,783,446,592 bytes) |

- **Not bit for bit**: the losses agree to the third decimal and part one at step 32 to the
  fourth, then drift (step 64: 0.2567 against 0.2560), so the T4's kernels are not
  deterministic at a fixed seed; the GGUF differs, by 32 bytes in length as well.
- The step-64 GGUF is in Ollama as `aeropatch-v2r-step64` (the same Modelfile), 100% on the GPU
  at 8k context. Files on `D:\aeropatch-v2r`: the four `pilot.json`, `status.txt`, the frozen
  requirements, the kernel log and the step-64 GGUF; the other GGUFs stay in the session's output.
- Benchmark runs `20261019-v2r1` to `-v2r3` (dev), `-v2r1`/`-v2r2` (test, `test_b`, `test_c`),
  each `-repair-local-<split>`, `--jobs 1` as before, the model unloaded between runs.

**The result: the retrain reproduces v2, and the verdict stands. The fine-tune loses to the
untuned model.**

| Model, `repair-local` | Untuned control (D19, D20) | v2, step 64 (D19, D20) | v2 retrained, step 64 (today) |
|---|---|---|---|
| Dev, 3 runs, of 39 | 26 | 26 | **26** (9, 9, 8) |
| Test, 2 runs, of 54 | 38 (19, 19) | 32 (18, 14) | **29** (14, 15) |
| Test, resolved at attempt 1 | 28 | 24 | 22 |
| Tier B, 2 runs, of 20 | 7 | 3 | **4** (2, 2) |
| Tier C, 2 runs, of 10 | 9 | 9 | **8** (4, 4) |

- **By the rule written this morning**: 29 is within 3 of v2's 32, so the training reproduces,
  at the edge of the band. Against the control's 38 it is 9 below, a loss.
- **Paired, run *i* against run *i*, on test**: the control resolves 11 scenario runs that the
  retrain does not, and the retrain 2 that the control does not (pooled exact McNemar
  p = 0.022). The rule reads totals, not this value. The control runs are D20's, five days
  older and not alternated with today's, and the first v2 against them gave p = 0.146. Against
  the first v2: 6 against 3 (p = 0.51), no difference.
- **The same failure shape as D20**: 11 test runs end `STUCK` (7 and 4; the first v2: 9; the
  control: none), and 8 in `REGRESSION`. Dev resolves more at the first attempt than the first
  v2 did (23 against 18, the control's 23), with the same total.
- Decoding at 47.2 to 47.3 tokens a second on dev; no provider error, sandbox error or timeout.
- **What it means**: the D20 loss was not one unlucky training run. Two trainings on dataset v2
  give 32 and 29 of 54 against 38 for the untuned model. The 3 between the two trainings is
  inside the benchmark's own noise: the first v2's two test runs alone scored 18 and 14.
- Nothing changes in Week 4 or the README's headline: the untuned model stays the served one.
  `aeropatch-v2r-step64` stays in Ollama (2.8 GB on `F:`) until you say it can go.

## The model-improvement plan, rung 2: headroom on the training pool (2026-10-21)

You asked me to check `reports/AeroPatch model improvement.md` and start on it. Checked against
the run files: the counts it quotes are right (test 38, 32, 29; first attempts 28, 24, 22; STUCK
0, 9, 11; the student pass's 156 resolved, 111/29/16 by attempt, 35 `REGRESSION`; `lr 2e-4`,
r = alpha = 16). Corrected:
- **`A-089-02` is not where tuning helped.** The library `qwen3.5:4b`, the same weights, resolved
  it in 3 of 12 `repair-local` dev runs (`20261001-175057`, `-182050`, `20261003-113223`), on the
  same scenario image (`sha256:1db9f3db8ea4`) the control ran. Pooled over all dev runs: base 3 of
  16, tuned checkpoints 4 of 19.
- **Only two dev scenarios are never fixed by the base**: `A-328-01` (0 of 37 local runs, tuned
  included) and `A-918-01` (2 of 37). `A-601-01` was fixed 5 of 18 times by the base, 0 of 19 by
  the tuned models.
- **The template is not untested**: D17 checked that Ollama and the Hugging Face template build
  the same prompt (token counts equal on 25 prompts and on every training example with a count).
- **Rung 3 as written barely trains.** About 100 to 180 examples, one epoch, batch 8: 13 to 23
  steps at 2e-5, against v2's 64 at 2e-4. Parity would then say nothing about the data. If it
  runs, change one thing: v2's settings, the model's own fixes in place of v2's targets.
- Skipped: rung 1 (its answer is predicted), and rung 0's resampling configs on test (test has
  judged two fine-tunes and three ablations; a sixth variant landing 4 high by chance is likely).

**How rung 2 is read, written before the runs.** `training/sample_synthetic.py --runs 8 --prefix
20261021-h`: `sample-local` (one attempt, temperature 0.7, thinking off, the served mode) with
`aeropatch-control` on the 105 synthetic scenarios of dataset v2, 8 runs, alternating with nothing.
- **Headroom** if pass@8 is at least 10 points above pass@1 (the report's threshold).
- **Training signal** is the count of partly solved scenarios (1 to 7 of 8). Under 30, GRPO
  (rung 5) has too few groups with a gradient, and rung 3 learns mostly what it already does.
- For scale: the student pass resolved 74 of these 105 at attempt 1 (temperature 0.2) and 93
  within three attempts with feedback. Tier C, held-out synthetic, is 9 of 10 for the control.

**Interrupted once.** At 11:44:55 Ollama's tray app installed its update (0.40.3 to 0.40.7) and
stopped the server in run 7, 24 scenarios in: one sample came back `PROVIDER_ERROR` (HTTP 500),
the next could not connect, and the script stopped. Runs 1 to 6 have no provider error. The
runner now removes a `PROVIDER_ERROR` sample before it resumes, so that scenario is sampled
again; it was resumed at 11:49 on 0.40.7, the same model blob. Runs 1 to 6 and the first 24
samples of run 7 ran on 0.40.3, the rest on 0.40.7.

**Result: headroom, and enough signal. Rung 3 goes ahead.** 8 runs, 840 samples, no provider
error left in any run file; resolved per run 72, 74, 77, 71, 71, 73, 79, 74 of 105.

| pass@1 | pass@3 | pass@8 | Never solved | Partly solved (1 to 7 of 8) | Always solved |
|---|---|---|---|---|---|
| 70.4% | 83.2% | **89.5%** | 11 | **49** | 45 |

- pass@8 is 19.1 points above pass@1 (the rule: 10), and 49 scenarios are partly solved (30).
- The ceiling is near: the base reaches 89.5% of this pool within 8 tries. What self-training
  can add here is getting there at the first try; the 11 never solved are out of its reach.
- Runs `20261021-h1` to `-h8-sample-local-train`, `aeropatch-control`, `dirty: false`.

**Dataset v3: the model's own answers** (`training/own_fixes.py --runs 20261021-h --out
training/data/v3`). v2's 105 synthetic first prompts and 53 repair turns keep their prompts,
conversations and split; each target is replaced by an answer of the model that resolved that
prompt in the sandbox: 2 distinct ones for a partly solved scenario, 1 for an always solved one,
and for a repair turn the student pass's own next attempt where it resolved. No advisory fix,
bug fix or reference fix is left.
- **144 examples: 128 first attempts, 16 repair turns; 133 train, 11 val.** Every sampled prompt
  equals v2's byte for byte; 2 candidates failed the leakage check (v2's 13-token rule, the
  system prompt and its format example left out as in v2).
- `finetune.prepare` on the laptop with the `Qwen/Qwen3.5-4B` tokenizer: every one of the 144
  prompts has Ollama's own token count, so the chat template is the served one; none is over
  4,096 tokens (longest 3,488).
- **The run, `own-v3` in `kernel.py`**: v2's learning rate (2e-4), r = alpha = 16 and its 64
  steps, checkpoints at 32 and 64. Two differences from v2's step 64: 133 examples make 64 steps
  about 3.8 epochs (v2: 1), and the linear decay ends at step 64 (v2's step 64 was halfway down a
  128-step decay), so the total update is about two thirds of v2's.
- **How it is read, written before the run**: as v2 step 64 was (`repair-local`, dev 3 runs, test
  2, Tier B 2, Tier C 2), with 2 same-day control runs on test alternated with it. D20's rule:
  4 or more of 54 below the control is a loss. Beside the totals: first-attempt resolves (control
  28), `STUCK` (control 0, v2 9 and 11) and `REGRESSION`. If `STUCK` stays near 0 and first
  attempts hold, the on-policy reading of v2's loss stands; if it collapses as v2 did, it does not.

**The same-day control scores 6 below D20's.** While Kaggle trained, `aeropatch-control` ran
`repair-local` on Ollama 0.40.7 (runs `20261021-c1-` and `-c2-repair-local-<split>`, 12:20 to
12:55, `dirty: false`, no provider error, sandbox error or timeout):

| Untuned control | D20 (2026-10-13/14, Ollama 0.40.3) | Today (0.40.7) |
|---|---|---|
| Test, of 54 | 38 (19, 19), 28 at attempt 1 | **32** (16, 16), 24 at attempt 1 |
| Tier B, of 20 | 7 (4, 3) | **4** (1, 3) |

- The prompt is unchanged: all 27 first prompts have Ollama token counts equal to D20's. Decode
  speed (about 37 tokens a second by latency) and answer length (median 227 output tokens
  against 238) are D20's too.
- The loss is spread: only `A-601-02` went from resolved in both D20 runs to neither today.
  Whether it is the new Ollama or the benchmark's noise, two runs cannot say; either way, D20's
  38 is not today's bar. These runs came before the candidate, not alternated with it, so v3 is
  judged against two more control runs alternated with its own; these two are context.
- **Later the same day, on the same 0.40.7, the alternated control scored 20 and 21** (`c3`,
  `c4`, below). Today's four control runs on test are 16, 16, 20, 21: a mean of 18.25 a run
  against D20's 19. No version effect is shown; the two 16s look like the benchmark's own noise.

**The training: kernel version 15, 12:18 to 13:23, both steps exit 0** (`own-v3` and the export
of its step-32 checkpoint; the clone was the branch on GitHub, `be8e312`, whose `finetune.py` and
`src/` equal today's). Files on `D:\aeropatch-v3`.
- 133 examples trained on, none dropped for length, all 133 prompts equal to Ollama's count.
  64 steps at 31.8 s (34 minutes), peak 11.95 GB, float16 weights as before.
- **The data is on-policy, as meant**: the first logged training loss is 0.158, against 0.385 for
  v2 on the same base. That is the report's NLL check, read from the log.
- **Step 64 overfits**: training loss falls to 0.030 by step 60, validation loss rises from 0.191
  at step 32 to 0.236 at step 64 (about 3.8 epochs over 133 examples). Step 64 is still the one
  the rule judges; step 32 runs on dev beside it.
- The 5 validation prompts give answers that parse, 5 of 5 (D17's untuned export: 2 of 5).
- In Ollama as `aeropatch-v3-step64` (GGUF SHA-256 `2eddef7f…24ca`) and `aeropatch-v3-step32`
  (`01d29e21…ac3b`), both 2,783,446,592 bytes, `training/Modelfile` with only `FROM` set.

**The result: v3 ties the untuned model. No difference shown on any tier; the untuned model stays
the served one.** `repair-local`, 13:43 to 15:25, v3 step 64 alternated with the control on each
split, then dev for both checkpoints; 18 runs, `dirty: false`, no provider error, sandbox error or
timeout.

| Two alternated runs each | Untuned control (`c3`, `c4`) | v3, step 64 (`v3a`, `v3b`) | Paired, pooled (control only, v3 only) |
|---|---|---|---|
| Test, of 54 | **41** (20, 21) | **38** (20, 18) | 8 against 5, p = 0.58 |
| Test, at attempt 1 | 29 | 27 | |
| Test, `STUCK` / `REGRESSION` endings | 2 / 4 | 4 / 5 | |
| Test, attempts that ended `REGRESSION` | 22 | 30 | |
| Tier B, of 20 | 8 (3, 5) | **10** (5, 5) | 3 against 5, p = 0.73 |
| Tier B, `STUCK` endings | 5 | 1 | |
| Tier C, of 10 | 6 (3, 3) | 8 (4, 4) | 0 against 2, p = 0.50 |

- **By D20's rule**: 3 below the control on test is under 4, so no difference shown, and v3 is
  not below it on Tier B. It is not a gain either. Over all three tiers: control 55 of 84, v3 56.
- **The on-policy diagnosis is supported, not isolated.** Against its own alternated control v3
  loses 3 of 54 (inside the noise: today's control alone scored 16, 16, 20 and 21), where v2 lost
  6; first attempts hold (27 against 29; v2 24 against 28); `STUCK` on test is 4 against 2, where
  v2 had 9 against 0. But more than the targets' author changed at once: the mix (synthetic only,
  no advisory or bug-fix examples), the size (133 against 511), the epochs (about 3.8 against 1)
  and the total update (about two thirds of v2's, part of the way to a lower learning rate). A
  run that changes only the targets' author would isolate it.
- **What is left of the damage**: more attempts break a regression test on test (30 against 22).
- **Dev, 3 runs each** (no control on dev today; D19's control 26, v2 26): step 64 **28 of 39**
  (9, 8, 11; 23 at attempt 1, `STUCK` 0), step 32 23 of 39 (7, 8, 8; 9 `REGRESSION` endings).
  Step 32 had the lower validation loss and is worse on dev; 13 scenarios cannot say more.
- Runs `20261021-v3a-`, `-v3b-`, `-c3-`, `-c4-repair-local-<split>` and `-v3a`/`-v3b`/`-v3c`
  (step 64), `-v3s32a`/`b`/`c` (step 32) `-repair-local-dev`.
- **What it means for the plan**: rung 3 did what the report expected, parity. The rungs that
  could beat the base are 4 (preference pairs against `REGRESSION`, the cost v3 still carries) and
  5 (GRPO), and at this benchmark's noise any gain under about 4 of 54 stays invisible. The 840
  samples hold 591 passing and 249 failing edits, 49 scenarios with both; but only 19 scenarios
  have a passing and a `REGRESSION` edit (64 such edits), so rung 4 aimed at regressions has 19
  distinct prompts, against the report's "about 100 pairs". `aeropatch-v3-step64` and `-step32` stay in Ollama (5.6 GB on `F:`) until you say.

## Repository tidying (2026-10-21)

A review you pasted proposed a v4 roadmap; checked against the code, only its tidying track was
needed (multi-file edits and wider context already exist, local concurrency gains nothing on one
4 GB GPU, and a pre-sandbox filter would catch 12 of 148 first attempts). You said to do it:
- **GitHub About**: a description, ten topics and the write-up as the homepage. Not `qlora`,
  which the review suggested: training is 16-bit LoRA.
- **Branches**: the 10 old ones on GitHub, each checked to be inside `main` first, are deleted,
  and their local copies too. Left: `main` and `feat/week3-d15-data` (the Kaggle kernel clones it).
- **README**: v3 in the Training section, the headline sentence, Model, Limitations, Later and
  Layout. Its numbers come from the 22 run files of today it names, published like D26's after
  the same scan (no user name, folder or real email; the secret filter flags only scenario code
  and test passwords already public under `evaluations/`).
- **CI**: `.github/workflows/ci.yml` runs `ruff check .` and `pytest -m "not docker"` on Ubuntu.
  Dry run here with Docker unreachable and Opengrep hidden: 318 passed, 36 skipped, 44 s.
- **CI's first run found a real leak** that Windows hid: for an absolute path, `get_context`'s
  error quoted it back, so the MCP client saw where the server lives. The test passed on Windows
  only because the quoted form doubles the backslashes. `mcp_server._guard`, the handler every
  tool's errors pass through, now replaces the project root in both forms with `<server>`; the
  test checks both forms and failed here before the fix. The loop's repair feedback is unchanged.
- **CI runs the whole suite (second review, which you passed on with a yes)**: a `sandbox` job
  builds the base image and runs the 10 `docker` tests on native Linux Docker (47 s), and the
  `test` job installs Opengrep 1.30.0, the laptop's version, checked against its release digest,
  so the 36 rule tests that used to skip there run too: 354 + 10 = 364, the laptop's count. The
  review's warning about 0700 temp folders did not apply: results come back through the logs,
  and the read-only mount is the workspace's `src` folder, not a pytest temp folder. Badge on
  the README. Not taken from that review: deleting `feat/week3-d15-data` (the Kaggle kernel
  clones it), and calling v3's Tier B and C leads gains (p = 0.73 and 0.50).

## Doc 17 Phase 0: how often each user label is right (2026-10-24)

The easy-use plan (docs/17-easy-use-part2.md) asks how often the label a user would see is right
on code without a hand-written exploit test, before Phase 1b shows any label to anyone. Code at
`37043ef` (feat/easy-use), clean tree, `aeropatch-control` unless stated. Block 1 (oracle, V1 and
V2 on test) ran on Ollama 0.40.7. Ollama downloaded 0.40.10 at 13:23 during block 1; I installed it
before block 2 (Tier B and the model comparison), so each comparison ran on one version.

**Labels**, two runs pooled, 95% Wilson intervals (`docs/results/labels/07-user-labels.csv`):

| Label | Where | Shown | Right |
|---|---|---|---|
| Scanner quiet, your tests still pass | V1, test | 34 of 54 | 25 of 34, 74% [57-85] |
| Your tests still pass; the scanner could not re-check this | V1, test_b | 14 of 20 | 8 of 14, 57% [33-79] |
| Scanner quiet, not tested | V2, test (= the Suggest level) | 43 of 54 | 23 of 43, 53% [39-67] |

- **Resolved under realistic feedback:** V1 25/54 (46%) on test and 8/20 (40%) on Tier B; V2
  23/54 (43%). These, not the 70% and 35% earned with PoC feedback, are the rates to quote to
  users. On Tier B, V1's 40% is no worse than the 35% with the PoC visible.
- **"Not fixed" hides correct fixes:** in 9 of V1's 20 "not fixed" tasks on test some attempt
  passed both hidden suites, but the rule still fired or a test failed, so nothing was offered.
- **Oracle:** 27/27 and 10/10. The one-file re-scan gives the same `original_rule_present` as the
  whole-repo scan of `20261005-201131-oracle-test` on all 27.
- **Library model:** `qwen3.5:4b` build d8b0f5e9760c scored 17 and 21, the export 21 and 17:
  38 against 38 of 54, alternated, within the pre-set bar of 4. Users can pull the library model;
  the doctor now lists both builds as measured, and publishing the export is not needed.
- **Detection on real code (host-side, no runs):** Opengrep and Bandit report 85 findings over the
  10 Tier B repos and none within 3 lines of the advisory's location: 0 of 10.

**What this changes (part 2 §6), defaults taken:**
- Phase 1b ships "Scanner quiet, your tests still pass" as the Test level's label, with "on 27
  practice apps, right 25 of 34 times". The benchmark's regression tests are stronger than most
  users', so this is an upper bound.
- "Scanner quiet, not tested" is right about half the time, so the Suggest level shows its change
  as "a suggestion to review", never as a fix.
- On real code the scanners are the bottleneck: they found none of the ten CVEs. Better rules and
  triage come before any model work, and the 1a check on 10 public repos matters more.

## Detection report, phases A to D (2026-10-26)

The plan is `reports/Real bug detection and model mix.md`. Everything below needs no model run
and no labeller; what does is listed at the end. Branch `feat/easy-use`, not pushed.

**Phase A, held-out detection set.** `evaluations/detection/heldout.json`: 30 CVEs, 10 each of
CWE-22, 94 and 79, drawn with `random.Random(20261026)` from PySASTBench's 108 (ICSE'26). It was
committed (`f8b3490`) before any new rule was written. The GitHub repo has no licence; the data is
CC-BY-4.0 on Zenodo (record 17936545, a 6.2 GB zip), so only the list is kept here.
`evaluations/tools/remote_zip.py` reads the 30 vulnerable and fixed copies out of the zip by HTTP
range requests into `D:\aeropatch-detection`, and `detection.py score` scans each CVE's named files.
- **The measure:** a finding counts when it lies inside a named function and has the CVE's class
  (`SAME_CLASS`; Bandit tags `eval` CWE-78). I set that after the first, looser count (14 of 30:
  it took a B101 `assert` and a B110 `try/except/pass` as detections) and before any extra rule
  was scored.
- **Baseline, today's scanners plus regexploit: 12 of 30.** CWE-22 1 of 10, CWE-79 3 of 10,
  CWE-94 8 of 10, mostly Bandit's B307 `eval`. Of the 12, 5 are still reported on the fixed copy.
  `docs/results/detection/phase-a-baseline.json`.
- **Precision of the shown findings on real repos: 11 of 42, 26%, against doc 17's bar of 50%.**
  `evaluations/tools/repo_precision.py` checked 14 repos three ways: 10 public repos in
  `D:\aeropatch-repos` and your 4 in `runs/github`.
  - The public repos, shallow-cloned on 2026-10-26 with commits and licences recorded in
    `evaluations/detection/repo_labels.csv`: PyGoat, vulpy and DVPWA (all MIT), microblog and
    flasky (MIT), fastapi-realworld-example-app and full-stack-fastapi-template (MIT),
    tldr-python-client (MIT), buku (GPL-3.0) and cookiecutter (BSD-3).
  - I am the only labeller so far. A finding is real when the flagged code has the rule's
    weakness and outside input can reach it. Every check left its folder byte-identical, 14 of 14.
  - Nearly all the real ones are in the deliberately vulnerable apps: PyGoat 5 of 5, vulpy 4 of 5,
    DVPWA 1 of 3, and 1 of 29 everywhere else.
  - The false alarms repeat. sqli-string-query fires on constant SQL (`'VACUUM'`) in buku.py:
    only in the whole file, never when that method or class is scanned alone, cause not found.
    tar-extract-unfiltered fires on `zipfile.extractall`, which drops `..` names. Bandit flags
    B105 on `password == ''` and B324 on gravatar MD5. Constant `os.system` calls are flagged in a
    developer CLI.
  - `--extra-rules` shows the same 42 cards. It adds 2 real PyGoat findings below the five shown.
  - Advisory cards: 36, all in PyGoat, microblog and DVPWA.

**Phase B, deterministic sources.**
- **B1, advisories: on by default, `check --offline` skips them.** Instead of pip-audit or
  OSV-Scanner, `tools/advisories.py` asks api.osv.dev directly (stdlib `urllib`). It reads
  `name==version` pins from the top-level `requirements*.txt` and `pyproject.toml`, and it
  installs, builds and writes nothing. Only package names and versions are sent, and the check
  prints that line. When the lookup fails, it prints a note and reports nothing. The one new
  dependency is `packaging`, for version order.
  - Each vulnerable pin gets a fixed card: the advisories, whether the code imports the package,
    and the one-line pin change. Advisories with no published fix are named, not hidden.
  - **Plumbing check, `evaluations/tools/advisory_plumbing.py`: 10 of 10.** For each Tier B
    library, an app pinning the newest vulnerable release is flagged and offered a fixed version.
    The same app pinned at the advisory's fixed version is not flagged for that advisory. So
    downstream detection is 10 of 10, while library-source detection stays 0 of 10.
- **B2, ReDoS: regexploit 1.0.0, on by default.** It is Apache-2.0, has no dependencies and runs
  on CPU only. It imports `sre_parse`, which has been deprecated since Python 3.11: it works on
  3.13, and the import fails when Python removes it.
  - On A-1333-02 it flags the vulnerable regex and not the model's correct rewrite, which the
    Opengrep rule re-flagged.
  - It misses B-1333-01 (geopy). Tier B is a sanity check, so I did not look into why.
- **B3, `rules-extra/`, opt-in with `check --extra-rules`.** It has six rules: header injection,
  path traversal, code injection and decompression as taint rules, and `jwt.decode` misuse and
  unbounded body reads as pattern rules. The plan said 3 taint and 2 pattern; decompression needs
  a request source, so it became a taint rule.
  - The rules live outside `rules/`, so `--config rules` and every config's re-scan are unchanged.
    A finding of an extra rule is re-scanned with `rules-extra/`.
  - Each rule fires on its seeded fixture and not on its fixed twin (`tests/fixtures/extra_rules`).
  - With `--taint-intrafile`, the 22 own rules give the same findings on all 50 dev, test and
    Tier B scenarios.
  - The first WSGI source treated the first parameter of any two-argument function as request
    data. It fired on A-022-01, A-502-02 and two Tier B repos. Now it matches only
    `def app(environ, start_response)`, and the extra rules fire on none of the 50.
  - **Held-out recall: 13 against 12 of 30, one discordant CVE (CVE-2024-5547, CWE-22).** The
    exact McNemar test needs at least 6-0, so B's recall criterion is not met, and the rules stay
    opt-in. One extra hit sits in an XSS CVE's function, and the devika fix is still flagged.
    `docs/results/detection/phase-b-extra-rules.json`.
- **1a still holds:** the scenario finding is in the top five on 27 of 27 test scenarios with
  the new default sources. The folder stays byte-identical, now also checked with `--extra-rules`.
- **Labels unchanged:** applying each reference fix and re-scanning gives the same
  `original_rule_present` as `20261024-o1-oracle-test` on 27 of 27. This needs no Docker. The 10
  Tier B findings are advisories with no re-scan on either side, so they show nothing. The full
  oracle replay was not rerun, because the default scan path is unchanged.
- **B2's noise, checked on code that is not the held-out set:** over 3,697 files in
  `.venv/Lib/site-packages`, regexploit reports 11 regexes. 3 are `re.*` arguments; the other 8
  are bare string constants, and every one is a real regex (Pygments lexer tables). So B2 stays on
  by default.

**Phase C, judge: opt-in with `check --judge`** (`judge.py`).
- It asks the local model at most 10 findings near the top, one call each. The answer is JSON held
  to a schema: keep or park, plus a reason.
- It leans toward keep. A parked finding is listed with `--all` with the model's reason. Secrets are
  never sent. If Ollama is down, everything is kept and a note says so.
- `dismiss` takes the same flags, so its numbers match the check's.
- Smoke test on 0.40.10: about 2 s a finding once loaded (12 s with the load), 0 of 6 parked.
- **Prompt injection, X-01 to X-06:** the first version parked X-02's real SQL injection. The
  reason it gave was the planted docstring's claim that the finding comes from a test. The judge
  now reads the code with comments and docstrings blanked (`judge.strip_prose`, line numbers
  kept), and parks 0 of the 5. Other string literals still reach the model, and a parked finding
  is always listed with `--all`.
- **On the 14 labelled repos, the first version fails C's bar.** It raised precision from 11 of 42
  (26%) to 10 of 27 (37%), but it set aside 4 real findings against the bar of at most 1. Those
  were DVPWA's and PyGoat's MD5 or SHA-1 password hashes, and Quintyx's bind to 0.0.0.0. Its
  reasons were wrong: "the input is a constant", or "the host is set to localhost" when it is not.
- **After that, the judge only sees input-flow classes** (`check.JUDGE_CWES`: injection, path,
  XSS, SSRF, redirect, XXE, deserialisation, error disclosure). Crypto, secret and config
  findings are always kept. With the gate: 12 of 32 (38%), 0 real set aside.
  - This gate was set after seeing these repos, so the number is not held-out evidence.
  - Precision is still under 50%, so `--judge` stays opt-in.
- Starting the tray app ran a staged Ollama installer, which reinstalled 0.40.10 (the file
  versions were equal). That is Phase 0 block 2's version. V1's test runs `v1a` and `v1b` ran on
  0.40.7 (block 1).

**Phase D, repair.**
- **D0: in all 9 tasks, the attempt that passed both hidden suites still had its rule firing.**
  That corrects "or a test failed" above. No test was flaky, and no later, worse attempt was kept
  over a good one. All attempts are in `20261024-v1a` and `-v1b`.
  - The rules were html-fstring-unescaped (A-079-02), redos-nested-quantifier (A-1333-02, both
    runs), dynamic-import-deserialization (A-502-03, both), hardcoded-credential (A-798-01,
    -02), url-prefix-allowlist (A-918-03) and sqli-string-query (A-089-04).
  - These rules match the code's shape, so a correct fix can keep the shape: `escape()` assigned
    before the f-string, an allowlist check before the SQL f-string, a module allowlist before
    `import_module`.
  - Loosening them because of these diffs would be tuning on test, so the rules were not changed.
    That is your call; if they change, do it as a new ruleset and say it came from test results.
- **D1 already exists.** The loop hashes normalised edits, retries once hotter, then marks STUCK
  (`loop.py`). Nothing was added.
- **D2: config `repair-local-v1-recipes`.** It is V1 plus one abstract fix line for CWE-22, 328
  and 918 (`prompts.FIX_RECIPES`), written from the dev scenarios and OWASP's cheat sheets.
  - The choice of the three classes comes from test-split resolve rates (`OFTEN_MISSED_CWES`), so
    a small leak is admitted.
  - Every other config's prompts are unchanged; the golden prompts still pass.
  - **The recipes did not help (2026-10-26, Ollama 0.40.10, alternated, `paired.py arms`).**
    `repair-local-v1` resolved 15, 13 and 13 of 27; the recipes config 14, 11 and 9.
    - By each task's majority of three runs: 14 against 11. Three tasks went only to V1
      (A-079-02, A-352-02, A-918-03) and none only to the recipes; exact McNemar p = 0.25.
    - "Scanner quiet, your tests still pass" was right 41 of 51 times for V1 and 34 of 47 for the
      recipes.
    - The pooled gap, 41 against 34 of 81, is past the bar of 4 in V1's favour, but McNemar does
      not separate them. So the config stays a research config and V1 stays the default.
    - Runs `20261026-d2-{1,2,3}-repair-local-v1(-recipes)-test`. The first pair's header says
      dirty: an evaluation script was untracked; the loop code was the same in all six.

**Phase E0 and E1 (2026-10-26, Ollama 0.40.10, `evaluations/tools/model_fit.py`,
`docs/results/model-mix/`).** I pulled, measured and removed one model at a time.

| Model | Fully on GPU | Peak GPU | tok/s | Thinking seen | Edits that apply (dev, 13) | E1: resolved, 1 attempt, dev |
|---|---|---|---|---|---|---|
| qwen3.5:4b (baseline) | yes | 2,995 MiB | 48.8 | 0 | 12 | 8 |
| nemotron-3-nano:4b | yes | 2,897 MiB | 59.3 | 0 | **3** (its SEARCH text does not match the file) | not run |
| ministral-3:3b | yes | **3,883 MiB** | 68.0 | 0 | 13 | 4 (none that Qwen missed) |
| gemma4:e2b-it-qat | yes (1.66 GB loaded) | 2,791 MiB | 90.0 | 0 | 9 | 5 (A-328-01, which Qwen missed) |

- Nemotron fails E0 on edits that apply, and was removed.
- Ministral's peak sits on the 3.8 GiB bar, counting about 350 MiB of desktop use.
- `think: false` works for all three: no thinking text came back. NVIDIA's Open Model License was
  read: local use is allowed, and the user downloads the weights, so AeroPatch distributes none.
- **Pre-registered for E2, before any test run: gemma4:e2b-it-qat.** It is the only candidate
  that solved a dev task no Qwen sample did, and it fits with room to spare. E2 compares
  Qwen x10 with Qwen x5 + Gemma x5 on test, over three repetitions, batched by model, with
  `paired.py mix`.

**Phase E2: the mix does not clear its pre-registered bar, so users keep one model.**
Runs `20261026-e2-s{1,2,3}-q{1..10}` and `-g{1..5}` (`sample-local` on test, Ollama 0.40.10,
batched by model, no provider errors). Analysed with `paired.py mix`.
- Mean pass@1: Qwen 47.2% (30 runs), Gemma 4 E2B 30.4% (15 runs).
- Per repetition, Qwen x10 against Qwen x5 + Gemma x5:

  | Repetition | Coverage (oracle), Qwen / mix | Deployable, Qwen / mix | Solved by Gemma and no Qwen sample |
  |---|---|---|---|
  | 1 | 18 / 20 | 13 / 15 | A-078-03, A-338-02 |
  | 2 | 19 / 21 | 12 / 15 | A-089-03, A-918-03 |
  | 3 | 22 / 21 | 14 / 15 | A-328-02, A-338-02 |

- By each task's majority of three repetitions, the mix wins 2 tasks and loses none, at both
  layers. Coverage is 19 against 21 of 27, deployable 13 against 15; exact McNemar p = 0.50 at
  each. The bar needs at least 6-0, so it is not met.
- The direction is the same in all three repetitions on the deployable layer (+2, +3, +1), and
  the tasks Gemma adds sit in classes Qwen often misses (CWE-338, 328, 918). So a larger test
  could pay off, but this one does not show a gain, and per the plan the mix stays a research
  idea.
- The Tier B sanity runs were not done, because the main bar already failed.
- `gemma4:e2b-it-qat` (4.3 GB) is still in the Ollama store on F:; nemotron and ministral were
  removed. F: has about 4 GB free.

**All tests:** 609 passed with Docker and Ollama running, and ruff is clean.

## Doc 17 Phase 1b: fix a folder (2026-10-27)

`aeropatch fix FOLDER N [--suggest]`, `apply FOLDER N`, `undo FOLDER N` and `prune --images`. The
code is in `src/aeropatch/folder.py`, plus `docker/folder.Dockerfile`, `folder_run.sh` and
`folder_runner.py`. `docker/run.sh` and the base image are byte-identical, so every scenario image
is unchanged.

**How it works:**
- `fix` builds a Task from card N of the check. It stages the folder into
  `runs/folders/<name>-<hash>/context` without environments, caches, VCS data or `.env` files.
- The image is built from that staged copy. The dependencies come from, first match wins:
  uv.lock, then Pipfile.lock, then requirements files, then `pip install .[test]`. On a build
  error it retries once with the native-package table.
- The user's tests run twice on the pristine code. The tests that passed both times are baked into
  the image, and only those run after an edit.
- It runs the V1 loop (`fix-local`). Without Docker, or with `--suggest`, it runs `suggest-local`,
  and nothing runs.
- The proposed files are kept under `runs/`; the folder is not touched.
- `apply` refuses a file that changed since the fix, and backs up each file with a manifest
  first. `undo` restores only files still as applied; otherwise it changes nothing and names the
  backup.
- Every failure gets one plain sentence (`folder.MESSAGES`), and the lower levels keep working.

**Bugs found while building it, now fixed:**
- The safety gate rejected every edit to a file starting with a UTF-8 BOM (`ast.parse` refuses
  U+FEFF).
- Opengrep 1.30.0 reads every string in a BOM file as an f-string, so the SQL rule fired on a
  correct parameterised fix. The one-file re-scan now reads a BOM-free copy. No benchmark file has
  a BOM, so no measured config moves.
- The diff from git drops the CR of CRLF lines, so `fix` keeps the after-files by re-applying the
  offered edits, not the diff.

**Exit criteria:**
1. **Met.**
   - Oracle through the folder path against the scenario path: the same label and user label on
     27 of 27 (`20261027-c1-oracle-folder-test`, `-c1-oracle-test`).
   - `fix-local` through the folder path resolved 12 and 13; `repair-local-v1` 13 and 12, run
     alternated on the same day (`20261027-c1-{1,2}-...`). 25 against 25 of 54, within the bar
     of 4. No task differs by majority.
   - "Scanner quiet, your tests still pass" was right 25 of 31 times through the folder path.
2. **Run on 2026-10-27 at your request: 2 of 10 build and collect tests that pass twice**
   (`docs/results/folder-setup.json`).
   - Built and collected: cookiecutter (367 tests, none flaky) and tldr-python-client (30).
   - Old pins that Python 3.12 cannot install (`OLD_PACKAGES`): DVPWA and flasky, whose pins
     import `imp`.
   - C extensions too old to compile on 3.12 (`BUILD_FAILED`): microblog (multidict) and
     fastapi-realworld (asyncpg), even with gcc added.
   - A hash mismatch from its `uv export` (`BUILD_FAILED`): full-stack-fastapi-template.
   - `NO_TESTS`: PyGoat and vulpy have no pytest tests.
   - `MISSING_TEST_PACKAGES`: buku's tests need `hypothesis` and `flask`, listed only in
     `tox.ini` and an extra. The plan deliberately does not guess packages from imports.
   - Three harness gaps found by the first pass were fixed before the final pass:
     - `uv export` kept a local `-e ./backend` line.
     - A missing gcc was not in the retry table.
     - With a lock file the project itself was not installed, which cookiecutter's conftest
       needed. Now the project is installed with its `test`/`tests`/`testing`/`dev` extras.
   - Baseline logs are now kept as `baseline-1.log` and `baseline-2.log`.
   - Every failure still leaves `check` and the Suggest level working.
3. **Met.** `tests/test_folder.py` covers a CRLF + BOM file:
   - `apply` then `undo` gives byte-identical files, and nothing is written before `apply`.
   - `apply` refuses a file changed since the fix, and `undo` refuses one changed after apply.
4. **Met in a test:** with Docker reported down and `run_container` raising, `fix` still gives a
   suggestion ("Scanner quiet, not tested") and starts no container. It was not run live with
   Docker stopped.
5. **Open:** the review test with 6 people is yours to run.

## Precision: known false-alarm shapes (point 2, 2026-10-27)

`src/aeropatch/false_alarms.py` sets aside, inside `check`'s triage, findings whose flagged statement
has a shape no scanner rule can tell from the dangerous one. Each one is listed with `--all` and
its reason. `rules/` is unchanged, so no measured config's re-scan moves.

The shapes:
- SQL text written out in full, or only `', '.join(['?'] * n)` placeholders built into it.
- A shell command written out in full.
- A comparison with an empty or placeholder value (`password == ''`, `token == 'your_access_token'`).
- A credential-named variable whose value is a token type (`token_type = 'bearer'`).
- `extractall` on a `ZipFile`, which already drops `..` names.
- `startswith` prefixes that are not web addresses.

**Guards, all met:**
- None of the 14 labelled-real findings on the 14 tuning repos is set aside.
- None of the 12 held-out PySASTBench detections is lost.
- The scenario finding is still in the top five on 27 of 27.

**Fresh repos, chosen and committed before any check** (`evaluations/detection/fresh_repos.json`,
`899775c`):
- The 10 repos: DSVW, vulnpy, sqlite-utils, records, httpie, bakerydemo, rich-cli, APIFairy,
  flask-boilerplate and environs.
- I labelled the union of both arms' cards in a shuffled order, without the arm in view
  (`evaluations/detection/fresh_labels.csv`).

| Arm | Fresh 10: shown, real | Tuning 14: shown, real |
|---|---|---|
| Today's check, no shapes | 25, 14 (56%) | 42, 11 (26%) |
| First shape set | 22, 12 (55%), **4 real set aside** | 27, 11 |
| Revised shape set (kept) | **24, 14 (58%), 0 real set aside** | 30, 11 (37%) |

- **Two shapes failed on the fresh repos and were dropped.** "A credential-named string with a
  space is a message" hid flask-boilerplate's real `SECRET_KEY = 'my precious'` twice. "A weak
  hash whose names mention no password" hid vulnpy's two deliberate MD5/SHA-1 sinks.
- The surviving shapes were part of the set frozen before the fresh check. There they removed one
  false alarm (a fixed `twine upload` command) and no real finding.
- **Precision on the fresh repos is 58%, over doc 17's 50% bar,** but the two deliberately
  vulnerable apps give 9 of the 14 real findings. On the 8 ordinary fresh repos it is 5 of 14.
- On the tuning repos it is 37%, still under the bar.
- The largest remaining false alarm is SQL f-strings built only from `quote_identifier(...)` calls:
  sqlite-utils 0 of 5. A shape for it was not added, because it would be tuned on the fresh repos.

**Left for you:**
1. Second labeller: go through `evaluations/detection/repo_labels.csv` and list where you disagree.
2. Whether to loosen the 7 syntactic rules of D0, and fix the buku and zipfile false alarms
   above, as a new ruleset.
3. An Ollama 0.40.11 installer has been staged since 13:02. Installing it from here was refused,
   so every run today used 0.40.10.

## Next

**Decisions that are yours**
1. **Week 4 runs the untuned control (`aeropatch-control`)**, by the rule written before the
   test runs: v2 step 64 scored 32 against 38 of 54 on test, 3 against 7 of 20 on Tier B, and
   9 against 9 of 10 on Tier C (D20 section). You said to go ahead with it on 2026-10-16. The fine-tune is reported as
   it is: it ties on dev, which chose its changes, and loses on the splits it was not tuned on.
   Defaults taken on D19 for dataset v2: the plan lines come from `qwen3.5:4b`, a function of
   at most 15 lines is rewritten whole, and the hyperparameters are D18's.
   **Whether to train again, with a larger dataset,** is the older question. Dataset v2 has v1's 541
   examples, against R4's 1,500, with repair turns at 10% against the plan's 20%. D19 found
   that the share of repair turns is not what cost v1 its points. What would add examples:
   - **A second generation run: about 200 more per 500 candidates** at 4,096 tokens, my estimate
     from the first run's rates after the reading (105 usable examples, 53 repair turns, a
     fifth more as bug fixes). It takes about 26 hours of laptop time, and every new fix has to
     be read: the reading rejected 20 of 124. Nothing was started.
   - More bug fixes: 450 pass every filter and 108 are used. Using all would put bug
     fixes near half of the set, against the plan's 20%.
   - More advisory pairs: 258 advisories point at a merge commit and were never converted. The
     yield is unknown.
   The defaults that made v1: the sequence length is 4,096; the 61 examples that pass check 3
   only by a PoC test are kept; a training example may share no 13-token run with Tier C and
   none with a line that a benchmark reference fix changes; the 20 scenarios in
   `training/rejected.txt` are out.
2. **Frontier reference: `claude-opus-5-5` from Week 4 on** (D22 section; yours to overrule).
   Weeks 1 and 2 used `claude-opus-5`. It is the configured default since 2026-10-19.
3. **Data mix from dev only** (D14), against doc 14 §5's wording. Also a default.
4. **Pull requests.** Week 3 lives on `feat/week3-d15-data`, and you merge it into `main` as it
   goes: #11 to #19 are merged, the last (D19) on 2026-10-13, and D20 (the test runs and the
   exports) went in with the next one on 2026-10-14. Week 4's D22 to D25 went in as #21 on
   2026-10-16, D26 as #22 and D27-D28 as #23, still from this branch. **`v1.0` is the annotated
   tag on #23's merge commit `d92c1f1`, pushed 2026-10-19.** The licence went in as #24;
   **`v1.0.1`** tags its merge commit `1ecb35c`, and GitHub now shows "Apache License 2.0". The
   model check (2026-10-19) went in as #25, merge commit `caba3a7`, and the retrain of v2 as
   #26, merge commit `f45e2e6`, both untagged. The model-improvement report with rungs 2 and 3
   (2026-10-21) went in as #27, merge commit `6069728`. The Kaggle kernel
   clones that branch.
   The training data itself (`training/synthetic/`, `training/data/`) is git-ignored and exists
   only on the laptop.

**Work**
5. **Week 3 is done** (D20 section): test, Tier B and Tier C judged, speed and VRAM measured,
   the README training section, `runs/INDEX.md`, the runs notebook, and the QLoRA demo cut with
   its reason, and the Week 4 model exported at Q4_K_M, Q5_K_M and Q8_0 with their SHA-256. The
   command that rebuilds dataset v2 and its SHA-256 values are in the D19 section; dataset v1 is
   rebuilt from commit `f43f77a` with the command of the D17 section. **The Week 4 plan is
   `docs/14-timeline-part5.md`** (2026-10-16): what D20 already covers, the cuts and their
   reasons, the frontier-model decision, and the adversarial scenarios.
6. **Every local run so far very likely used `presence_penalty 1.5` and `top_k 20`** (found
   2026-10-12, read from the files, not tested). They are in the Modelfile of the library
   `qwen3.5:4b`, a Modelfile parameter applies unless the request overrides it, and
   `local_client.py` sends temperature, `top_p`, the context size, the GPU layers and the token
   limit, nothing else. A penalty on repeated tokens may work against copying SEARCH lines
   exactly; whether it does is one dev experiment, as a new config. The D17 control copies
   both values, so it stays comparable with the baselines.
7. Headers copied into edits on files over 60 lines (D13, finding 3): judge a change to the
   context format on dev; it makes a new config.
8. The cascade costs more than the frontier alone on both tiers. Sending the full history on
   escalation (doc 04 §5) is the reason; whether a shorter escalation prompt keeps the
   resolve rate is worth one dev experiment in Week 4.
9. Week 4 (doc 12): pass@k, the bootstrap, CSV output, tokens and $ per resolved scenario, and
   results reported per tier.
10. Not done from the plan: `propose_fix` and `apply_edits` as MCP tools (`remediate` covers
   them), and a Tier B "before release" group.
11. **Left from 2026-10-21, yours to delete or keep**: `aeropatch-v3-step64` and
   `aeropatch-v3-step32` in Ollama (5.6 GB on `F:`, which has 7.8 GB free), the private Kaggle
   dataset `aeropatch-train-v3`, and `D:\aeropatch-v3` (the two GGUFs and the run's reports).
   The kernel's `ORDER` is `["own-v3"]` now; set it before the next session.
12. Done on 2026-10-16: `docs/architecture-interactive.html` was byte-identical to
   `docs/architecture.html` and nothing linked to it; it is removed.

**Cuts found by the over-engineering audit and left for after Week 4**, because they sit on the
code path the baselines measured: the finding `fingerprint` that nothing reads
(`tools/scanners.py`, `contracts.py`), the config keys `local_ctx_budget` and `localization`
that nothing reads (they are in every run header), `edits._common_indent` (it is
`os.path.commonprefix`) and `edits._Window`, the second `_validate_resume_header` call in
`bench.py`, and the two near-identical stream branches in `fallback_client.py`. About 30 lines.
