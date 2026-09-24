# 15 — Resume Claims, Deliverables and README Outline

Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. Problems with the original resume bullets

| Original claim | Problem | Fix |
|---|---|---|
| "autonomous vulnerability remediation agent" | "Autonomous" overstates it once there's a human approval gate, which there should be | "automated … with human-approved PRs" |
| "using the Model Context Protocol (MCP)" | Fine, if MCP is real and demoed; the inner loop doesn't need it | "exposed as an MCP server (spec 2026-07-28)" |
| "network-isolated Docker containers" | Good; the specific hardening makes it stronger | Name the controls briefly |
| "Fine-tuned a 3B … using QLoRA" | Primary model is 4B with LoRA (Qwen3.5 advice); a "35B-A3B" model must never be called 3B | State the exact model and method |
| "comparable Pass@1 … to frontier APIs" | Unmeasured; likely false on real CVEs; "comparable" needs a CI | Report the measured gap with its scope |
| "eliminating cloud token costs" | Only for scenarios solved locally; escalations still cost | "cut API spend per resolved scenario by X%" |
| "resolving over 75% of synthetic test failures within 2 iterations" | A target presented as a result; "synthetic" invites scrutiny | Use the measured repair gain (doc 12) |
| "lowered manual debugging overhead" | Unmeasurable as written | Drop it, or replace it with a measured proxy |

Rule: **every number on the resume comes from a run file.** Write the bullets on D28, not before.

## 2. Bullet templates (fill the brackets from measured results)

**Systems and architecture**
> Built AeroPatch, an automated Python vulnerability-remediation pipeline (localize → patch →
> verify → repair) with tree-sitter context extraction, Opengrep/Bandit intake, and hardened
> network-less Docker sandboxes (read-only root, dropped capabilities, resource limits),
> exposed to AI clients as an MCP server; human-approved draft PRs only.

**Model specialization and MLOps**
> Fine-tuned Qwen3.5-4B with LoRA (Unsloth/TRL, free T4) on [N] sandbox-verified remediation
> examples, raising resolve rate on a [M]-scenario vulnerability benchmark from [a]% to [b]%
> (frontier reference: [c]%), served locally as a 4-bit GGUF on a 4 GB laptop GPU at [t] tok/s.

**Cost-aware routing**
> Designed a local-first cascade with frontier fallback that resolved [x]% of scenarios
> without any API call and cut API spend per resolved vulnerability by [y]% vs frontier-only,
> at a [z] pp accuracy difference (95% CI [l, u]).

**Self-correction and evaluation**
> Built a test-feedback repair loop (PoC + regression tests, trimmed tracebacks) that fixed
> [g]% of first-attempt failures within 2 repairs; compared it against independent resampling
> (pass@k) and published a reproducible benchmark with CIs and failure attribution.

Pick the 3 strongest bullets once the results are in. If the fine-tuning delta is small, lead
with the evaluation and security design; those hold up regardless of the numbers.

## 3. Wording rules

- Say "Python", "function-level", and "[M]-scenario benchmark". Scope makes a claim believable.
- Say "vs frontier reference [model name, date]". Model names age fast, and dates help.
- Never "state-of-the-art", "production-grade", or "enterprise-ready" for a 4-week project.
- A null or negative result can be a bullet too: "showed that test-feedback repair
  outperformed resampling by [d] pp at equal budget" is a real finding.

## 4. Repository deliverables checklist

| Deliverable | Path | Done when |
|---|---|---|
| Core package | `src/` | `aeropatch remediate <scenario>` resolves a dev scenario |
| MCP server | `mcp_server/server.py` | Lists tools; demo call from an MCP client works |
| Sandbox image | `docker/sandbox.Dockerfile` | Security tests pass |
| Scenarios | `evaluations/scenarios/` | 40–50 validated; split frozen |
| Benchmark + metrics | `evaluations/` | Tables/charts regenerate from `runs/` with one command |
| Training | `training/` | Dataset build + training + export reproducible from the README |
| Compose | `docker-compose.yml` | `llm` service + demo come up with one command |
| Tests | `tests/` | Edit engine, gates, sandbox, MCP path validation, metrics |
| Docs | `docs/` + `README.md` | Results, reproduction steps, isolation statement, limitations |
| Model (optional) | HF Hub | Adapter + GGUF + model card with license and eval table |
| Demo | README GIF/video | 60 s: MCP client → scan → remediate → diff → draft PR on your demo repo |

