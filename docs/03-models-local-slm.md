# 03 — Local Small Language Model (SLM) Selection

Maps to: `src/models/local_client.py`, `training/`. Back to the index: [00-overall-plan.md](00-overall-plan.md)
All scores are "(reported)" from model cards or vendor blogs as of 2026-09-24. Verify before quoting.

## 1. Requirements for the local model

1. Fits in **4 GB VRAM** at Q4 with ≥8k context (doc 02).
2. Permissive license (Apache-2.0/MIT), because the repo and any adapter will be public.
3. Good at Python code and at following a strict output format (search/replace edit blocks).
4. Trainable with Unsloth/TRL on a free T4, and exportable to GGUF for llama.cpp/Ollama.
5. Recent enough that the training cutoff can be dated, which matters for contamination control.

## 2. Candidate table

| Model | Released | Params | License | Local Q4 fit (4 GB) | Train on free T4 | Notes |
|---|---|---|---|---|---|---|
| **Qwen3.5-4B** | Mar 2026 | 4B (hybrid Gated DeltaNet + attention) | Apache-2.0 | Yes (~2.5–2.8 GB weights) | LoRA 16-bit ~10 GB: yes | Newest small Qwen; 262k ctx; thinking on/off; LiveCodeBench v6 55.8, BFCL-V4 50.3 (card) |
| Qwen3.5-2B | Mar 2026 | 2B | Apache-2.0 | Easily | LoRA ~5 GB: yes | Faster; weaker; good ablation point |
| Qwen3.5-0.8B | Mar 2026 | 0.8B | Apache-2.0 | Easily | LoRA ~3 GB: **even locally** | Too weak for real fixes; only a "train on laptop" demo |
| Qwen2.5-Coder-3B-Instruct | Nov 2024 | 3B dense | **Qwen Research (non-commercial)** | Yes (~1.9 GB) | QLoRA: yes | Code-specialized, but license and age count against it |
| **Qwen2.5-Coder-1.5B-Instruct** | Nov 2024 | 1.5B dense | Apache-2.0 | Easily | QLoRA locally: plausible | Best candidate for "trained on a 4 GB laptop" |
| Gemma 4 E4B | Apr 2026 | ~4.5B effective (~8B total, PLE) | Apache-2.0 | Tight | 10–17 GB: T4 borderline | Native function calling; multimodal overhead |
| Gemma 4 E2B | Apr 2026 | ~2.3B effective | Apache-2.0 | Yes | ~8 GB: yes | Edge-oriented; good second family for comparison |
| Llama 3.2-3B | Sep 2024 | 3B | Llama Community | Yes | Yes | Older and weaker at code; drop |

Models that are **not** local options, but are useful as ceilings or teachers (hosted inference only):

| Model | Size | Why it matters |
|---|---|---|
| Qwen3-Coder-Next | 80B total / 3B active (MoE) | 70.6% SWE-bench Verified (reported); open-weights ceiling and possible teacher |
| Qwen3.6-35B-A3B | 35B total / 3B active | Needs ~20 GB at Q4; "3B active" still means 35B of weights in memory |
| Qwen3.8-27B | 27B dense | ~18 GB at Q4; newest open Qwen; there is no official sub-10B Qwen3.8 |

Watch the "A3B" trap. A 35B-A3B model is not a 3B model. The whole model must fit in memory,
so don't describe it as a "3B model" on the resume.

## 3. Key facts that shape the choice

- **Unsloth says not to QLoRA Qwen3.5** (dense or MoE), because 4-bit quantization error is
  higher than normal on this architecture. Use 16-bit LoRA instead: ~10 GB for 4B, ~5 GB for 2B.
  That rules out local training for Qwen3.5-2B/4B but fits a free T4.
- **Qwen2.5-Coder QLoRA is well trodden** and works on small GPUs. Unsloth's unmerged 4 GB guide
  peaked at ~1.5 GB for a 1B model. A 1.5B model at seq 1–2k is plausible on 4 GB, but pilot it first.
