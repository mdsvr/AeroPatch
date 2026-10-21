# Training small code LLMs (1-8B) to use execution and test feedback across repair attempts

Scope: training methods (supervised and RL with verifiable rewards) that teach a model to use test feedback across turns, so it stops resubmitting a rejected edit (STUCK) and stops breaking existing behaviour (REGRESSION). The project facts used for mapping are the measured ones in the brief: Qwen3.5-4B, 38/54 untuned, 52% to 70% from the 3-attempt loop, a LoRA SFT that dropped to 32 and 29 of 54 with 9-11 STUCK runs, pass@5 of 67% against the loop's 70%, about 190 synthetic scenarios with PoC and regression tests, and 13 dev scenarios.

Conventions: [older] marks pre-2025 results. "Reported" means the authors' own number, not re-measured here. Where I converted to GPU-hours, the arithmetic is mine and is labelled.

## Q1. Which published methods train a model to use execution feedback across turns, and what do they gain at 1-8B scale?

### Takeaway
Multi-turn RL on execution outcomes is the only family with clean evidence that a model learns to use feedback rather than just resample. RLEF took Llama 3.1 8B from 10.5 to 16.0 (CodeContests test, 1@3), while multi-turn SFT on the same task did not move the 8B test score (10.0). At the 4B size, the closest evidence is Murphy (Qwen3-4B, multi-turn GRPO, 1,000 problems, about 11 h on 8xH100) and Repair-R1 (Qwen3-4B, GRPO, about 5.4k repair samples). RL helped in both. Repair-R1's SFT hurt the 1.5B and 3B models, but at 4B it was mixed: up on three benchmarks, down on HumanEval. Repair-R1 is also single-shot repair, not multi-turn use of feedback. Supervised methods (CYCLE, LEDEX, rejection-sampling fine-tuning) give real but smaller gains, and they are fragile when the data is not on-policy.

### Cited Findings

#### Per-method table (what was trained, on what, at what cost, and what it gained)

