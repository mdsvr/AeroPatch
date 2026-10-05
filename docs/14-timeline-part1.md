# 14 — Revised 4-Week Timeline, Part 1: Weeks 1–2 (Foundations and Baselines)

Continues in [14-timeline-part2.md](14-timeline-part2.md) (Weeks 3–4, risk register, cut list).
Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. What changed from the original schedule

| Original | Revised | Why |
|---|---|---|
| W1: MCP + sandbox + schemas | W1: environment, sandbox, **first 10 scenarios**, single-shot pipeline, **baselines** | You can't measure fine-tuning without a baseline |
| W2: orchestration + repair loop | W2: repair loop, gates, router, **40–50 scenarios**, thin MCP wrapper, full baselines | MCP is a wrapper; the scenarios are the long pole |
| W3: data + QLoRA + AWQ/vLLM | W3: data (reusing W2 logs), LoRA on Kaggle, GGUF, llama.cpp/Ollama | Hardware and tooling reality (docs 02, 03, 10) |
| W4: build benchmark + docs | W4: **run** the benchmark, ablations, reporting, packaging | The benchmark already exists by W4 |

Critical path: **environment → sandbox → scenarios → baseline → dataset → training → final eval**.
Anything off this path (MCP wrapper, Gemma baseline, ablations) gets cut first if you fall behind.

Assumed effort is ~6 focused hours/day. Days marked (O) include an overnight unattended run.

## 2. Week 1: environment, sandbox, first scenarios, first numbers

**Status: complete (2026-09-29).** Evidence and the D6 table are in `NOTES.md`; the D7 decision
is in doc 03 §5.

| Day | Work | Output / acceptance check |
|---|---|---|
| D1 | Environment (doc 02), done Windows-native: `uv` + Python 3.12, Docker Desktop, Ollama for Windows; pull Qwen3.5-4B and Qwen2.5-Coder-3B Q4; repo skeleton, `.gitignore`, `.env` | A model answers in < 10 s; peak VRAM recorded |
| D2 | Sandbox (doc 07): `sandbox-base.Dockerfile` + `scenario.Dockerfile`, run-phase flags, read-only scratch mount + stdout results, JUnit parser, cleanup | The 6 sandbox security tests pass |
| D3 | Scenario format (doc 11) + scenario validator (4 checks) + first 5 Tier A scenarios (SQLi, command injection, path traversal, unsafe deserialization, SSRF) | Validator passes all 5 |
| D4 | Context extraction + scanners (doc 06): tree-sitter scopes, Opengrep rules for the first CWEs, Bandit; 5 more scenarios (10 total = dev split) | `get_context` tests pass; each scenario's finding is detected |
| D5 | Edit engine + minimal gates + prompt v1 + `local_client` + `fallback_client` (doc 08, doc 04) | Edit-engine unit tests pass; one scenario resolved end-to-end by the frontier model |
| D6 (O) | Single-attempt baseline: 10 dev scenarios × {Qwen3.5-4B, Qwen2.5-Coder-3B, frontier reference (Claude Opus 5 via Claude Code)}, oracle localization | First results table (apply, resolve, latency, VRAM) |
| D7 | Buffer; model bake-off decision (doc 03); Week 1 notes | Chosen primary SLM, with the table that justifies it |

**Week 1 exit criteria**
- [x] One command runs a scenario end-to-end: `aeropatch remediate <scenario>`.
- [x] 10 validated dev scenarios exist, and the split is recorded.
- [x] A baseline table exists for at least 2 local models and 1 frontier model.
- [x] The sandbox security tests pass. Nothing the model sees contains a secret.

If you're behind at D7, cut the third local model and continue. Don't cut the sandbox tests
or the scenario validator.

## 3. Week 2: repair loop, gates, full scenario set, full baselines

**Status (2026-10-01): D8 and D9 done and measured on the dev split** (`NOTES.md`, Week 2).
D10 started: 3 larger scenarios added to dev (13 dev, 0 test; 13 of 40–50). **2026-10-03:** the
dev runs were repeated on the merged commit, and 20 Tier A test scenarios were added (13 dev, 20
test; 33 of 40–50; split not frozen). Tier B and D12 onwards not started.