- **Qwen3.5 in llama.cpp needs a recent build**, because of the Gated DeltaNet layers.
  Pin the llama.cpp/Ollama version in `docker-compose.yml` and the README.
- **Thinking mode costs latency.** On a 3050, 500 thinking tokens take tens of seconds.
  Default to non-thinking mode for edits (`enable_thinking: false`) and measure thinking mode
  as an ablation. If you train without reasoning traces, the model's thinking mode may degrade;
  Unsloth advises keeping ≥75% reasoning examples if you want to preserve it.
- **Multimodal models carry extra weights.** Qwen3.5 and Gemma 4 small models are natively
  multimodal. Serve text-only: llama.cpp simply doesn't load the vision projector, and vLLM
  has `--language-model-only` for Qwen3.5.

## 4. Recommendation

| Role | Model | Why |
|---|---|---|
| **Primary fine-tune target** | **Qwen3.5-4B** (LoRA 16-bit on Kaggle T4) | Newest Apache-2.0 small model; fits 4 GB at Q4; long context |
| Local-training demo / ablation | Qwen2.5-Coder-1.5B-Instruct (QLoRA on the 3050) | Only credible way to say "trained on a 4 GB laptop GPU" |
| Untuned baselines | Qwen3.5-4B, Qwen2.5-Coder-3B-Instruct, Gemma 4 E4B | Shows what fine-tuning adds; covers two families |
| Open-weights ceiling (optional) | Qwen3-Coder-Next via a hosted provider | "Best open model" reference point |
| Frontier reference | See [04](04-models-frontier-and-routing.md) | Upper bound and fallback |

If Qwen3.5-4B gives you trouble (loader bugs, GGUF issues, T4 memory), fall back to
**Qwen2.5-Coder-3B-Instruct with QLoRA**, and note its non-commercial license in the README
and on the model card. A research/portfolio project is non-commercial use, but say so explicitly.

## 5. Week 1 bake-off procedure (half a day)

Run every candidate **untuned** on the first 10 scenarios (doc 11). Use oracle localization,
temperature 0.2, non-thinking mode, and the same prompt template. Record:

| Metric | Why |
|---|---|
| Edit-apply rate | Can the model produce blocks that apply mechanically? |
| PoC-fixed rate | Does the vulnerability test pass? |
| Regression-free rate | Did it break anything else? |
| Latency p50 (s) and decode tok/s | Real cost on this laptop |
| Peak VRAM (GB) | Must stay < 3.8 GB |

Decision rule: pick the highest (PoC-fixed AND regression-free) rate among models with ≥80%
apply rate and p50 latency under 30 s. If two are within one scenario of each other, prefer the
Apache-2.0 model with the longer context. Record the result as a table in the README; it becomes
the "Untuned" row of the final results.

## 6. Prompting a small model (applies to all candidates)

- Keep the context small: the vulnerable function, its imports, the class header, and 1–2
  callers. Use tree-sitter scopes, not whole files (doc 06). Small models get worse fast past a
  few thousand tokens, even when the window is 262k.
- Put the output format **last** in the prompt, with one short example of a search/replace block.
- Use constrained decoding where it helps. llama.cpp GBNF grammars or Ollama's JSON-schema
  `format` can force the edit-block structure and cut apply failures.
- Keep temperature low (0.0–0.3) for pass@1 runs. Use 0.6–0.8 for pass@k sampling (doc 12).
- Never ask the small model for a full unified diff with line numbers. The harness computes the diff.

## 7. Serving settings (starting point, tune in Week 1)

| Setting | Value |
|---|---|
| Quant | Q4_K_M (Q5_K_M if VRAM allows; compare apply rate) |
| Context | 8192 (raise only if scenarios need it) |
| GPU layers | all (`-ngl 99`); verify no CPU offload in the logs |
| Batch / parallel slots | 1 (single user, sequential) |
| Temperature / top_p | 0.2 / 0.9 for pass@1 |
| Max new tokens | 1024 (edits are short; stop runaway generations) |
| Stop sequences | End-of-edit marker from the edit format (doc 08) |

Next: [04-models-frontier-and-routing.md](04-models-frontier-and-routing.md)
