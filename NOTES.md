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

## Next

**Decisions that are yours** (the first three were taken as defaults on 2026-10-03):
1. **Tier B (real CVEs): not built.** The set is 40 Tier A scenarios, the low end of the plan's
   40–50, and Opus's 27/27 shows that test cannot separate frontier models. Tier B puts real
   vulnerable project code and pinned dependencies in the repo. If it is added, it goes under
   its own key in `split.json`.
2. **Frontier reference: still `claude-opus-5`.** Moving to `claude-opus-5-5` means re-running
   `repair-claude-code` and `cascade-claude-code` on dev and test, about 30 minutes.
3. **Data mix from dev only** (D14), against doc 14 §5's wording.
4. **Teacher model for `inject_cwe.py`** (doc 09 §4): open weights, stronger than the student,
   hosted. Nothing can run unattended from D15 until this is chosen.
5. **Push and PR.** This work is committed locally and not pushed.

**Work**
6. Week 3, D15: run `inject_cwe.py` with the chosen teacher; write `prepare_dataset.py` (doc 09)
   with the dedupe and leakage checks.
7. Headers copied into edits on files over 60 lines (D13, finding 3): judge a change to the
   context format on dev; it makes a new config.
8. Week 4 (doc 12): pass@k, the bootstrap, CSV output, tokens and $ per resolved scenario.
9. Not done from the plan: a model run killed and resumed (only the oracle was); the MCP call
   from Claude Code or Inspector; `propose_fix` and `apply_edits` as MCP tools.
10. The architecture pages (`docs/architecture*.html`) still carry a "What's blocking D6?"
    prompt, and `architecture.html` and `architecture-interactive.html` are the same file twice.

**Cuts found by the over-engineering audit and left for after Week 4**, because they sit on the
code path the baselines measured: the finding `fingerprint` that nothing reads
(`tools/scanners.py`, `contracts.py`), the config keys `local_ctx_budget` and `localization`
that nothing reads (they are in every run header), `edits._common_indent` (it is
`os.path.commonprefix`) and `edits._Window`, the second `_validate_resume_header` call in
`bench.py`, and the two near-identical stream branches in `fallback_client.py`. About 30 lines.
