# 12 — Metrics Definitions, Statistics and Reporting (Week 4)

Maps to: `evaluations/metrics.py`. Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. The plan's "Pass@3" means two different things. Split it.

The plan uses "Pass@1 & Pass@3" for "single-turn accuracy vs multi-turn accuracy after
self-repair". Those are two different metrics, and reviewers who know the Codex paper will
point it out:

| Metric | Definition | Feedback? |
|---|---|---|
| **pass@k** | Probability that at least one of k **independent** samples resolves the scenario (Chen et al., 2021) | **No**. Samples don't see each other or any test output |
| **resolve@k** (with repair) | Fraction of scenarios resolved within the first k attempts of the repair loop | **Yes**. Attempt i sees the failures of attempts < i |

Report both, since they answer different questions. pass@k measures how much the model's
sampling diversity is worth. resolve@k measures how much the test-feedback loop is worth.
Comparing resolve@3 with pass@3 at the same generation budget shows whether feedback beats
plain resampling. That's a sharp result for the write-up either way.

## 2. pass@k: use the unbiased estimator

Draw n ≥ k samples per scenario (n = 5 here), count c resolved, then average over scenarios:

```python
from math import comb
def pass_at_k(n: int, c: int, k: int) -> float:
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)
```

Checks for the one small test file: `pass_at_k(5, 0, 1) == 0`, `pass_at_k(5, 5, 3) == 1`,
and `pass_at_k(5, 2, 1) == 0.4` (for k = 1 it equals c/n). Sample at temperature 0.6–0.8
for pass@k, and report greedy (temperature ≤ 0.2) results separately as "pass@1 (greedy)".

## 3. Full metric catalogue