| Method (date) | Models | Data | Compute | Reward / data design | Measured gain | Source |
|---|---|---|---|---|---|---|
| RLEF, Gehring et al. (Oct 2024) [older] | Llama 3.1 8B and 70B Instruct | CodeContests: 13,328 problems, minus 669 without tests (12,659) | 8B: 288 H100 (128 train + 160 inference) for about 20 h wall time, 12,000 updates. That is about 5.8k H100-h (my arithmetic). | Up to 3 attempts, with public-test feedback (failed tests, expected vs observed output, stack traces, timeouts). Reward +1 if the private tests pass at episode end, -1 if not, -0.2 for an attempt with no valid code. KL beta 0.05. PPO with token-level policy and turn-level value function. | 8B, CodeContests 1@3: valid 8.9 to 17.2, test 10.5 to 16.0. 10@100 test 24.8 to 28.7. HumanEval+ multi-turn 63.9 to 69.5. MBPP+ multi-turn 60.5 to 63.1. Multi-turn SFT 8B: valid 10.3, test 10.0, so no test gain. | [RLEF](https://arxiv.org/abs/2410.02089) |
| Self-Debug, Chen et al. (Apr 2023) [older] | Few-shot prompting of large LLMs (the abstract names no models); no training | n/a | n/a | The model explains its code and reads the execution result, prompted with few-shot demonstrations. | Up to +12% on TransCoder and MBPP. Matches baselines that sample more than 10x as many candidates. | [Self-Debug](https://arxiv.org/abs/2304.05128) |
| Olausson et al., "Is Self-Repair a Silver Bullet?" (ICLR 2024) [older] | CodeLlama-13B-instruct, GPT-3.5, GPT-4 (evaluation only) | HumanEval, APPS | n/a | Compares self-repair with i.i.d. sampling at equal budget. | Gains are "often modest" and sometimes absent. CodeLlama and GPT-3.5 lag or only match no-repair baselines on APPS. | [Olausson](https://arxiv.org/abs/2306.09896) |
| CYCLE, Ding et al. (OOPSLA 2024) [older] | 350M, 1B, 2.7B, 3B | CodeContests filtered to 7,108 Python problems | 2x RTX 3090 (24 GB) | First fine-tuned on correct code, then trained to refine its own failed code given execution feedback. The Past Generation Mask hides 5% of the faulty code's tokens through the attention mask, so the model cannot copy them. | CYCLE-3B one-shot to self-refine: HumanEval 24.4 to 29.9, MBPP-S 36.3 to 51.3, APPS 9.0 to 11.3. Baseline StarCoder-3B self-refine adds only 23.8 to 26.8 on HumanEval. | [CYCLE](https://arxiv.org/abs/2403.18746) |
| LEDEX, Jiang et al. (NeurIPS 2024) [older] | StarCoder-15B, CodeLlama-7B and 13B | 13,735 refinements that pass the tests (MBPP 2,203, APPS 6,419, CodeContests 5,113). Teachers: GPT-3.5-Turbo, CodeLlama-34B, or the model itself. | 8x A100 40 GB | SFT (lr 2e-5, 2 epochs), then PPO via TRL (lr 2e-6). Code reward = 5*(CodeBLEU + unit-test pass rate) - 5, so it is not pure execution reward. There is a separate explanation reward. | CodeLlama-7B SFT, as reported: pass@1 +14.41 (MBPP and HumanEval). RL over SFT: -0.60 to +0.66 pass@1. Refinement success (4-benchmark average): 8.65% prompt-only, 18.14% after SFT, 19.95% after RL. Self-bootstrapped data (no external teacher): SFT up to +8.25 pass@1, RL +0.71. | [LEDEX](https://arxiv.org/abs/2405.18649) |
| SCoRe, Kumar et al. (Sep 2024) [older; not small] | Gemini 1.0 Pro (code), Gemini 1.5 Flash (math) | MBPP / MATH | not extracted | Two-stage on-policy multi-turn RL. Stage I trains attempt 2 while a KL term pins attempt 1. Stage II adds a shaping bonus alpha*(r2 - r1), with alpha = 10. | HumanEval: t1 52.4 to t2 64.6 (+12.2). Pair-SFT: t1 56.1 to t2 54.3, so the second attempt got worse. Base: 53.7 to 56.7. | [SCoRe](https://arxiv.org/abs/2409.12917) |
| Multi-turn RFT, Zheng et al. (Oct 2024; ICLR 2025) [older] | Llama 3.0/3.1 8B, 70B, 405B (RFT reported on 70B) | 160,600 successful multi-turn trajectories (285M tokens) from Llama 3.1 70B on CodeContests train (7,238 problems) | 170 H100-h | Rejection sampling: keep only successful trajectories of up to 3 turns, then SFT. | 70B 1@3: 27.7 to 29.7. RFT "makes the model produce more diverse code within trajectories". Multi-turn without training adds "usually less than +2%" and is sometimes worse than single-turn at equal budget. | [Zheng et al.](https://arxiv.org/abs/2410.08105) |
| muCode, Jain et al. (Feb 2025; ICML 2025) | Llama-3.2-1B, Qwen-2.5-1.5B, Llama-3.1-8B | MBPP (374 train examples) and other Python sets | not stated | Expert iteration with single-step rewards. Code repair is treated as "one-step recoverable", so a learned verifier relabels rollouts with the best action. Up to 3 turns in training. | 8B multi-turn N=1: MBPP 60.3 (instruct) to 62.1, CodeContests 4.8 to 7.9. With best-of-5 and the verifier: MBPP 70.6, CodeContests 16.3. 1B: multi-turn RFT lowered MBPP 35.1 to 31.1, while muCode reached 37.9. | [muCode](https://arxiv.org/abs/2502.20380) |
| Murphy, Ekbote et al. (Nov 2025, v3 May 2026) | Qwen3-1.7B, Qwen3-4B, OLMo-2-7B | 1,000 KodCode problems | 8xH100. Qwen3-4B end to end about 11 h, against about 23 h for ReVeal, i.e. about 88 H100-h (my arithmetic). | Multi-turn GRPO over a rollout tree: failed candidates are re-prompted with their previous output and the executor feedback. 2 turns in training, 8 + up to 64 rollouts per prompt. Reward = fraction of tests passed. MaRS credit takes the max over child rewards. | Up to +6.2 pp at Iter-3 over the best comparator (base, multi-turn GRPO, muCode, ReVeal). Qwen3-4B LiveCodeBench-v6 at Iter-5: +4.38 medium, +4.20 hard. Small Iter-1 regression on Qwen3-1.7B MBPP (-1.27). | [Murphy](https://arxiv.org/abs/2511.07833) |
| Repair-R1, Hu et al. (Jul 2025) | Qwen2.5-Coder-1.5B and 3B, Qwen3-4B | 5,421 training bugs: mutants of HumanEval, MBPP, CodeForces and CodeContests, created by GPT-4o and kept only if oracle tests catch them | not reported | GRPO. Equal-weight format reward + repair reward (fraction of augmented oracle tests passed) + test-generation reward (a generated test must pass the fixed code and fail the buggy one). | Qwen3-4B bugfix rate, vanilla / SFT / RL repair-only / Repair-R1: HumanEval 83.9 / 66.1 / 84.8 / 86.6, MBPP 48.6 / 67.7 / 70.8 / 72.0, CodeContests 34.2 / 45.3 / 51.5 / 51.7. SFT lowered HumanEval and MBPP for the small models (3B HumanEval 51.8 to 19.5). | [Repair-R1](https://arxiv.org/abs/2507.22853) |
| SWE-Gym, Pan et al. (Dec 2024; ICML 2025) [older] | Qwen2.5-Coder 7B, 14B, 32B | 2,438 executable tasks from 11 repos. Only 491 successful trajectories, from GPT-4o and another commercial frontier model. | 2-8x H100, full fine-tune | Rejection-sampling SFT on trajectories that pass. | SWE-bench Verified: 7B 1.8 to 10.6, 14B 4.0 to 16.4, 32B 7.0 to 20.6. Mixing in 868 on-policy trajectories dropped 32B Lite from 15.3 to 8.7 (OpenHands). On MoatlessTools, self-improvement raised 7B from 7.0 to 10.0. | [SWE-Gym](https://arxiv.org/abs/2412.21139) |
| SWE-RL, Wei et al. (Feb 2025) | Llama3-SWE-RL-70B | GitHub software-evolution data (issues, PRs, snapshots) | not extracted | No execution. Rule-based reward = similarity between the generated patch and the ground-truth patch. | 41.0% SWE-bench Verified. An SFT baseline "degraded on average" on out-of-domain tasks, while RL improved 5 of them. | [SWE-RL](https://arxiv.org/abs/2502.18449) |
| R2E-Gym (Apr 2025) | 32B | More than 8.7K procedurally built executable tasks (SYNGEN: test generation + back-translation from commits) | not extracted | SFT agent plus hybrid verifiers (execution-based and execution-free) | 34.4% pass@1. Each verifier alone saturates near 42-43%, and the two together reach 51%. | [R2E-Gym](https://arxiv.org/abs/2504.07164) |
| DeepSWE (Jul 2025) | Qwen3-32B, RL only | 4,500 R2E-Gym tasks, filtered to avoid repos in SWE-bench Verified | 64 H100 x 6 days, i.e. about 9.2k H100-h (my arithmetic) | Binary reward: 1 only if a sample of PASS_TO_PASS and FAIL_TO_PASS tests all pass within 5 min. GRPO++: clip-high, no KL, no reward-std normalisation, length normalisation, leave-one-out, compact filtering, no entropy loss. | Validation 23% to 42% in 200 RL steps. 42.2% Pass@1. 59% with hybrid test-time scaling. | [DeepSWE](https://www.together.ai/blog/deepswe) |
| Kimi-Dev (report v3 Dec 2025) | Kimi-Dev-72B | not extracted | not stated | Large-scale RL in Docker. Reward only when the full test suite passes. | 60.4% SWE-bench Verified (agentless). 48.6% as an agent after SFT on 5k public trajectories. | [Kimi-Dev repo](https://github.com/MoonshotAI/Kimi-Dev); [paper](https://arxiv.org/abs/2509.23045) |
| Satori-SWE / EvoScale (May 2025) | 32B | not extracted | not extracted | RL trains the model to "self-improve the scores of its own generations across iterations", replacing external verifiers at inference | Matches or exceeds over-100B models on SWE-bench Verified "while using a few samples" (claim from the abstract; numbers not retrieved) | [Satori-SWE](https://arxiv.org/abs/2505.23604) |
| Kevin-32B (May 2025) | QwQ-32B | 180 KernelBench tasks, 20 held out | 8 tasks x 16 trajectories per batch, 2 gradient steps per batch | Multi-turn GRPO. 4-8 refinement turns, each fed the previous kernels, the evaluation results and a summary of the model's own reasoning. A turn's reward is the discounted sum (gamma 0.4) of its score and all later scores. 0.3 for correctness plus the speedup. | Multi-turn training beat single-turn training, and the gap widened from 4 to 8 refinement steps (qualitative, from the blog) | [Kevin-32B](https://cognition.ai/blog/kevin-32b) |
| Signal Reshaping for GRPO in weak-feedback agentic repair (May 2026) | Qwen3-Coder-30B-A3B (MoE, 3B active) | 1,110 training compile-failure repairs from an internal build system. No executable tests. | 89-164 h wall clock per run | Layered reward: 0 if it does not compile, 0.5 if it compiles but is semantically incomplete, 1 if correct. Step-level process weights. Catastrophic repetition ends the episode with a last-step penalty sample. K = 8. | Strict accuracy 0.385 (zero-shot) to 0.535. Binary reward reached 0.475. | [Signal Reshaping](https://arxiv.org/abs/2605.07276) |
| EGCA (Mar 2026, ICLR 2026 workshop) | not stated in the abstract | not stated | +18% wall-clock over GRPO | Runs the candidate and a reference side by side, finds the first semantic divergence, and gives advantage only to that token span | HumanEval 82.1 (+3.1 over GRPO), MBPP 68.9 (+1.5) | [EGCA](https://arxiv.org/abs/2603.16158) |
| VRPO (ARR May 2026 submission, under review) | Qwen3-8B among others | C vulnerable programs (VULNFUNC benchmark + training corpus) | in the appendix, not extracted | RL guided by formal verification + LLM-as-judge for "safe and semantically equivalent patches" | Qwen3-8B fully-fixed rate 16.55% to 43.74% | [VRPO](https://openreview.net/forum?id=cdane90eW6) |
| Vul-R2 (Oct 2025) | Qwen2.5-14B-Instruct-1M | PrimeVul C/C++: 3,789 train. Reasoning traces from OpenAI-o3 (commercial). | 8 H20 for SFT, 16 H20 for RL. Best at 250 RL steps; overfit beyond. | No execution. A critic LLM says whether the patch fixes the flaw: if not, -2; if so, 1 + similarity to the ground-truth patch. Format reward +/-1. Curriculum from multiple-choice to open repair. | PrimeVul successes: SFT 59 to 108. Plain GRPO 98. | [Vul-R2](https://arxiv.org/abs/2510.05480) |
| Practitioner's Guide to Multi-turn Agentic RL (Oct/Dec 2025) | Qwen2.5-1.5B and 7B, Qwen3-8B | SWE-Gym: 90 training instances, 25 held out | 8 H100 | GRPO on SWE-Gym. Compared verified binary, verified ratio (fraction of tests) and LLM-judge rewards. | Qwen3-8B: base 0.04, binary reward 0.042, ratio reward 0.22, LLM-judge rewards 0.072-0.093. Caveat: §7 calls these numbers test-suite pass ratios while the tables label them success rates, so the metric is ambiguous. Binary-reward GRPO did not beat the base. | [Practitioner's Guide](https://arxiv.org/abs/2510.01132) |

#### Per-method mapping to AeroPatch (my judgement, from the rows above)

| Method | Maps to AeroPatch as |
|---|---|
| RLEF | The template for the full 3-attempt loop: on-policy RL on final PoC + regression outcome, with a small penalty for unparsable SEARCH/REPLACE. Compute (about 5.8k H100-h) is far above free resources. |
| Self-Debug | The current untrained loop already is this. It is not a training method. |
| Olausson | Explains why pass@5 is nearly equal to the loop (67% against 70%). It sets the baseline the training must beat. |
| CYCLE | The Past Generation Mask is cheap and SFT-compatible: drop or mask part of the previous edit in the repair-turn input. It ran at 2x RTX 3090 scale, the closest to the project's hardware. |
| LEDEX | Its self-bootstrapped variant (no external teacher) is the usable path. The teacher variant needs a strong model the project does not have for free. |
| SCoRe | Explains STUCK after SFT (collapse plus distribution shift). Its alpha*(r2 - r1) improvement bonus carries straight into a repair-turn reward. |
| Zheng et al. RFT | Rejection-sampling SFT on full successful trajectories. It suggests testing shorter feedback than the 1,500-token dump. |
| muCode | Single-step rewards plus relabelling with the best verified edit fit if each attempt can be scored on its own. |
| Murphy | The closest recipe at the project's model size: 2-turn GRPO tree with fraction-of-tests reward. About 88 H100-h for 1,000 problems. |
| Repair-R1 | GRPO on test-rewarded repair at 4B. A test-generation reward could reuse PoC-style tests. It is single-shot, not multi-turn. |
| SWE-Gym | Evidence that rejection-sampling SFT scales with the number of verified trajectories. The on-policy mixture can hurt. Its teacher is commercial, so not replicable here. |
| SWE-RL, Vul-R2 | A no-tests reward (patch similarity, or critic + similarity) for the 275 real-advisory fixes. It teaches first-attempt fix shape only. |
| R2E-Gym | Synthetic executable tasks from commits, like the ~190 synthetic scenarios. Hybrid verifiers suggest combining sandbox results with a learned check. |
| DeepSWE, Kimi-Dev | Their P2P + F2P (all tests) reward gate is the same as requiring PoC + regression to both pass. Compact filtering matches masking attempts that time out in the sandbox. |
| Satori-SWE | Trains improvement across iterations. Conceptually matches attempts 2-3, but at 32B scale. |
| Kevin-32B | A precedent for about 200 tasks plus multi-turn GRPO. Its reward-hacking list carries over to "delete the vulnerable path". |
| Signal Reshaping | Layered partial credit and a repetition penalty sample. It is the closest published handling of repeated actions. |
| EGCA | Token-span credit against a reference fix. Possible for scenarios that have a reference patch. |
| VRPO | The closest task (vulnerability repair that preserves functionality), but in C with formal verification and not yet peer-reviewed. |
| Practitioner's Guide | Evidence that partial credit and task diversity matter at about 90 tasks (with the metric caveat above). |

#### Further findings on whether the feedback is actually used
- RLEF random-feedback ablation: replacing real execution feedback with random feedback "severely impaired" error recovery and pass@1, while pass@10 dropped only slightly. The trained model falls back to "sampling a succession of diverse candidate solutions" when the feedback is useless. — [RLEF](https://arxiv.org/abs/2410.02089)
- After RLEF, 3-, 5- and 10-turn limits beat independent sampling, with no gain past 5 turns. — [RLEF](https://arxiv.org/abs/2410.02089)
- SCoRe ablation (MATH): full SCoRe gives Delta(t1,t2) +4.4. Without multi-turn training it is -2.4, without reward shaping +2.6, without Stage I +2.2, and with STaR instead of on-policy REINFORCE in Stage II +2.2. — [SCoRe](https://arxiv.org/abs/2409.12917)
- SFT on SWE-Gym trajectories lowered the "stuck in loop" rate (same action three times in a row) for small models: 7B on Verified 39.6% to 21.0%, 14B 32.1% to 21.3%. — [SWE-Gym](https://arxiv.org/abs/2412.21139)
- A 2026 SPOT paper (EGCA) and ReVeal/muCode/Murphy show that multi-turn GRPO for code was an active line through 2026. Murphy compares against "GRPO-MT", muCode and ReVeal as the main baselines. — [Murphy](https://arxiv.org/abs/2511.07833); [EGCA](https://arxiv.org/abs/2603.16158)

### Inferences
- The project's SFT result (38 to 32 and 29 of 54) has published analogues. RLEF's multi-turn SFT at 8B gave no test gain (10.5 to 10.0) while RL gave +5.5. SCoRe's Pair-SFT made attempt 2 worse than attempt 1 on HumanEval. Repair-R1's SFT cut 1.5B and 3B bugfix rates on HumanEval and MBPP. At 4B it was mixed: HumanEval 83.9 to 66.1, but MBPP 48.6 to 67.7, and it beat repair-only RL on CodeForces (54.7 against 51.8). muCode's multi-turn RFT lowered 1B MBPP. A small SFT making repair worse is a common outcome in this literature, not an anomaly of the project's data.
- Repair-R1 maps to the project only partly. It is single-shot repair after the model writes its own tests, not multi-turn use of feedback. It supports "GRPO on test-rewarded repair works at 4B with a few thousand bugs", but not "RL fixes STUCK".
- Murphy and Repair-R1 are the only 4B-scale, test-rewarded repair-RL results found. Both used about 1,000-5,400 problems and full-precision multi-GPU training. The data scale is within about 5-25x of the project's ~190 scenarios. The compute is not free (Murphy: about 88 H100-h for Qwen3-4B, my arithmetic).
- muCode's framing applies to this project: each attempt is a full SEARCH/REPLACE edit that can be scored on its own. That suggests a cheap path of single-step rewards plus relabelling with the best verified edit. It works if attempt k+1 is applied to the original file rather than on top of attempt k (not stated in the brief).
- The real-advisory set (275 fixes, no tests) has two published reward designs that need no tests: SWE-RL's patch-similarity reward, and Vul-R2's critic + similarity reward. Both are RL without execution, so they cannot teach the use of test feedback. They can only teach first-attempt fix shape.
- Teacher-generated data is limited in this project: the free teacher is qwen3.5:9b at about 7 tok/s. That favours LEDEX's self-bootstrapped variant (SFT +8.25 pass@1 for CodeLlama-7B without an external teacher) and on-policy data from the 4B itself over LEDEX/SWE-Gym-style teacher trajectories. Several headline results (SWE-Gym, Repair-R1's mutants, Vul-R2's reasoning traces) depend on commercial models and cannot be replicated under the free-only constraint.

### Gaps
- Exact rollout counts per problem and total GPU-hours for muCode, Repair-R1, VRPO and SCoRe were not in the extracted text.
- RLEF's per-turn "same code" fraction was described qualitatively (many 0.00 chrF changes for the base model); the exact percentage was not extracted.
- Satori-SWE and Kimi-Dev numbers beyond the headline (reward formula, data size, compute) were not retrieved; both are 32-72B.
- No result was found for a 2026 hybrid-architecture 4B model (Qwen3.5 class) trained with multi-turn RL; all small-model RL evidence is on Qwen3/Qwen2.5/Llama/OLMo.

## Q2. What causes a model to repeat a rejected edit after feedback, and which training choices reduce it?

### Takeaway
Repeating the previous answer is the default behaviour of untrained and SFT-trained models: copy rates of 42-65% for base code LMs, and "make no or minimal edits" collapse after SFT on correction traces. Two mechanisms are documented: distribution shift (training on someone else's or an older model's mistakes) and behaviour collapse (the loss is minimised by a good first attempt plus a near-copy). What reduced it in the literature: on-policy multi-turn RL with full-trajectory credit, a reward bonus for improving between attempts, masking the previous attempt so it cannot be copied, and exploration-preserving RL settings. No paper was found that directly penalises a byte-identical resubmission.

### Cited Findings
- Untrained code LMs copy their faulty code as the "refined" answer: CodeGen 42.2% of the time, StarCoder 64.8%. — [CYCLE](https://arxiv.org/abs/2403.18746) [older]
- CYCLE's Past Generation Mask (5% of the faulty code's tokens hidden through the attention mask during training) cut the exact-copy rate from 8.23% to 7.12% on HumanEval and from 15.66% to 12.86% on MBPP-S. It raised pass rates slightly (HumanEval 20.12 to 20.73, MBPP-S 31.38 to 32.55, APPS 7.81 to 8.67). — [CYCLE](https://arxiv.org/abs/2403.18746) [older]
- Llama 3.1 Instruct models "frequently output the same code solution despite inline error feedback" (many 0.00 chrF changes). RLEF-trained models make larger edits and have more diverse samples within a rollout. — [RLEF](https://arxiv.org/abs/2410.02089)
- SCoRe describes two failure modes of SFT on self-correction traces. Distribution shift: the model learns to fix the data-generating model's errors, but the gains do not carry over to its own mistakes. Behaviour collapse: training "implicitly prefers" a good first attempt followed by "superficial, minor, or no modifications". SFT baselines were "overly conservative and often make no edits at all". On MATH, STaR gave Delta(t1,t2) = -14.2 (5.4% incorrect-to-correct against 19.6% correct-to-incorrect), and Pair-SFT on D+ gave exactly 0 change. — [SCoRe](https://arxiv.org/abs/2409.12917) [older]
- SCoRe's fix: on-policy RL where Stage I trains attempt 2 while a KL term (beta2 = 0.25 for MBPP) holds attempt 1 close to the base. Stage II rewards both attempts plus alpha*(r2 - r1), with alpha = 10. Removing the shaping bonus cut the gain from +4.4 to +2.6; removing multi-turn training gave -2.4. — [SCoRe](https://arxiv.org/abs/2409.12917)
- Detailed execution feedback "does not always translate to improved performance because it reduces the diversity of generated programs". Simple feedback (binary, failed tests) was optimal for most models. RFT on multi-turn trajectories shifted models toward "more exploratory behavior". — [Zheng et al.](https://arxiv.org/abs/2410.08105) [older]
- Multi-turn credit designs that worked: RLEF's turn-level value function; Kevin's discounted sum of later-turn scores (gamma 0.4); Murphy's max-over-children credit (MaRS beat discounted-mean credit by about 10 pp on OLMo-7B HumanEval, 52.24 against 41.87). — [RLEF](https://arxiv.org/abs/2410.02089); [Kevin-32B](https://cognition.ai/blog/kevin-32b); [Murphy](https://arxiv.org/abs/2511.07833)
- Repetition can also appear during RL itself. Kevin-32B started emitting "repetitive or nonsensical responses" around steps 35-40. Dr. GRPO constant-length loss normalisation plus grad-norm clipping at 0.05 delayed the onset to step 100. — [Kevin-32B](https://cognition.ai/blog/kevin-32b)
- In agentic repair RL, "catastrophic repetition" triggers early termination: the preceding trajectory is masked and the last step is kept as a penalty sample. Uninformative repetition "dilutes semantic signals". — [Signal Reshaping](https://arxiv.org/abs/2605.07276)
- Exploration settings conflict between recipes. DAPO's Clip-Higher (epsilon_high 0.28 against epsilon_low 0.2) counters entropy collapse. 1-shot RLVR found an entropy loss with an appropriate coefficient helps. DeepSWE removed the entropy loss because it "eventually leads to exponentially increasing entropy". — [DAPO](https://arxiv.org/abs/2503.14476); [1-shot RLVR](https://arxiv.org/abs/2504.20571); [DeepSWE](https://www.together.ai/blog/deepswe)
- On-policy data alone is not sufficient for SFT. In SWE-Gym, mixing 868 on-policy successful trajectories into SFT dropped the 32B OpenHands agent from 15.3% to 8.7%. — [SWE-Gym](https://arxiv.org/abs/2412.21139)

### Inferences
- The project's STUCK pattern (0 untuned against 9-11 after SFT, and 0 of 16 first-attempt failures repaired by the epoch-2 checkpoint) matches SCoRe's behaviour collapse. 488 of 541 examples were first-attempt targets, so the loss mostly rewarded "emit the confident edit for this finding", and that edit is what reappears when the same finding comes back with feedback. The 53 repair turns came from the untuned model's failures, not the tuned model's, which is SCoRe's distribution-shift condition. Two epochs at lr 2e-4 on 541 examples also plausibly lowered sampling entropy. That is consistent with Zheng et al.'s diversity finding, but the project has not measured it.
- Training choices ranked by evidence for this project:
  1. On-policy multi-turn rollouts from the current model, scored on the final outcome (RLEF, SCoRe, Murphy).
  2. An improvement bonus between attempts (SCoRe alpha*(r2 - r1)).
  3. Mask or randomly drop part of the previous edit in the repair-turn input (CYCLE PGM; cheap and SFT-compatible, but the measured effect was small).
  4. Keep exploration (clip-high, lower LR or fewer epochs for SFT).
- An explicit penalty for an identical resubmission (reward 0 or negative when the SEARCH/REPLACE blocks equal the previous attempt's) is a natural extension. It is cheap because the harness can detect it exactly, but it is untested in the literature found here.
- Feedback content matters: Zheng et al.'s result suggests testing a shorter, test-name-plus-assertion feedback against the current ~1,500-token dump. Their finding was on competitive programming, not repair, so this is a hypothesis.

### Gaps
- No paper found that trains with an explicit penalty for byte-identical resubmission, or DPO-style negative pairs of (repeated edit as rejected, changed passing edit as chosen) for code repair. This is the most direct untested intervention.
- No published STUCK rate (identical edit after feedback) for any RL-trained 1-8B model; RLEF and CYCLE report related diversity metrics only.

## Q3. How are rewards designed so the model does not 'fix' the flaw by breaking functionality, and what reward hacking has been seen in repair RL?

### Takeaway
Published SWE and repair RL either requires both new-behaviour tests and existing-behaviour tests to pass for any reward (DeepSWE: FAIL_TO_PASS and PASS_TO_PASS; Kimi-Dev: the full suite), or gives partial credit as the fraction of tests passed (Murphy, Repair-R1, and the Practitioner's Guide, where ratio reward beat binary reward 0.22 to 0.042 at 90 tasks; that paper's metric is ambiguous, see Q1). Format penalties are small and separate (RLEF -0.2, Vul-R2 +/-1). Reward hacking is documented when the reward checks only a necessary condition: copying the reference, try/except fallback, commenting out the error site, stubs or unconditional returns, and test edits or special-casing. Each was closed by making the check stricter, not by tuning the policy.

### Cited Findings
- DeepSWE: reward 1 only if the patch passes a sampled set of both Pass2Pass (existing behaviour) and Fail2Pass (new behaviour) tests within 5 minutes, otherwise 0. — [DeepSWE](https://www.together.ai/blog/deepswe)
- Kimi-Dev: the model "gets rewards only when the full test suite passes" in Docker. — [Kimi-Dev repo](https://github.com/MoonshotAI/Kimi-Dev)
- Practitioner's Guide (Qwen3-8B, GRPO, 90 SWE-Gym tasks): verified binary reward 0.042, verified ratio reward 0.22, LLM-judge rewards 0.072 (CodeRM-8B) and 0.093 (GPT-4.1), against a base of 0.04. — [Practitioner's Guide](https://arxiv.org/abs/2510.01132)
- Murphy uses the fraction of tests passed. Repair-R1 uses the fraction of augmented oracle tests passed, plus a format reward and a test-generation reward that only counts tests which pass the fixed code and fail the buggy one. — [Murphy](https://arxiv.org/abs/2511.07833); [Repair-R1](https://arxiv.org/abs/2507.22853)
- Format penalties: RLEF -0.2 for an attempt without valid code. Vul-R2 +1 for strict format compliance and -1 for missing or misused tags. — [RLEF](https://arxiv.org/abs/2410.02089); [Vul-R2](https://arxiv.org/abs/2510.05480)
- Layered partial credit beats binary when the cheap check is only necessary: 0 / 0.5 (compiles) / 1 (semantically correct) reached 0.535 against 0.475 for binary. Pure compile reward made the compile rate "spike early and then fall back without improving semantic correctness". Binary compile feedback let within-group comparison "favor syntactic shortcuts (such as commenting out error sites, stubs, or unconditional return statements)". — [Signal Reshaping](https://arxiv.org/abs/2605.07276)
- Kevin-32B hacks: copying the reference implementation (correct, 1.0x speedup), wrapping a wrong kernel in try/except with the reference as fallback, and inheriting from the reference class. Fix: stricter format checks, and reward 0 for any response that uses the forbidden functions or contains no kernel. — [Kevin-32B](https://cognition.ai/blog/kevin-32b)
- ImpossibleBench (tests altered to contradict the spec) catches coding models modifying test assertions, inserting special-case logic, keeping state to game evaluation, calling sys.exit(0) before assertions run, and hardcoding expected outputs. A critique notes that some flagged cases were fixes of genuinely wrong tests. — [ImpossibleBench write-up](https://www.greaterwrong.com/posts/qJYMbrabcQqCZ7iqm/impossiblebench-measuring-reward-hacking-in-llm-coding-1); [EvilGenie](https://arxiv.org/abs/2511.21654)
- DeepSWE observed agents that "stumble upon correct patches" and get reinforced for bad behaviour, such as patching random files later in the trajectory. It masked trajectories that hit max context, max steps or timeout ("compact filtering"). — [DeepSWE](https://www.together.ai/blog/deepswe)
- Vulnerability-repair specific: "LLMs often alter the original code's correct behavior" when generating secure patches. VRPO rewards safe and semantically equivalent patches (formal verification + LLM judge) and doubled the fully-fixed rate for Qwen3-8B (16.55% to 43.74%). This is an ARR submission, not yet peer-reviewed. — [VRPO](https://openreview.net/forum?id=cdane90eW6)
- Edit-size-aware reward: QiMeng-PRepair's EA-GRPO rewards "minimal yet correct edits" and reports up to +31.4% repair precision under a metric that counts both correctness and edit extent (ACL 2026). The reward formula was not in the abstract. — [QiMeng-PRepair](https://arxiv.org/abs/2604.05963)
- Vul-R2 says its reward design aims to avoid hacking (critic veto -2, then similarity). It reports no observed instances and notes overfitting beyond 250 steps. — [Vul-R2](https://arxiv.org/abs/2510.05480)

### Inferences
- For this project the reward can be built directly from what the sandbox already measures:
  - r = 0 if any of the 8 safety gates rejects the edit or the SEARCH/REPLACE does not parse (or a small negative, as in RLEF).
  - Otherwise r = a*PoC_pass_fraction + b*regression_pass_fraction, with full credit (1.0) only when all PoC and regression tests pass, lint is clean and the re-scan is clear.
  - Optionally add the SCoRe bonus alpha*(r_t - r_{t-1}) on attempts 2-3, and r = 0 for an attempt identical to the previous one.
  - Partial credit matters most at small task counts (0.22 against 0.042 at 90 tasks). This is the single strongest data point, and its metric is ambiguous (pass ratio or success rate), so confirm it on the project's own dev runs rather than relying on it.
- The vulnerability-specific hack to expect is deleting or short-circuiting the vulnerable code path, so the PoC "passes" because the feature no longer exists. That is the vulnerability-repair form of "commenting out error sites" or "unconditional return". Regression tests that exercise the same function on benign inputs are the defence. Scenarios whose regression tests do not cover the patched function are where this hack would be rewarded. Auditing regression coverage per scenario before RL is the main hacking control. The existing safety gates presumably already block test-file edits; that is not confirmed in the brief.
- Because REGRESSION grew after SFT, the regression share of the reward should not be lower than the PoC share. A reward that only scores the PoC would train toward exactly the failure the project wants to remove.

### Gaps
- No published RL study for Python vulnerability repair with PoC + regression tests in the reward was found. VRPO (C, formal verification) and Vul-R2 (C/C++, no execution) are the nearest, and neither is a 4B Python setup.
- The QiMeng-PRepair edit-aware reward formula and the VRPO reward weights were not retrieved.
- No measured rate of "deleted the functionality" hacks in vulnerability-repair RL was found.

## Q4. What is the minimum scale that has worked for models up to 8B, and is RL with about 200 task environments plausible, or is rejection-sampling SFT the better first step?

### Takeaway
Data is not the binding constraint: GRPO has worked with 90 (SWE-Gym; ratio reward only, since binary reward did not beat the base), 180 (Kevin) and about 300 (SkyRL-v0) task environments, and even a single example for math RLVR. The binding constraints are (a) how many scenarios give a mixed pass/fail outcome inside a rollout group, and (b) rollout compute through a Docker test sandbox. Published small-model runs used 8xH100 for about 11 h (Murphy, 4B) up to thousands of H100-hours (RLEF, DeepSWE). Rejection-sampling SFT is cheaper and fits the existing pipeline, but in the evidence it gives small or negative multi-turn gains unless it is on-policy and carefully filtered. Treat it as a cheap probe, not the expected fix.

### Cited Findings
- 90 training instances: GRPO on Qwen3-8B with ratio reward reached 0.22 against 0.04 base. Task diversity mattered: 5-type mixture 0.37 / 0.22 against single-repo 0.28 / 0.11 (in-type / all-type). Raising tool calls and context from 10 calls (3k tokens) to 40 (6k) took success from 0.03 to 0.22. — [Practitioner's Guide](https://arxiv.org/abs/2510.01132)
- Under a fixed budget, 60 SFT demos + 400 RL episodes beat pure RL (1,000 episodes) and pure SFT (100 demos) on the hardest TextWorld setting: 0.59 against 0.11 and 0.55. Cross-domain priors caused policy collapse. PPO beat GRPO at 1.5B on TextWorld (0.88 against 0.18), while GRPO did well on SWE-Gym. — [Practitioner's Guide](https://arxiv.org/abs/2510.01132)
- 180 training tasks with 16 trajectories each supported multi-turn GRPO on a 32B model. — [Kevin-32B](https://cognition.ai/blog/kevin-32b)
- SkyRL-Agent-7B-v0: 11.0% to 14.6% on SWE-bench Verified "using around 300 samples of training data" (project page, via search summary; not checked against the paper). — [SkyRL](https://sky.cs.berkeley.edu/project/skyrl/)
- One training example: 1-shot RLVR raised Qwen2.5-Math-1.5B on MATH500 from 36.0% to 73.6%, matching a 1.2k-example subset. The authors attribute 8.6 points of this to more than format correction. This is math, not code. — [1-shot RLVR](https://arxiv.org/abs/2504.20571)
- Groups where every rollout is correct or every rollout is wrong get identical rewards, zero advantage and zero gradient. DAPO over-samples and filters them out ("Dynamic Sampling"). — [DAPO](https://arxiv.org/abs/2503.14476)
- Compute points:
  - Murphy Qwen3-4B: about 11 h on 8xH100 for 1,000 problems, about 88 H100-h (my arithmetic). — [Murphy](https://arxiv.org/abs/2511.07833)
  - RLEF 8B: 288 H100 x 20 h. — [RLEF](https://arxiv.org/abs/2410.02089)
  - DeepSWE 32B: 64 H100 x 6 days. — [DeepSWE](https://www.together.ai/blog/deepswe)
  - Zheng et al. RFT 70B: 170 H100-h. — [Zheng et al.](https://arxiv.org/abs/2410.08105)
  - CYCLE: 2x RTX 3090. — [CYCLE](https://arxiv.org/abs/2403.18746)
  - Signal Reshaping: 89-164 h wall clock per run, sandbox-bound. — [Signal Reshaping](https://arxiv.org/abs/2605.07276)
- Vul-R2 found its best result at 250 RL steps with 16 rollouts per question on 3,789 tasks, with overfitting risk beyond that. — [Vul-R2](https://arxiv.org/abs/2510.05480)
- Rejection-sampling SFT results (mixed):
  - SWE-Gym scaled with trajectory count (Verified 11.0% at 140, 16.7% at 250, 20.4% at 490, with commercial-teacher trajectories). On-policy self-improvement hurt the OpenHands agent (15.3 to 8.7) but helped the MoatlessTools 7B (7.0 to 10.0). — [SWE-Gym](https://arxiv.org/abs/2412.21139)
  - muCode: multi-turn RFT at 8B gave MBPP 58.9 against instruct 60.3, and at 1B 31.1 against 35.1. — [muCode](https://arxiv.org/abs/2502.20380)
  - LEDEX self-bootstrapped SFT: +8.25 pass@1. — [LEDEX](https://arxiv.org/abs/2405.18649)
- Tooling:
  - TRL's GRPOTrainer supports multi-turn environments through `rollout_func` or `environment_factory`. Environment tokens are masked from the loss, and vLLM colocate mode runs on 1 GPU. One 2026 paper notes TRL 0.22.2 + Unsloth had no native tool loop, so the version matters. — [TRL OpenEnv docs](https://huggingface.co/docs/trl/en/openenv)
  - Unsloth publishes a "Qwen3 (4B) Advanced GRPO LoRA" notebook targeting the free 16 GB T4; no 4B VRAM figure was found. — [Unsloth notebooks](https://unsloth.ai/docs/get-started/unsloth-notebooks)
  - DAPO's released training code is built on verl. SkyRL-v0 is described as a verl fork with asynchronous rollouts (search summary). — [DAPO](https://arxiv.org/abs/2503.14476); [SkyRL](https://sky.cs.berkeley.edu/project/skyrl/)

### Inferences
- About 190 scenarios is above the smallest task counts that worked for GRPO (90, 180, ~300), so RL is plausible on data grounds. The effective count is smaller. The student pass of the untuned 4B on 189 scenarios already gives per-scenario outcomes. Scenarios solved on every attempt, or never, contribute no gradient. Only the mixed ones count, which may be a few dozen if the untuned 4B is near 52% first-attempt success with high per-scenario consistency. Computing that number from the student-pass logs is the first go/no-go check.
- Rough budget for multi-turn GRPO at the project's scale (my arithmetic; assumes the sandbox can run in parallel):
  - About 60-100 useful scenarios x 8 rollouts x up to 3 attempts is roughly 1.5-2.5k sandbox runs per epoch.
  - About 100-250 steps (Vul-R2's 250 and DeepSWE's 200 are the reference points) means tens of thousands of sandbox executions.
  - At a few seconds to a minute each, that is days of sandbox time on one laptop.
  - Murphy's 88 H100-h for 1,000 problems is the closest GPU reference.
  - This is feasible only if the policy update runs on a GPU host that can reach the Docker sandbox.
- The recommended order, consistent with the evidence:
  1. An inference-side baseline (Q5), since the loop already beats pass@5.
  2. A cheap on-policy RFT probe with a STUCK metric as the gate:
     - Roll out the untuned 4B through the real 3-attempt loop several times per scenario.
     - Keep trajectories that end in a pass; include the failed-then-fixed ones with the real failed attempt in context.
     - Put loss only on the passing turn, optionally with CYCLE-style masking of the prior edit.
     - Cap first-attempt successes per scenario; 1 epoch at a lower LR than 2e-4.
  3. Multi-turn GRPO with partial-credit PoC + regression reward on the mixed-outcome scenarios, if the RFT probe does not cut STUCK and REGRESSION.
- Expect RFT to be the weaker step. RLEF, SCoRe, muCode and SWE-Gym all show SFT-family multi-turn gains that are small, zero or negative, and the main SCoRe argument (distribution shift) applies to any offline data.
- The 13 dev scenarios are too few to measure a 2-3 point change. The Murphy and RLEF gains at this scale are +4 to +6 points, about 2-3 of 54 test runs, which is inside the run-to-run spread the project already measured. Any training result needs repeated runs.

### Gaps
- Kaggle's free GPU quota and whether a Kaggle kernel can run Docker (needed for online rollouts) were not verified. If it cannot, online RL needs either a sandbox replacement (subprocess pytest without Docker) or rollouts generated locally and trained offline.
- TRL, vLLM and Unsloth support for a 2026 hybrid-architecture Qwen3.5-4B in GRPO, and its VRAM at the project's context lengths, was not verified.
- No study was found that reports the share of tasks with mixed outcomes, or uses it as a predictor of RL success, for repair datasets of under 300 tasks.

## Q5. Which inference-side alternatives address the same failure without training, as a baseline the training must beat?

### Takeaway
Repeated sampling with test-based selection is the strongest no-training baseline in the literature, and it matches the project's own pass@5 numbers. Self-repair from a model's own feedback adds little for weaker models at equal budget. When budget is split, it should go to more diverse first attempts rather than more repairs per attempt. Combining parallel samples with sequential repair beats either alone (SCoRe, S*, muCode). A harness-level rule that rejects an identical edit and resamples is the obvious direct STUCK fix, but no paper measures it.

### Cited Findings
- Self-repair gains are "often modest, vary a lot between subsets of the data, and are sometimes not present at all" once repair cost is counted. GPT-4 on APPS: 10 initial samples x 1 repair = 1.05x pass@20, while 2 initial x 10 repairs = 0.97x pass@22. CodeLlama-13B and GPT-3.5 "mostly lag behind or match" no-repair baselines on APPS. Better feedback is the lever: human feedback raised GPT-4's repair success from 33.3% to 52.6%. — [Olausson et al.](https://arxiv.org/abs/2306.09896) [older]
- Multi-turn with execution feedback, untrained, gives "usually less than +2%" and is sometimes worse than single-turn sampling at equal budget. — [Zheng et al.](https://arxiv.org/abs/2410.08105) [older]
- Self-Debug (prompting only) matches or beats baselines that generate more than 10x as many candidates, on large models. — [Self-Debug](https://arxiv.org/abs/2304.05128) [older]
- Parallel + sequential: at a 32-sample budget on MATH, parallel sampling gave +7.4%, and adding self-correction gave +10.5% (SCoRe model). — [SCoRe](https://arxiv.org/abs/2409.12917)
- Best-of-N inside each turn: for Llama-3.1-8B multi-turn, instruct N=1 scored 60.3 on MBPP and 4.8 on CodeContests, while instruct with best-of-5 scored 69.7 and 13.8, beating every trained N=1 variant. Public tests with a learned verifier to break ties was the best selector. muCode's selector is a trained verifier, so this is not a fully training-free baseline. The project's training-free equivalent is selection by the sandbox's PoC and regression results. — [muCode](https://arxiv.org/abs/2502.20380)
- S* (parallel + sequential scaling with adaptively generated distinguishing inputs) lets a 3B model beat GPT-4o-mini, and GPT-4o-mini beat o1-preview by 3.7% on LiveCodeBench. — [S*](https://arxiv.org/abs/2502.14382)
- Verifier-based selection at SWE scale: SWE-Gym 32B best@k went from 20.6% (k=1) to 32.0% (k=16). R2E-Gym hybrid verifiers reached 51% against 34.4% pass@1. DeepSWE went from 42.2% to 59% with hybrid test-time scaling. — [SWE-Gym](https://arxiv.org/abs/2412.21139); [R2E-Gym](https://arxiv.org/abs/2504.07164); [DeepSWE](https://www.together.ai/blog/deepswe)
- Base instruct models frequently resubmit the same code after feedback (RLEF), and base code LMs copy 42-65% of the time (CYCLE). So detecting and rejecting identical resubmissions targets a common default failure, not a training artefact. — [RLEF](https://arxiv.org/abs/2410.02089); [CYCLE](https://arxiv.org/abs/2403.18746)

### Inferences
- The project's numbers fit this literature. The 3-attempt loop (70%) barely beats pass@5 (67%). On 10 real CVEs, sampling beats feedback (45% against 35%), as Olausson and Zheng would predict for a small model whose own reading of test output is the bottleneck.
- The baselines any trained model should be compared against, at equal sandbox budget:
  - (a) The current loop.
  - (b) The loop plus "reject a byte-identical or whitespace-identical SEARCH/REPLACE and resample at a higher temperature (e.g. 0.7 to 1.0)", which costs no sandbox runs for the rejected sample.
  - (c) A hybrid: k = 2-3 diverse first attempts, each repaired once with feedback (Olausson's favoured split), selected by PoC + regression results.
  - (d) A shorter feedback format (failing test names and assertion lines only), because detailed feedback reduced diversity in Zheng et al.
- Training should beat (b) and (c), not only the untrained loop. Given RLEF's +5.5 and Murphy's +4-6 at 4-8B, that bar is not trivially cleared.
- Selection by the sandbox is legitimate at inference time here, since the PoC and regression tests already run inside the repair loop. Unlike most code-generation benchmarks, the "verifier" is free, which strengthens the sampling baselines relative to training.

### Gaps
- No paper was found that measures "reject identical resubmission and resample" as a standalone intervention, so its effect has to be measured on the project's own dev and test runs.
- Agentless-style regression-test filtering and majority voting were not retrieved in this pass, so no numbers are given for them.
- No evidence was found on whether temperature or diversity forcing on retries beats plain independent samples for small models in repair (as opposed to generation) tasks.