**Status (2026-10-03, end of day): D11–D14 done, with two things left out on purpose.** The set is
40 Tier A scenarios (13 dev, 27 test), frozen; **Tier B and Tier C were not built**. D12's three
pieces exist. The D13 baselines ran on the frozen test split in an afternoon, not overnight, and
a re-check of them found and fixed a cascade bug (`NOTES.md`, D13). D14's analysis is written,
and `training/inject_cwe.py` exists but has only had a smoke test: its teacher model is not
chosen yet.

**Status (2026-10-05): Tier B built and measured; Week 2 is closed except for Tier C.** Ten
real-CVE scenarios were added under `test_b` (50 scenarios in total) and all three repair
configs were run on them. A model run was killed and resumed, and Claude Code called the MCP
server. Tier C waits for the teacher model of Week 3 (`NOTES.md`, 2026-10-05).

| Day | Work | Output / acceptance check |
|---|---|---|
| D8 | Repair loop (doc 08 part 1): attempt plan, feedback builder, budgets, identical-edit detection, refusal-as-routing | A scenario that fails attempt 1 and succeeds on attempt 2, visible in the logs |
| D9 | Full gate set + 16 gate tests; router modes `local` / `frontier` / `cascade` (doc 04) | Gate tests pass; all three modes run on one scenario |
| D10 | Tier A scenarios 11–24 (remaining CWEs, easy + harder variants) | Validator passes; the "delete the body" check catches destructive fixes |
| D11 | Tier A to ~28; Tier B: pick 10–15 Python CVEs from PatchEval-Verified / CVE-Bench (Gatti), preferring post-March-2026; adapt them to the scenario format | 40–50 validated scenarios; `split.json` **frozen** |
| D12 | Benchmark runner: resume and run header already exist (`aeropatch bench`); add concurrency 2 + `metrics.py` v1 + thin MCP wrapper (doc 06) | `aeropatch bench --config repair-local --split test` works; MCP tool list visible in Inspector/Claude Code |
| D13 (O) | Full baselines with repair: untuned SLM `local`; frontier `frontier`; untuned SLM `cascade` | Baseline headline table with CIs (doc 12) |
| D14 | Buffer; baseline analysis (failure attribution, per-CWE); start the synthetic CWE-injection script (doc 09) so it can run unattended from D15 | Written notes: where the SLM fails and why. These guide the data mix |

**Week 2 exit criteria**
- [x] The full loop with repair runs unattended over the whole set and can resume. Evidence in
      two pieces: the three repair configs each ran unattended over the 27 test scenarios (and
      over the 13 dev ones that morning, as separate commands), and resume was shown with the
      `oracle` config at `--jobs 2`, killed after 8 results and resumed to 27/27. On 2026-10-05 a
      `repair-local` run on dev was hard-killed after 5 results and resumed to 13 distinct results.
- [x] 40–50 validated scenarios, with the dev/test split frozen and committed. 50: 40 Tier A and
      10 Tier B.
- [x] A baseline headline table for untuned SLM (`local`, `cascade`) and frontier, with CIs
      (`NOTES.md`, D13; `aeropatch report`).
- [x] The failure-attribution chart for the untuned SLM exists; it guides the Week 3 data. It is
      the text chart in `aeropatch report`. The data mix uses the dev runs only (`NOTES.md`, D14).
- [x] The MCP server lists tools and serves one real call. It's a thin wrapper, as planned. Called
      from the SDK's stdio client and, on 2026-10-05, from headless Claude Code with a throwaway
      MCP config.

## 4. Detailed task lists for the riskiest days

**D2: sandbox (the day most likely to overrun)**
- [x] `sandbox-base.Dockerfile`: pinned base digest, non-root user, harness tools pinned.
- [x] `run(image, scratch_dir)` using `containers.run(detach=True, volumes={scratch: /src:ro})`
      → `wait(timeout)` → `logs()` split on result markers → `remove` in `finally` (doc 07 §5).
- [x] `/harness/run.sh` in the image: copy `/src` → `/work` (patch already applied on the host),
      run tests, print results.
- [x] Container env explicitly empty except `PYTHONDONTWRITEBYTECODE=1` and `HOME=/tmp`.
- [x] JUnit XML parsing into pass/fail per test ID; failure classification labels.
- [x] The 6 security tests from doc 07; run them twice to check cleanup.
- If you're stuck by mid-afternoon: get the plain run working first (network none + limits),
  then add `--read-only`, tmpfs and non-root one flag at a time. Each flag can break something.

