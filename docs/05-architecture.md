# 05 — Revised Architecture

Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. Principle: deterministic pipeline, model as a pure function

The original diagram draws an "Autonomous Orchestrator" that plans and routes. For a 4B model,
the more reliable design is the **Agentless pattern** (Xia et al., 2024). The pipeline is fixed
code: localize → build context → generate edit → gate → validate → repair. The model is called
at one point only, where it maps (context, feedback) to an edit proposal. It has no shell, no
tool calls and no file access.

Why this design:
- **Capability**: Small models are weak at long multi-step tool use (Qwen3.5-4B reports
  BFCL-V4 50.3). A fixed pipeline removes that failure mode.
- **Security**: The model can't run commands, so a prompt injection in repository text
  can only produce a bad edit. The scope gate and tests then catch it (doc 13).
- **Evaluability**: Every step is logged and replayable, which makes it possible to
  attribute failures to localization, generation, or validation.
- **Cost**: A fixed pipeline uses one generation per attempt, where an agent explores
  for many turns.

MCP still has a job, but on the *outside*. It exposes AeroPatch's tools (scan, localize, apply,
validate) to external agents such as Claude Code or Claude Desktop. That's the part worth
putting on a resume, and it doesn't slow down the inner loop (doc 06).

## 2. Revised flow

```text
finding (Opengrep/Bandit | CVE text | failing PoC) -> INTAKE (normalize to Task schema)
 -> LOCALIZE (finding -> file/function; tree-sitter scope + callers)
 -> GENERATE (router: local SLM -> frontier fallback) -> EditProposal (search/replace)
 -> GATE (scope, size, forbidden paths, syntax parse)  -- reject -> GENERATE (counts as attempt)
 -> VALIDATE in sandbox (apply, PoC test, regression tests, lint, re-scan)
 -> pass: REPORT (diff + evidence) -> human approves -> draft PR on your fork
 -> fail: REPAIR CONTEXT (trimmed traceback, failed assertions) -> GENERATE (max 3 total)
```

The evaluation harness (doc 11) calls the same pipeline once per scenario. Evaluation is a
first-class caller, not an afterthought.

## 3. Components

| Component | Responsibility | Key dependencies | Size estimate |
|---|---|---|---|
| Intake | Parse a finding/CVE/PoC into a `Task` | stdlib `json`, `dataclasses` | ~60 LOC |
| Localizer | Map the finding to file + function; extract scoped context | `tree-sitter`, `tree-sitter-python` | ~150 LOC |
| Scanners | Run Opengrep/Bandit, normalize findings | subprocess | ~80 LOC |
| Prompt builder | Assemble the prompt from Task + context + history | stdlib string templates | ~80 LOC |
| Router + clients | Choose the model, call it, record usage/refusals | `httpx` (Ollama), `anthropic` | ~150 LOC |
| Edit engine | Parse search/replace blocks, apply them, produce the unified diff | stdlib `difflib`, `git` | ~120 LOC |
| Gates | Deterministic checks on the proposed edit | stdlib `ast`, `pathlib` | ~80 LOC |
| Sandbox | Build image, run container, collect results | `docker` SDK | ~150 LOC |
| Test parser | Turn pytest output into a structured failure summary | pytest `--junitxml` + stdlib XML | ~60 LOC |
| Loop | The state machine tying everything together | stdlib | ~120 LOC |
| MCP server | Thin wrapper exposing the functions above | MCP Python SDK v2 / FastMCP | ~80 LOC |
| Benchmark | Run scenarios × configs, write JSONL logs | stdlib `concurrent.futures` | ~120 LOC |
| Metrics | Compute pass@k, resolve@iter, cost, latency | stdlib `math`, `statistics` | ~100 LOC |

That's about 1.3k lines of Python for the core, plus training scripts (~300 LOC). This is a
four-week project; no component needs a framework.

## 4. Data contracts (the only shared types)

| Type | Key fields |
|---|---|
| `Task` | `id`, `repo_path`, `commit`, `cwe`, `finding` (rule id, message, file, line), `description`, `allowed_paths`, `poc_tests`, `regression_tests` |
| `Context` | `files` (path → scoped snippet with line ranges), `imports`, `callers`, `token_count` |
| `EditProposal` | `edits` (list of `{path, search, replace}`), `rationale` (≤3 sentences), `model`, `usage` |
| `GateResult` | `ok`, `violations` (list of codes such as `FORBIDDEN_PATH`, `OUT_OF_SCOPE`, `TOO_LARGE`, `SYNTAX_ERROR`) |
| `SandboxResult` | `applied`, `poc_passed`, `regressions_passed`, `lint_ok`, `rescan_clean`, `failures` (trimmed), `duration_s`, `timed_out` |
| `Attempt` | `n`, `route`, `proposal`, `gate`, `sandbox`, `latency_s`, `cost_usd`, `refusal` |
| `RunResult` | `task_id`, `config`, `attempts`, `resolved`, `final_diff` |

