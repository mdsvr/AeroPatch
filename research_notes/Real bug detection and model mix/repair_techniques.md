# Repair-side techniques that raise (or do not raise) the security-fix rate of small local models (as of 2026-10-24)

Reading key used on every finding:
- **Size**: model and parameter count. Most results below are for models far above 10B. Do not read GPT-4o / Gemini / Sonnet effect sizes as 4B effect sizes.
- **Lang**: Py, C/C++, Java, Go/JS, or multi.
- **Oracle**: [EXEC-PoC+tests] exploit test plus functional tests; [EXEC-PoC] exploit only; [EXEC-tests] unit tests (general bugs); [SA] static analyser re-scan; [EM] exact match with the reference patch.
- **Loc**: whether the fix location was given to the model (Loc-given) or not (Loc-free).

Headline caveat: almost no execution-validated evidence exists for models under 10B on Python vulnerability repair. The only small-model security data points found are (1) VulnRepairEval, where Qwen3-8B scored 0/23 with thinking on and off (a floor effect that says little); (2) SecureFixAgent, 1.3B-7B models validated by a Bandit re-scan only, with no tests, so it cannot speak to behaviour-breaking fixes; (3) general (non-security) repair with CodeLlama-7B. Everything else is transferred from larger models, C/C++ or Java, or general code repair.

## 1. Sampling and selection (best-of-n, self-consistency, test-based selection, majority voting)

### Takeaway
Test-based selection over independent samples is the best-supported cheap lever, and the sandbox already provides the verifier for free. In Agentless (GPT-4o, Py), almost all of the selection gain came from reproduction (issue-revealing) tests, not from regression tests or majority voting. This maps directly onto AeroPatch's 70% (exploit test visible) against 46% (exploit hidden) gap. No 1-8B result on SWE-bench-style selection was found.

