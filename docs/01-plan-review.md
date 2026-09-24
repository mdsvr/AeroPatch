# 01 — Review of the Original AeroPatch Plan

Research date: 2026-09-24. Figures from third-party sources are marked "(reported)".
Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. Verdict in one paragraph

The core idea holds up. Localize → generate a patch → test it in a sandbox → feed failures back →
open a PR is the same loop behind Agentless, SWE-agent, and the DARPA AIxCC finalists
(Team Atlanta's Atlantis, Trail of Bits' Buttercup). Five parts of the plan need to change:
(1) your machine can't run the Week 3 training as written; (2) the fallback model, Gemini 2.0 Flash,
was retired on 2026-06-01; (3) the evaluation is built last, when it has to come first;
(4) the model is asked to emit raw unified diffs, the edit format small models get wrong most often;
(5) the resume numbers are written as outcomes before anything has been measured.
The plan works once these are fixed. If they aren't, Week 3 and Week 4 will fall apart.

## 2. Section-by-section scorecard

| Plan section | Status | Main issue | Fix (doc) |
|---|---|---|---|
| Architecture diagram | Keep, with edits | No evaluation box, no scope gate, no human gate before PR | 05 |
| Week 1 MCP server | Keep, shrink | MCP spec went stateless (2026-07-28); tools should be plain functions first | 06 |
| Week 1 tree-sitter | Keep | Fine; add Opengrep/Bandit, and note the Semgrep rules-license issue | 06 |
| Week 1 Docker sandbox | Keep, harden | `network_mode=none` alone is not enough; deps must be baked in first | 07 |
| Week 1 JSON schemas | Change | "Unified diff" output schema → search/replace edit schema | 08 |
| Week 2 LangGraph/asyncio | Simplify | A 6-state loop doesn't need a framework; plain Python is enough | 08 |
| Week 2 repair loop (3x) | Keep | Also cap by token budget; forbid test-file edits | 08 |
| Week 2 safety gates | Keep, extend | Add prompt-injection handling and a no-edit-tests rule | 08, 13 |
| Week 3 data curation | Change | SWE-bench is bug-fix data, not vulnerability data; contamination risk | 09 |
| Week 3 QLoRA 3B | Change | 4 GB VRAM; QLoRA not recommended for Qwen3.5; license of Qwen2.5-Coder-3B | 03, 10 |
| Week 3 AWQ + vLLM | Change | vLLM is not realistic on a 4 GB laptop GPU; use GGUF + llama.cpp/Ollama | 10 |
| Week 4 benchmark | Move earlier | Without a Week 1 baseline you can't measure what fine-tuning changed | 11 |
| Week 4 metrics | Fix definitions | "Pass@3" is used for two different things | 12 |
| docker-compose | Keep | Fine, but GPU passthrough on Windows needs the WSL2 backend | 02 |
| Resume impact | Rewrite | Numbers are asserted before measurement | 15 |

## 3. Things that are outdated as of Sep 2026

- **Gemini 2.0 Flash**: Google's deprecations page lists shutdown on 2026-06-01. It names
  `gemini-3.6-flash` as the replacement. Newer Flash models exist (3.7 Flash, and 3.8 Flash released
  2026-09-02). Details: [04-models-frontier-and-routing.md](04-models-frontier-and-routing.md).
- **Qwen 2.5-Coder-3B**: Released in 2024. It's still a capable code model, but it ships under the
  **Qwen Research License (non-commercial)**. The 0.5B/1.5B/7B/14B/32B sizes are Apache-2.0; the 3B is not.
  Newer Apache-2.0 small models exist: Qwen3.5-4B/2B (March 2026) and Gemma 4 E2B/E4B (April 2026).
- **Llama 3.2-3B**: Comes under the Llama community license, and it's older and weaker at code than
  the options above. Drop it, or keep it only as a historical baseline.
- **MCP**: The 2026-07-28 spec is stateless. It removed the initialize handshake and session IDs,
  and it deprecated Sampling, Roots, and Logging. Tutorials written for the 2024–2025 spec are stale.
- **SWE-bench Verified**: OpenAI stopped reporting it in 2026, citing flawed tests and contamination.
  Don't use it as a headline metric, and don't take training data from it.
- **Semgrep**: The engine is LGPL-2.1, but the Semgrep-maintained rules now carry a restrictive
  rules license. Opengrep, an LGPL-2.1 fork (v1.27.1 reported Aug 2026), restores taint analysis
  in the free edition.

## 4. Things that are unrealistic as written

1. **"QLoRA a 3B model" on this laptop.** The GPU is an RTX 3050 Laptop with 4 GB VRAM, and the
   machine has 16 GB RAM. Unsloth's own 4 GB guide used a 1B model, and that PR is still unmerged.
   Unsloth says not to QLoRA Qwen3.5 at all, and 16-bit LoRA on Qwen3.5-4B needs ~10 GB.
   So training moves to a free cloud T4 (Kaggle/Colab). See [02](02-hardware-and-environment.md).
2. **"Serve with vLLM."** vLLM targets Linux datacenter GPUs, and on 4 GB it would leave almost no room
   for KV cache. llama.cpp or Ollama with a Q4 GGUF fits and works on Windows/WSL2.
