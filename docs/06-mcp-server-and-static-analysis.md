# 06 — MCP Server, AST Context Extraction and Static Analysis (Week 1)

Maps to: `mcp_server/server.py`, `src/tools/`. Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. MCP in September 2026: what changed

The current spec is **2026-07-28**, the largest revision since MCP launched (reported). The
changes that matter for this project:

| Change | Consequence for AeroPatch |
|---|---|
| Protocol is **stateless**: no `initialize` handshake, no `Mcp-Session-Id`; version and capabilities travel in `_meta` on each request | Every tool call must be self-contained: pass `repo`, `task_id`, etc. explicitly |
| Multi Round-Trip Requests (`resultType: "input_required"`) replace server-initiated requests | Not needed; tools don't ask the user questions mid-call |
| `tools/list` results are cacheable (`ttlMs`, `cacheScope`) | Keep the tool list static so clients can cache it |
| Tasks moved to an extension (`io.modelcontextprotocol/tasks`) | Optional for the long `remediate` tool; start without it |
| **Sampling, Roots, Logging deprecated** (12-month support window); legacy HTTP+SSE transport deprecated | Don't build on them; pass repo paths as arguments, not roots |
| Authorization hardening (issuer validation, CIMD instead of DCR) | Irrelevant for local stdio; relevant only if you ever host it |

SDKs: the official **MCP Python SDK v2** is the stable line and supports 2026-07-28 plus earlier
revisions. **FastMCP** (2.x–4.x) reportedly supports both the stateless and the 2025-11-25
revisions. Pick one, pin its version, and use **stdio** transport. It's all that Claude Code,
Claude Desktop and similar local clients need.

## 2. Role of the MCP server (thin wrapper)

- Real logic lives in `src/tools/*.py` as plain functions. The agent loop calls them directly,
  in-process, with no protocol overhead.
- `mcp_server/server.py` just registers those functions as MCP tools (~80 LOC). Each function
  therefore has one implementation and two callers: the loop, and external agents via MCP.
- Demo value: "Claude Code, scan this repo and remediate finding X using AeroPatch" is a
  compelling 60-second video for the README.

## 3. Tool surface (keep it small)

| Tool | Input | Output | Annotations |
|---|---|---|---|
| `scan` | `repo`, optional `rules` | list of normalized findings | read-only |
| `get_context` | `repo`, `path`, `line` | scoped context (function, class header, imports, callers) | read-only |
| `propose_fix` | `task` | `EditProposal` (calls the router) | read-only on repo; open-world (may call an API) |
| `apply_edits` | `repo`, `edits` | unified diff + gate result (in a scratch worktree) | writes scratch only |
| `validate` | `task_id`, `diff` | `SandboxResult` | runs the sandbox; no host writes |
| `remediate` | `task` | `RunResult` (full loop) | combination of the above |

Deliberately **not exposed**: `commit`, `push`, `open_pr`. These run as human-invoked CLI
commands after you review the diff (doc 13). The plan listed `commit` as an MCP tool; keeping
write access to real branches out of reach of any model is the safer default.

Use MCP tool annotations (`readOnlyHint`, `destructiveHint`, `openWorldHint`) truthfully, so
clients can apply their own approval policies.

## 4. Input validation at the MCP boundary (security, don't skip)

- `repo` must resolve (via `Path.resolve()`) to a path under an allowlisted root, e.g.
  `~/aeropatch/evaluations/scenarios/` or a configured workspace. Reject anything else.
- `path` must resolve inside `repo` (no `..` traversal, no symlinks pointing out).
- `edits[].path` goes through the same check, plus the scope gate (doc 08).
- Cap input sizes: search/replace text ≤ 20 KB per edit and ≤ 10 edits.
- Tool errors return structured error results. Don't let raw tracebacks with host paths go
  back to the client.

## 5. AST context extraction (tree-sitter + stdlib `ast`)

Use each parser for what it does best:

| Need | Tool | Why |
|---|---|---|
| Find the enclosing function/class for a line; list imports and callers | **tree-sitter** (`tree-sitter` + `tree-sitter-python`) | Error-tolerant: it parses files that are mid-edit or broken, and extends to JS/Go later (PatchEval languages) |
| Syntax check on the patched file (gate) | stdlib **`ast.parse`** | Strict and exact, with zero dependencies; failing means the edit broke the syntax |
| Exact function spans for Python | stdlib `ast` (`lineno`/`end_lineno`) | Useful cross-check for tree-sitter spans in tests |

