# 14 — Revised 4-Week Timeline, Part 2: Weeks 3–4, Risk Register, Cut List

Part 1: [14-timeline-part1.md](14-timeline-part1.md). Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. Week 3: data, training, export, serving

| Day | Work | Output / acceptance check |
|---|---|---|
| D15 (O) | Synthetic CWE injection runs unattended (teacher + sandbox verification); MoreFixes Python filter + commit→search/replace conversion (doc 09) | Verified pairs accumulating; conversion spot check: 20/20 byte-exact |
| D16 (O) | SWE-smith / SWE-Gym conversion; student attempts on synthetic tasks → repair-turn examples; leakage checks | `stats.md` with counts per filter/CWE/source; zero repo overlap with eval |
| D17 | Freeze dataset v1; Kaggle **pilot** (50 steps); laptop QLoRA pilot for Qwen2.5-Coder-1.5B | Pilot log: VRAM, tok/s, ETA; sample outputs parse |
| D18 | Full LoRA run for Qwen3.5-4B on Kaggle (1–3 h); dev-scenario eval of each checkpoint | Loss curves; dev table per checkpoint |
| D19 | Optional second run (r=32 or 3 epochs) if dev results are flat; merge + GGUF export (Q4/Q5/Q8) on Kaggle | GGUF files downloaded; SHA-256 recorded |
| D20 | Local serving (Ollama Modelfile or llama-server); smoke test; full dev run with repair | Fine-tuned model resolves dev scenarios end-to-end on the laptop |
| D21 | Buffer; pick the final checkpoint and quant; write the training section of the README | Decision recorded with the dev table |

**Week 3 exit criteria**
- [ ] Dataset v1 frozen, with `stats.md` and leakage report.
- [ ] Fine-tuned adapter + GGUF (3 quant levels) exist, and the chosen one is served locally.
- [ ] Dev results for the fine-tuned model sit next to the untuned baseline.
- [ ] The laptop QLoRA demo either worked (VRAM log) or its failure is documented.

**If fine-tuning shows no gain on dev**: that's still a result. Check train/inference parity
first (same prompt builder? same chat template? thinking disabled in both?), then data quality
(does the SEARCH text match exactly?), then the learning rate. Report an honest null result
over a tuned-on-test positive one.

## 2. Week 4: final runs, ablations, packaging, write-up

| Day | Work | Output / acceptance check |
|---|---|---|
| D22 (O) | Final **test** runs: untuned SLM, fine-tuned SLM (local + cascade), frontier, all with repair on/off | Headline + delta tables (doc 12) |
| D23 (O) | pass@5 sampling for fine-tuned SLM + frontier; a second greedy seed for the fine-tuned SLM | pass@k table; run-to-run variance |
| D24 (O) | Ablations on the fine-tuned model: quant Q4/Q5/Q8, grammar on/off, oracle vs tool localization, thinking on/off | Ablation tables |
| D25 | `metrics.py` final: CIs, McNemar, cost–accuracy chart, repair curve, failure attribution, per-CWE | All charts/tables generated from run files |
| D26 | `docker-compose.yml` (llm service + demo), README (architecture, reproduction commands, results, isolation statement, limitations), MCP demo recording, draft PRs on your **own demo repos** | Fresh-clone reproduction of one scenario in ≤ 3 commands |
| D27 | Security checklist (doc 13), secret/history scan, model card, optional HF upload | Checklist all ticked |
| D28 | Buffer; resume bullets filled from measured numbers (doc 15); short blog-style write-up | Final commit tagged `v1.0` |

**Week 4 exit criteria**
- [ ] Every number in the README traces to a `runs/*.jsonl` file named next to it.
- [ ] Fresh clone to one resolved scenario takes ≤ 3 commands (documented, tested once).
- [ ] The security checklist is complete; the repo is safe to make public.
- [ ] Resume bullets contain only measured numbers.

## 3. Weekly review questions (30 minutes every Sunday)

1. Did the week's exit criteria pass? If not, which cut-list item (section 6) pays for the gap?
2. What does the latest run table say that you didn't expect? Write it in `NOTES.md`.
3. Is anything being built that isn't on the critical path? Stop it, or put it on the later list.
4. Is every number produced so far traceable to a run file? If not, fix it now, not in Week 4.
5. Frontier spend so far vs budget (below). Is a cheaper tier needed for sweeps? That's your call.

## 4. Budget summary (time and money)

| Item | Estimate | Notes |
|---|---|---|
| Focused hours | ~160 (28 days × ~6 h) | Buffers on D7, D14, D21, D28 |
| Unattended overnight runs | ~8 nights | D6, D13, D15, D16, D22–D24 (+1 spare) |
| Kaggle GPU hours | ~6–10 of the 30/week quota | Pilot + 1–2 full runs + export |
| Frontier API spend | ~$20–60 total | Baselines, cascade runs, pass@5 on one frontier model; depends on the tier chosen |
| Teacher inference for data | ~$0–20 | Free tiers or a cheap hosted open-weights model |
| Disk | ~40–60 GB | Scenario images, GGUFs, runs |