3. **"Comparable Pass@1 to frontier APIs."** On PatchEval-Verified, frontier models reportedly score
   80%+ pass@1 (leaderboard, Jul 2026). A 4B model won't match that on real CVEs. It can close the gap
   on narrow, well-localized, function-level fixes, and that's the claim worth testing.
4. **"75% of failures resolved within 2 iterations."** The self-repair literature
   ("Is Self-Repair a Silver Bullet?", Olausson et al., ICLR 2024) finds modest gains that depend on
   feedback quality. Treat 75% as a target, not a result.
5. **"Eliminating cloud token costs."** That's only true for tasks the local model solves. Every
   escalation still costs tokens. Report cost per *resolved* scenario, not per request.

## 5. Things that are missing

- **Evaluation-first sequencing.** Build the harness and baselines in Weeks 1–2 (doc 11).
- **Two kinds of test per scenario**: a PoC test that fails before the fix and passes after, plus
  regression tests that pass both before and after. Otherwise the model can "fix" SQL injection by
  deleting the query.
- **No-edit-tests rule**: the agent must never modify tests, CI, lockfiles, or configs. A patch
  that edits the test to pass is the classic benchmark cheat.
- **Prompt-injection handling**: repository text (comments, READMEs, issue bodies) is untrusted
  input that goes straight into the model's context (doc 13).
- **Refusal handling**: frontier models run cyber safety classifiers. A vulnerability agent will
  sometimes get `stop_reason: "refusal"`. That should be a routing event, not a crash (doc 04).
- **Contamination control**: split training and evaluation data by time and by repository (doc 09).
- **Human gate before any PR**: open draft PRs to your own fork only, and never auto-merge.
- **Environment setup**: Python isn't installed on the host yet (only the Microsoft Store alias).

## 6. What the plan gets right (keep these)

- Deterministic validation in a sandbox is the right source of truth. LLM-as-judge is not.
- Capping the repair loop at 3 is sensible. Most gains come in the first 1–2 repairs.
- Local-first with frontier fallback is the right cost structure, and it gives the project an
  interesting research question: how much of the frontier's success can a 4B model keep?
- tree-sitter for scoping context is the right tool; it keeps prompts small for a small model.
- Small, specialized fine-tuning on a narrow output format is where small models gain the most.

## 7. Top risks (full list in doc 14)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Local training does not fit / crashes | High | High | Train on Kaggle/Colab T4; local only for inference |
| Too few verified training examples | Medium | High | Synthetic CWE injection + verified distillation (doc 09) |
| Fine-tuned model shows no gain | Medium | Medium | A baseline exists by Week 1, so a null result is still reportable |
| Sandbox deps need network | High | Medium | Two-phase build: install at build time, `--network none` at run |
| Frontier refusals on exploit-like text | Medium | Low | Neutral prompts, refusal fallback, log refusal rate |
| Benchmark contamination | Medium | High | Your own scenarios + post-March-2026 CVEs |
| Time overrun | High | Medium | Cut MCP to a thin wrapper; skip LangGraph; skip AWQ |

## 8. Prior art, and where AeroPatch fits

| System | Who | What it does | What AeroPatch can learn from it |
|---|---|---|---|
| Atlantis (1st, AIxCC 2025) | Team Atlanta (Georgia Tech, Samsung, KAIST, POSTECH) | Fuzzing + symbolic execution + LLM agents; finds and patches | Validation by execution matters more than the model |
| Buttercup (2nd, AIxCC 2025) | Trail of Bits, open source | Finds bugs and deploys patches cost-efficiently (28 found, 19 patched, reported) | Cost-awareness is a design goal, not an afterthought |
| AIxCC finals overall | DARPA | 7 teams patched 43 of 54 synthetic vulnerabilities (reported) | Synthetic planted vulns are an accepted benchmark style |
| CodeMender (preview, Jul 2026) | Google DeepMind | Gemini + program analysis, fuzzing, differential testing; human review before upstreaming | Human review stays in the loop even at Google scale |
| Aardvark | OpenAI | Security researcher agent integrated with Codex; proposes patches | Patch plus evidence plus one-click human review |
| Copilot Autofix / Agentic Autofix | GitHub | Code-scanning alerts → suggested fixes; agentic preview Jul 2026 | Intake from static-analysis alerts is the mainstream workflow |
| Agentless | Academic (UIUC) | Fixed localize → repair → validate pipeline, no agent loop | The right pattern for a small model (doc 05) |

**AeroPatch's niche**: none of the systems above asks how much of this a 4B model on a
laptop GPU can do, or when it must escalate. The framing that sets AeroPatch apart is
"local-first remediation with measured escalation and cost". That's a research question,
and it's honest about capability.
It also avoids competing head-on with Google, OpenAI and GitHub on raw accuracy, a contest
a 4-week solo project can't win.

What to borrow directly:
- From AIxCC systems: treat the PoC as the oracle, and patch only once a PoC reproduces the bug.
- From CodeMender and Aardvark: show evidence (tests before/after) next to every patch.
- From Agentless: keep the pipeline fixed and let the model do one narrow job.
- From Copilot Autofix: take scanner alerts as intake, since developers already live there.

## 9. How to read the rest of the docs

Read the docs in number order. Each file is about 150 lines and covers one category.
[00-overall-plan.md](00-overall-plan.md) has the revised plan on one page, plus the decision table.
