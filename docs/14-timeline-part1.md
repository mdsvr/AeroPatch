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

| Day | Work | Output / acceptance check |
|---|---|---|
| D1 | Environment (doc 02): WSL2 update, `uv` + Python 3.12, Docker WSL integration, Ollama/llama.cpp; pull Qwen3.5-4B and Qwen2.5-Coder-3B Q4 GGUFs; repo skeleton, `.gitignore`, `.env` | `nvidia-smi` works in WSL; a model answers in < 10 s; peak VRAM recorded |
| D2 | Sandbox (doc 07): `sandbox.Dockerfile`, run-phase flags, read-only scratch mount + stdout results, JUnit parser, cleanup | The 6 sandbox security tests pass |
| D3 | Scenario format (doc 11) + scenario validator (4 checks) + first 5 Tier A scenarios (SQLi, command injection, path traversal, unsafe deserialization, SSRF) | Validator passes all 5 |
| D4 | Context extraction + scanners (doc 06): tree-sitter scopes, Opengrep rules for the first CWEs, Bandit; 5 more scenarios (10 total = dev split) | `get_context` tests pass; each scenario's finding is detected |
| D5 | Edit engine + minimal gates + prompt v1 + `local_client` + `fallback_client` (doc 08, doc 04) | Edit-engine unit tests pass; one scenario resolved end-to-end by the frontier model |
| D6 (O) | Single-attempt baseline: 10 dev scenarios × {Qwen3.5-4B, Qwen2.5-Coder-3B, frontier reference}, oracle localization | First results table (apply, resolve, latency, VRAM) |
| D7 | Buffer; model bake-off decision (doc 03); Week 1 notes | Chosen primary SLM, with the table that justifies it |

**Week 1 exit criteria**
- [ ] One command runs a scenario end-to-end: `aeropatch remediate <scenario>`.
- [ ] 10 validated dev scenarios exist, and the split is recorded.
- [ ] A baseline table exists for at least 2 local models and 1 frontier model.
- [ ] The sandbox security tests pass. Nothing the model sees contains a secret.

If you're behind at D7, cut the third local model and continue. Don't cut the sandbox tests
or the scenario validator.

## 3. Week 2: repair loop, gates, full scenario set, full baselines

| Day | Work | Output / acceptance check |
|---|---|---|
| D8 | Repair loop (doc 08 part 1): attempt plan, feedback builder, budgets, identical-edit detection, refusal-as-routing | A scenario that fails attempt 1 and succeeds on attempt 2, visible in the logs |
| D9 | Full gate set + 16 gate tests; router modes `local` / `frontier` / `cascade` (doc 04) | Gate tests pass; all three modes run on one scenario |
| D10 | Tier A scenarios 11–24 (remaining CWEs, easy + harder variants) | Validator passes; the "delete the body" check catches destructive fixes |
| D11 | Tier A to ~28; Tier B: pick 10–15 Python CVEs from PatchEval-Verified / CVE-Bench (Gatti), preferring post-March-2026; adapt them to the scenario format | 40–50 validated scenarios; `split.json` **frozen** |
| D12 | Benchmark runner (resume, run header, concurrency 2) + `metrics.py` v1 + thin MCP wrapper (doc 06) | `run_benchmark.py --config baseline-local --split test` works; MCP tool list visible in Inspector/Claude Code |
| D13 (O) | Full baselines with repair: untuned SLM `local`; frontier `frontier`; untuned SLM `cascade` | Baseline headline table with CIs (doc 12) |
| D14 | Buffer; baseline analysis (failure attribution, per-CWE); start the synthetic CWE-injection script (doc 09) so it can run unattended from D15 | Written notes: where the SLM fails and why. These guide the data mix |

**Week 2 exit criteria**
- [ ] The full loop with repair runs unattended over the whole set and can resume.
- [ ] 40–50 validated scenarios, with the dev/test split frozen and committed.
- [ ] A baseline headline table for untuned SLM (`local`, `cascade`) and frontier, with CIs.
- [ ] The failure-attribution chart for the untuned SLM exists; it guides the Week 3 data.
- [ ] The MCP server lists tools and serves one real call. It's a thin wrapper, as planned.

