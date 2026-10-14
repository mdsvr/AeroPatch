# AeroPatch

AeroPatch asks how much automated vulnerability remediation a 4B model on a 4 GB laptop GPU can
do. It fixes Python vulnerabilities locally, proves each fix in a network-less sandbox, retries
with test feedback, and escalates to a frontier model only when needed. Every claim is measured
on a contamination-controlled benchmark.

Status: **end of Week 3 (2026-10-14). Fine-tuning did not help: the tuned model ties the untuned
one on dev (26 of 39 each) and scores below it on test (32 against 38 of 54), so Week 4 runs the
untuned model** (see [Training](#training-week-3), [NOTES.md](NOTES.md) and the plan in
[docs/](docs/00-overall-plan.md)).
Week 2's baselines on test, with up to three attempts, two runs for the local model:

| | 27 hand-built test scenarios | 10 real-CVE scenarios |
|---|---|---|
| Qwen3.5-4B, untuned, local, $0 | 17/27 and 18/27 | 5/10 and 5/10 |
| Claude Opus 5 | 27/27 | 10/10 |
| Cascade (local, local, then Opus) | 27/27, 16 fixed locally | 10/10, 4 fixed locally |

The hand-built scenarios were written by Claude models, so they are easy ground for Opus. The
real-CVE ones use other projects' vulnerable code and their own upstream fixes, published between
2026-03-31 and 2026-10-02; with ten of them the intervals are wide (5/10 is 24–76%).
Outputs are **candidate fixes that need human review**.

## Pipeline

```text
finding (Opengrep/Bandit) -> Task -> scoped context (tree-sitter)
  -> model (local SLM | Claude fallback) -> RATIONALE + SEARCH/REPLACE blocks
  -> edit engine (scratch copy, git diff) -> safety gates (8 deterministic rules)
  -> hardened sandbox: PoC tests + regression tests + lint + re-scan
  -> RESOLVED, or repair feedback -> next attempt
```

The model is a pure function from context to edits. It has no tools and no shell. Tests are
baked into the sandbox image and exposed through root-owned, read-only paths. Candidate code still
runs in pytest's process, so this is not a defense against code deliberately tampering with the
interpreter or test runner; use the sandbox for your own scenarios and pinned public repos.

## Quick start

```powershell
uv sync
uv run aeropatch build-base              # sandbox base image (once)
uv run aeropatch validate --all          # 4 checks per scenario; builds scenario images
uv run aeropatch bench --config oracle   # harness self-check: must resolve every dev scenario (--split test, test_b, test_c for the others)
uv run pytest -q                         # unit + sandbox containment tests
```

`uv run` does not load `.env` automatically. To pass `ANTHROPIC_API_KEY`, for example, use
`uv run --env-file .env aeropatch bench --config baseline-frontier --split dev`. `OLLAMA_HOST`
in that file overrides the local model endpoint.

Local model (Ollama running, model pulled):

```powershell
uv run aeropatch remediate A-089-01 --config baseline-qwen3.5-4b
uv run aeropatch bench --config baseline-qwen3.5-4b --split dev
uv run aeropatch bench --config baseline-qwen2.5-coder-3b --split dev
uv run aeropatch bench --config baseline-frontier --split dev   # needs ANTHROPIC_API_KEY; costs money
uv run aeropatch bench --config baseline-claude-code --split dev   # same model via `claude -p` on a subscription
uv run aeropatch bench --config repair-local --split test   # 3 attempts with test feedback
uv run aeropatch report runs/<a>.jsonl runs/<b>.jsonl       # CIs, resolve@k, McNemar, per CWE
```

`bench` resumes a killed run when given the same `--run-id`. `--jobs 2` runs two scenarios at
once (two sandboxes; local generation stays one at a time).

Other commands: `aeropatch scan <repo>`, `aeropatch context <repo> <path> <line>`,
`aeropatch prune`. Nothing in the CLI commits, pushes or opens pull requests.

MCP: `uv run aeropatch mcp` serves `scan`, `get_context`, `validate` and `remediate` over stdio
(for example `claude mcp add aeropatch -- uv run aeropatch mcp`, run from this directory). It only
reads repositories under `evaluations/scenarios/`.

## Training (Week 3)

LoRA on Qwen3.5-4B (r 16, alpha 16, 16-bit base, not QLoRA) with Unsloth on one Kaggle T4:
2 epochs, 128 steps, sequences up to 4,096 tokens, learning rate 2e-4, batch 1 with accumulation
8, seed 3407. About 97 minutes, 13.1 GB peak. The data is git-ignored and stays on the laptop;
[training/stats-v2.md](training/stats-v2.md) has the counts.

- **Dataset v2, 541 examples** (511 train, 30 validation): 275 fixes from GitHub advisories,
  105 synthetic fixes made by a local teacher (`qwen3.5:9b`) and checked in the sandbox, 53
  repair turns from the untuned model's own failed attempts, and 108 general bug fixes
  (SWE-Gym, SWE-smith). Filters for size, context, the safety gates, duplicates, secrets and
  leakage: no benchmark project, no advisory after the cutoff, no copied benchmark code.
- **The comparison is against an untuned control**: the same base exported through the same
  merge and GGUF path with no adapter, so the difference is the adapter alone.
- **Dev, 3 runs each, resolved of 39**: control 26; dataset v1 20 at step 64 and 20 at step 128;
  dataset v2 **26** at step 64 and 23 at step 128. v1 taught the model to copy the finding's
  message as its plan and to edit inside function bodies; v2 rewrote each target's first line as
  a plan and made a small function one whole block. Dev chose those two changes, so it ties
  and proves nothing more; test and Tier B decide.
- **Test, 2 runs each, resolved of 54**: control **38**, v2 step 64 **32**. By the rule set
  before the runs (4 or more below is a loss) the fine-tune loses, though the gap alone is not
  significant (paired exact McNemar p = 0.15). Its fixes break regression tests more often.
  Week 4 runs the untuned model. Real CVEs (Tier B, of 20): control 7, v2 3. Held-out
  synthetic scenarios (Tier C, of 10): 9 each.
- **Serving**: the Q4_K_M GGUF with [training/Modelfile](training/Modelfile)
  (`ollama create <name> -f Modelfile` beside the file). On the RTX 3050 the tuned model and the
  control are both 100% on the GPU, 3,043 MiB at peak, and decode at about 46.5 tokens a second.
- **Reproduce**: `prepare_dataset.py build` (command and SHA-256 in [NOTES.md](NOTES.md), D19),
  then the `full-v2` run of [training/kaggle/kernel.py](training/kaggle/kernel.py), which clones
  this branch and runs [training/finetune.py](training/finetune.py).
- **Not done**: the laptop QLoRA demo on Qwen2.5-Coder-1.5B (cut-list item 6). The GPU went to
  benchmark runs, and the laptop has no local training stack.

## Layout

| Path | What |
|---|---|
| `src/aeropatch/agent/` | `loop.py` state machine, `edits.py`, `gates.py`, `prompts.py`, `router.py` |
| `src/aeropatch/models/` | Ollama client, Claude API client, Claude Code (`claude -p`) client, oracle (reference-fix replay) |
| `src/aeropatch/sandbox/` | hardened Docker runner, JUnit parser |
| `src/aeropatch/tools/` | tree-sitter context, scanners, scratch workspaces, path validation |
| `src/aeropatch/scenario.py` | scenario loader and the 4-check validator |
| `src/aeropatch/bench.py` | JSONL benchmark runner (resumable, `--jobs 2`) |
| `src/aeropatch/metrics.py` | the report: Wilson intervals, resolve@k, exact McNemar, speed and cost, per-CWE table, failure attribution |
| `src/aeropatch/mcp_server.py` | thin MCP wrapper over the tools (stdio) |
| `docker/` | sandbox base + per-scenario Dockerfiles, `run.sh`, hash-pinned harness tools |
| `rules/` | AeroPatch's own Opengrep ruleset (22 rules) |
| `evaluations/scenarios/` | 55 scenarios: 40 hand-built (Tier A, 16 CWEs), 10 from real CVEs (Tier B, each with the upstream licence) and 5 held out from the synthetic training data (Tier C); `split.json` is frozen at 13 dev, 27 test, 10 real-CVE test and 5 synthetic test |
| `training/` | Week 3 data. `inject_cwe.py`: synthetic, sandbox-verified training examples from a local teacher model. `prepare_dataset.py`: real fix pairs from GitHub advisories as SEARCH/REPLACE targets, and the dataset build. `finetune.py`: LoRA and GGUF export; `kaggle/`: the kernel that runs it; `Modelfile`: serving in Ollama |
| `runs/` | run logs (gitignored), and [runs/INDEX.md](runs/INDEX.md), which lists every run |

## Sandbox isolation (honest statement)

Hardened runc containers: `--network none`, read-only root, size-capped tmpfs, `cap-drop ALL`,
`no-new-privileges`, pids/memory/CPU limits, non-root user, explicit minimal environment, base
image pinned by digest, harness tools pinned by hash. Containers share the Docker VM's kernel,
so a kernel exploit could escape. This suits your own scenarios and public repos at pinned
commits, not arbitrary untrusted repositories. See [docs/07-sandbox.md](docs/07-sandbox.md).

## Data handling

Prompts are scanned for secret patterns before they leave the process. API keys stay in the
orchestrator and never reach a sandbox (tested). Only scenario code is sent to the frontier API.
