# 10 — Fine-Tuning and Quantized Local Serving (Week 3, days 3–5)

Maps to: `training/finetune.py`, `training/configs/`, `src/models/local_client.py`.
Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. Method: LoRA or QLoRA depends on the base model

| Base model | Method | Where | Why |
|---|---|---|---|
| Qwen3.5-4B (primary) | **LoRA, 16-bit base** | Kaggle/Colab T4 | Unsloth: don't QLoRA Qwen3.5; ~10 GB VRAM at seq 2k |
| Qwen2.5-Coder-1.5B (laptop demo) | **QLoRA** (4-bit base) | Local RTX 3050 | Established path; small enough for 4 GB (pilot first) |
| Qwen2.5-Coder-3B (fallback) | QLoRA | T4 | If Qwen3.5 tooling misbehaves; non-commercial license |

Rename the plan's "QLoRA Fine-Tuning" to **"Parameter-efficient fine-tuning (LoRA/QLoRA)"**,
and say which base model got which method. Reviewers who know the Unsloth guidance will notice.

## 2. Stack

- **Unsloth** (memory-efficient kernels, chat templates, GGUF export) + **TRL** `SFTTrainer`
  / `SFTConfig` + **PEFT**. Pin the exact versions in `training/requirements.txt`; the trl API
  changed several times in 2025–2026.
- Runs as a Kaggle notebook that clones the repo and calls `training/finetune.py`, so the
  notebook itself holds no logic.
- The dataset is uploaded as a private Kaggle dataset or pulled from a private HF dataset repo.
  Never put API keys in the notebook; use Kaggle Secrets.

## 3. Starting hyperparameters (tune only if the pilot says so)

| Parameter | Value | Note |
|---|---|---|
| LoRA rank `r` / alpha | 16 / 16 (try 32 / 32 once) | Enough capacity for a format + domain adaptation |
| Dropout | 0 | Unsloth default; data is small but clean |
| Target modules | Unsloth defaults for the model (attention q/k/v/o + MLP gate/up/down) | The plan's "projection layers"; the hybrid layers in Qwen3.5 have their own names, so use the library's list |
| Max sequence length | 2048 (4096 only if the length histogram needs it) | Memory scales with it |
| Batch / grad accumulation | 1 / 8 (effective 8) | Fits the T4 |
| Learning rate / schedule | 2e-4, linear or cosine decay, 5% warmup | Typical LoRA SFT |
| Epochs | 2 (compare against 3 once) | Watch the validation loss |
| Optimizer | `adamw_8bit` | Unsloth-recommended |
| Precision | fp16 on T4 (no bf16), bf16 on L4/A100 | Leave the dtype on auto |
| Loss masking | Assistant tokens only | `train_on_responses_only` |
| Gradient checkpointing | `"unsloth"` | Needed for 4B on 16 GB |
| Seed | fixed (e.g. 3407), recorded in the run config | Reproducibility |

## 4. Pilot run first (~15 minutes)

Before spending hours on a full run:
1. Train 50 steps on 400 examples.
2. Check that the loss goes down, peak VRAM stays below 14 GB, and tokens/sec is sane.
   Extrapolate the full-run time.
3. Generate on 5 validation prompts and check the outputs parse as SEARCH/REPLACE blocks.
4. Only then start the full run. Save checkpoints every ~200 steps (Kaggle sessions end at 12 h).

## 5. Checkpoint selection uses dev scenarios, not the test set

- Split the benchmark (doc 11) into **dev (~10 scenarios)** and **test (30–40)** at the
  start of Week 1, and never select anything on test.
- For each saved checkpoint, compute on dev: apply rate, resolve rate, mean output length.
- Pick the checkpoint with the best dev resolve rate; break ties on apply rate.
- Signs of overfitting: validation loss rising, outputs copying training rationales verbatim,
  or the apply rate staying high while the resolve rate falls.
- Optional forgetting check: 20 small general coding prompts before and after training,
  to show the model didn't lose general ability.

## 6. Export: merge, then GGUF, then quantize (do it in the cloud)

1. Save the **LoRA adapter** separately (tens to a few hundred MB). This is the artifact to publish.
2. Merge the adapter into the 16-bit base and export **GGUF**. The Unsloth Qwen3.5 guide lists
   `q4_k_m`, `q8_0` and `f16` for `save_pretrained_gguf`. Produce `q5_k_m` (or any other level)
   from the f16 GGUF with llama.cpp's `llama-quantize`.
