# AeroPatch

AeroPatch asks how much automated vulnerability remediation a 4B model on a 4 GB laptop GPU can
do. It fixes Python vulnerabilities locally, proves each fix in a network-less sandbox, retries
with test feedback, and escalates to a frontier model only when needed. Every claim is measured
on a contamination-controlled benchmark.

Status: **Week 1** (see [NOTES.md](NOTES.md) and the plan in [docs/](docs/00-overall-plan.md)).
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
baked into the sandbox image, so a patch can never change the tests it is judged by.

## Quick start

```powershell
uv sync
uv run aeropatch build-base              # sandbox base image (once)
uv run aeropatch validate --all          # 4 checks per scenario; builds scenario images
uv run aeropatch bench --config oracle   # harness self-check: must resolve 10/10
uv run pytest -q                         # unit + sandbox containment tests
```

Local model (Ollama running, model pulled):

```powershell
uv run aeropatch remediate A-089-01 --config baseline-qwen3.5-4b
uv run aeropatch bench --config baseline-qwen3.5-4b --split dev
uv run aeropatch bench --config baseline-qwen2.5-coder-3b --split dev
uv run aeropatch bench --config baseline-frontier --split dev   # needs ANTHROPIC_API_KEY; costs money
uv run aeropatch report runs/*.jsonl
```

Other commands: `aeropatch scan <repo>`, `aeropatch context <repo> <path> <line>`,
`aeropatch prune`. Nothing in the CLI commits, pushes or opens pull requests.

## Layout

| Path | What |
|---|---|
| `src/aeropatch/agent/` | `loop.py` state machine, `edits.py`, `gates.py`, `prompts.py`, `router.py` |
| `src/aeropatch/models/` | Ollama client, Claude client, oracle (reference-fix replay) |
| `src/aeropatch/sandbox/` | hardened Docker runner, JUnit parser |
| `src/aeropatch/tools/` | tree-sitter context, scanners, scratch workspaces, path validation |
| `src/aeropatch/scenario.py` | scenario loader and the 4-check validator |
| `src/aeropatch/bench.py` | JSONL benchmark runner (resumable) and baseline table |
| `docker/` | sandbox base + per-scenario Dockerfiles, `run.sh`, hash-pinned harness tools |
| `rules/` | AeroPatch's own Opengrep ruleset (10 rules) |
| `evaluations/scenarios/` | 10 Tier A dev scenarios, `split.json` |
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