## 4. Detailed task lists for the riskiest days

**D2: sandbox (the day most likely to overrun)**
- [ ] `sandbox.Dockerfile`: pinned base digest, non-root user, harness tools pinned.
- [ ] `run(image, scratch_dir)` using `containers.run(detach=True, volumes={scratch: /src:ro})`
      → `wait(timeout)` → `logs()` split on result markers → `remove` in `finally` (doc 07 §5).
- [ ] `/harness/run.sh` in the image: copy `/src` → `/work`, apply, run tests, print results.
- [ ] Container env explicitly empty except `PYTHONDONTWRITEBYTECODE=1` and `HOME=/tmp`.
- [ ] JUnit XML parsing into pass/fail per test ID; failure classification labels.
- [ ] The 6 security tests from doc 07; run them twice to check cleanup.
- If you're stuck by mid-afternoon: get the plain run working first (network none + limits),
  then add `--read-only`, tmpfs and non-root one flag at a time. Each flag can break something.

**D3: scenario format and first scenarios**
- [ ] `scenario.json` schema written down (doc 11) and a loader that validates required fields.
- [ ] Validator implementing all 4 checks (vulnerable baseline, reference fix, destructive
      fix caught, finding detected).
- [ ] 5 scenarios, each: a ~50–150-line app, 1–2 PoC tests, 3–6 regression tests,
      reference fix, lockfile.
- Tip: write the reference fix and the "delete the body" check first. They tell you whether
  your regression tests are strong enough before you invest in the rest.

**D5: edit engine and clients**
- [ ] Parser for RATIONALE + SEARCH/REPLACE blocks; ignore text after the last block.
- [ ] Applier with exact → whitespace-tolerant → closest-lines feedback (doc 08 part 1).
- [ ] `git diff` capture; `git apply --check` inside the sandbox.
- [ ] `local_client.generate()` against Ollama/llama-server; `fallback_client.generate()` with
      the `anthropic` SDK, including refusal detection and usage capture.
- [ ] The minimal gates for day 1: `FORBIDDEN_PATH`, `OUT_OF_SCOPE`, `SYNTAX_ERROR`.

**D1: environment (do it in this order; each step unblocks the next)**
- [ ] `wsl --update`, `wsl --shutdown`, reopen Ubuntu; `nvidia-smi` shows the RTX 3050.
- [ ] Set a `.wslconfig` memory cap (~10 GB) so WSL and Docker can't starve Windows.
- [ ] Install `uv`, then `uv python install 3.12`; `uv init aeropatch` in `~/`.
- [ ] Docker Desktop: WSL2 engine on, Ubuntu integration on; `docker run --rm hello-world` works in Ubuntu.
- [ ] Ollama (or llama.cpp with CUDA) installed; pull the Qwen3.5-4B Q4_K_M and
      Qwen2.5-Coder-3B Q4_K_M GGUFs; one chat request each; note tok/s and peak VRAM.
- [ ] Repo skeleton from doc 05 (empty modules only); `.gitignore` covers `.env`, `runs/`, `*.gguf`.
- [ ] `.env` with the frontier API key; one tiny API call from Python succeeds.
- [ ] Copy `docs/` from `F:\AeroPatch\docs` into the repo; first commit.
- Accounts (Kaggle, Hugging Face, API console) are created by you; the code only reads keys from `.env`.

**D11: Tier B real CVEs (slowest scenario type)**
- [ ] Shortlist ~25 Python candidates from PatchEval-Verified and CVE-Bench (Gatti). Keep
      those with small dependency sets and fast test suites.
- [ ] Reuse the benchmark's own PoC tests where they exist; add 3+ regression tests if missing.
- [ ] Put each one through the same validator; expect ~50% to be dropped for flaky tests,
      heavy dependencies or build failures.
- [ ] Record `published_date` and the source URL for the pre/post-release split (doc 09).

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
