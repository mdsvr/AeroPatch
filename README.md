# AeroPatch

AeroPatch asks how much automated vulnerability remediation a 4B model on a 4 GB laptop GPU can
do. It fixes Python vulnerabilities locally, proves each fix in a network-less sandbox, retries
with test feedback, and escalates to a frontier model only when needed. Every claim is measured
on a contamination-controlled benchmark.

Status: **Week 2 complete** (see [NOTES.md](NOTES.md) and the plan in [docs/](docs/00-overall-plan.md)).
Baselines with up to three attempts on the frozen test split (27 scenarios, 2026-10-03): untuned
Qwen3.5-4B resolves 17/27 and 18/27 in two runs (95% CIs 44–78% and 48–81%) at $0, Claude Opus 5 resolves 27/27
(88–100%), and the cascade resolves 27/27 with 16 of them fixed locally. All 40 scenarios are
hand-built and were written by Claude models, so the Opus number is an upper bound on easy ground.
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
uv run aeropatch bench --config oracle   # harness self-check: must resolve every scenario
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

## Layout

| Path | What |
|---|---|
| `src/aeropatch/agent/` | `loop.py` state machine, `edits.py`, `gates.py`, `prompts.py`, `router.py` |
| `src/aeropatch/models/` | Ollama client, Claude API client, Claude Code (`claude -p`) client, oracle (reference-fix replay) |
| `src/aeropatch/sandbox/` | hardened Docker runner, JUnit parser |
| `src/aeropatch/tools/` | tree-sitter context, scanners, scratch workspaces, path validation |
| `src/aeropatch/scenario.py` | scenario loader and the 4-check validator |
| `src/aeropatch/bench.py` | JSONL benchmark runner (resumable, `--jobs 2`) and baseline table |
| `src/aeropatch/metrics.py` | Wilson intervals, resolve@k, exact McNemar, per-CWE table, failure attribution |
| `src/aeropatch/mcp_server.py` | thin MCP wrapper over the tools (stdio) |
| `docker/` | sandbox base + per-scenario Dockerfiles, `run.sh`, hash-pinned harness tools |
| `rules/` | AeroPatch's own Opengrep ruleset (22 rules) |
| `evaluations/scenarios/` | 40 Tier A scenarios over 16 CWEs; `split.json` is frozen at 13 dev, 27 test |
| `training/` | `inject_cwe.py`: synthetic, sandbox-verified training examples (Week 3 data) |
| `runs/` | run logs (gitignored) |

## Sandbox isolation (honest statement)

Hardened runc containers: `--network none`, read-only root, size-capped tmpfs, `cap-drop ALL`,
`no-new-privileges`, pids/memory/CPU limits, non-root user, explicit minimal environment, base
image pinned by digest, harness tools pinned by hash. Containers share the Docker VM's kernel,
so a kernel exploit could escape. This suits your own scenarios and public repos at pinned
commits, not arbitrary untrusted repositories. See [docs/07-sandbox.md](docs/07-sandbox.md).

## Data handling

Prompts are scanned for secret patterns before they leave the process. API keys stay in the
orchestrator and never reach a sandbox (tested). Only scenario code is sent to the frontier API.
