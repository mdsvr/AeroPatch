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

## Next (Week 2, doc 14)

1. D8 repair loop: `repair-local` and `cascade` configs exist; run them on the dev split.
2. Check A-502's regression test (above) before adding scenarios 11–24.
3. SEARCH mismatches are the most common local failure: the repair turn's closest-lines feedback
   is the first thing to measure.
4. Section 15 of the architecture page (`docs/architecture-interactive.html`, and the local `docs/architecture.html` copy) still shows D6/D7 as pending.
