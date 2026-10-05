# AeroPatch

AeroPatch asks how much automated vulnerability remediation a 4B model on a 4 GB laptop GPU can
do. It fixes Python vulnerabilities locally, proves each fix in a network-less sandbox, retries
with test feedback, and escalates to a frontier model only when needed. Every claim is measured
on a contamination-controlled benchmark.

Status: **Week 2 complete, except the held-out synthetic tier, which waits for Week 3's teacher model**
(see [NOTES.md](NOTES.md) and the plan in [docs/](docs/00-overall-plan.md)). Baselines with up to
three attempts, two runs for the local model:

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
uv run aeropatch bench --config oracle   # harness self-check: must resolve every dev scenario (--split test, test_b for the others)
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
| `src/aeropatch/bench.py` | JSONL benchmark runner (resumable, `--jobs 2`) |
| `src/aeropatch/metrics.py` | the report: Wilson intervals, resolve@k, exact McNemar, speed and cost, per-CWE table, failure attribution |
| `src/aeropatch/mcp_server.py` | thin MCP wrapper over the tools (stdio) |
| `docker/` | sandbox base + per-scenario Dockerfiles, `run.sh`, hash-pinned harness tools |
| `rules/` | AeroPatch's own Opengrep ruleset (22 rules) |
| `evaluations/scenarios/` | 50 scenarios: 40 hand-built (Tier A, 16 CWEs) and 10 from real CVEs (Tier B, each with the upstream licence); `split.json` is frozen at 13 dev, 27 test and 10 real-CVE test |
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
