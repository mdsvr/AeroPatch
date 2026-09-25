# AeroPatch working notes

## Week 1 status (2026-09-25)

Built and tested in a Linux cloud container (Docker 29, no GPU, no Ollama).

| Plan item (doc 14) | State |
|---|---|
| D1 repo skeleton, config, `.env` handling | Done. `src/aeropatch/` package with an `aeropatch` CLI |
| D2 sandbox + 6 security tests | Done. All 6 pass, twice in a row (cleanup verified) |
| D3 scenario format, validator, first 5 scenarios | Done. CWE-89, 78, 22, 502, 918 |
| D4 context extraction, scanners, 5 more scenarios | Done. CWE-79, 601, 1333, 328, 209; 10-rule Opengrep ruleset |
| D5 edit engine, gates, prompt v1, local + fallback clients | Done. All 8 gates (the plan needed only 3 on D5) |
| D6 single-attempt baseline, 2 local models + frontier | **Needs the laptop** (Ollama + GPU; API key and spend) |
| D7 bake-off decision | **Needs D6 numbers** |

Checks that pass here:
- `aeropatch validate --all`: 10/10 scenarios pass all 4 checks (vulnerable baseline, reference
  fix, destructive fix caught, scanner finding detected).
- `aeropatch bench --config oracle`: 10/10 resolved through the real edit engine, gates and sandbox.
  A killed run resumes and skips finished tasks.
- `pytest`: 88 tests (edit engine, gates, context, paths, JUnit parsing, loop with a scripted
  model, Claude/Ollama clients mocked, scenario/rule checks, sandbox containment).

## Model check (against the current Claude model table, cached 2026-06-24)

- Doc 04's IDs and prices are current. `claude-opus-5` stays the default frontier model;
  `claude-sonnet-5` / `claude-haiku-4-5` remain your cost choice after D6.
- The Claude client uses adaptive thinking + `output_config.effort` (no `budget_tokens`, no
  `temperature`, both rejected on current models), streams, checks `stop_reason == "refusal"`
  before reading content, and turns on server-side fallbacks (`fallbacks: "default"`, beta
  `server-side-fallback-2026-07-01`; cyber refusals are rerouted by Anthropic).
- **Verify on the laptop:** the Ollama tags in `config.py` (`qwen3.5:4b`,
  `qwen2.5-coder:3b-instruct-q4_K_M`) are my best guess at the library names. Run
  `ollama list` after pulling and override with `--local-model <tag>` if they differ.

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
- **Opengrep wasn't reachable from the cloud container** (GitHub release downloads blocked). The
  rules were tested with Semgrep 1.178 (same rule syntax) as a stand-in: each rule fires on its
  scenario and is silent on the reference fix. Re-run `pytest tests/test_scenarios.py` on the
  laptop, where `.tools\opengrep.exe` exists.

## Next steps on the laptop (D6-D7)

1. `ollama pull` the Qwen3.5-4B and Qwen2.5-Coder-3B Q4 models; check the tags; record peak VRAM.
2. `uv run aeropatch build-base` then `uv run aeropatch validate --all` (proves Docker Desktop works).
3. `uv run pytest -q` (the sandbox tests must pass on Docker Desktop too).
4. D6 baselines: the three `bench` commands in the README, then `aeropatch report runs/*.jsonl`.
5. D7: apply the doc 03 §5 decision rule to the table; record it here.