**D3: scenario format and first scenarios**
- [x] `scenario.json` schema written down (doc 11) and a loader that validates required fields.
- [x] Validator implementing all 4 checks (vulnerable baseline, reference fix, destructive
      fix caught, finding detected).
- [ ] 5 scenarios, each: a ~50–150-line app, 1–2 PoC tests, 3–6 regression tests,
      reference fix, lockfile. **Not met as specified:** 10 scenarios exist and pass the
      validator, but the apps are only 6–19 lines (stdlib-only), so contexts are tiny and flatter
      every model. Make the Week 2 scenarios closer to the plan.
- Tip: write the reference fix and the "delete the body" check first. They tell you whether
  your regression tests are strong enough before you invest in the rest.

**D5: edit engine and clients**
- [x] Parser for RATIONALE + SEARCH/REPLACE blocks; ignore text after the last block.
- [x] Applier with exact → whitespace-tolerant → closest-lines feedback (doc 08 part 1).
- [x] `git diff` capture; the patch is applied on the host to the scratch copy (doc 06 §9).
- [x] `local_client.generate()` against Ollama/llama-server; `fallback_client.generate()` with
      the `anthropic` SDK, including refusal detection and usage capture.
- [x] The minimal gates for day 1: `FORBIDDEN_PATH`, `OUT_OF_SCOPE`, `SYNTAX_ERROR` (all 8 built).

**D1: environment (as done, Windows-native; doc 02 §5)**
- [x] `uv` + `uv python install 3.12`; project in `F:\AeroPatch` (the WSL route was blocked).
- [x] Docker Desktop with Linux containers; `docker run --rm hello-world` works.
- [x] Ollama for Windows; pulled `qwen3.5:4b` and `qwen2.5-coder:3b-instruct-q4_K_M`; tok/s and
      peak VRAM recorded (48 / 75 tok/s; 3,787 / 2,440 MiB).
- [x] Repo skeleton (doc 05); `.gitignore` covers `.env`, `runs/`, `.tools/`, `*.gguf`.
- [ ] `.env` with the frontier API key: not set up. Claude Code on a subscription is used instead
      (doc 04 §3).
- [x] `docs/` in the repo; first commit.
- Accounts (Kaggle, Hugging Face, API console) are created by you; the code only reads keys from `.env`.

**D11: Tier B real CVEs (slowest scenario type)**
- [x] Shortlist candidates. **Done from the GitHub advisory database instead of PatchEval-Verified
      and CVE-Bench:** 154 advisories since 2026-03-15 fit the shape (one small single-file fix
      with a test, permissive licence, pure Python); 16 fix commits were read.
- [x] PoC tests come from the tests each upstream fix added; regression tests come from the
      project's own suite (4 to 17 per scenario).
- [x] Same validator. 10 of the 16 were built and all 10 pass; the other 6 were dropped before
      building (timing-only tests, fixes spread over several functions, heavy fixtures, or the
      50-scenario ceiling).
- [x] `published_date`, the advisory URL, the CVE id and both commit hashes are in `scenario.json`.
      All ten were published after Qwen3.5's release, so there is no "before release" group.

## 5. How Week 2 feeds Week 3 (don't skip this link)

- Week 2 runs produce thousands of logged **student attempts** with sandbox verdicts. Failed
  attempts on **non-eval** synthetic tasks become repair-turn training examples (doc 09).
  Never reuse eval-scenario attempts for training.
- The per-CWE failure table decides the synthetic mix. Oversample the CWEs where the untuned
  model fails.
- The failure attribution also shows what fine-tuning can realistically fix. `FORMAT_FAIL` and
  `GATE_REJECT` are very trainable. `POC_STILL_FAILS` on hard CWEs is less so.

## 6. Daily hygiene (15 minutes/day, saves days later)

- Commit at the end of each day with a message naming the day's acceptance check.
- Log every benchmark run in `runs/INDEX.md`: run ID, config, git commit, and a one-line takeaway.
- Keep a `NOTES.md` of surprises, which become the README's "lessons learned" section.
- When a check fails at day's end, write the failing command in `NOTES.md` so the next day
  starts with it.

Continue: [14-timeline-part2.md](14-timeline-part2.md)