If spend runs over, first cut pass@5 for the frontier model, then run the frontier baseline
greedily only once. Don't skip the frontier baseline entirely; the delta story needs it.

## 5. Risk register

| # | Risk | Likelihood | Impact | Early signal | Mitigation / fallback |
|---|---|---|---|---|---|
| R1 | Local training doesn't fit on 4 GB | High | Low (planned for) | Pilot OOM | Cloud T4 is the primary plan; the laptop demo is optional |
| R2 | Kaggle/Colab quota or session limits | Medium | Medium | Queueing, 12 h cutoffs | Checkpoint every 200 steps; Colab backup; ~$5–10 of paid GPU time as a last resort |
| R3 | Qwen3.5 tooling issues (loader, GGUF, llama.cpp build) | Medium | Medium | Export or load errors | Fall back to Qwen2.5-Coder-3B QLoRA (note the license) |
| R4 | Too few verified training examples | Medium | High | < 800 verified by D16 | Lean on MoreFixes pairs + SWE-smith; lower the target to 1.5k |
| R5 | Scenario authoring slower than planned | High | High | < 25 scenarios by D11 | Accept 30 scenarios; drop Tier C; fewer CWEs, keep two variants each |
| R6 | Deps need network at run time | High | Medium | pip errors in the sandbox | Two-phase build (doc 07); vendor wheels |
| R7 | Frontier refusals distort baselines | Medium | Low | Refusal rate > 10% | Neutral prompts; server-side fallback; report the rate |
| R8 | Benchmark contamination | Medium | High | Pre/post-release gap on Tier B | Tier A is your own; report tiers separately |
| R9 | Fine-tuned model not better | Medium | Medium | Flat dev results | Parity checks (section 1); report the honest null result |
| R10 | Laptop thermal throttling on long runs | Medium | Low | tok/s drops over time | Record tok/s per attempt; run overnight on AC power; cooling pad |
| R11 | Cost overrun on frontier sweeps | Low | Medium | $ tracker > budget | Per-scenario $ cap; pass@k only on 2 models; cheaper tier is your choice |
| R12 | Scope creep (LangGraph, multi-language, RL) | High | High | Work outside the critical path | Cut list below; "later" list in the README |

## 6. Cut list (what to drop, in order, if behind schedule)

1. Gemma 4 baseline (keep two local models at most).
2. Tier C held-out synthetic scenarios.
3. Thinking-mode ablation, then the grammar ablation.
4. The second training run (keep the first if dev improved at all).
5. pass@5 sampling (keep greedy pass@1 and resolve@k).
6. Laptop QLoRA demo.
7. HF Hub upload and model card polish.
8. The MCP demo video (keep the MCP server itself; it's small).

**Never cut**: sandbox hardening and its tests, the gates and their tests, the scenario
validator, baselines before training, the dev/test split, and traceable numbers. These make
the project credible; everything else is decoration.

## 7. Milestone demos (show someone at the end of each week)

A 5-minute demo to a friend, mentor or rubber duck at the end of each week catches drift early:
- **End of W1**: "Here's a vulnerable app. One command runs the pipeline; here's the diff,
  here's the PoC test going red → green in the sandbox, and here's the first baseline table."
- **End of W2**: "Here's the repair loop fixing something on attempt 2, the gates rejecting
  a test edit, 40+ validated scenarios, and the untuned-vs-frontier baseline with CIs."
- **End of W3**: "Here's the fine-tuned model running on my laptop. It resolves these dev
  scenarios the untuned model couldn't, and here's the training data pipeline and leakage report."
- **End of W4**: "Here's the README results section, the cost–accuracy chart, the
  adversarial scenarios at 0% injection success, and a draft PR on my demo repo."

If you can't give a week's demo honestly, that week's exit criteria weren't met. Use the
cut list rather than pushing the demo back.

## 8. Definition of done (whole project)

- [ ] A fresh clone reproduces one resolved scenario in ≤ 3 commands on the documented setup.
- [ ] The benchmark (40–50 scenarios + 4–6 adversarial) runs end-to-end and resumes.
- [ ] Headline, delta, repair-curve, cost–accuracy, failure-attribution and per-CWE results
      are all generated from committed run files (or published run archives).
- [ ] The fine-tuned model is served locally at Q4 on the 4 GB GPU, with measured VRAM and tok/s.
- [ ] Security checklist (doc 13) complete; isolation statement and limitations in the README.
- [ ] Resume bullets written from measured numbers only (doc 15).

## 9. "Later" list (put it in the README as future work)

- gVisor or a microVM sandbox on a Linux host.
- JavaScript/Go support (tree-sitter grammars; PatchEval's other languages).
- Model-driven localization over large repos.
- RL with a sandbox reward (GRPO).
- LangGraph port, if durable multi-step human-in-the-loop workflows become necessary.
- Dependency-upgrade remediation (pip-audit findings).

Next: [15-resume-and-deliverables.md](15-resume-and-deliverables.md)