3. Do the merge/convert on Kaggle. Converting a 4B model needs more RAM than the laptop's
   16 GB comfortably provides (Unsloth suggests ~32 GB for 4B+).
4. Download only the GGUF files you'll serve (Q4_K_M, plus Q8_0 for the ablation).

**Drop AWQ from the plan.** AWQ targets GPU serving stacks like vLLM. With llama.cpp/Ollama
as the server, GGUF is the native format, and one format means one export path.

## 7. Quantization ablation (a cheap, strong resume data point)

Run the dev + test sets with the fine-tuned model at Q4_K_M, Q5_K_M and Q8_0, and report
resolve rate, apply rate, tokens/sec and peak VRAM for each. It answers "how much quality
does 4-bit cost on a narrow task?" with your own measurements.

## 8. Local serving

- **Ollama**: a `Modelfile` with `FROM ./aeropatch-q4_k_m.gguf`, the base model's chat
  template, `num_ctx 8192`, `temperature 0.2`, and the stop sequence after `>>>>>>> REPLACE`
  blocks. Run `ollama create aeropatch -f Modelfile`.
- **llama.cpp `llama-server`**: `-m model.gguf -ngl 99 -c 8192 --jinja` (uses the embedded
  chat template), plus an optional `--grammar-file edits.gbnf` to constrain the output to the
  edit format.
- Grammar-constrained decoding is an ablation. Measure the apply rate with and without it.
  It usually helps small models, but it can hurt the content if the grammar is too strict.
- Pin the server version in `docker-compose.yml`. Qwen3.5 needs a llama.cpp build with Gated
  DeltaNet support.

## 9. Local client (`local_client.py`)

- One function: `generate(messages, **params) -> (text, usage)`. It uses `httpx` against
  Ollama's `/api/chat` (or llama-server's chat endpoint) and returns the prompt/completion
  token counts from the response.
- Timeouts: 120 s per call. On a connection error, fail fast (doc 08: never silently escalate).
- Record the `model` digest/tag in every `Attempt`, so a result can always be traced to a GGUF file.

## 10. Publishing the model (optional, but good for the portfolio)

- Hugging Face Hub: push the adapter and the Q4_K_M GGUF with a model card covering the base
  model and its license, data sources and filters, training config, the eval table (dev/test,
  all quant levels), known limitations (Python-only, function-level, may produce plausible
  but wrong fixes), and intended use (defensive remediation with human review).
- Derivatives of Qwen2.5-Coder-3B must carry the **Qwen Research License**. Qwen3.5-4B and
  Qwen2.5-Coder-1.5B derivatives can use Apache-2.0, subject to your data sources' terms.

## 11. Stretch goal only: RL with a sandbox reward

Unsloth ships a GRPO notebook for Qwen3.5-4B, and SWE-RL-style training uses execution
feedback as the reward. With one T4 and 2–20 s sandbox runs per sample, RL is slow and risky
for a 4-week plan. Consider it only after SFT results exist. The reward would be "resolved"
per doc 08, with a small bonus for smaller diffs.

## 12. Training troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| CUDA OOM at step 1 | Sequence too long / batch too big | Lower max seq to 1536; keep batch 1; confirm gradient checkpointing is on |
| Loss stuck near its starting value | Wrong masking (training on the prompt), learning rate too low | Check `train_on_responses_only` markers match the chat template; try lr 3e-4 |
| Loss drops to ~0 fast | Duplicates / leakage / trivially short targets | Re-run the dedupe; inspect the shortest 20 targets |
| Fine-tuned model ignores the format | Template mismatch between training and serving | Serve with the exact template used in training; compare rendered prompts byte by byte |
| Output repeats blocks endlessly | Missing EOS in targets or missing stop sequence | Append EOS to every target; set stop strings in the Modelfile |
| GGUF much worse than the adapter | Quantization loss or a bad merge | Compare Q8_0 vs Q4_K_M on dev; re-export from the merged 16-bit model |
| Kaggle session dies mid-run | 12 h limit or idle timeout | Resume from the last checkpoint; save every ~200 steps |

## 13. Deliverables

- [ ] Pilot log: VRAM, tokens/sec, estimated full-run time.
- [ ] Full run: training/validation loss curves, the chosen checkpoint and why (dev table).
- [ ] GGUF files at 3 quant levels, and one command to serve them locally.
- [ ] Laptop QLoRA demo on Qwen2.5-Coder-1.5B, with peak VRAM screenshot/log (or a
      documented failure and the reason).

Next: [11-evaluation-benchmark.md](11-evaluation-benchmark.md)