**Effectiveness**
| Metric | Definition |
|---|---|
| Resolve rate | Resolved scenarios / total (definition in doc 08: applied ∧ gates ∧ PoC ∧ regressions) |
| resolve@1, @2, @3 | Cumulative resolved by attempt 1, 2, 3 |
| Repair gain | (resolve@3 − resolve@1) / (1 − resolve@1): share of first-attempt failures later fixed |
| Repair gain by iteration | Separate shares fixed at attempt 2 and at attempt 3 (the plan's "self-correction efficiency") |
| pass@1 (greedy), pass@k (sampled) | Section 2 |
| Apply rate | Attempts whose edit parsed and applied / all attempts |
| Gate rejection rate | By code (`FORBIDDEN_PATH`, `OUT_OF_SCOPE`, `RISKY_IMPORT`, ...) |
| PoC-fixed rate | PoC passes, ignoring regressions: shows "fixed but broke something" |
| Regression-free rate | Regressions pass, among applied edits |
| Scanner-clean rate | Original finding gone and no new findings (secondary signal) |

**Efficiency and cost**
| Metric | Definition |
|---|---|
| $ per resolved scenario | Total API $ (from `usage` logs × price table) / resolved count |
| Tokens per resolved scenario | Input, output and cache-read tokens, reported separately |
| Wall-clock per resolved scenario | End-to-end seconds, including sandbox time |
| Latency per attempt | p50 / p95 generation seconds; sandbox seconds separately |
| Throughput | Prompt-processing tok/s and decode tok/s (local) |
| Peak VRAM / RAM | Measured during runs (`nvidia-smi` sampling at 1 Hz) |

**Routing and behaviour**
| Metric | Definition |
|---|---|
| Escalation rate | Cascade scenarios that used the frontier / total |
| Local-resolved share | In cascade mode: resolved without any frontier call / resolved |
| Refusal rate | Refusals / frontier calls, by provider and category |
| Stuck rate | Runs stopped for repeating an identical edit |
| Failure attribution | Share of each primary failure cause (doc 05, section 8) |

## 4. Statistics: be honest about small samples

With ~35 test scenarios, uncertainty is large, and the write-up should show it.
- **Confidence intervals**: report 95% **Wilson** intervals for every rate. At a 50% rate with
  n = 35, the interval is about ±16 percentage points. Two models 10 points apart may not differ.
- **Paired comparisons**: models run on the same scenarios, so compare them with an **exact
  McNemar test** on the discordant pairs (A solved and B didn't, or the reverse), or with a
  paired bootstrap over scenarios (10k resamples) for the difference in resolve rate.
- **Wording of claims**: "comparable to frontier" is only defensible as "the difference was
  X pp, 95% CI [a, b]". If the CI is wide, say the benchmark is too small to separate them.
  That's a respectable finding; overclaiming isn't.
- **Seeds**: for greedy runs, run the fine-tuned model twice to show run-to-run variance.
  llama.cpp on GPU is not bit-exact deterministic.
- Report **per tier** (A hand-built / B real CVE / C synthetic) as well as overall. Real-CVE
  numbers are the ones that transfer to other settings.

**Sample-size intuition (95% Wilson interval half-widths, approximate)**

| Scenarios (n) | Observed rate 20% | 50% | 80% |
|---|---|---|---|
| 20 | ±17 pp | ±20 pp | ±17 pp |
| 35 | ±13 pp | ±16 pp | ±13 pp |
| 50 | ±11 pp | ±13 pp | ±11 pp |
| 100 | ±8 pp | ±10 pp | ±8 pp |

Going from 35 to 50 scenarios buys only ~2–3 pp of precision. Going from 50 to 100 buys
another ~3–4 pp at double the authoring cost. Paired tests (McNemar) are more sensitive than
comparing two independent intervals, because both models face the same scenarios. That's why
the delta table uses them. Given the timeline, 40–50 scenarios is the practical sweet spot.

## 5. Implementation notes (`metrics.py`, ~100 LOC)

- Input: one or more `runs/*.jsonl` files. Output: Markdown tables + a CSV per table.
- Pure functions over parsed records. There's no model or sandbox access, so re-scoring is instant.
- The price table (doc 04) lives in one dict with a `prices_as_of` date printed under every
  cost table.
- Tests: the pass@k checks above, a Wilson interval check against a known value, and a tiny
  synthetic JSONL with hand-computed resolve@k and repair gain.

## 6. Report layout (goes into the README)

1. **Headline table** (test split, oracle localization, repair on). One row per model/mode
   with resolve@1, resolve@3, pass@5, apply rate, $ per resolved, p50 latency, peak VRAM.
2. **Delta table**: untuned SLM → fine-tuned SLM → frontier, with CIs and McNemar p-values.
3. **Cost–accuracy chart**: x = $ per resolved (log scale), y = resolve rate. Local models
   sit at x = 0, so show them as a separate marker with wall-clock time in the label.
4. **Repair curve**: resolve@1/2/3 per model, which shows where feedback helps.
5. **Failure attribution**: stacked bars of primary failure cause per model.
6. **Ablations** (fine-tuned model): quantization Q4/Q5/Q8; grammar on/off; oracle vs tool
   localization; thinking mode on/off; repair feedback full vs trimmed.
7. **Per-CWE table**: which vulnerability classes the SLM handles and which need escalation.
   This is the most practically useful table for anyone reading the project.
8. **Limitations**: Python only, function-level fixes, small benchmark, tests as the oracle
   (a passing PoC doesn't prove a fix is complete), and the hardware used.

## 7. Example headline table (shape only; fill it from real runs)

| Model / mode | resolve@1 | resolve@3 | pass@5 | Apply | $/resolved | p50 s | VRAM GB |
|---|---|---|---|---|---|---|---|
| Qwen3.5-4B untuned, local | — | — | — | — | $0 | — | — |
| AeroPatch-4B (FT, Q4), local | — | — | — | — | $0 | — | — |
| AeroPatch-4B cascade → Claude | — | — | n/a | — | — | — | — |
| Claude (frontier reference) | — | — | — | — | — | — | n/a |

Every cell links to (or names) the run file it came from. No number goes into the README
or the resume that can't be traced to a JSONL line.

Next: [13-security-threat-model.md](13-security-threat-model.md)
