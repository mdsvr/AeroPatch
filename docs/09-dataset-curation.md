# 09 — Training Data Curation (Week 3, days 1–3)

Maps to: `training/prepare_dataset.py`. Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. What the plan gets wrong about data

- **SWE-bench is bug-fix data, not security data**, and SWE-bench Verified is contaminated and
  has flawed tests. OpenAI stopped reporting it in 2026. Don't train on it, and don't use it
  as the headline eval.
- **CVE commit datasets have no tests.** They give before/after code but can't verify that a
  model's alternative fix is correct. They're good for supervised pairs and useless as
  execution-verified data.
- **Raw unified diffs as targets** would train the format doc 08 rejects. Targets must be
  search/replace blocks.
- Missing entirely: **repair-turn examples**. The self-correction loop is the thing being
  sold, so train it directly.

## 2. Candidate sources

| Source | What it is | Language | Tests? | Use |
|---|---|---|---|---|
| **MoreFixes** (v4, 2026-06-20, reported) | CVE fix commits mined from NVD 2.0 + GHSA | multi | No | Python subset → security fix pairs |
| **CVEfixes** | Earlier CVE→fix-commit collection (the MoreFixes predecessor) | multi | No | Cross-check / dedupe with MoreFixes |
| PyPA advisory-database / GHSA | Python advisories with fix-commit links | Python | No | Mine recent Python fixes yourself if needed |
| **SWE-smith** | Synthetic bug instances + ~5k agent trajectories (Python repos) | Python | Yes | General single-function repair skill, format practice |
| **SWE-Gym** | Real repo tasks with executable environments + ~491 trajectories | Python | Yes | Same, smaller |
| **Your synthetic CWE injection** (below) | Clean function + injected vuln + PoC test | Python | **Yes** | The core verified security set, including repair turns |
| MegaVul, PrimeVul, Big-Vul | C/C++ vulnerability datasets | C/C++ | No | Skip (wrong language) |
| PatchEval, Vul4Py, CVE-Bench, your scenarios | Benchmarks | Py/Go/JS | Yes | **Evaluation only; never train on these** (exclude their repos too) |

Check each dataset's license before redistributing anything derived from it. The simplest
policy: publish the **scripts**, not the dataset, and publish the adapter weights only if
every source permits it.

## 3. Synthetic CWE injection: the verified core (recommended)

This is the SWE-smith idea applied to security, and it gives execution-verified examples:
1. Pick clean functions from permissively licensed Python projects, avoiding every repo that
   appears in your eval set. Focus on code that touches SQL, files, subprocesses, templates,
   deserialization, URLs, crypto, and auth.
2. Have a teacher model **inject** one CWE from your list (doc 11) into the function, and write
   a PoC test that fails on the injected version and passes on the original.
3. Verify in the sandbox: the PoC fails on the injected code, passes on the original, and the
   repo's existing tests pass on both. Discard anything that doesn't verify.
4. The verified pair (injected → original) is a training example, with tests attached.
5. Run a **student** attempt (your untuned SLM) on it. When it fails, the failed edit plus the
   sandbox feedback plus the correct fix make a **repair-turn example**.

Target ~1,000–2,000 verified synthetic examples. On free or cheap inference that takes about
2–3 days of mostly unattended runs.

## 4. Teacher model and terms of use

- Several commercial API terms restrict using outputs to develop competing models. Read the
  current terms of any provider before training on its outputs, and record your conclusion in
  the README.
- Cleanest option: an **open-weights teacher** under a permissive license, run through a hosted
  inference provider. Candidates: Qwen3-Coder-Next or Qwen3.6-35B-A3B. Check each model card's
  license.
- Whatever the teacher, keep **only sandbox-verified outputs** (rejection sampling). The
  teacher's authority doesn't matter once a test is the judge.

## 5. Example format (must equal inference format exactly)

- `prepare_dataset.py` must import and reuse **the same** `get_context()` (doc 06) and
  `build_prompt()` (doc 08) as inference. Train/inference skew is the most common silent
  fine-tuning bug.
- Render the examples with the base model's own chat template
  (`tokenizer.apply_chat_template`).
