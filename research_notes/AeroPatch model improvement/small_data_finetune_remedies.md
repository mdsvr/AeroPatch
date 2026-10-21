# Why small-data LoRA SFT makes a strong 4B instruct model worse, and the remedies that have been measured

Scope: mechanisms behind a fine-tune scoring below its untuned base on the task it was tuned for (AeroPatch: Qwen3.5-4B, 541 examples, LoRA r=16/alpha=16, lr 2e-4, 2 epochs; test 38 -> 32 / 29 of 54, STUCK 0 -> 9-11), and remedies with numbers. Dating convention: findings from 2023-2024 are marked [older]. Blog and vendor guidance is marked [opinion/practitioner]. All else is a measured result from the cited paper.

## Q1. What mechanisms explain a fine-tune scoring below its base on the task it was tuned for?

### Takeaway
The best-supported 2025-2026 explanation is distribution shift from off-policy targets. Forgetting tracks the KL divergence between the tuned and base model on the new task's own inputs, and SFT on targets the model would not have written moves it much further than on-policy training does. Two older mechanisms add to it. Offline training on correction pairs collapses retries into "make no or minimal changes", which matches STUCK. Fitting examples the model cannot already solve ("Unknown" knowledge) raises hallucination once they are memorised. LoRA does not protect a post-trained model from losing its post-training behaviours.