## 5. README outline

1. One-paragraph summary + headline result table (doc 12, section 7).
2. Architecture diagram (doc 05) + the five-layer prompt-injection walkthrough (doc 13).
3. Quick start: WSL2 prerequisites → `uv sync` → `docker compose up llm` → one scenario.
4. How it works: localization, edit format, gates, sandbox, repair loop, routing.
5. Benchmark: tiers, CWE coverage, scenario anatomy, validation checks, dev/test split.
6. Results: headline, delta with CIs, cost–accuracy chart, repair curve, failure attribution,
   per-CWE table, ablations.
7. Fine-tuning: data sources and filters, contamination controls, hyperparameters, hardware.
8. Security: threat model summary, isolation statement, dual-use boundaries.
9. Limitations and future work (doc 14 part 2, "later" list).
10. Licenses: code license, model licenses (Qwen Research License note if used), data terms.

## 6. Repository hygiene (makes the public repo read as professional)

- **License**: MIT or Apache-2.0 for your code. Apache-2.0 includes a patent grant and
  matches most of the model licenses here.
- **CI** (GitHub Actions, free): lint (`ruff`), unit tests (edit engine, gates, metrics, MCP path
  validation), the Opengrep rule tests, and the scenario validator on 3 small scenarios.
  Skip GPU and model calls in CI.
- **Badges**: CI status and license only. More looks like decoration.
- **`SECURITY.md`**: how to report issues with AeroPatch itself; restate the dual-use boundaries.
- **Pinned everything**: `uv.lock`, the base image digest, the model server version, GGUF
  SHA-256s, and the prices-as-of date. Reproducibility is the claim; pinning backs it up.
- **Small commits with meaningful messages**: reviewers do skim history.
- **No secrets in history**: run a history scan before the repo goes public (doc 13).

## 7. The 60-second demo (storyboard)

1. (0–10 s) Terminal: a vulnerable Flask app; the Opengrep finding shown in one line.
2. (10–25 s) Claude Code (or another MCP client) is asked to "remediate this finding with
   AeroPatch"; the `remediate` tool call is visible.
3. (25–40 s) The attempt timeline: local attempt 1 fails the PoC, attempt 2 passes; the
   diff is shown; the PoC goes red → green; the regressions stay green.
4. (40–50 s) `aeropatch submit` asks for confirmation; a draft PR appears on your demo repo.
5. (50–60 s) Cut to the README results table and the cost–accuracy chart.
Record it at 1080p, with no audio needed, and burn in captions. A GIF version goes at the
top of the README.

## 8. Interview talking points (prepare these, they come up)

- **Why not let the model use tools?** Small-model tool use is unreliable, and a model
  without capabilities is much harder to weaponize through prompt injection (doc 05, doc 13).
- **Why search/replace instead of diffs?** Line-number arithmetic is where small models fail.
  The harness generates the diff (doc 08).
- **How do you know the fix is real?** PoC tests check behaviour and fail before the fix;
  regression tests stop destructive fixes; the validator proves both properties (doc 11).
- **Isn't pass@3 just resampling?** That's exactly why both are measured (doc 12).
- **How do you avoid contamination?** Hand-built scenarios, time and repo splits, 13-gram
  checks, and pre/post-release reporting (doc 09).
- **What would you do with more time or hardware?** gVisor/microVM sandbox, JS/Go,
  RL with a sandbox reward, model-driven localization (doc 14 part 2).

## 9. Project-page / LinkedIn summary (template, fill in from results)

> **AeroPatch**: can a 4B model on a 4 GB laptop GPU fix real security bugs?
> I built a pipeline that takes a scanner finding, extracts the vulnerable function with
> tree-sitter, asks a small fine-tuned model for a minimal fix, and proves it in a network-less
> Docker sandbox with exploit and regression tests, retrying with the test feedback when it
> fails. On [M] Python vulnerability scenarios, fine-tuning raised the local model from [a]% to
> [b]% resolved (frontier reference: [c]%), and a local-first cascade cut API spend per fix by
> [y]%. Prompt-injection attempts planted in the code got past the defences 0 times out of [k].
> Code, benchmark and write-up: [link].

Keep it under ~120 words, and lead with the question rather than the tech stack. Post it only
after the numbers exist.

Next: [16-sources.md](16-sources.md)