- Assistant target: `RATIONALE: ...` plus the SEARCH/REPLACE blocks. Nothing else.
- Loss is computed only on assistant tokens (Unsloth's `train_on_responses_only`).
- For Qwen3.5: train in non-thinking mode (empty think block per the chat template), unless you
  deliberately keep ≥75% reasoning examples to preserve thinking (Unsloth guidance, doc 03).

## 6. Converting a real fix commit into search/replace targets

1. Take the pre-fix file and the post-fix file from the commit (non-test files only).
2. Build the context from the pre-fix file at the changed function (same `get_context`).
3. For each diff hunk: SEARCH is the removed lines plus enough unchanged context lines to be
   unique in the file, and REPLACE is the added lines with the same context.
4. **Verify**: apply the blocks with the real `edits.py` to the pre-fix file and require a
   byte-exact match with the post-fix file. Drop the example if it doesn't match.
5. Write the rationale from the CVE summary or commit message, trimmed to at most 2 sentences.

## 7. Filters (applied in this order; log the counts at each step)

| Filter | Rule |
|---|---|
| Language | Python files only |
| Size | ≤ 60 changed lines, ≤ 2 functions touched, 1 file (v1) |
| Noise | Drop commits that also rename, reformat or bump versions (hunk count > 6, whitespace-only hunks) |
| Tests | Test-file changes are removed from targets (the model never edits tests) |
| Dedupe | Exact hash of the normalized pre-fix function; drop repeats |
| Length | Prompt + target ≤ 2,048 tokens (most) and ≤ 4,096 (hard cap) |
| Secrets | Drop anything matching key/token patterns |
| Leakage | Drop any repo that appears in the eval set; drop CVEs published after the training cutoff |

## 8. Target mix and size

| Slice | Share | Source |
|---|---|---|
| Security fix, first attempt | ~55% | Synthetic CWE (verified) + MoreFixes Python |
| Repair turns (failed edit + feedback → fix) | ~20% | Synthetic set with student failures |
| General single-function bug fixes | ~20% | SWE-smith / SWE-Gym final patches, converted |
| Format-hardening (whitespace-tricky SEARCH, multi-block edits) | ~5% | Synthetic |

Total: **2,000–5,000 examples**. Quality beats quantity at this scale, and 2k clean examples
beat 20k noisy ones for teaching a fixed output format. Hold out 5% as a validation split
for loss monitoring. The benchmark in doc 11 is a separate, untouched set.

## 9. Contamination controls (report them in the README)

- **Time split**: training CVEs are published before a fixed cutoff (e.g. 2026-01-01). Real-CVE
  eval scenarios come after the base model's release (Qwen3.5: March 2026) where possible.
- **Repo split**: no repository appears in both training and eval. Enforce it with an
  explicit exclude list checked in code.
- **Overlap check**: a 13-gram overlap scan between eval vulnerable functions and all training
  prompts, with every hit investigated.
- **Base-model memorization**: report real-CVE results split into "published before model
  release" and "after". A big gap suggests memorization.

## 10. Quality checks on synthetic injections (don't trust the teacher)

Teacher models tend to inject vulnerabilities that are either trivially obvious or not actually
exploitable. Filter both automatically:
- **Exploitability**: the PoC must fail on the injected code *for the right reason*. For
  example, the SQLi test asserts that a quote in the input is treated as data. A test that
  fails from an ImportError or a syntax error doesn't count.
- **Minimality**: the injected diff is ≤ 10 changed lines, which keeps the fix local, like
  real-world single-function fixes.
- **Detectability split**: record whether Opengrep/Bandit flags the injected code. Keep both
  flagged and unflagged cases, since real findings arrive both ways (scanner vs CVE report).
- **Diversity**: cap each (CWE, source repo) pair at ~30 examples, so one repo's style
  doesn't dominate.
- **Human spot check**: read 30 random verified examples (~1 hour). If more than 3 look wrong
  or silly, tighten the filters before training. This hour prevents a wasted training run.

## 11. Deliverables

- [ ] `prepare_dataset.py` produces `train.jsonl`, `val.jsonl`, and `stats.md` (counts per
      filter, per CWE, per source, and a token-length histogram).
- [ ] Of 20 random examples, all 20 re-apply byte-exact (a spot check of the conversion).
- [ ] Leakage check script prints zero repo overlaps and lists any 13-gram hits.

Next: [10-finetuning-and-serving.md](10-finetuning-and-serving.md)