### Cited Findings
- **Agentless patch selection (GPT-4o, Py, SWE-bench Lite, 300 issues, Loc-free, [EXEC-tests]):** majority voting only 77 (25.67%); + regression-test filtering 81 (27.00%); + reproduction tests 96 (32.00%). Regression filtering adds about 1.3 pp; reproduction tests add 5 pp more. — [Agentless v2](https://arxiv.org/html/2407.01489v2)
- Agentless reproduction tests: 213 of 300 issues got a test that reproduces the issue on the original repo, but only 94 of those print "Issue resolved" with the ground-truth patch applied, so generated reproduction tests are noisy. — [Agentless v2](https://arxiv.org/html/2407.01489v2)
- Agentless sampling: 4 location sets x 10 patches gave 96 (32.00%) against 88 (29.33%) for 40 samples on the greedy location and 80 for one greedy sample per location set. Performance plateaus at about 40 samples. Oracle upper bound over all samples: 126 (42.0%). Average cost $0.70 and about 78k tokens per issue. — [Agentless v2](https://arxiv.org/html/2407.01489v2)
- **Repeated sampling (Large Language Monkeys, DeepSeek-Coder-V2-Instruct, large MoE, SWE-bench Lite):** coverage rises from 15.9% at k=1 to 56% at k=250. Where answers are automatically verifiable (coding), coverage converts directly into solved problems; majority voting and reward models "plateau beyond several hundred samples". Submitted 2024-07-31, revised 2024-12-30. — [Brown et al.](https://arxiv.org/abs/2407.21787)
- **Small model, general Py code, [EXEC-tests]:** Llama-3.1-8B instruct N=1 scored MBPP 60.3 / CodeContests 4.8; with best-of-5 it scored 69.7 / 13.8, beating every trained N=1 variant. muCode with best-of-5 and a learned verifier: 70.6 / 16.3. (Feb 2025.) — [muCode](https://arxiv.org/abs/2502.20380)
- **Self-repair vs sampling at equal budget (CodeLlama-13B, GPT-3.5, GPT-4; HumanEval/APPS):** gains "often modest" and sometimes absent; CodeLlama-13B and GPT-3.5 "mostly lag behind or match" no-repair baselines on APPS. GPT-4: 10 initial x 1 repair = 1.05x pass@20; 2 initial x 10 repairs = 0.97x. (ICLR 2024, older.) — [Olausson et al.](https://arxiv.org/abs/2306.09896)
- Multi-turn with execution feedback, untrained, gives "usually less than +2%" and is sometimes worse than single-turn sampling at equal budget (Llama 3.x, CodeContests). — [Zheng et al.](https://arxiv.org/abs/2410.08105)
- Verifier-based selection at SWE scale (32B and up): SWE-Gym Qwen2.5-Coder-32B best@k 20.6% (k=1) to 29.8% (k=8) to 32.0% (k=16); Satori-SWE-32B greedy 35.8 to Best@50 41.6 with reward model + unit tests; CWM majority voting over patches without test generation 58.4% against 53.9% without test-time scaling and 65.8% with full TTS. (Satori-SWE and CWM figures are from search snippets, not read in full.) — [SWE-Gym](https://arxiv.org/pdf/2412.21139); [Satori-SWE](https://arxiv.org/pdf/2505.23604); [CWM](https://arxiv.org/pdf/2510.02387)
- **Vul4Py (Py, 100 real CVEs, [EXEC-PoC+tests], Loc-given, Aug 2026):** of 119 patches that pass the exploit test, 15 (12.6%) fail the project's functional suite, 14 of them from agents "whose larger edits more often disturb unrelated behavior". Of the 104 patches passing both oracles, 98 (94%) were manually judged semantically equivalent to the developer fix. — [Vul4Py](https://arxiv.org/pdf/2608.00692)
- General repair, 600k patches (CodeLlama-7B to 33B, Java/C/Py): 30 samples per bug perform comparably to 200; 76.59% of DeepSeek-Coder's correct Defects4J patches and 89.6% of StarCoder's IntroClass correct patches fell within the first 30. Models were complementary (DeepSeek-Coder fixed 19 unique of 50 on Defects4J v2.0). — [Empirical Evaluation of LLMs in APR, 2025](https://arxiv.org/html/2506.13186v1)
- PatchEval (multi-lang incl. Py, 230 executable CVEs): 98 CVEs are fixed by at least one approach, only 5 by all, and 15 by exactly one, i.e. strong complementarity between models and runs. — [PatchEval](https://arxiv.org/html/2511.11019v1)

### Inferences
- AeroPatch's own pass@5 is roughly equal to the 3-attempt loop on both sets (18 against 19 of 27 scenarios; 5 against 4 of 10 CVEs), well under its own significance bar. That is consistent with Olausson/Zheng: for a small model, feedback-driven repair buys little over independent samples. It does not show that sampling beats feedback.
- AeroPatch's pass@5 almost certainly counts a sample as fixed when the hidden check passes, so it is an upper bound (oracle selection). Sampling only pays off when a run-time selector can tell the samples apart. Vul4Py's 94% precision is for exploit plus functional tests together; with regression tests and the re-scan only, Agentless suggests selection adds about 1.3 pp (25.67 to 27.0).
- The hidden-exploit setting (46%) is the Agentless "no reproduction test" case. The technique with the best evidence for closing it is to have the model (or a template) write a candidate exploit/reproduction test first, keep it only if it fails on the vulnerable code, then use it to select patches. This is the prerequisite that makes best-of-n work in scanner-driven use. Whether a 4B model can write useful exploit tests is unmeasured (see Gaps).
- Time cost (my arithmetic, assumes about 300 output tokens per SEARCH/REPLACE answer and the stated 46 tok/s): about 7 s generation per sample, so pass@5 adds about 30-40 s of generation plus 5 sandbox runs; the sandbox, not the model, is probably the dominant cost. A hybrid of 2-3 diverse first attempts each repaired once (Olausson's favoured split) costs about the same as the current 3-attempt loop.

### Gaps
- No 1-8B result for best-of-n or test-based selection on SWE-bench Lite/Verified or on any vulnerability benchmark was found. The smallest SWE-bench verifier results found are 14B (DeepSWE-Verifier) and a 30B-A3B MoE (SWE-RM).
- No study measured whether small models can generate exploit/reproduction tests for security bugs.

## 2. Retrieval and knowledge (CWE fix guidance, fix recipes, RAG over past fixes)

### Takeaway
The sources conflict, and the conflict matters. Bundled "knowledge" (CWE/CVE details plus a same-CWE historical example) roughly halved repairs when removed in PatchEval (large models, Loc-given). But a bare CWE-ID adds nothing, and concrete retrieved examples hurt in VulKey (C/C++, fine-tuned 15-32B, EM). Abstract per-CWE repair patterns (CWE type + edit action + key semantic element) are the knowledge form with the best support, and they map directly onto AeroPatch's salted-KDF, SSRF-resolved-IP and archive-path gaps. RAG over concrete past fixes is unproven and can hurt; it must be measured before adoption. No small-model evidence exists for either.

### Cited Findings
- **PatchEval knowledge ablation (Go/JS/Py, 230 CVEs, [EXEC-PoC+tests], Loc-given, single attempt, Nov 2025):** with knowledge -> without: GPT-4.1 43 -> 22; Gemini-2.5-Pro 52 -> 29; DeepSeek-R1 44 -> 30; Qwen3-Max 41 -> 23. "Knowledge" is defined as "the CWE/CVE details of the target vulnerability, along with a historical example" of a similar vulnerability with the same CWE and language from an earlier CVE. — [PatchEval](https://arxiv.org/html/2511.11019v1)
- **VulKey (C/C++ PrimeVul, 435 instances, [EM] over 100 samples, models fine-tuned first, FSE 2026, v3 2026-06-27):**
  - CWE-type prefix: StarCoderBase-15B 23.9 -> 23.6; Qwen2.5-Coder-32B 23.2 -> 22.5 (no gain).
  - Concrete same-CWE examples in context: random selection 11.9 / 12.9; BM25 similarity RAG 17.9 / 16.8; both below the 23.9 / 23.2 baseline.
  - Abstract three-level patterns (CWE type, syntactic action, semantic key element): 31.5% EM, +7.6 over the best baseline, also best on Java Vul4J (18 fixes). Ablation: without CWE type 26.4, without key element 27.6, without action 27.1.
  - The abstract says CWE-ID concatenation gives "negligible benefits" and few-shot examples are "rigid, non-generalizable".
  - — [VulKey](https://arxiv.org/pdf/2605.01769)
- **VulnRepairEval (Py, 23 CVEs, [EXEC-PoC], Sep 2025):** the vulnerability-type hint was mixed (small gains for Qwen3-235B and Qwen3-8B-Thinking, no change for DeepSeek-R1 and Qwen3-235B-Thinking, a notable drop for DeepSeek-V3); the example-based prompt gave "no significant improvement". Exact per-prompt numbers are only in a figure. — [VulnRepairEval](https://arxiv.org/html/2509.03331v1)
- **General repair, small model (CodeLlama-7B, ConDefects-Py, [EXEC-tests], method-level Loc-given):** adding one example raised CodeLlama-7B from 15 to 46 fixes (+206.7%); for DeepSeek-Coder-33B, the effect was -23.1%. — [Empirical Evaluation of LLMs in APR](https://arxiv.org/html/2506.13186v1)
- SAN2PATCH (C/C++, GPT-4o, USENIX Security 2025): staged prompting (comprehension, localization, fix strategy, patch) with tree-structured prompting and validation, from sanitizer logs; 79.5% on VulnLoc against 43% (ExtractFix) and 51% (VulnFix); 63% on its new 27-bug SAN2VULN set. Memory-safety bugs only. — [USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/kim-youngjoon)
- Vul-R2 (C/C++, Qwen2.5-14B, [EM]): prompted CoT 14B 9.89 against 13.56 for SFT and 24.83 for SFT+RLVR; reasoning traces from OpenAI o3 (off-limits under the free-data rule). — [Vul-R2](https://arxiv.org/html/2510.05480v1)

### Inferences
- PatchEval's large drop may partly come from CVE text, which can describe the fix; AeroPatch at fix time has a scanner finding, not a CVE description. So the PatchEval effect is an upper bound for scanner-driven repair.
- Defensible plan item: hand-written, abstract per-CWE "fix recipes" (what invariant to enforce, which API, where the check goes: e.g. "derive with a per-user random salt and a KDF, compare with hmac.compare_digest"; "resolve the hostname, check every resolved IP against private/link-local ranges, connect to the checked IP"; "resolve the member path and require it to stay under the destination"). This matches the VulKey form and targets the three named knowledge failures. It costs only prompt tokens.
- RAG over AeroPatch's 144 verified fixes: concrete examples hurt fine-tuned 15-32B models in VulKey but helped CodeLlama-7B a lot in general repair. The direction for a 4B model on Python security is unknown, so it needs an A/B on the project's own sets before adoption.

### Gaps
- No source measured CWE recipes or fix-example retrieval for a model under 10B on vulnerability repair with execution checks.
- RAVEN (agentic RAG over historical fixes, open-source models, locally deployable, reported 83.13% on 160 CVEs, June 2026) and KeaRepair (83.64% with Gemini-3.1-Pro) were seen only through summaries; their figures are unverified. — [RAVEN summary](https://chatpaper.com/paper/301944); [KeaRepair](https://www.emergentmind.com/papers/2607.00820)
- SecLLMHolmes was not checked in this pass.

## 3. Localization

### Takeaway
Wrong localization is the largest single failure cause in the security benchmarks found: 56-78% of failures in VulnRepairEval (Py) and a 20-pp drop for agents when the location is withheld in PatchEval. AeroPatch is in a better position than these benchmarks because the scanner finding gives the line. The residual risk is fixes that need edits away from the flagged line (multi-hunk, multi-file), where success collapses.

### Cited Findings
- **VulnRepairEval (Py, 23 CVEs, [EXEC-PoC]):** "Miss Vulnerable Code" share of failures: Gemini 2.5 Pro 0.609, Gemini 2.5 Flash 0.696, o4-mini 0.739, DeepSeek-R1 0.609, **Qwen3-8B-Thinking 0.782**, Qwen3-235B-Thinking 0.565; patch errors about 0.17-0.35. — [VulnRepairEval](https://arxiv.org/html/2509.03331v1)
- **PatchEval localization precision (large models, multi-lang):** average fixes without line hint 46.3; precise line 54.3; approximate 47.0; imprecise 42.7. Agents without location: SWE-Agent (Gemini 2.5) 53 -> 32; Claude-Code 43 -> 29. — [PatchEval](https://arxiv.org/html/2511.11019v1)
- **PatchEval patch complexity (average repair rate across approaches):** 1-5 changed lines 32.5%; 5-10 23.6%; 10-20 13.4%; 20-50 10.0%; 50+ 2.1%. 1 hunk 25.3%; 2 hunks 15.4%; 3+ 5.0%. 1 file 20.5%; 2 files 6.2%; 3+ 0%. — [PatchEval](https://arxiv.org/html/2511.11019v1)
- **Agentless localization (GPT-4o, SWE-bench Lite):** file-level hit rate 81.67% (combined prompting + embedding); related elements 58.33% (skeleton format); edit locations 49.67-56.33%. Final patches hit the right function in 52.0% and the right line in 35.3%. — [Agentless v2](https://arxiv.org/html/2407.01489v2)
- Lingma SWE-GPT 7B (Qwen2.5-Coder-7B based, Py): 18.20% on SWE-bench Verified with its own multi-stage localization pipeline; repository reports 51.16% fault-location success on Verified (search snippet, not read in full). — [Lingma SWE-GPT](https://arxiv.org/pdf/2411.00622); [repo](https://github.com/crz218/Lingma-SWE-GPT)
- General repair: on BugsCpp, 76% of DeepSeek-Coder-33B's patches modified the wrong locations; effectiveness dropped significantly for functions over 100 lines. — [Empirical Evaluation of LLMs in APR](https://arxiv.org/html/2506.13186v1)
- ESEM 2026 study (algorithmic bugs, DeepSeek/GPT/Llama): "imprecise fault localization can substantially enlarge the performance gap between APR techniques" (search snippet, not read in full). — [Liu et al., ESEM 2026](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESEM.2026.40)

### Inferences
- For scanner-driven repair the line is known, so Agentless-style file localization adds little. What may help is "related element" context: pulling the callers/callees and the config or helper the fix must touch (two-file SQL injection, SSRF fix in the HTTP helper) into the tree-sitter context.
- AeroPatch's failures are in edits beyond one hunk or one file, where PatchEval rates fall to 5-6%.

### Gaps
- No source measured how often a small model's failures on scanner-located (line-given) Python vulnerabilities come from editing the wrong place.

## 4. Reasoning (thinking modes, chain-of-thought)

### Takeaway
Thinking and CoT are not a lever for vulnerability repair in any source found. Thinking variants scored at or below their non-thinking twins in PatchEval, CoT removal had "limited impact", and Qwen3-8B scored 0/23 either way in VulnRepairEval. This agrees with AeroPatch's own 41 against 38 of 54 (not significant). Structured "analyse the bug first" prompting helped weak 7B models on general bugs but hurt a stronger 33B model.

### Cited Findings
- **PatchEval (large models, Loc-given):** Doubao1.6-Thinking 34 against Doubao1.6 38; DeepSeek-R1 44 against DeepSeek-V3 41. Removing the CoT instruction: GPT-4.1 43 -> 43, Gemini-2.5-Pro 52 -> 51, DeepSeek-R1 44 -> 49, Qwen3-Max 41 -> 37; the paper calls this "limited impact". Average tokens per CVE (probably prompt plus output): Doubao1.6-Thinking 10.28k against Doubao1.6 6.89k (about 1.5x); DeepSeek-R1 10.15k against DeepSeek-V3 3.65k (about 2.8x). — [PatchEval](https://arxiv.org/html/2511.11019v1)
- **VulnRepairEval (Py):** Qwen3-8B 0/23 and Qwen3-8B-Thinking 0/23; Qwen3-235B 0/23 and Qwen3-235B-Thinking 2/23; chain-of-thought had a "negligible overall effect". — [VulnRepairEval](https://arxiv.org/html/2509.03331v1)
- **General repair, [EXEC-tests]:** a bug-analysis step raised CodeLlama-7B from 28 to 43 (ConDefects-Java) and 15 to 60 (ConDefects-Py), but lowered DeepSeek-Coder-33B from 118 to 63 (Java) and 93 to 72 (Py); the authors blame inaccurate analyses misleading strong models. — [Empirical Evaluation of LLMs in APR](https://arxiv.org/html/2506.13186v1)
- ESEM 2026: stronger reasoning settings "do not consistently yield better cost-efficiency", and the effect "varies considerably across different LLM families" (search snippet, not read in full). — [Liu et al., ESEM 2026](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESEM.2026.40)
- Vul-R2 (C/C++, 14B): prompted CoT gave 9.89 EM against 24.83 after SFT+RL on reasoning data, so reasoning helped only once trained (with o3-generated traces). — [Vul-R2](https://arxiv.org/html/2510.05480v1)

### Inferences
- Time cost in multiples: PatchEval's same-family thinking models used about 1.5x and 2.8x the total tokens of their non-thinking twins. The output-only multiple, which sets laptop time, was not reported, but it is larger than the total-token ratio because the prompt is shared. The same time buys one or more extra non-thinking samples, a better-supported use of it.
- Short structured analysis (state the invariant, then edit) may still be worth a cheap A/B for a 4B model, since the 7B general-repair result was positive; long thinking is not.

### Gaps
- No source compared thinking budgets against patch correctness for models under 10B on security repair with non-zero success.

## 5. Training (RL with execution reward, preference pairs, rejection-sampling fine-tuning, distillation)

### Takeaway
At 4-8B, multi-turn RL on execution outcomes is the only family with clean evidence that the model learns to use feedback, with gains of about 4-6 points on general code; SFT-family gains are small, zero or negative unless the data is on-policy. No vulnerability-repair training result with execution validation exists at under 10B. On a free Kaggle T4, SFT works, but GRPO on Qwen3.5-4B is high-risk (vision-only reference notebook, fp32 fallback, no vLLM, about 80 s a step, 300+ steps needed). AeroPatch's own LoRA results (541 examples lost; 144 self-verified fixes tied) are consistent with this literature.

### Cited Findings
- RLEF: Llama 3.1 8B from 10.5 to 16.0 (CodeContests test, 1@3); multi-turn SFT on the same task did not move the 8B (10.0). Replacing real feedback with random feedback "severely impaired" recovery. — [RLEF](https://arxiv.org/abs/2410.02089)
- Murphy (Qwen3-4B, multi-turn GRPO, 1,000 KodCode problems, about 88 H100-h): up to +6.2 pp over the best comparator; Qwen3-4B LiveCodeBench-v6 +4.38 medium, +4.20 hard. — [Murphy](https://arxiv.org/abs/2511.07833)
- Repair-R1 (Qwen3-4B, GRPO, 5,421 mutant bugs): bugfix rate vanilla / SFT / RL / Repair-R1 on HumanEval 83.9 / 66.1 / 84.8 / 86.6; MBPP 48.6 / 67.7 / 70.8 / 72.0. SFT lowered 3B HumanEval 51.8 to 19.5. — [Repair-R1](https://arxiv.org/abs/2507.22853)
- Practitioner's Guide (GRPO on 90 SWE-Gym tasks, Qwen3-8B): base 0.04; binary verified reward 0.042 (no gain); fraction-of-tests reward 0.22; LLM-judge rewards 0.072-0.093 (metric labelling ambiguous). — [Practitioner's Guide](https://arxiv.org/abs/2510.01132)
- SWE-Gym (Qwen2.5-Coder 7B/14B/32B, rejection-sampling SFT on 491 trajectories from commercial models): "stuck in loop" rate (same action three times) for 7B on Verified fell from 39.6% to 21.0%; mixing 868 on-policy trajectories dropped the 32B OpenHands agent from 15.3% to 8.7%. — [SWE-Gym](https://arxiv.org/abs/2412.21139)
- LEDEX (CodeLlama-7B): self-bootstrapped SFT (no external teacher) up to +8.25 pass@1; RL on top +0.71. — [LEDEX](https://arxiv.org/abs/2405.18649)
- SecureFixAgent (Py, Bandit + LoRA, DeepSeek-Coder 1.3B/6.7B, Qwen2.5-Coder 3B/7B, CodeLlama-7B, CodeGemma-7B, **[SA] only, no tests**, Sep 2025): LLM-only fix accuracy raw -> LoRA: Qwen2.5-Coder-3B 72.97 -> 79.72; Qwen2.5-Coder-7B 74.32 -> 79.72; DeepSeek-Coder-1.3B 62.16 -> 71.62. Aggregate: LLM-only 74.32%, LLM-only fine-tuned 79.72%, iterative loop with base model 81.08%, loop fine-tuned 87.83%. Average iterations 4 (base) and 3 (fine-tuned), although the abstract says "typically converging within three iterations". Fine-tuning data size not given; fine-tuning peak memory up to 40 GB. — [SecureFixAgent](https://arxiv.org/html/2509.16275v1)
- Vul-R2 (C/C++, Qwen2.5-14B, [EM]): SFT with reasoning data alone 22.30; SFT+RLVR 24.83, so RL added about 2.5 points. — [Vul-R2](https://arxiv.org/html/2510.05480v1)
- T4 feasibility: the only Qwen3.5-4B GRPO notebook is a vision one; on a T4 it falls back to float32 and took 1:20:25 for 60 steps (about 80 s a step) with 2 generations and 1,024-token completions. Unsloth says GRPO needs at least 300 steps "for the reward to actually increase" and "a minimum of 12 hours". The text-only GRPO path had shape-mismatch bugs (unsloth#5121). — [Unsloth notebook](https://github.com/unslothai/notebooks/blob/main/nb/Qwen3_5_(4B)_Vision_GRPO.ipynb); [Unsloth RL guide](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide); [unsloth#5121](https://github.com/unslothai/unsloth/issues/5121)

### Inferences
- 300 GRPO steps at about 80 s is about 6.7 h of T4 time before rewards are expected to rise (my arithmetic). That excludes the sandbox runs each step's reward needs, and holds only if the text GRPO path runs at all on Qwen3.5 in fp32.
- Training should be compared against the cheap inference baselines (sandbox-selected best-of-n plus duplicate-edit rejection, below), not only against the untrained loop. Given RLEF's +5.5 and Murphy's +4-6 at 4-8B, that bar is not trivially cleared.
- SecureFixAgent's gains are Bandit-pass gains; they do not show that LoRA avoids behaviour-breaking fixes.

### Gaps
- No under-10B vulnerability-repair training result with exploit plus regression-test validation was found.
- No confirmed working text-only GRPO run of Qwen3.5-4B on a T4 was found.

## 6. Deterministic help (codemods, per-CWE templates, constrained decoding of the edit format)

### Takeaway
Pixee's codemodder-python has deterministic, AST-based fixes for a set of common Python CWEs. It is AGPL-3.0, active (last push 2026-10-22), and best used as a first pass before the model. It covers none of AeroPatch's three named knowledge gaps cleanly: its SSRF codemod swaps in a wrapper library rather than adding a resolved-IP check in place, and nothing covers archive paths or salted key derivation. No evidence was found on constrained or grammar decoding of SEARCH/REPLACE for small models; the one format study found that small open models "benefit little from any formatting choice".

### Cited Findings
- codemodder-python core codemods (repo listing `src/core_codemods`) that touch security CWEs: `add_requests_timeouts`, `disable_graphql_introspection`, `django_debug_flag_on`, `django_session_cookie_secure_off`, `django_json_response_type`, `enable_jinja2_autoescape`, `flask_enable_csrf_protection`, `flask_json_response_type`, `harden_pickle_load`, `harden_pyyaml`, `harden_ruamel`, `https_connection`, `jwt_decode_verify`, `limit_readline`, `lxml_safe_parser_defaults`, `lxml_safe_parsing`, `process_creation_sandbox`, `replace_flask_send_file`, `requests_verify`, `secure_cookie_mixin`, `secure_flask_cookie`, `secure_flask_session_config`, `secure_random`, `sql_parameterization`, `subprocess_shell_false`, `tempfile_mktemp`, `upgrade_sslcontext_minimum_version`, `upgrade_sslcontext_tls`, `url_sandbox`, `use_defused_xml`. There are also `semgrep`, `sonar` and `defectdojo` subfolders for findings from external tools. License AGPL-3.0; last push 2026-10-22. — [codemodder-python repo](https://github.com/pixee/codemodder-python) (listing read through the GitHub API)
- `url_sandbox` (CWE-918/CWE-20) rewrites non-literal `requests.get(...)` to `security.safe_requests.get(...)`, adding Pixee's `security` package as a dependency; its docs say the default behaviour "raises a SecurityException if a user attempts to access a known infrastructure location". Review guidance: merge after cursory review. — [url_sandbox source](https://github.com/pixee/codemodder-python/blob/main/src/core_codemods/url_sandbox.py); [python-security safe_requests](https://github.com/pixee/python-security/blob/main/src/security/safe_requests/api.py)
- CLI: `codemodder /path` (edits in place), `codemodder --dry-run /path`, `codemodder --list`; install `pip install codemodder[semgrep]`. — [codemodder-python README](https://github.com/pixee/codemodder-python)
- Diff-XYZ (Oct/Nov 2025): search-replace "performs best for larger models across most tasks"; "smaller open models benefit little from any formatting choice". — [Diff-XYZ](https://arxiv.org/abs/2510.12487)
- Aider: edit failures usually happen because the model is "disobeying the system prompts"; above about 25k tokens of context, most models become less likely to conform. — [Aider edit errors](https://aider.chat/docs/troubleshooting/edit-errors.html)
- Format and syntax errors are a real share of failures even for large models: PatchEval reports mismatched quotes and undefined variables; VulnRepairEval puts patch errors at about 17-35% of failures. — [PatchEval](https://arxiv.org/html/2511.11019v1); [VulnRepairEval](https://arxiv.org/html/2509.03331v1)

### Inferences
- Run codemodder (as a separate CLI process, not imported, which keeps more distance from AGPL obligations) on the findings it covers. Send only what it does not fix to the model. That removes the model from the easy cases, so it does not raise the model's fix rate on hard ones.
- For the three knowledge gaps, AeroPatch would need its own templates (the recipes in section 2), or deterministic fix templates for the narrowest patterns (for example a `zipfile`/`tarfile` extraction guard).
- Constrained decoding is low priority: AeroPatch's gates already reject malformed edits, and Diff-XYZ suggests format choice matters little at small size.

### Gaps
- No measurement found of grammar- or JSON-schema-constrained decoding (for example llama.cpp GBNF or Ollama structured outputs) on SEARCH/REPLACE edit validity or fix rate for small models.
- Whether `safe_requests` checks the resolved IP (DNS rebinding) was not verified; the source read was only the codemod, not the library.
- AeroPatch's own licence, and whether running an AGPL CLI as a subprocess is acceptable to it, was not checked.

## 7. Which techniques address the observed failures (behaviour-breaking fixes, repeated edits, missing domain knowledge)

### Takeaway
- **Behaviour-breaking fixes:** sandbox-selected best-of-n plus a minimal-edit instruction. The paired oracle (exploit plus functional tests) was 94% precise, but in scanner-driven use it needs a generated exploit test.
- **Repeated edits:** reject duplicates in the harness and resample. No paper measures this directly; the SWE-Gym and Olausson evidence supports it indirectly.
- **Missing domain knowledge:** abstract per-CWE recipes (best evidence in VulKey, C/C++) and deterministic templates. Sampling cannot supply knowledge the model lacks, and thinking does not either.

### Cited Findings
- Behaviour-breaking: 12.6% of exploit-passing patches broke functional tests in Vul4Py, mostly larger agent edits; DeepSeek-V3 produced 12 PatchEval patches that passed security tests but failed functionality tests; success falls sharply with patch size (32.5% at 1-5 lines against 2.1% at 50+). — [Vul4Py](https://arxiv.org/pdf/2608.00692); [PatchEval](https://arxiv.org/html/2511.11019v1)
- Execution feedback is decisive for real Python CVEs at large scale: with the same Claude Sonnet 4 backbone and location hints, OpenHands fixed 41/100 against 4/100 for direct prompting (Vul4Py), at $1.32 and 490 s against $0.05 and 6 s per instance. PatchEval feedback (compiler errors, failing PoC; 5 rounds): Gemini-2.5-Pro 52 -> 122, GPT-4.1 43 -> 89, DeepSeek-R1 44 -> 105, o3 40 -> 113, with a plateau after about 5 rounds. — [Vul4Py](https://arxiv.org/pdf/2608.00692); [PatchEval](https://arxiv.org/html/2511.11019v1)
- Repeated edits: base instruct models often resubmit the same code after feedback (RLEF); base code LMs copy 42-65% of the time (CYCLE); SFT on trajectories cut a 7B agent's "stuck in loop" rate from 39.6% to 21.0% (SWE-Gym). — [RLEF](https://arxiv.org/abs/2410.02089); [CYCLE](https://arxiv.org/abs/2403.18746); [SWE-Gym](https://arxiv.org/abs/2412.21139)
- Detailed feedback reduced diversity in multi-turn generation; RFT "makes the model produce more diverse code within trajectories". — [Zheng et al.](https://arxiv.org/abs/2410.08105)
- Missing knowledge: CWE-ID alone gives about zero; abstract patterns give +7.6 EM (C/C++); bundled CVE/CWE knowledge plus example roughly doubles fixes for large models (multi-lang). — [VulKey](https://arxiv.org/pdf/2605.01769); [PatchEval](https://arxiv.org/html/2511.11019v1)
- Small models fail very differently from large ones on Python CVEs: Qwen3-8B 0/23 in VulnRepairEval while the best large model reached 5/23. — [VulnRepairEval](https://arxiv.org/html/2509.03331v1)

### Inferences
- The large feedback gains in PatchEval (about 2-3x for frontier models) contrast with AeroPatch's small-model result, where pass@5 and the feedback loop are roughly equal (5 against 4 of 10 CVEs; 18 against 19 of 27 scenarios). This fits Olausson: the gain from feedback depends on the model's ability to read it.
- Duplicate-edit rejection (my inference, not measured anywhere): normalise the SEARCH/REPLACE pair, refuse an identical edit before the sandbox, and resample at a higher temperature. It costs only one extra generation, about 7 s at 46 tok/s.
- Suggested ranking for a 4 GB laptop, by evidence strength against cost:
  1. Sandbox-selected sampling (k independent first attempts, optionally 1 repair each), together with a model- or template-written exploit test that is kept only if it fails on the vulnerable code. The test is the prerequisite: without it the run-time selector has only regression tests and the re-scan, and Agentless suggests that adds about 1.3 pp.
  2. Duplicate-edit rejection.
  3. Per-CWE abstract recipes for the known gap classes.
  4. codemodder first pass for covered CWEs.
  Not worth it on current evidence: thinking mode, bare CWE-ID hints, concrete-example RAG without an A/B, constrained decoding, GRPO on a T4 before a smoke test.

### Gaps
- No source measured any of these techniques on a sub-10B model on Python vulnerabilities with exploit plus regression-test validation; every effect size above must be re-measured on AeroPatch's own 27 scenarios and 10 CVEs.
