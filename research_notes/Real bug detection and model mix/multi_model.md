# Multiple small local models for code repair and vulnerability work (as of 2026-10-24)

Scope note: research run with about 25 tool calls. Paper numbers were checked against the arXiv abstract pages unless marked otherwise. Items marked "(from memory, unverified)" were not confirmed on any page this session. Items marked "(search summary)" came from a search-engine summary and were not opened; treat their exact numbers as unverified. Arithmetic marked "computed here" was done locally with exact binomial sums.

## 1. Ensembles of different models against best-of-n from one model (diversity, union, MoA, routing, cascades)

### Takeaway
Mixing models raises the oracle "union" (coverage) much more than it raises what a selector can actually pick: on SWE-bench the union of five strong systems reached 80.8% but selection got 66.2%, only 3.4 points over the best member. For a fixed budget, more samples of the single best model often match or beat a mix (Self-MoA beats mixed MoA by 6.6 points on AlpacaEval 2.0), so a second family pays off only if it is close in quality to Qwen3.5-4B and fails on different tasks. Almost no published ensemble or routing result is for models under 10B on code repair.

### Cited Findings
- Repeated sampling from one model: DeepSeek-Coder-V2-Instruct on SWE-bench Lite went from 15.9% solved with one sample to 56% with 250 samples, and coverage grows roughly log-linearly with sample count over four orders of magnitude. Majority voting and reward models stop improving after a few hundred samples, so selection, not generation, is the bottleneck where there is no automatic verifier (July 2024, rev. Dec 2024). — [Brown et al., Large Language Monkeys, arXiv 2407.21787](https://arxiv.org/abs/2407.21787)
- Union of different systems on SWE-bench Verified ("Barrel of Monkeys", leaderboard as of 2025-01-15): CodeMonkeys plus the top four submissions give 80.8% coverage (oracle: solved if any candidate is correct). Their selector picks 66.2%; the best single member (Blackbox AI Agent) scores 62.8%; random choice from the ensemble scores 60.9%. CodeMonkeys alone: 57.4% (Jan 2025). — [CodeMonkeys, arXiv 2501.14723](https://arxiv.org/pdf/2501.14723); [Stanford blog](https://scalingintelligence.stanford.edu/blogs/codemonkeys)
- DEI (Diversity Empowers Intelligence), a committee that reranks patches from several SWE agents: a group of open-source agents with best individual resolve rate 27.3% on SWE-bench Lite reached 34.3% with DEI (a 25% relative gain); the best group reached 55%. The paper argues that different agents solve more distinct issues than repeated runs of one agent (Aug 2024; agents built on large hosted models, not sub-10B). — [Zhang et al., arXiv 2408.07060](https://arxiv.org/abs/2408.07060)
- Mixture-of-Agents with only open-source models scored 65.1% on AlpacaEval 2.0 against 57.5% for GPT-4 Omni (June 2024; chat quality, not code; the proposers were large open models, sizes not checked on the abstract page). — [Wang et al., arXiv 2406.04692](https://arxiv.org/abs/2406.04692)
- S* (test-time scaling for code, 2025): parallel sampling plus sequential revision, with selection by generating "distinguishing inputs" that make two candidates behave differently and executing them; evaluated on the Qwen2.5-Coder-Instruct series from 0.5B to 32B on LiveCodeBench, and the abstract reports S* lets a 3B model outperform GPT-4o-mini. This is single-family scaling, the clearest sub-10B evidence found, and it is code generation, not repair. — [Li et al., S*, arXiv 2502.14382](https://arxiv.org/pdf/2502.14382) (search summary of abstract; per-size table not read)
- Self-MoA (one model sampled several times, then aggregated) beats standard mixed-model MoA by 6.6% on AlpacaEval 2.0 and by 3.8% on average across MMLU, CRUX and MATH; "mixing different LLMs often lowers the average quality of the models", so MoA is sensitive to the weakest proposer (Feb 2025). — [Li, Lin, Xia, Jin, Rethinking MoA, arXiv 2502.00674](https://arxiv.org/abs/2502.00674)
- Sampling-and-voting ("Agent Forest"): performance scales with the number of instances of one model, and the gain grows with task difficulty (Feb 2024, TMLR; the abstract gives no figures). — [Li et al., More Agents Is All You Need, arXiv 2402.05120](https://arxiv.org/abs/2402.05120)
- RouteLLM (router between one strong and one weak model, trained on preference data) cuts cost by more than 2x in some cases without losing quality, and its routers keep working when the strong and weak models are swapped at test time (June 2024, rev. Feb 2025). Evaluated on general chat and reasoning benchmarks with GPT-4-class strong models, not code repair with two small models. — [Ong et al., arXiv 2406.18665](https://arxiv.org/abs/2406.18665)
- FrugalGPT cascades (cheap model first, escalate when a scorer is unsure) match the best single LLM (GPT-4) with up to 98% cost reduction, or beat GPT-4 accuracy by 4% at equal cost (May 2023, older work). — [Chen, Zaharia, Zou, arXiv 2305.05176](https://arxiv.org/abs/2305.05176)
- Errors are correlated across models: on one leaderboard, when two models are both wrong they pick the same wrong answer about 60% of the time; correlation rises with shared architecture and provider, and larger, more accurate models have more correlated errors even across providers (ICML 2025). — [Kim, Garg, Peng, Garg, arXiv 2506.07962](https://arxiv.org/html/2506.07962v1); [PMLR](https://proceedings.mlr.press/v267/kim25e.html)

### Inferences
- The project already has the strongest cheap lever: Qwen3.5-4B pass@5 = 67% against 45% pass@1 on 27 scenarios. The gap is selection, as in Large Language Monkeys and CodeMonkeys. A second model only adds value through tasks that no Qwen sample solves; measure that directly (see section 6) before building routing.
- Fair comparison needs equal budget: union(Qwen x5, Gemma x5) must be compared with Qwen x10, not with Qwen x5. A union of more samples is always at least as large, so comparing unequal budgets credits the mix with plain sample count.
- Self-MoA and the correlated-errors paper both predict that a weaker second family (for example a 1-3B Gemma or a small Nemotron) mostly lowers average quality; a mix helps only when the other model's pass@1 is within a few points of Qwen's on these tasks.
- Routing (RouteLLM-style) needs a trained router and many labelled tasks; with 27 scenarios a hand rule ("send Python-deserialization tasks to model B") is the only realistic form, and it risks overfitting.
- A local cascade (Qwen first, other family on the third attempt) is the free analogue of the earlier Qwen-then-Opus cascade, but the earlier 100% and 90% came from a much stronger third model; a peer-sized model will not reproduce that jump.

### Gaps
- No published result found for ensembles or routing of models under 10B on program repair or vulnerability repair; the DEI, CodeMonkeys and MoA results all use large models. The only sub-10B evidence found (S*) is single-family sampling plus execution-based selection on code generation.
- No measured numbers found for the specific models the user named (DeepSeek, Mistral, Nemotron, Gemma small variants) on Python security repair.
- DEI's union and oracle figures for different agents versus repeated runs were not read (only the abstract).

## 2. Roles for a second model: diverse patch generator, judge or reviewer, scanner triage, test writer, critique and revise

### Takeaway
The best-measured second-model role is a planner/editor split (Aider architect mode, +3 to +5 points even when both roles use the same model) and majority voting on binary detection (+3.1 points over the best single model, larger than for localisation). Small thinking models can judge code surprisingly well (Qwen3-8B beat trained 70B judges in CodeJudgeBench), but every judge is unstable to answer order (up to 14 points) and judges favour their own family when they are wrong, so a judge must never be the only gate when tests exist.

### Cited Findings
- Aider architect/editor (Sept 2024, aider code-editing benchmark): o1-preview architect with o1-mini or DeepSeek editor 85.0%; same-model pairs also gain over solo: Claude 3.5 Sonnet 77.4% solo to 80.5% paired with itself, GPT-4o 71.4% to 75.2%, GPT-4o-mini 55.6% to 60.2%. Pairing with DeepSeek as editor was at or slightly below same-model pairing (Sonnet+DeepSeek 78.9% vs Sonnet+Sonnet 80.5%). — [aider: Separating code reasoning and editing](https://aider.chat/2024/09/26/architect.html)
- Aider, QwQ-32B as architect with Qwen2.5-Coder-32B as editor: 74%, below Sonnet alone at 84%; QwQ alone "was unable to comply with even the simplest editing format", so the editor role rescued a model that could reason but not edit (Dec 2024, the only locally runnable architect pair aider reported). — [aider: QwQ](https://aider.chat/2024/12/03/qwq.html)
- R1 architect plus Sonnet editor: 64.0% on the polyglot benchmark at 14x lower cost than the earlier o1 result; o1 plus Sonnet did not beat o1 alone, so a second model does not always help (Jan 2025). — [aider: R1 + Sonnet](https://aider.chat/2025/01/24/r1-sonnet.html)
- Diverse LLMs on software QA tasks (six models, some small, including Gemma-7B): majority voting improved over the best single LLM by 3.1% on vulnerability detection versus 1.4% on fault localisation, attributed to the binary output making votes easy; Gemma-7B was the best single model on vulnerability detection (+7.8% accuracy over the GPT-3.5 baseline) (Sept 2024; ensemble includes Llama-3-70B). — [Beyond ChatGPT, arXiv 2409.01001](https://arxiv.org/html/2409.01001v1) (search summary)
- DVDR-LLM (Dec 2025): several LLMs judge code independently and a vulnerability is flagged on majority agreement; 10-12% higher detection accuracy than the average single model, with recall +18% and F1 +11.8% on multi-file cases. A higher agreement threshold lowers false positives but raises false negatives. Note the comparison is against the average model, not the best one. — [Diverse LLMs vs. Vulnerabilities, arXiv 2512.12536](https://arxiv.org/html/2512.12536v1) (search summary)
- CodeJudgeBench (26 judges on code generation, repair and unit-test generation; arXiv July 2025, ACL 2026): thinking models clearly beat non-thinking ones; Qwen3-8B beat specially trained judges up to 70B; swapping the order of the two candidates moved accuracy by up to 14%; all models were sensitive to response order, variable names and misleading comments. — [Jiang et al., arXiv 2507.10535](https://arxiv.org/pdf/2507.10535); [ACL 2026](https://aclanthology.org/2026.acl-long.888/)
- Small and cost-optimised judges show the most position bias; one large-scale judge evaluation reports a position-bias rate of 0.192 for Qwen3-8B against 0.002 for Gemini 2.5 Pro (June 2026). — [Reliability without Validity, arXiv 2606.19544](https://arxiv.org/pdf/2606.19544) (search summary, unverified numbers)
- Self-preference: on math, factual and code benchmarks with ground truth, much of a judge's preference for its own outputs matches real quality, but harmful self-preference persists where the judge model is a poor generator on that task; long chain-of-thought before judging reduces it (2025). — [Do LLM Evaluators Prefer Themselves for a Reason?, arXiv 2504.03846](https://arxiv.org/html/2504.03846v3)
- Judges favour outputs from themselves or their own family, and self-preference grows with output length on LiveCodeBench (2026). — [Self-Preference Bias in Rubric-Based Evaluation, arXiv 2604.06996](https://arxiv.org/pdf/2604.06996) (search summary)
- Earlier work linked a judge's ability to recognise its own text with the strength of its self-preference (Apr 2024). — [Panickssery et al., arXiv 2404.13076](https://arxiv.org/abs/2404.13076v1)
- A 2026 audit of LLM-as-judge for software engineering exists. — [Bias in the Loop, arXiv 2604.16790](https://arxiv.org/pdf/2604.16790) (found, not read)

### Inferences
- Best-supported roles for a second local model, in order: (a) voter on binary scanner triage ("is this finding real?"), where voting is measured to help most; (b) independent patch generator from another family, only if its pass@1 is near Qwen's; (c) test writer (section 3); (d) judge, last, and only as a tie-breaker among patches that already pass every check.
- Do not let Qwen judge Qwen patches: the self-preference work says the harm concentrates on exactly the tasks the generator got wrong. Use a different family as judge, run it with thinking on, and judge each pair twice in swapped order, accepting only consistent verdicts.
- Architect/editor gains came from a strong reasoner paired with a reliable editor. With 4B models the editor role mostly matters for format compliance; AeroPatch already constrains edit format, so expect less than the +3 to +5 points aider saw.
- Critique-and-revise with a peer-sized model was not found measured for repair; treat it as unproven.

### Gaps
- No measured result found for small models writing exploit or regression tests for security patches.
- No measured pairings of Gemma, Mistral, Nemotron or DeepSeek small models with Qwen on repair.
- DVDR-LLM and Beyond ChatGPT model lists and sizes were not checked in full.

## 3. Choosing among several patches without ground truth

### Takeaway
Systems pick by executed behaviour first: filter on existing and generated tests, then cluster or vote by output behaviour or by normalised patch text, and use a model judge only for what remains. Selection recovers only part of the union (CodeMonkeys: 66.2% picked from 80.8% available, random 60.9%).

### Cited Findings
- Agentless: a three-phase pipeline (localisation, repair, patch validation) with one model; 32.00% (96 fixes) on SWE-bench Lite at a reported cost of $0.70 (v2, Oct 2024; v1 July 2024). The abstract does not describe the validation step; my recollection that it filters sampled patches with regression tests and model-written reproduction tests and then majority-votes over normalised patches is (from memory, unverified). — [Xia et al., Agentless, arXiv 2407.01489](https://arxiv.org/abs/2407.01489)
- CodeT: the same model writes test cases, and candidates are ranked by "dual execution agreement" between generated tests and other code samples; it raised HumanEval pass@1 to 65.8%, +18.8 points absolute over code-davinci-002 (July 2022, older work). — [Chen et al., CodeT, arXiv 2207.10397](https://arxiv.org/abs/2207.10397)
- S* picks between candidates by having the model write inputs that make two candidates disagree, then running both, with no reference tests needed (2025). — [arXiv 2502.14382](https://arxiv.org/pdf/2502.14382) (search summary)
- Majority voting and reward-model selection plateau after a few hundred samples; selection is the bottleneck where there is no automatic verifier. — [Large Language Monkeys, arXiv 2407.21787](https://arxiv.org/abs/2407.21787)
- CodeMonkeys selection over a mixed ensemble got 66.2% vs 60.9% random vs 80.8% oracle; its selector closes less of the gap on a mixed ensemble than within its own candidates. — [arXiv 2501.14723](https://arxiv.org/pdf/2501.14723)
- DEI reranks candidate patches with a committee and notes current agents "could solve far more issues" with a reranker that tells which candidates are correct. — [arXiv 2408.07060](https://arxiv.org/pdf/2408.07060)

### Inferences
- A cheap ordering for AeroPatch: (1) keep patches that pass the hidden suite stand-ins already in the loop (scanner clean, existing tests, sandbox); (2) run every surviving patch against tests written by a different family than the patch author, and keep the patch passing most; (3) group patches with identical behaviour on all tests and prefer the largest group; (4) only then a cross-family judge in both orders; (5) final tie-break on smallest diff.
- Tests written by the same model that wrote the patch share its blind spots (correlated errors, section 1), so cross-family test writing is the most defensible use of a second model in selection.

### Gaps
- No source found measuring cross-family test generation versus same-model tests for patch selection on security fixes.

## 4. Running several models in Ollama on 4 GB VRAM: load costs, settings, batching, alternatives

### Takeaway
Only one 2.7 GB Q4 model fits in 4 GB VRAM with its KV cache, so Ollama will evict and reload on every model change; the cost is the load (a few seconds from NVMe or from the Windows file cache, tens of seconds from an HDD) plus losing the warm state. Batch all work for one model, then switch once; pass keep_alive 0 on the last call of a batch to free VRAM and the server's RAM.

### Cited Findings
- Ollama defaults: models stay loaded 5 minutes; `keep_alive: 0` in the API, or `ollama stop <model>`, unloads at once; the API value overrides `OLLAMA_KEEP_ALIVE`. — [Ollama FAQ](https://docs.ollama.com/faq)
- `OLLAMA_MAX_LOADED_MODELS` default is 3 x number of GPUs (3 for CPU); `OLLAMA_NUM_PARALLEL` default 1; `OLLAMA_MAX_QUEUE` default 512 (503 when full). With GPU inference a new model must fully fit in VRAM to load alongside others; if memory is short, new requests queue and idle models are unloaded to make room. Parallel requests multiply context (KV cache) size. — [Ollama FAQ](https://docs.ollama.com/faq)
- KV cache quantisation: `OLLAMA_KV_CACHE_TYPE` = f16 (default), q8_0 or q4_0, needs flash attention, and is global to all models. — [Ollama FAQ](https://docs.ollama.com/faq)
- Load time depends on storage: one hosting benchmark (process start to first served request) gives an 8B INT4 model 3 s from NVMe, 12 s from SATA SSD, 28 s from HDD, and a 38 GB 70B model 10 s / 72 s / 195 s. — [gigagpu benchmark page](https://gigagpu.com/?p=13020) (vendor blog, methodology unclear)
- Another guide: 70B loads in about 6 s from Gen4 NVMe against about 85 s from a USB 3.0 SATA SSD. — [runaihome](https://runaihome.com/blog/ollama-change-model-storage-location-free-c-drive-2026/) (blog)
- Slow first answers are often cold starts after the 5-minute unload. — [DEV Community, 2026](https://dev.to/jovan_chan_9500711396d4e6/ollama-keeps-reloading-the-model-fix-vram-unloading-cold-starts-and-model-swapping-2026-25b7) (blog)
- llama.cpp `llama-server` router mode: start with no model, `--models-dir` for the folder, `--models-max` for how many stay loaded (default 4, 0 unlimited), `--models-autoload` loads on demand, `--models-preset` INI for per-model settings; one user runs `--models-max 1` so a request for another model evicts the current one first, warning that two models loaded together can overcommit VRAM and freeze the machine. — [llama-server reference (Mintlify mirror of ggml-org docs)](https://www.mintlify.com/ggml-org/llama.cpp/api/tools/llama-server); [glukhov.org guide](https://glukhov.org/llm-hosting/llama-cpp/llama-server-router-mode/)
- llama-swap (a proxy that starts and stops one llama-server per model) was not covered by the search; a commenter suggested router mode makes it unnecessary for single-machine use (opinion). — [glukhov.org guide](https://glukhov.org/llm-hosting/llama-cpp/llama-server-router-mode/)
### Inferences
- Project context from the brief and project notes (not a public source): qwen3.5:9b with `--num-gpu 20` (partial CPU offload) runs at about 7 tok/s on this laptop, against 46 tok/s for Qwen3.5-4B fully on GPU.
- Per-switch cost estimate for a 2-3 GB GGUF on this laptop (computed here, not measured): about 1-3 s to read from an NVMe SSD, about 15-25 s from a 100-150 MB/s HDD, near zero disk time when Windows still has the file in its page cache (16 GB RAM can hold one or two such files), plus CUDA context and graph setup of a few seconds. Measure with `ollama ps` and the `load_duration` field that Ollama returns in each `/api/generate` response.
- Interleaving models per task (Qwen, Gemma, Qwen, Gemma...) on 27 tasks with 5 samples each would cost up to about 270 switches; batching by model costs one switch per model per run. Order work as: all Qwen samples for all tasks, save, unload; all model-B samples, save, unload; then the judge or test-writer pass.
- On GPU the FAQ already says a second model must fit fully in VRAM to load beside the first, so on 4 GB Ollama will evict anyway. `OLLAMA_MAX_LOADED_MODELS=1` is still a cheap guard, mainly for partly offloaded models (such as a 9B judge with `--num-gpu 20`), where my guess (unverified) is that Ollama could otherwise keep two models' CPU-side weights resident. Keep `OLLAMA_NUM_PARALLEL=1` so the KV cache is not multiplied. Neither setting is shown to fix the earlier commit-memory failure; unloading with keep_alive 0 at the end of each batch is the more direct way to cap the server growth seen while a model stays loaded.
- CPU offload of a 7-9B model (7 tok/s) is about 6x slower than the 4B on GPU; a 9B judge reading a patch and writing a short verdict is affordable, a 9B generator producing five patches per task is not.
- Time loads from wherever the server actually reads the models (the project notes say OLLAMA_MODELS points at a missing D: folder while the tray app still serves models), and do not move models to C:, per the project's storage rule.

### Gaps
- No Windows-specific Ollama load-time measurement for 2-4 GB GGUFs on an RTX 3050 was found; the numbers above are vendor or blog figures for other hardware.
- No official Ollama or llama.cpp benchmark of swap cost was found.
- llama-swap documentation was not read.

## 5. Open-source agents that use two models, and measured effects

### Takeaway
Aider's architect/editor is the only widely measured two-model design, and its only locally runnable pair (QwQ-32B + Qwen2.5-Coder-32B, 74%) is far bigger than 4 GB VRAM allows. Agentless uses one model for every stage; DEI and CodeMonkeys combine whole systems built on hosted models. No measured two-small-local-model agent result was found.

### Cited Findings
- Aider architect/editor results and same-model gains, see section 2. — [aider architect](https://aider.chat/2024/09/26/architect.html); [aider QwQ](https://aider.chat/2024/12/03/qwq.html); [aider R1+Sonnet](https://aider.chat/2025/01/24/r1-sonnet.html)
- Aider leaderboard rows for architect mode are system results, so the model label needs checking before comparing (search summary). — [aider R1+Sonnet](https://aider.chat/2025/01/24/r1-sonnet.html)
- A user report (not a benchmark) describes running architect mode at home with Ollama DeepSeek-R1 7B and Qwen2.5-Coder 7B. — [DEV Community](https://dev.to/sikamikanikobg/testing-aider-practical-experience-with-different-models-58f2) (anecdote)
- Agentless: single model, three-phase pipeline (localisation, repair, patch validation), 32.00% on SWE-bench Lite (section 3). — [arXiv 2407.01489](https://arxiv.org/abs/2407.01489)
- DEI committee over several agents, +7 points absolute over the best open-source agent on SWE-bench Lite. — [arXiv 2408.07060](https://arxiv.org/abs/2408.07060)

### Inferences
- The aider same-model architect gain suggests a cheap first experiment needs no second model: Qwen as planner (thinking on, plain-language fix plan) then Qwen as editor (thinking off, edit only). Compare against current single-pass Qwen at equal sample count.

### Gaps
- OpenHands and SWE-agent were not checked for documented two-model local setups (budget); I found no measured result for them with two small local models.

## 6. Statistics with 27 and 10 tasks

### Takeaway
On 27 tasks one model's pass rate has a standard error of about 9-10 points. An exact McNemar test at p < 0.05 needs a net margin (tasks only the ensemble solves minus tasks only the baseline solves) that rises from 6 (6-0) to 10 (14-4) as the number of such split tasks grows from 6 to 18; on 10 tasks only a near-sweep can show anything. Compare paired per task, with equal sample budgets, and repeat runs to average out sampling noise.

### Cited Findings
- Paired standard error for two models on the same questions is the SE of the per-question score difference divided by sqrt(n), smaller than the unpaired SE when the two models' per-question scores are positively correlated; questions sharing a source should use clustered SEs, which on popular evals can be over 3x the naive SE (Nov 2024). — [Miller, Adding Error Bars to Evals, arXiv 2411.00640](https://arxiv.org/pdf/2411.00640); [Anthropic summary](https://www.anthropic.com/research/statistical-approach-to-model-evals)
- Position paper: do not use central-limit-theorem error bars on LLM evals with fewer than a few hundred items (2025). — [arXiv 2503.01747](https://arxiv.org/pdf/2503.01747) (found, not read)
- A Python package, errorbars, implements CLT and clustered SEs, paired variance reduction and power analysis. — [PyPI errorbars](https://pypi.org/project/errorbars/)
- Large Language Monkeys reports coverage rising log-linearly with sample count, which is why a union of more samples always looks better. — [arXiv 2407.21787](https://arxiv.org/abs/2407.21787)

### Inferences
- Computed here: binomial SE of a pass rate on 27 tasks is 9.6 points at 45% and 9.0 points at 67%; on 10 tasks it is about 15 points. The measured 45% to 67% gain (pass@1 to pass@5) is about 2 SEs on 27 tasks, but pass@5 is a union, so it is guaranteed to be at least pass@1 and is not a fair "improvement".
- Computed here, exact two-sided McNemar at p < 0.05 by number of discordant tasks (tasks where exactly one system succeeds): 6 discordant need 6-0; 9 need 8-1; 12 need 10-2; 15 need 12-3; 18 need 14-4. So the needed net margin is 6 (6-0), 7 (8-1), 8 (10-2), 9 (12-3), 10 (14-4); on 10 tasks, at least 6-0 among the split tasks.
- Union bias: per-task union of model A and model B (k samples each) must be compared with 2k samples of the better model alone, per task, paired. Use the unbiased pass@k estimator from n > k samples rather than one run of k, which lowers run-to-run noise.
- Practical protocol: run each arm 3 times (different seeds) at equal sample budget, report the per-task success rate for each arm, test with a paired sign test or McNemar on tasks that differ, and treat any net gain under 6 to 10 tasks out of 27 (depending on how many tasks split) as not shown. Pre-register the comparison (which arms, which budget) before running, since trying several mixes and reporting the best inflates false positives.
- With only 10 real-CVE tasks, use them as a sanity check (does the mix ever solve one Qwen never solves?) rather than as evidence of a rate change.

### Gaps
- No source found on power analysis specific to pass@k or union comparisons with this few tasks; the thresholds above are my own exact-binomial computation.