Implement these as `dataclasses` with a `to_json()`. Pydantic is optional and only earns its
place if you want JSON-schema export for the MCP tool signatures, which the MCP SDK already derives.

## 5. State and logging

- One **append-only JSONL file per benchmark run**: one line per `Attempt`, plus a final
  `RunResult` line. No database.
- Every metric in doc 12 is computed from these logs. You can re-score without re-running models.
- Save the exact prompt and raw model output per attempt under `runs/<run_id>/<task_id>/`.
  That's needed for debugging and for building repair-turn training data (doc 09).
- Checkpointing comes for free. Resume a run by skipping task IDs that already have a
  `RunResult` line. This is why LangGraph's durable execution isn't needed here.

## 6. Revised repository structure (differences from the original plan)

| Original path | Revised | Reason |
|---|---|---|
| `docker/vllm.Dockerfile` | **drop**; use the official Ollama or llama.cpp server image in compose | No vLLM on 4 GB |
| `mcp_server/tools/` | `src/tools/` (real code) + `mcp_server/server.py` (thin wrapper) | One implementation, two front doors |
| `src/agent/graph.py` | `src/agent/loop.py` | Plain state machine, no LangGraph |
| — | `src/agent/edits.py`, `src/agent/gates.py` | Edit parsing/diffing and safety gates are core logic |
| `src/sandbox/manager.py` + `runner.py` | may merge into `src/sandbox/sandbox.py` | Two files for ~200 LOC is optional |
| `training/finetune_qlora.py` | `training/finetune.py` | Qwen3.5 uses LoRA 16-bit, not QLoRA |
| `evaluations/dataset/` | `evaluations/scenarios/<id>/` with `scenario.json` + repo | One folder per scenario |
| — | `runs/` (gitignored) | JSONL logs and raw outputs |
| — | `docs/` | These planning docs |

## 7. Runtime topology (docker-compose)

| Service | Image | GPU | Network |
|---|---|---|---|
| `llm` | Ollama or llama.cpp server (pinned version) | yes (WSL2 GPU) | internal only |
| `agent` | Python 3.12 + the `aeropatch` package | no | internal + egress to the frontier API |
| sandboxes | `aeropatch-sandbox:<scenario>` built on demand | no | **none** |

The agent starts sandbox containers through the Docker socket. Mounting the socket gives the
agent container root-equivalent control of Docker, so during development run the agent
**on WSL2 directly**, not in a container. Use compose only for the `llm` service and for the
one-command demo, and document this trade-off in the README.

## 8. Walkthrough: one scenario end to end (illustrative)

Scenario `A-089-01`: a Flask endpoint builds SQL with an f-string.
1. **Intake**: Opengrep rule `aeropatch.python.sqli-fstring` fires at `app/db.py:42`. It becomes
   a `Task` with CWE-89, `allowed_paths=["app/db.py"]`, and the PoC and regression test IDs.
2. **Localize**: tree-sitter finds `def find_user(name)` spanning lines 38–47, plus the imports
   and one caller in `app/routes.py`. The context is ~900 tokens.
3. **Generate (attempt 1, local)**: the SLM returns one SEARCH/REPLACE block switching to a
   `?` placeholder. It parses and applies. The gates pass: one file, 1 changed line, no risky imports.
4. **Validate**: the PoC `test_name_with_quote_is_data` still **fails**. The model changed the
   query but passed `name` as a string, not a tuple, so sqlite raised a binding error.
5. **Repair context**: the trimmed failure is 12 lines: the assertion, the `ProgrammingError`
   message, and the offending line.
6. **Generate (attempt 2, local)**: the fix now passes `(name,)`. It applies and gates pass.
7. **Validate**: PoC passes, all 6 regression tests pass, the re-scan is clean. Result: `RESOLVED`
   at attempt 2, cost $0, 31 s end-to-end.
8. **Report**: `runs/<id>/A-089-01/report.md` holds the diff and evidence. `aeropatch submit` is
   available, but nothing happens until you run it.

This trace is exactly what the README demo and the interview story should show. It's
concrete, it's checkable, and it shows the repair loop earning its keep.

## 9. Failure attribution (built in, because it's what reviewers ask about)

Each failed scenario gets exactly one primary cause, taken from the logs:
`LOCALIZATION_MISS` (edit outside the ground-truth function), `FORMAT_FAIL` (edit didn't parse
or apply), `GATE_REJECT`, `POC_STILL_FAILS`, `REGRESSION`, `TIMEOUT`, `REFUSAL`, `BUDGET_EXHAUSTED`.
A stacked bar of these causes per model is the most informative chart in the final report.

Next: [06-mcp-server-and-static-analysis.md](06-mcp-server-and-static-analysis.md)