### Cited Findings
**Distribution shift / KL (newest evidence)**
- RL's Razor (Shenfeld, Pari, Agrawal, Sep 2025):
  - Forgetting is predicted by the forward KL between the fine-tuned and base policy, measured on the new task's distribution. A quadratic fit gives R^2 = 0.96 +/- 0.01 in a toy setting and R^2 = 0.71 in the LLM experiments.
  - Weight-change measures predict forgetting far worse: L1 R^2 = 0.34, Fisher-weighted L2 R^2 = 0.58.
  - LLM experiments used Qwen 2.5 3B-Instruct (plus 7B/14B), on math, science QA and tool use.
  - "SFT can converge to distributions arbitrarily far from the base model", whereas on-policy RL is biased toward KL-minimal solutions.
  - [Source](https://arxiv.org/html/2509.04259)
- Retaining by Doing (Chen, Razin, Narasimhan, Chen; Oct 2025, ICML 2026). Models: Llama-3.2-1B, Llama-3.1-8B, Qwen-2.5-1.5B and Qwen-2.5-7B Instruct, with SFT targets taken from Llama-3.3-70B.
  - "Gain" is the target-task improvement. "Drop" is the average fall on the other tasks.
  - Llama-3.1-8B-Instruct:

    | Target | SFT gain / drop | GRPO gain / drop |
    |---|---|---|
    | IFEval | +25.2 / -27.8 | +18.4 / -3.4 |
    | MMLU | +11.1 / -38.5 | +14.6 / +0.2 |
    | Countdown | +25.5 / -36.4 | +60.4 / +0.5 |

  - Qwen-2.5-7B-Instruct, Countdown target: SFT +10.4 / -29.2, GRPO +29.2 / +0.3.
  - AlpacaEval win rate of Llama-3.1-8B-Instruct (base 41.6) after SFT on IFEval / MMLU / Countdown falls to 23.5 / 11.6 / 0.0. After RL on the same targets it stays at 43.1 / 41.2 / 42.0.
  - The authors attribute RL's robustness to its use of on-policy data, not to the KL penalty or advantage estimation.
  - [Source](https://arxiv.org/html/2510.18874v3)
- Mitigating Forgetting via Low-Perplexity Token Learning (Wu et al., Jan 2025, rev. Dec 2025; Gemma 2 IT 2B, Llama 3 8B Instruct and three more models):
  - Fine-tuning on LLM-generated data degrades non-target tasks less than fine-tuning on ground truth.
  - The benefit comes from fewer high-perplexity tokens.
  - Masking the high-perplexity tokens in ground-truth data gives similar preservation.
  - Numbers were not on the abstract page.
  - [Source](https://arxiv.org/abs/2501.14315)
- [older] I Learn Better If You Speak My Language (EMNLP 2024; Mistral-7B-Instruct-v2, Llama2-13b-chat, about 1,000 training examples per task):
  - LLM-generated responses have lower perplexity under the student before training than human responses do.
  - Training sets with higher perplexity consistently give lower performance.
  - Mistral on GSM8K: 0.434 with human targets vs 0.597 with GPT-4 targets.
  - MBPP: 0.276 with human targets vs 0.354.
  - [Source](https://arxiv.org/html/2402.11192)
- [older] Learning Dynamics of LLM Finetuning (Ren & Sutherland, ICLR 2025) gives a mechanistic account of two failure types strengthened by finetuning [Source](https://openreview.net/forum?id=tPNHOoZFl9):
  - using phrases or facts from the answer to question B when answering question A;
  - repeating similar simple phrases.

**Loss of retry / self-correction behaviour (directly relevant to STUCK)**
- [older] SCoRe, "Training Language Models to Self-Correct via RL" (2024; Gemini 1.0 Pro for code, 1.5 Flash for MATH). Results on MATH, two attempts:
  - Base: Acc@t1 52.6, Acc@t2 41.4.
  - STaR on self-generated corrections (D_StaR+): 53.6 -> 54.0. Incorrect-to-correct 2.6%.
  - Pair-SFT D_SFT+: 55.0 -> 55.0, with 0% of answers changed in either direction.
  - Models SFT'd on offline revision traces "are overly conservative and often make no edits at all". Offline methods also suffer a shift between the data-collection policy's mistakes and the model's own.
  - [Source](https://arxiv.org/html/2409.12917)
- [older] RLEF (Gehring et al., Oct 2024; Llama 3.1 8B/70B, CodeContests, 3 attempts with execution feedback):
  - Instruct models "perform only minimal code edits and frequently output the same code solution despite inline feedback pointing out errors".
  - 8B solve rate, test (11@33): Instruct 10.5, SFT 10.0, RLEF 16.0. The paper's Table 3a and 3b SFT variants differ, and the extraction was ambiguous about which SFT row is which.
  - Random feedback severely hurts the RLEF model, which shows it actually reads the feedback.
  - [Source](https://arxiv.org/html/2410.02089)

**New knowledge -> hallucination**
- [older] Gekhman et al. (2024; PaLM 2-S, closed-book QA). Examples are classed by whether the model can already produce the answer: Known (HighlyKnown / MaybeKnown / WeaklyKnown) vs Unknown.
  - Unknown examples are learned significantly slower than Known ones. Once learned, they linearly increase hallucination.
  - With early stopping, training on all data D is almost identical to training on D_Known. At convergence, D underperforms D_Known, with a gap proportional to the Unknown ratio.
  - D_MaybeKnown gives the best overall result, better than D_HighlyKnown.
  - [abs](https://arxiv.org/abs/2405.05904); [html](https://arxiv.org/html/2405.05904v3)

**LoRA does not prevent forgetting of post-training behaviour**
- [older] LoRA Learns Less and Forgets Less (Biderman et al., 2024; Llama-2-7B, about 100K code IFT pairs):
  - LoRA forgets less than full FT. Average of HellaSwag/ARC/WinoGrande at epoch 16: full FT 0.414 vs LoRA r=64 0.509.
  - LoRA also learns less. HumanEval at epoch 4: r=16 0.358, full FT 0.470.
  - Full FT shows "distribution collapse": fewer unique generations than the base, with LoRA in between.
  - [Source](https://arxiv.org/html/2405.09673v2)
- [opinion/practitioner, with measured table] Thinking Machines "On-Policy Distillation" (Oct 2025):
  - On post-trained Qwen3-8B, "LoRA learns less (knowledge) and still forgets its original post-training behaviors".
  - Mid-training on 100% domain documents dropped IF-eval from 85% to 45%.
  - [Source](https://thinkingmachines.ai/blog/on-policy-distillation/)
- [older] LoRA vs Full Fine-tuning: An Illusion of Equivalence (Shuttleworth et al., 2024):
  - LoRA creates "intruder dimensions" (new high-rank singular vectors). Intruder count correlates with forgetting (Spearman 0.971 on RoBERTa) but not with test accuracy.
  - Low rank, and a fixed alpha instead of alpha = 2r, give more intruders and more forgetting.
  - At larger learning rates LoRA forgot more than full FT.
  - [Source](https://arxiv.org/html/2410.21228v3)

**How Qwen small models were made**
- Qwen3 report (May 2025): Qwen3-0.6B to 14B were built by Strong-to-Weak Distillation, in two phases:
  - off-policy distillation;
  - on-policy distillation, where the student samples its own responses and its logits are aligned to Qwen3-32B or 235B-A22B by minimising KL.
  - On Qwen3-8B, on-policy distillation reached AIME'24 74.4 vs 67.6 for RL, at 1,800 vs 17,920 GPU hours (Table 21).
  - [Source](https://arxiv.org/html/2505.09388v1)

### Inferences
- **Transfer assumption, stated plainly.**
  - Almost every forgetting number above measures non-target tasks. AeroPatch loses on its own target task.
  - The step being assumed is that "forgetting" here is the base's pre-existing repair skill, a post-training behaviour from Qwen's distillation, being overwritten by off-policy targets that teach a worse version of the same task.
  - The closest published analogue is an on-target, below-base result: Olmo-3-7B-Think with answer-only SFT fell from 31.2 to 23.5 on its own target, and on-policy SDFT raised it to 43.7 ([Source](https://arxiv.org/html/2601.19897)).
  - Caveat: that drop was partly a reasoning-format mismatch (answer-only targets for a thinking model). AeroPatch's v1-to-v2 history (copying finding text, editing only inside function bodies) shows a similar format-imitation effect.
- **Dominant mechanism.** The likeliest cause for AeroPatch is off-policy edit tokens, not epochs or overfitting.
  - 275 of the 541 targets are upstream human commit diffs, and 105 more are written by a different model (9B).
  - Only the RATIONALE line is in the 4B's own words, and the SEARCH/REPLACE tokens dominate the loss.
  - Under RL's Razor and Retaining by Doing, this is the profile that maximises KL shift per example.
  - The checkpoints at 32, 64 and 128 steps scoring the same fits this. The shift happens in the first ~256 examples, before any late memorisation phase.
- **STUCK is predicted by the 53 repair turns.**
  - Each pairs the untuned model's failed attempt and the feedback with a corrected fix.
  - Per the project design (docs/09-dataset-curation.md and the architecture doc, section 11), that fix is the scenario's reference "correct fix", not the 4B's own successful retry. So the pair is off-policy.
  - This is the offline-correction setup SCoRe shows collapses into "no edits" (Pair-SFT: 0% of answers changed). RLEF reports the same "repeat the same code" pattern in 8B Instruct models.
  - The conclusion does not depend on who wrote the fix: SCoRe's self-generated corrections (D_StaR+) also collapsed, changing only 2.6% of answers from incorrect to correct.
  - Untuned AeroPatch had 0 STUCK, so the training data, not the base, most plausibly introduced it.
- **REGRESSION is plausibly a "new knowledge" effect** (Gekhman):
  - Real advisory fixes often depend on project-specific context, a design choice or a behaviour change the 4B cannot infer from the scoped context, so they are Unknown examples for it.
  - Fitting them teaches it to make confident edits it cannot justify, which a regression suite catches.
  - Gekhman measured this for QA facts, not code. Applying it to code is an inference.
- **Qwen3-family small models sit on a teacher-shaped, on-policy-distilled mode.** That makes them unusually sensitive to SFT on text from outside that mode. This is consistent with the Qwen3 report but not tested in it, and the Qwen3.5 report was not found.
- **The LoRA setting is not a safety margin.** It is r=16 with alpha=r, rather than the alpha=2r both Biderman and Shuttleworth recommend. The Thinking Machines result shows LoRA on a post-trained Qwen3-8B still erases post-training behaviour.

### Gaps
- No source measures off-policy vs on-policy SFT for code repair on a 4B model with a sandbox verifier. All forgetting evidence is from math, QA, instruction following and tool use.
- Qwen3.5 small-model post-training details were not found (the search returned the Qwen3 report only).
- **Possible confound, not from the literature: a chat-template mismatch between Unsloth training and Ollama serving.** Qwen3/3.5 in non-thinking mode emits an empty think block, and a difference in how the two templates handle it could alone cost accuracy. A second, untested confound is Q4_K_M quantisation of a merged LoRA delta.

## Q2. Self-distillation and on-policy data: what gains do they show for 1-8B models, and do they avoid the drop below base?

### Takeaway
On-policy or self-written targets consistently cut the forgetting caused by SFT, often by a factor of 2-10. They do not guarantee staying above the base:
- SDFT on code data still left the seed model's off-target average lower, although the code metric itself rose.
- SFT on a model's own samples at a default learning rate still forgets.
- One code-agent attempt at self-improvement (SWE-Gym) lost accuracy.

The most robust results come from methods that stay on-policy throughout training (RL, on-policy distillation, 2026 on-policy SDFT), not from a one-shot dataset of self-generated text.

### Cited Findings
**[older] SDFT, rewrite targets in the model's own words** (Yang et al., ACL 2024). The seed model rewrites each reference answer under a task-independent template. Setup: Llama-2-7b-chat, LoRA r=8 on q/v only, lr 1e-4 cosine, 2-5 epochs.
- OpenFunctions, seed vs vanilla FT vs SDFT:

  | | OpenFunctions | GSM8K | HumanEval | Avg |
  |---|---|---|---|---|
  | Seed | 19.6 | 29.4 | 13.4 | 20.8 |
  | Vanilla FT | 34.8 | 21.5 | 9.8 | 22.0 |
  | SDFT | 36.6 | 29.1 | 15.2 | 27.0 |

- MagiCoder code data (2,000 examples), the case closest to AeroPatch:
  - The target code metric rose under both methods: HumanEval went from 13.4 (seed) to 18.9 with vanilla FT and to 18.3 with SDFT.
  - The off-target tasks fell. With vanilla FT, OpenFunctions dropped 19.6 -> 3.6 and GSM8K 29.4 -> 23.2, for a 3-task average of 15.2 vs seed 20.8.
  - SDFT's 3-task average was 17.1, still below seed. That gap is off-target forgetting, from a seed that was weak at code.
- AlpacaEval win rate (seed 66.0) after OpenFunctions: vanilla 35.5, SDFT 67.7.
- [Source](https://arxiv.org/html/2402.13669)

**2026 on-policy SDFT, "Self-Distillation Enables Continual Learning"** (Shenfeld, Damani, Hübotter, Agrawal; Jan 2026).
- How it works: the same model, conditioned on the demonstration in context, acts as teacher. Reverse KL is minimised on the student's own samples.
- Qwen2.5-7B, new-task / prior-capability average:

  | Task | Base | SFT | DFT | SDFT |
  |---|---|---|---|---|
  | Tool use | 42.9 / 65.5 | 63.2 / 56.0 | 64.2 / 60.8 | 70.6 / 65.4 |
  | Science Q&A | 32.1 / 65.5 | 66.2 / 53.4 | 54.8 / 60.2 | 70.2 / 64.5 |

- Olmo-3-7B-Think trained with answer-only supervision: base 31.2, SFT 23.5 (below base), SDFT 43.7.
- Scale limit: at 3B the model's in-context learning is too weak and SDFT lags SFT. It beats SFT by about 4 points at 7B and about 7 at 14B.
- Cost: about 2.5x the FLOPs and 4x the wall-clock of SFT.
- [Source](https://arxiv.org/html/2601.19897); code is TRL-based [GitHub](https://github.com/idanshen/Self-Distillation)

**SFT on the model's own filtered samples ("Self-SFT")** (Retaining by Doing, 2025). Self-SFT keeps only correct responses from 5 samples per prompt.
- Llama-3.2-1B-Instruct, drop on other tasks:

  | Target | Self-SFT | SFT on 70B targets | GRPO |
  |---|---|---|---|
  | IFEval | 6.9% | 26.2% | 1.6% |
  | MMLU | 34.6% | 28.9% | 0.3% |
  | Countdown | 25.3% | 24.2% | -0.6% |

  On MMLU and Countdown, Self-SFT forgot as much as SFT on 70B targets, or more.
- Qwen-2.5-1.5B-Instruct, IFEval target: Self-SFT 3.0% drop vs SFT 6.2%.
- At lr 1e-5 instead of 1e-4, "a smaller learning rate reduces forgetting but fails to reach the same target performance even with more epochs".
- "Iterative-SFT" resamples on-policy data at the start of each epoch. It reached target accuracy comparable to or higher than SFT, with mild to no forgetting (numbers only in Figure 7).
- The paper does not state whether LoRA was used.
- [Source](https://arxiv.org/html/2510.18874v3)

**[opinion/practitioner, measured] Thinking Machines** (Oct 2025):
- "Running SFT on top of Qwen3-32B's own samples degrades performance" on IF-eval. The stated reason: every finite batch differs from the model's distribution, so updates drift and the data becomes off-policy over time.
- On-policy distillation from the original Qwen3-8B as teacher restored IF-eval to 83% (from 79%) while keeping the new knowledge (41% vs 18% before).
- The loss is a per-token reverse KL that needs teacher logprobs on student samples.
- [Source](https://thinkingmachines.ai/blog/on-policy-distillation/)

**Rejection-sampling fine-tuning and expert iteration**
- [older] RFT (Yuan et al., 2023; LLaMA-7B, GSM8K):
  - SFT 35.9% vs 49.3% with combined rejection samples from multiple models.
  - Gains grow with the number of distinct correct reasoning paths.
  - RFT brings more improvement to weaker models, and better models improve less as supervised data grows.
  - [Source](https://arxiv.org/abs/2308.01825)
- [older] ReST-EM, "Beyond Human Data" (Singh et al., 2023; PaLM 2-S*/L, 64 samples per APPS problem):
  - Over the base: APPS +5.6 (S*) and +6.4 (L); MATH +5.94 / +6.34. This beats SFT on human-written solutions.
  - APPS regressed in the second iteration.
  - Gains grow with model size, and 1,000 MATH questions already gave significant gains.
  - [Source](https://arxiv.org/html/2312.06585)
- [older] SelfCodeAlign (2024; 3B-33B models, 74k self-generated pairs validated by tests in a sandbox):
  - CodeQwen1.5-7B scored 67.1 HumanEval+ pass@1. Training on GPT-3.5-distilled OSS-Instruct gave 61.6, and Evol-Instruct 59.1.
  - Ablation: a model benefits more from its own data than from a stronger teacher's when the gap between them is small. When the teacher is clearly stronger, distillation wins.
  - [Source](https://arxiv.org/html/2410.24198)
- SWE-Gym (Dec 2024, ICML 2025; Qwen2.5-Coder-Instruct 7B/14B/32B):
  - 491 successful trajectories raised SWE-Bench Verified for 7B from 1.8% to 10.6% and for 32B from 7.0% to 20.6%.
  - It reduced the stuck-in-loop rate by 4.6-18.6 points.
  - Self-improvement failed: adding 868 of the 32B model's own successful trajectories cut SWE-Bench Lite from 15.3% to 8.7%.
  - [Source](https://arxiv.org/html/2412.21139)
- [older] SCoRe, self-generated corrections: STaR on its own correction traces still produced almost no changes on retry (Acc@t1 53.6 -> Acc@t2 54.0). Online multi-turn RL was needed to make the second attempt add accuracy. [Source](https://arxiv.org/html/2409.12917)

### Inferences
**SDFT rewrite (Yang 2024) is the cheapest fit for the current pipeline.**
- The 4B rewrites each of the 541 reference fixes "in its own words" given the reference. The rewrite is kept only if it passes the existing 8 gates plus the sandbox.
- Expected effect is a smaller drop, not a guaranteed gain.
  - On MagiCoder, SDFT matched vanilla FT on the code target (HumanEval 18.3 vs 18.9) and kept more off-target ability (average 17.1 vs 15.2, seed 20.8).
  - That seed was weak at code. There is no published test on a seed that is already strong at the target, which is the AeroPatch case.

**Expert iteration / RFT on own verified successes is the closest match to the "not yet tried" item.**
- Sample k outputs from the untuned 4B per training scenario and keep the ones the sandbox accepts.
- This produces near-zero-KL targets that the sandbox verifies.
- Two cautions apply:
  - Retaining by Doing and Thinking Machines both show that even own-sample SFT forgets at a default learning rate.
  - SWE-Gym's self-improvement attempt lost accuracy.
- So it should be paired with a lower learning rate and few steps (Q3).

**Gekhman supports a known-filtered recipe** (MaybeKnown examples are the most useful; Unknown ones hurt at convergence):
- When the 4B solves a scenario in some but not all of k samples (MaybeKnown), keep its passing sample.
- When it never solves it (Unknown), drop the scenario, or keep only a sandbox-verified SDFT rewrite.

**For STUCK, the evidence says SFT on any correction pairs, self-generated or not, mostly teaches "change nothing".**
- The lowest-risk move is to drop or rebuild the 53 repair turns.
- Teaching actual use of feedback needs online multi-turn RL (SCoRe, RLEF), not SFT.

**On-policy distillation from qwen3.5:9b would follow the Qwen3 and Thinking Machines recipe.** It needs teacher logprobs on 4B samples during training, and a 9B teacher at 16-bit does not fit a T4 beside the student.

**2026 on-policy SDFT is borderline at 4B.** It lagged SFT at 3B and costs 2.5-4x the compute, which makes it a second choice on Kaggle T4 time.

### Gaps
- No paper found that applies RFT or SDFT to vulnerability repair, or to a 3-5B model with a test-suite verifier, and reports the base-vs-tuned delta.
- Exact Iterative-SFT numbers and the lr 1e-5 Self-SFT numbers sit in figures (Figures 3 and 7 of Retaining by Doing) and were not extractable.
- Not verified whether Ollama returns per-token logprobs good enough for distillation. That decides whether a local 9B teacher can serve as the on-policy distillation teacher.
- STaR (Zelikman 2022) and ReST (Gulcehre 2023) were not fetched. Their numbers are on older, non-instruct models.

## Q3. Cheap knobs with evidence: learning rate, epochs, rank, modules, NEFTune, loss masking, replay, interpolation and merging

### Takeaway
Two knobs are measured, directly relevant and cheap:
- **A lower learning rate.** Shown on Qwen3-4B itself, it preserves general ability with a small target cost.
- **Shrinking the LoRA delta at inference.** Done by alpha scaling or interpolating with the base, it needs zero retraining and can cut forgetting by 20-33% at almost no target cost.

Next come replay of on-policy general data and loss reweighting on low-probability tokens (TALR, DFT, perplexity masking). NEFTune has no evidence for code correctness. Epoch count is not the lever here.

### Cited Findings
**Learning rate**
- SFT Doesn't Always Hurt General Capabilities (Sep 2025, ICLR 2026). Full-FT runs on MedCalc and ESCI.
  - Qwen3-4B, standard SFT at lr 1e-6: domain 0.548, general 0.784.
  - Qwen3-4B, standard SFT at lr 5e-6: domain 0.578, general 0.543.
  - Averaged over Qwen2.5-3B, Qwen3-4B and Gemma3-4B, lr 1e-6 vs 5e-6: general 0.692 vs 0.381, domain 0.534 vs 0.558.
  - Conclusion: a smaller learning rate "can substantially mitigate general performance degradation while preserving comparable target-domain performance".
  - [Source](https://arxiv.org/html/2509.20758)
- [opinion/practitioner, measured on loss] LoRA Without Regret (Thinking Machines, Sep 2025):
  - The optimal LoRA LR is about 10x the full-FT LR. It changes by less than 2x between rank 4 and rank 512, and is about 15x for runs under about 100 steps.
  - LoRA matches full FT on small-to-medium SFT datasets.
  - Attention-only LoRA "significantly underperforms" MLP-only, and adding attention to MLP adds nothing.
  - LoRA is less tolerant of large batch sizes.
  - [Source](https://thinkingmachines.ai/blog/lora/)
- [older] Biderman et al. 2024:
  - Best LoRA LR was 5e-4 for code IFT and 2e-4 for math IFT, against full-FT 5e-5 and 1e-5.
  - Recommended practice: target all modules (gains mostly from MLP), alpha = 2r, and sweep LR in [1e-5, 5e-4], taking the highest stable value.
  - This is tuned for learning a new domain on a base model, not for preserving an instruct model.
  - [Source](https://arxiv.org/html/2405.09673v2)
- [opinion/practitioner] Unsloth LoRA guide:
  - LR range 2e-4 to 5e-6, 2e-4 as the start; 1-3 epochs; rank 16 or 32; alpha = r or 2r; all linear layers.
  - "If your training loss drops below 0.2, your model is likely overfitting."
  - Remedies listed: multiply alpha by 0.5, or average the merged model with the original instruct model.
  - Train-on-responses-only masking gives "about 1 percentage point" in the vendor's own measurement.
  - [Source](https://unsloth.ai/docs/get-started/fine-tuning-llms-guide/lora-hyperparameters-guide)

**Scaling the delta / interpolation / WiSE-FT**
- [older] Illusion of Equivalence: scaling only the top intruder dimension by lambda.
  - LLaMA2-7B MetaMath r=256: lambda 0.3 gave accuracy -0.1 and forgetting -33.3%. Lambda 0.5 gave accuracy +1.8 and forgetting -25.2%.
  - Lambda 0.1 cost much more accuracy (-18.7 on MNLI at r=1), and lambda > 1 increased forgetting.
  - [Source](https://arxiv.org/html/2410.21228v3)
- SFT Doesn't Always Hurt: WiSE-FT, base-tuned weight averaging, on Qwen3-4B at lr 5e-6:
  - It kept general at 0.753 (vs 0.543 for standard SFT) but domain fell to 0.382 (vs 0.578).
  - Interpolation trades away much of the target gain.
  - In the same tables, LoRA at full-FT learning rates barely learned the domain (Qwen3-4B 0.237 at 5e-6). This is consistent with LoRA needing about 10x the LR.
  - [Source](https://arxiv.org/html/2509.20758)
- The PEFT LoRA scale is lora_alpha/r, fixed at config time. add_weighted_adapter(weights=[...]) builds weighted combinations, then merge_and_unload() merges them. [Source](https://huggingface.co/docs/peft/main/en/developer_guides/lora)
- llama.cpp loads an adapter at an explicit scale with `--lora-scaled`. [Source](https://www.simplified.guide/llama-cpp/server-set-lora-adapter)
- The Ollama Modelfile page fetched for this note documents no adapter-scale parameter. [Source](https://docs.ollama.com/modelfile)

**Loss reweighting / masking**
- TALR (in SFT Doesn't Always Hurt) down-weights hard tokens with w proportional to p^(1/tau).
  - Average at lr 5e-6: general 0.502 vs 0.381 standard, domain 0.542 vs 0.558.
  - Qwen3-4B at 5e-6: general 0.614 vs 0.543, domain 0.583 vs 0.578.
  - [Source](https://arxiv.org/html/2509.20758)
- Masking high-perplexity ground-truth tokens matches the forgetting reduction of training on LLM-generated data (Gemma 2 2B, Llama 3 8B). [Source](https://arxiv.org/abs/2501.14315)
- DFT as a baseline in the 2026 SDFT paper (Qwen2.5-7B) [Source](https://arxiv.org/html/2601.19897):
  - Tool use: 64.2 new / 60.8 prior, vs SFT 63.2 / 56.0.
  - Science: 54.8 / 60.2, vs SFT 66.2 / 53.4.
  - It preserves more but can learn less.

**Replay of general or on-policy data**
- [opinion/practitioner, measured] Thinking Machines, Qwen3-8B:
  - Mixing 30% of chat data sampled from Qwen3-8B itself into the mid-train kept IF-eval at 79% vs 45% with 100% domain data.
  - Sampling the background data from Qwen3-8B preserved chat better than sampling from Qwen3-32B.
  - [Source](https://thinkingmachines.ai/blog/on-policy-distillation/)
- Spurious Forgetting (ICLR 2025): much of the apparent forgetting is task-alignment loss. Freezing the bottom layers mitigates it. Numbers not fetched. [Source](https://arxiv.org/abs/2501.13453)

**NEFTune** [older]
- Llama-2-7B on Alpaca: AlpacaEval rose from 29.79% to 64.69%. Evol-Instruct, ShareGPT and OpenPlatypus each gained 8-10%.
- All reported gains are on conversational preference, with none shown for code correctness.
- [Source](https://arxiv.org/abs/2310.05914)

### Inferences
**Zero-training first step: an alpha-scaling sweep on the existing v2 adapter.**
- Scale s in {0.25, 0.5, 0.75}. Implement it by setting lora_alpha = s x 16 in adapter_config.json before merging, or with llama.cpp `--lora-scaled`.
- Check `use_rslora` in adapter_config.json first. If it is true, the scale is alpha/sqrt(r) (per the PEFT docs), and lora_alpha = s x 16 still scales the delta by s. Just don't reason about absolute scale as alpha/r.
- Score each on dev and test.
- Because the tuned model is not better than base on any reported metric (dev 26 = 26, test and CVE lower), the sweep is more likely to find a point near base than above it.
- Its value is diagnostic. A monotone curve from base to tuned would confirm that the delta is net-harmful, not that it holds a useful direction plus noise.

**LR:**
- The 10x LoRA-to-full-FT rule plus the measured Qwen3-4B full-FT sweet spot of about 1e-6 to 5e-6 suggests a LoRA LR of about 1e-5 to 5e-5. AeroPatch uses 2e-4, roughly 4-20x higher.
- This is an extrapolation: the 10x rule was measured on loss, not on forgetting.
- Retaining by Doing warns that a lower LR also reaches less of the target gain.

**Rank and alpha:**
- Moving to alpha = 2r (32 at r=16) is the measured recommendation for fewer intruder dimensions.
- Doing so doubles the effective update (scale alpha/r goes from 1 to 2) at a fixed LR.
  - Combined with an LR of 2e-5 to 5e-5, the net reduction is only about 2-5x, not 4-10x.
  - If both change, quote the effective step (LR x alpha/r) rather than the LR alone.
- Lowering the rank is not supported: lower ranks produced more intruders and more forgetting.
- **Attribution on a 54-run eval.** Changing data, LR, alpha and epochs in one run makes the cause unknowable. Change the data first with the other knobs fixed, or run the arms separately.

**Epochs:**
- Flat validation loss from step 32 and equal dev scores at steps 32/64/128 mean fewer epochs will not recover the base.
- Unsloth's own heuristic flags train loss below 0.2 (0.18 here) as overfitting. That is consistent with fitting off-policy tokens, but the damage already exists at step 32.

**Replay:**
- Adding the 4B's own outputs on general or coding prompts (on-policy background data, in the Thinking Machines style) is cheap with Ollama.
- It is measured to protect instruction following on Qwen3-8B. Whether it protects the repair skill is untested.

**NEFTune:** low priority. Its only evidence is chat-quality win rate.

### Gaps
- No measured result found for alpha scaling or WiSE-FT on a code-repair or test-pass metric. All interpolation numbers are general-benchmark retention.
- The full-model alpha-scaling sweep (scaling the whole delta, not just intruder dimensions) has no published LLM numbers in the sources found. Only vendor guidance supports it.
- Qwen3.5-4B is a hybrid architecture, and no source was found on which modules to target in its linear-attention layers.
- Self-Synthesized Rehearsal and other replay papers were not fetched.
- TIES and DARE: no measured single-task recovery result found.
  - Both are designed to combine several task vectors.
  - With a single LoRA delta against its own base, TIES's magnitude trimming and DARE's random drop-and-rescale only sparsify or shrink that one delta. They are a noisier form of the scaling sweep, not a different remedy. This is an inference.

## Q4. Data quality vs quantity: how many examples beat a strong base, and do off-policy human commit diffs hurt?

### Takeaway
No source gives an example count at which code-repair SFT beats an already-strong instruct base. The relevant scaling evidence says the opposite of "more data fixes it":
- Stronger models gain less from more supervised data.
- Self-generated data beats teacher data only when the teacher is not much stronger.
- Human-written targets carry more high-perplexity tokens, which cause forgetting.

Large gains from a few hundred trajectories (SWE-Gym) come from bases that started near zero.

### Cited Findings
- [older] LIMA (2023): a 65B LLaMA tuned on 1,000 curated examples was judged equivalent or preferred to GPT-4 in 43% of cases. Its abstract says almost all knowledge is learned in pretraining, so a small instruction set mainly teaches format. [Source](https://arxiv.org/abs/2305.11206)
- [older] RFT scaling (2023): performance is log-linear in supervised data, and "better models improve less with enlarged supervised datasets". [Source](https://arxiv.org/abs/2308.01825)
- SWE-Gym (2024/2025): 491 trajectories lifted Qwen2.5-Coder-7B from 1.0% to 10.0% on SWE-Bench Lite, a base near zero. Adding 868 self-sampled successes to the 32B lowered Lite from 15.3% to 8.7%. [Source](https://arxiv.org/html/2412.21139)
- [older] SelfCodeAlign: self-generated, test-validated data beats a stronger teacher's data only when the performance gap is small. [Source](https://arxiv.org/html/2410.24198)
- [older] SDFT: 2,000 MagiCoder code examples with vanilla FT pulled Llama-2-7b-chat's 3-task average from 20.8 to 15.2, while HumanEval itself rose from 13.4 to 18.9. The loss was off-target, from a seed weak at code. [Source](https://arxiv.org/html/2402.13669)
- [older] I Learn Better (EMNLP 2024): human-written targets have higher perplexity under the student, and higher-perplexity training sets consistently gave lower accuracy. Mistral-7B on MBPP: 0.276 with human targets vs 0.354 with GPT-4 targets. [Source](https://arxiv.org/html/2402.11192)
- Low-perplexity token learning (2025): the forgetting gap between ground-truth and LLM-generated targets comes from high-perplexity tokens. [Source](https://arxiv.org/abs/2501.14315)
- [older, snippet only] An ISSTA 2023 vulnerability-repair study (Java) cites prior work that fine-tuning improved LLM fixing by at least 31%. That was in an era of weak, non-instruct code models, and only the search snippet was read. [Source](https://www.cs.purdue.edu/homes/lintan/publications/vulfix-issta23.pdf)

### Inferences
**More of the same data is unlikely to help.**
- Adding off-policy GHSA diffs increases the high-perplexity token mass, which is the measured driver of forgetting.
- Better selection is the likelier lever: drop examples the 4B can never solve, and rewrite the rest on-policy.

**A simple data audit with direct support in the literature is per-example perplexity under the untuned 4B.**
- Rank the 541 targets by mean token NLL under the base.
- The SDFT and low-perplexity papers predict that the highest-NLL slice (likely the human commit diffs) does the most damage.
- Ablate it by training on v2 minus the top-NLL quartile, or by masking high-NLL tokens.

**Data "quality" for this task means verified and in the model's own distribution, not human-written.**
- The 105 sandbox-verified synthetic fixes from the 9B are closer to on-policy than the 275 human diffs, but still off-policy.
- Per SelfCodeAlign, a 9B teacher is not "clearly stronger" than a strong 4B, so own-sample data may beat it.

### Gaps
- No study found that fine-tunes a small instruct model on CVE or GHSA commit diffs and reports the effect against the untuned instruct baseline.
- No LIMA-style count exists for code repair on modern 3-8B instruct models.
- No source quantifies how often upstream security fixes bundle unrelated or behaviour-changing edits. That would directly test the REGRESSION hypothesis.

## Q5. Which single remedy is most likely to lift AeroPatch above the untuned base, and what result would be expected?

### Takeaway
The best-evidenced single remedy is verifier-filtered self-training (RFT / expert iteration). Train only on the untuned 4B's own sandbox-passing outputs, at a much lower learning rate, and leave out the off-policy diffs and the offline repair turns.

The literature supports this reliably restoring roughly base-level performance by removing the off-policy shift. It supports a gain above base only weakly. The ceiling is the base model's own pass@k on the training scenarios, and the expected gain at 54 test runs is within noise unless it is several runs.

### Cited Findings
**Evidence that the remedy removes the cause:**
- On-policy data is the factor behind low forgetting [Retaining by Doing](https://arxiv.org/html/2510.18874v3).
- Forgetting tracks KL to the base on the task [RL's Razor](https://arxiv.org/html/2509.04259).
- Self-written targets reduce the drop [SDFT 2024](https://arxiv.org/html/2402.13669).

**Evidence of gains from self-training with a verifier:**
- [older] ReST-EM: +5.6 to +6.4 points on APPS for PaLM 2, with regression after more than one or two iterations [Source](https://arxiv.org/html/2312.06585).
- [older] RFT on LLaMA-7B [Source](https://arxiv.org/abs/2308.01825).
- [older] SelfCodeAlign on 3-33B code models [Source](https://arxiv.org/html/2410.24198).

**Evidence that it can still fail:**
- Self-SFT at lr 1e-4 forgot as much as off-policy SFT on 2 of 3 Llama-1B targets [Source](https://arxiv.org/html/2510.18874v3).
- SFT on Qwen3-32B's own samples degraded IF-eval [Source](https://thinkingmachines.ai/blog/on-policy-distillation/).
- SWE-Gym self-improvement fell from 15.3% to 8.7% [Source](https://arxiv.org/html/2412.21139).

**Evidence that SFT will not fix STUCK:**
- Self-generated correction SFT leaves retries almost unchanged [SCoRe](https://arxiv.org/html/2409.12917).
- Instruct models repeat code without RL [RLEF](https://arxiv.org/html/2410.02089).

**Lower-LR evidence on the same model family:** Qwen3-4B at lr 1e-6 vs 5e-6 gives general 0.784 vs 0.543 for domain 0.548 vs 0.578 [Source](https://arxiv.org/html/2509.20758).

### Inferences
**Project facts that limit the recipe** (from training/stats-v2.md, not from the literature):
- **Only 158 of the 541 v2 examples are sandbox-checked:** 105 synthetic first attempts plus 53 repair turns. The other 383 (275 GHSA, 108 SWE-Gym/SWE-smith) "re-apply byte-exact and have no test".
- **So the RFT pool is limited to the synthetic CWE scenarios**: 189 were built, and 105 survived the leakage and diversity filters. The GHSA fixes cannot be self-trained on unless PoC and regression tests are built for them.
- **A headroom proxy already exists.** In the run `20261009-student-pass`, the untuned 4B resolved 111 of 189 synthetic scenarios at the first attempt (59%) and 156 within three attempts with feedback (83%). That leaves 33 never solved.
  - The 45 scenarios solved only on a retry are the MaybeKnown set Gekhman found most useful.
  - The 4B's own passing outputs there are ready-made on-policy targets, including on-policy repair turns. Check whether the run directory kept the outputs.
- **Scale caveat.** About 105-160 self-generated examples is far smaller than the 1,000+ problems behind the ReST-EM and RFT gains. That alone limits the expected lift.

**Recommended recipe (synthesis, not a published protocol):**
1. **Find the headroom first.** For every training scenario, sample k=8 from the untuned Q4_K_M 4B at temperature about 0.7 and run the full gate and sandbox pipeline. Record pass@1 and pass@8.
   - If pass@8 is barely above pass@1, self-training has little room. Every recipe in Q2 can only sharpen pass@1 toward pass@k.
   - The 59% to 83% gap between first attempt and within three is an encouraging lower-bound signal. It is sequential with feedback, not independent sampling.
2. **Build the dataset from the 4B's own passing outputs only.**
   - Prefer scenarios that are MaybeKnown (pass in some, not all, samples), and cap each scenario at 1-2 distinct passes.
   - For scenarios that never pass, either drop them (Gekhman) or add an SDFT-style own-words rewrite of the reference fix, kept only if it passes the sandbox.
   - Leave out the 275 raw human diffs and the 53 offline repair turns.
3. **Train gently:**
   - LoRA all linear layers, r=16, alpha=16 (unchanged, so only the data and the LR move).
   - LR about 2e-5 to 5e-5 (roughly 4-10x lower than now), 1 epoch.
   - Save checkpoints. Then sweep the merged adapter scale {0.5, 1.0} on dev before touching test.
   - Moving to alpha=32 is a separate later arm. It doubles the effective step.
4. **Optionally run one more iteration** with the tuned model as sampler (Iterative-SFT / ReST-EM). Stop at 2, since ReST-EM regressed past that on APPS.

**Expected result.** This is a judgement from the effect sizes above, not a measured prediction.
- Test 36-41 of 54, against 38 untuned, so most likely parity. CVE about 6-8 of 20, against 7. STUCK back near the untuned 0-2.
- A gain beyond base is plausible only if step 1 shows meaningful pass@8 headroom.
- At n=54 with p of about 0.7, one standard error is about +/-3.4 runs (binomial; scenarios repeat in pairs, so the effective n is smaller and the error larger).
  - Any difference of 1-3 runs should be treated as noise.
  - Claiming improvement needs about +5 or more, or a paired per-scenario comparison.
- Most of the expected benefit is removing the 6-9 run loss, not adding new capability.

**Second-best choices:**
- **The alpha-scaling sweep on the existing adapter.** It needs no retraining, so run it first as a diagnostic.
- **Rebuilding the data as v2 with targets rewritten in the 4B's own words (SDFT 2024).** It keeps the knowledge content of the real fixes. In the only published code test it matched vanilla FT on the code target and forgot less off-target, but that seed was weak at code, so the AeroPatch case (a seed strong at the target) is untested.

**What would actually teach use of feedback (fixing STUCK beyond "don't break it"):** online multi-turn RL with the sandbox as reward (SCoRe, RLEF).
- LoRA matches full fine-tuning for RL even at low rank [LoRA Without Regret](https://thinkingmachines.ai/blog/lora/).
- But GRPO on a 4B with Docker-sandbox rewards on a Kaggle T4 is a much larger build. Treat it as a later step.

### Gaps
- No published result tests RFT, SDFT or on-policy distillation on a small instruct model that is already strong at the target code task. The expected range above is an extrapolation.
- The untuned 4B's independent pass@k on AeroPatch training scenarios is unknown. It is the single number that decides whether self-training can exceed the base. The only proxy is 59% at the first attempt and 83% within three with feedback, on 189 synthetic scenarios.
- No source covers whether self-training only on synthetic CWE-injection scenarios transfers to real CVEs (the 20-run CVE set), or narrows the model to the injection distribution.
- Not verified: whether Unsloth/TRL on a T4 can run the 2026 on-policy SDFT (2.5x FLOPs, 4x wall-clock) or GRPO with an external Docker reward within Kaggle session limits.