Context assembly for a finding at `path:line`, sized for a 4B model (target ≤ 3k tokens):
1. The **full enclosing function**, or the enclosing method plus the class header.
2. **Signatures only** of the class's other methods, so the model knows what exists.
3. Module-level **imports** and constants referenced in the function.
4. Up to **2 call sites** (±3 lines each), found by name match. This is approximate, and the
   limitation should be documented; there's no type-resolved call graph in v1.
5. The finding text (rule ID, CWE, message) and, on repair turns, the trimmed test failure.

Show code **without line-number prefixes**. The model has to copy `SEARCH` text verbatim, and
line-number prefixes get copied into it. Pass line ranges as a separate header line instead.

## 6. Static analysis scanners

| Scanner | License | Strength | Use in AeroPatch |
|---|---|---|---|
| **Opengrep** (Semgrep fork, v1.27.1 reported Aug 2026) | LGPL-2.1 | Pattern + taint rules, inter-procedural taint in the free edition, SARIF/JSON output | Primary finding source; re-scan after the patch |
| **Bandit** | Apache-2.0 | Zero-config Python security checks, fast | Second opinion; quick CWE coverage |
| Semgrep CE | Engine LGPL-2.1; **registry rules under the Semgrep Rules License** | Largest rule registry | Fine to run locally; **don't copy registry rules into a public repo** |
| pip-audit | Apache-2.0 | Vulnerable dependency versions | Out of scope for v1 (dependency bumps aren't code patches) |

Rules strategy: write **your own small Opengrep ruleset** (10–15 rules) for the CWEs in your
scenarios (doc 11). It ships with the repo under your license, avoids the rules-license
question, and shows real understanding in interviews.

Scanners play two roles:
- **Intake**: a finding becomes a `Task` (rule → CWE, file, line, message).
- **Validation signal**: after the patch, the original finding should be gone and no new
  high-severity findings should appear. This is a secondary signal only. Scanner-clean doesn't
  mean secure, and the PoC test (doc 07) is the ground truth.

## 7. Normalized finding format (what every scanner is converted into)

| Field | Example | Notes |
|---|---|---|
| `tool` | `opengrep` / `bandit` | Source scanner |
| `rule_id` | `aeropatch.python.sqli-fstring` / `B608` | Stable ID used for per-rule stats |
| `cwe` | `CWE-89` | From rule metadata; required for AeroPatch rules |
| `severity` | `high` | Normalized to low/medium/high |
| `path`, `line`, `end_line` | `app/db.py`, 42, 42 | Repo-relative only |
| `message` | "User input in f-string SQL" | Trimmed to 200 chars before it reaches a prompt |
| `fingerprint` | hash(rule_id, path, normalized snippet) | Lets the re-scan check that *this* finding is gone, even if lines moved |

When both scanners report the same line, merge the two findings and keep both rule IDs.

## 8. Writing your own Opengrep rules (guidance)

- One rule per CWE pattern, with metadata `cwe`, `severity`, and a short `message` written as
  a fact ("user input reaches SQL string formatting"), not an instruction to the model.
- Prefer **taint mode** (source → sink) for injection classes: sources are request params,
  CLI args and file contents; sinks are `cursor.execute`, `subprocess.*`, `open`,
  `yaml.load`, `pickle.loads`, `requests.get`.
- Add a `sanitizer` for the correct fix (e.g. parameterized `execute(query, params)`), so the
  re-scan comes back clean after a proper fix.
- Every rule gets two fixtures in `tests/rules/`: vulnerable code (must match) and fixed code
  (must not). Run them with Opengrep's rule-test mode in CI.
- Keep the ruleset small (10–15 rules). Its job is intake for your scenarios, not coverage
  of all Python security issues.

## 9. Git operations (inside `src/tools/git_ops.py`)

- For each attempt, create a scratch **git worktree** at the scenario's pinned commit (or a
  fresh copy into the sandbox), so a failed attempt never dirties the source checkout.
- Compute the diff with `git diff --no-color` after the edit engine applies edits. The model
  never writes the diff (doc 08).
- Check that the diff applies with `git apply --check` inside the sandbox before running tests.
- Commits happen only on the human-invoked `aeropatch submit` path (doc 13).

## 10. Week 1 deliverables for this component

- [ ] `scan(repo)` returns normalized findings from Opengrep and Bandit for 3 sample repos.
- [ ] `get_context(repo, path, line)` returns ≤ 3k-token context; unit tests on 5 fixtures,
      including a nested function, a decorated method, and a file with a syntax error.
- [ ] MCP server lists the tools; one successful call from MCP Inspector or Claude Code.
- [ ] Path-validation tests: traversal, symlink escape, and non-allowlisted repo are all rejected.

Next: [07-sandbox.md](07-sandbox.md)
