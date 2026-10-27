# Lightweight DeepSeek, Mistral, Nemotron and Gemma models as alternatives or companions to Qwen3.5-4B (as of 2026-10-24)

Scope: open-weight models from these four families that could run on an RTX 3050 Laptop (4 GB VRAM, 16 GB RAM) in Ollama or llama.cpp at about 6-8k context, with free licences, for SEARCH/REPLACE patch writing. Baseline: qwen3.5:4b Q4_K_M, a 3.1 GiB file (local `ollama /api/tags`, 2026-10-24, Ollama 0.40.10), measured by the project at 3,043 MiB peak at 8k and about 46 tok/s with thinking off.

Labels used below:
- **[V]**: the vendor reports this benchmark and no independent source checks it.
- **mode**: whether the score was taken with thinking/reasoning on. AeroPatch runs with thinking **off**, so most published coding scores do not describe the setup it would use.
- **File size**: the Ollama download size. It is not the VRAM footprint. Fit is listed as "unknown until measured" wherever the two could differ.

## 1. Which current models exist in each family that could fit, and what are their specs?

### Takeaway
Judging by file size, two new models are likely full-GPU fits on 4 GB: **Nemotron 3 Nano 4B** (2.8 GB, March 2026) and **Ministral 3 3B** (3.0 GB, December 2025). Fit for **Gemma 4 E2B** (4.6 GB Q4_K_M file, 4.3 GB qat) and **Gemma 4 E4B** (6.6 GB, 6.1 GB qat) is unknown until checked locally. Both files are above 4 GB, but the tech report puts their quantized core weights at 0.8 GB and 2.3 GB. DeepSeek has nothing new and small. Its only sub-9B models are the January 2025 R1 distills and the May 2025 R1-0528-Qwen3-8B distill, all thinking-only. Every other model in these families is far too large (DeepSeek V4-Flash, Mistral Small 4, Devstral, Nemotron 3 Nano 30B-A3B, Gemma 4 12B/26B/31B).

### Comparison table

| Model | Released | Params | Licence | Context | Ollama tag : Q4_K_M file | Est. VRAM at 8k | LiveCodeBench (mode) | Other vendor scores | Fit verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Qwen3.5-4B** (baseline) | Mar 2026 | 4B | Apache-2.0 | 262,144 (to 1.01M) | `qwen3.5:4b` : 3.1 GiB (local) | 3,043 MiB (measured) | v6 55.8 [V] (mode not stated on card) | MMLU-Pro 79.1, GPQA-D 76.2, IFEval 89.8, BFCL-V4 50.3, TAU2-Bench 79.9 [V] | fits (measured) |
| **Nemotron 3 Nano 4B** | 2026-03-16 | 3.97B, Mamba-2/MLP hybrid with only 4 attention layers | NVIDIA Nemotron Open Model License | 262,144 | `nemotron-3-nano:4b` / `4b-q4_K_M` : 2.8 GB | about 3 GB (inference) | 51.8 [V] (reasoning **on**) | Reasoning off: IFEval-Prompt 82.8 / -Instr 88, BFCL v3 61.1, RULER-128k 91.1, Tau2 Airline/Retail/Telecom 28.0/34.8/24.9. Reasoning on: AIME25 78.5, GPQA 53.2, IFEval 87.9/92 [V] | likely fits |
| **Ministral 3 3B** (Instruct 2512) | 2025-12-04 | about 3B LM plus a vision encoder | Apache-2.0 | 256K | `ministral-3:3b` / `3b-instruct-2512-q4_K_M` : 3.0 GB | about 3-3.5 GB (inference; the file includes the vision encoder) | 54.8 [V], but measured on the **Reasoning** variant, which is not the tag Ollama ships | Instruct: Arena Hard 30.5, WildBench 56.8, MATH maj@1 83.0 [V] | likely fits |
| **Gemma 4 E2B** | Apr 2026 | 2.3B effective, 5.1B with embeddings | Apache-2.0 | 128K | `gemma4:e2b` / `e2b-it-q4_K_M` : 4.6 GB; `e2b-it-qat` : 4.3 GB | unknown until measured (report: 0.8 GB quantized weights plus 0.05 KV) | v6 44.0 [V] (mode not stated; thinking is configurable) | MMLU-Pro 60.0, GPQA-D 43.4, Codeforces 633, Tau2 avg 24.5 [V] | unknown until measured |
| **Gemma 4 E4B** | Apr 2026 | 4.5B effective, 8B with embeddings | Apache-2.0 | 128K | `gemma4:e4b` (= latest) / `e4b-it-q4_K_M` : 6.6 GB; `e4b-it-qat` : 6.1 GB | unknown until measured (report: 2.3 GB quantized weights plus 0.14 KV) | v6 52.0 [V] (mode not stated) | MMLU-Pro 69.4, GPQA-D 58.6, Codeforces 940, Tau2 avg 42.2, BBEH 33.1 [V] | unknown until measured; may need partial offload |
| Ministral 3 8B (Instruct 2512) | 2025-12-04 | 8.4B LM + 0.4B vision | Apache-2.0 | 256K | `ministral-3:8b` : 6.0 GB | over 4 GB, so offload needed | 61.6 [V] (Reasoning variant) | Arena Hard 50.9, WildBench 66.8 [V] | offload only |
| Ministral 3 14B | 2025-12-04 | 14B | Apache-2.0 | 256K | `ministral-3:14b` : 9.1 GB | heavy offload | 64.6 [V] (Reasoning variant) | | no |
| Nemotron Nano 9B v2 | not verified (parent of the 4B) | 9B hybrid | NVIDIA Open Model License | | no `nemotron-nano` Ollama library page (404) | over 4 GB | not collected | | offload only; superseded on this hardware by the 4B |
| Nemotron 3 Nano 30B-A3B | not verified (Ollama base tags 10 months old) | 30B MoE, about 3B active | NVIDIA Open Model License | 1M | `nemotron-3-nano:30b-a3b-q4_K_M` : 24 GB | no | | | no (24 GB is above 16 GB of RAM) |
| DeepSeek-R1-Distill-Qwen-1.5B / 7B | 2025-01-20 | 1.5B / 7B (Qwen2.5 base) | MIT (Qwen2.5 base, Apache-2.0) | | `deepseek-r1:1.5b` / `deepseek-r1:7b` (sizes not checked) | 1.5B fits; 7B borderline | not collected for these sizes | | superseded; thinking-only |
| DeepSeek-R1-Distill-Llama-8B | 2025-01-20 | 8B (Llama-3.1 base) | MIT + Llama 3.1 licence | | not the current `deepseek-r1:8b` | offload | 39.6 [V] | AIME24 50.4, GPQA-D 49.0, CF 1205 [V] | superseded |
| DeepSeek-R1-0528-Qwen3-8B | May 2025 | 8B (Qwen3 base) | MIT | | `deepseek-r1:8b` | offload | not collected | | offload only; thinking-only |
| DeepSeek-Coder-V2-Lite | not verified | 16B MoE, 2.4B active | not verified this session | | `deepseek-coder-v2:16b` | about 14.7 GB Q4 (calculator), so about 70% offloaded | | | offload; about 5.5 tok/s estimated (not measured) |
| DeepSeek V4-Flash | 2026-04-24 | 284B MoE, 13B active | "permissive" (per secondary source) | 1M | 160 GB on HF | no | | | no |
| Mistral Small 4 | 2026-03-16 | 119B MoE, 6B active | Apache-2.0 | 262K | 242 GB on HF | no | | | no |
| Devstral 2 / Devstral Small 2 | late 2025 | 123B / (Small not checked) | Devstral 2: modified MIT (limit for companies above $20M monthly revenue) | | | no | | Devstral 2 SWE-bench Verified 72.2% | no |
| Gemma 3 1B / 4B | not verified | 1B / 4.3B | Gemma Terms of Use (not re-checked this session) | | `gemma3:1b` 0.76 GiB, `gemma3:4b` 3.11 GiB (both already pulled locally) | 4B: about 3.3 GB (inference) | | Gemma3-4B-Instruct Arena Hard 31.8, WildBench 49.1 (from Mistral's comparison table) | fits; superseded by Gemma 4 |
| Gemma 3n E2B / E4B | not verified | | not verified | | not checked | | | | superseded by Gemma 4 E-series; not researched |
| CodeGemma 2B / 7B | not verified | | not verified | | not checked | | | | older generation; not researched |
| Nemotron-Mini-4B / Llama-3.1-Nemotron-Nano 4B/8B | not verified | | not verified | | not checked | | | | older generation; not researched this session (the 4B line now appears to be Nemotron 3 Nano 4B) |
| Ministral 8B (original, 2024 line) | not verified | | not verified (possibly the Mistral Research License) | | not checked | | | | older generation, superseded by Ministral 3; not researched |

### Cited Findings
**Gemma 4**
- The Gemma 4 sizes are E2B, E4B, 12B, 26B A4B and 31B. The licence is Apache 2.0, and the card was last updated 2026-07-30. E2B is 2.3B effective (5.1B with embeddings) and E4B is 4.5B effective (8B with embeddings). Both have 128K context, native function calling and configurable thinking: "Thinking is enabled by including the `<|think|>` token at the start of the system prompt." — [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
- E4B / E2B benchmarks [V]: LiveCodeBench v6 52.0% / 44.0%, Codeforces ELO 940 / 633, MMLU-Pro 69.4 / 60.0, GPQA Diamond 58.6 / 43.4, Tau2 (average over 3) 42.2 / 24.5, BigBench Extra Hard 33.1 / 21.9, MRCR v2 128k 25.4 / 19.1. Gemma 3 27B (no think) scores LCB v6 29.1. — [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4); same table in the [Gemma 4 Technical Report, arXiv 2607.02770](https://arxiv.org/pdf/2607.02770)
- The tech report's memory table gives E2B at bf16 4.6 / quantized 0.8† / KV cache +0.05, and E4B at bf16 9.0 / quantized 2.3† / KV cache +0.14 (GB; the dagger footnote was not read). — [Gemma 4 Technical Report](https://arxiv.org/pdf/2607.02770)
- Google says the per-layer embedding (PLE) tables are large but used only for lookups, so static weight memory is higher than the effective parameter count. Its estimates leave out the runtime and the context window. — [ai.google.dev Gemma docs, via search summary](https://ai.google.dev/gemma/docs/core)
- Ollama `gemma4` tags (page read 2026-10-24): `e2b` 4.6-7.5 GB, `e2b-it-q4_K_M` 4.6 GB, `e2b-it-qat` 4.3 GB, `e4b` (= `latest`) 6.6-9.5 GB, `e4b-it-q4_K_M` 6.6 GB, `e4b-it-qat` 6.1 GB, `12b-it-q4_K_M` 8.0 GB; all have Text and Image input and 128K context (E-series). The Q4_K_M tags were re-uploaded "3 weeks ago". The model page lists vision, tools, thinking and audio. — [ollama.com/library/gemma4/tags](https://ollama.com/library/gemma4/tags)
- One write-up reports about 59 tok/s from Gemma 4 E2B on a GTX 1650 Ti (4 GB) in llama.cpp. It also found that the automatic GPU layer split was not always the fastest. This comes from a search summary; the page itself was not read. It is a single secondary source and does not cover E4B. — [Towards AI: Local LLMs up to 2.24x faster on a 4GB NVIDIA GPU](https://pub.towardsai.net/how-i-made-local-llms-up-to-2-24-faster-on-a-4gb-nvidia-gpu-e0c02f2b1821)
- Google's LiteRT-LM table lists E4B decode at 18 tok/s on CPU and 91 tok/s on GPU (RTX 4090, Linux). These are LiteRT-LM figures, not llama.cpp. — [LiteRT-LM Gemma 4 page](https://developers.google.com/edge/litert-lm/models/gemma-4.md.txt)

**Nemotron**
- NVIDIA-Nemotron-3-Nano-4B: released 2026-03-16 under the NVIDIA Nemotron Open Model License. It has 3.97B parameters, a Mamba2-Transformer hybrid architecture compressed from Nemotron-Nano-9B-v2, and up to 262K context. Thinking is on by default and is turned off "via a system prompt or by adding `enable_thinking=False` to `apply_chat_template()`". Tool calling uses the qwen3_coder parser in vLLM, and llama.cpp is a listed engine. — [HF model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16)
- Its architecture is "primarily of Mamba-2 and MLP layers combined with just four Attention layers." — [unsloth/NVIDIA-Nemotron-3-Nano-4B](https://huggingface.co/unsloth/NVIDIA-Nemotron-3-Nano-4B)
- Benchmarks [V], reasoning off: BFCL v3 61.1, IFBench-Prompt 43.2, IFEval-Prompt 82.8, IFEval-Instruction 88, HaluEval 62.2, RULER (128k) 91.1, Tau2 Airline/Retail/Telecom 28.0/34.8/24.9. Reasoning on: AIME25 78.5, MATH500 95.4, GPQA 53.2, LCB 51.8, IFEval 87.9/92. The card has no Qwen comparison rows. — [HF model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16)
- NVIDIA describes it as its "first model specifically optimized for on-device deployment," aimed at GeForce RTX, Jetson and Spark. NVIDIA publishes an official Q4_K_M GGUF. — [HF blog](https://huggingface.co/blog/nvidia/nemotron-3-nano-4b); [nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF)
- Ollama `nemotron-3-nano` tags: `4b` 2.8-2.9 GB, `4b-q4_K_M` 2.8 GB, `4b-q8_0` 4.2 GB, all with 256K context. The model is tagged tools and thinking. Most 4B tags were updated "6 days ago" and q8_0/bf16 "7 months ago". `30b-a3b-q4_K_M` is 24 GB. — [ollama.com/library/nemotron-3-nano/tags](https://ollama.com/library/nemotron-3-nano/tags)
- `ollama.com/library/nemotron-nano/tags` returned HTTP 404, so the 9B v2 has no official Ollama library page under that name. — [ollama.com/library/nemotron-nano/tags](https://ollama.com/library/nemotron-nano/tags)

**Mistral**
- Mistral 3 launched with Ministral 3 in 3B, 8B and 14B sizes, under Apache 2.0, in base, instruct and reasoning variants. — [Mistral: Introducing Mistral 3](https://mistral.ai/news/mistral-3/); [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1pceipb/mistral_just_released_mistral_3_a_full_openweight/)
- Ministral 3 3B was released 2025-12-04 under Apache 2.0. — [llm-stats](https://llm-stats.com/models/ministral-3-3b-base-2512)
- Ministral 3 8B Instruct 2512: 8.4B LM plus 0.4B vision encoder, 256k window, native function calling (vLLM `--tool-call-parser mistral`), Apache 2.0 for commercial and non-commercial use. Benchmarks [V] for the Reasoning variants (AIME25 / GPQA-D / LiveCodeBench): 14B 0.850/0.712/0.646, 8B 0.787/0.668/0.616, 3B 0.721/0.534/0.548. The table also lists Qwen3-VL-4B-Thinking at LCB 0.513. Instruct (Arena Hard / WildBench / MATH maj@1): 3B 0.305/56.8/0.830, Gemma3-4B-Instruct 0.318/49.1/0.759, Qwen3-VL-4B-Instruct 0.438/56.8/0.900. The card gives no HumanEval or MBPP. — [HF Ministral-3-8B-Instruct-2512](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512)
- The Ministral 3 tech report gives post-training scores of 8B Arena Hard 50.9 / WildBench 66.8 and 3B 30.5 / 56.8. — [Ministral 3, arXiv 2601.08584](https://arxiv.org/pdf/2601.08584)
- Ollama `ministral-3` tags: `3b` / `3b-instruct-2512-q4_K_M` 3.0 GB, `3b-instruct-2512-q8_0` 4.5 GB, `8b` / `8b-instruct-2512-q4_K_M` 6.0 GB, `14b-instruct-2512-q4_K_M` 9.1 GB. All have 256K context and Text and Image input, and were updated "10 months ago". Only instruct tags are listed; there are no reasoning tags. — [ollama.com/library/ministral-3/tags](https://ollama.com/library/ministral-3/tags)
- Mistral Small 4 (released 2026-03-16) is a 119B MoE with 6B active, Apache 2.0, a 242 GB download and 262K context. — [Simon Willison](https://simonwillison.net/tags/mistral/?page=1); [OpenRouter](https://openrouter.ai/mistralai/mistral-small-2603/api)
- Devstral 2 is a 123B model under a "modified MIT" licence that restricts companies above $20M monthly revenue, and scores 72.2% on SWE-bench Verified. A Devstral Small 2 also exists (late 2025). — [Simon Willison](https://simonwillison.net/tags/mistral/?page=1)

**DeepSeek**
- The Ollama `deepseek-r1` page lists `deepseek-r1:8b` = DeepSeek-R1-0528-Qwen3-8B, plus `1.5b` / `7b` / `14b` / `32b` = R1-Distill-Qwen and `70b` = R1-Distill-Llama. The weights are MIT; the Qwen distills derive from Apache-2.0 Qwen2.5 and the Llama 8B from the Llama 3.1 licence. — [ollama.com/library/deepseek-r1:8b](https://ollama.com/library/deepseek-r1:8b)
- A user points out that "deepseek-r1:8b" is really a Qwen3 model distilled by DeepSeek, not a DeepSeek-architecture 8B. — [r/ollama](https://www.reddit.com/r/ollama/comments/1l703uz/8b_model_of_deepseek_cant_do_the_most_simple/)
- R1-Distill-Llama-8B [V]: AIME24 50.4, MATH-500 89.1, GPQA-D 49.0, LiveCodeBench 39.6, CodeForces 1205. Released 2025-01-20. — [HF DeepSeek-R1-Distill-Llama-8B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-8B); [llm-stats](https://llm-stats.com/models/deepseek-r1-distill-llama-8b)
- DeepSeek V4 (2026-04-24): V4-Flash is 284B total / 13B active and 160 GB on HF; V4-Pro is 865 GB; both have 1M context. — [Simon Willison](https://simonwillison.net/2026/apr/24/deepseek-v4); [NYU Shanghai RITS](https://rits.shanghai.nyu.edu/ai/deepseek-releases-v4-open-source-1-6t-moe-with-1m-context)
- A "V4-Lite" (about 200B, March 2026) appears only in weak sources and has no official confirmation. — [framia.converge.ai](https://framia.converge.ai/page/en-US/news/deepseek-v4-release-date)
- DeepSeek-Coder-V2 16B Lite: a calculator site puts Q4_K_M at about 14.7 GB, which means about 70% offload on 4 GB. It estimates about 5.5 tok/s decode with about 35 s time-to-first-token on an RTX 3050 Ti Laptop 4GB, and 2.3 tok/s on a GTX 1650. These are **estimates, not measurements**. — [willitrunai: 3050 Ti laptop](https://willitrunai.com/can-run/deepseek-coder-v2-16b-on-rtx-3050-ti-laptop-4gb); [willitrunai: GTX 1650](https://willitrunai.com/can-run/deepseek-coder-v2-16b-on-gtx-1650-4gb)

**Baseline and local state**
- Qwen3.5-4B card [V]: LiveCodeBench v6 55.8, MMLU-Pro 79.1, GPQA Diamond 76.2, IFEval 89.8, BFCL-V4 50.3, TAU2-Bench 79.9. Context is 262,144, extensible to 1,010,000. In the same table, Qwen3.5-9B scores LCB 65.6 and BFCL-V4 66.1. — [HF Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B)
- Pulled locally on 2026-10-24: qwen3.5:4b 3.1 GiB, gemma3:4b 3.11 GiB, gemma3:1b 0.76 GiB, llama3.2:3b 1.88 GiB, qwen2.5-coder:3b 1.8 GiB, qwen3.5:9b 6.1 GiB, and the aeropatch-* fine-tunes at 2.5-2.6 GiB. Ollama is 0.40.10. No Gemma 4, Ministral or Nemotron model is pulled. — local `GET /api/tags` and `/api/version`

### Inferences
- **Nemotron 3 Nano 4B should have the smallest 8k footprint of any 4B-class option.** Its file (2.8 GB) is smaller than qwen3.5:4b (3.1 GiB), and with only four attention layers its KV cache at 8k should be tiny. An estimate of about 3 GB or less at 8k seems reasonable but is unmeasured.
- **Ministral 3 3B's 3.0 GB file includes a vision encoder.** If Ollama loads the projector onto the GPU, it will use VRAM that does no work for text patches. Expect about the same footprint as qwen3.5:4b.
- **Gemma 4 E-series fit is the open question.** The tech report's 0.8 / 2.3 GB "quantized" figures probably exclude the PLE tables and the audio/vision encoders that the Ollama files bundle (4.6 / 6.6 GB). Whether Ollama keeps the PLE tables in CPU RAM decides whether E4B runs fully on the GPU. Check with `ollama ps` plus nvidia-smi at `num_ctx` 8192 before benchmarking.
- **The qat tags are smaller than q4_K_M** (E2B 4.3 vs 4.6 GB, E4B 6.1 vs 6.6 GB) and are the first to try if fit is tight.
- On published LiveCodeBench, Qwen3.5-4B (55.8) is level with or ahead of all the small candidates: Ministral 3 3B Reasoning 54.8, Gemma 4 E4B 52.0, Nemotron 3 Nano 4B reasoning-on 51.8, Gemma 4 E2B 44.0. No candidate is a clear upgrade on vendor numbers. Any gain would have to show up in format adherence or in thinking-off behaviour, which only a local bake-off can measure.

### Gaps
- No Q4_K_M VRAM-at-8k measurement or tokens/s figure on a 4 GB RTX 3050 was found for Nemotron 3 Nano 4B, Ministral 3 3B or Gemma 4 E4B. The E2B figure (about 59 tok/s on a GTX 1650 Ti) is a single secondary source.
- The dagger footnote on the Gemma 4 report's memory table (what "quantized" covers) was not read.
- The NVIDIA Nemotron Open Model License text was not read. Commercial-use terms, attribution rules and any acceptable-use limits (for example on security content) are unverified.
- Not checked this session:
  - Gemma 3 / 3n / CodeGemma licence (believed to be Gemma Terms of Use).
  - DeepSeek-Coder-V2-Lite licence (believed to be the DeepSeek Model License).
  - Devstral Small 2 parameter count and licence.
  - Ollama file sizes for `deepseek-r1:1.5b` / `7b`.
- Release dates are unverified for Gemma 3, Gemma 3n, CodeGemma, DeepSeek-Coder-V2-Lite, Nemotron 3 Nano 30B-A3B and Nemotron Nano 9B v2.
- Older lines not researched: Nemotron-Mini-4B, Llama-3.1-Nemotron-Nano 4B/8B, and the original Ministral 3B/8B (2024). Their specs, licences (including whether the original Ministral 8B used the Mistral Research License) and Ollama tags are all unchecked.
- No release-date page for Gemma 4 was found. "April 2026" comes from the brief, and the `gemma4:cloud` and `31b-cloud` tags being 4-6 months old is consistent with it.
- No newer DeepSeek model under about 9B was found for 2026. DeepSeek appears to have stopped releasing small distills after R1-0528-Qwen3-8B (May 2025).

## 2. Coding and repair ability compared with Qwen3.5-4B

### Takeaway
None of the candidates has a published Aider polyglot, SWE-bench Verified, HumanEval+ or security-repair score. The only shared coding benchmark is LiveCodeBench, and every number for it is vendor-reported and mostly from thinking mode. On that basis Qwen3.5-4B (55.8) is at least as strong as every candidate that fits. Ministral 3 3B (54.8, Reasoning variant) and Gemma 4 E4B (52.0) are close behind, and so is Nemotron 3 Nano 4B (51.8, reasoning on). There is no shared tool-calling benchmark: Nemotron reports BFCL v3 and Qwen reports BFCL-V4.

### Cited Findings
- LiveCodeBench, all vendor-reported:

  | Model | LCB | Version / mode | Source |
  |---|---|---|---|
  | Qwen3.5-4B | 55.8 | v6, mode not stated | [Qwen card](https://huggingface.co/Qwen/Qwen3.5-4B) |
  | Ministral 3 3B Reasoning | 0.548 | Reasoning variant | [Ministral card](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512) |
  | Gemma 4 E4B | 52.0 | v6 | [Gemma 4 card](https://ai.google.dev/gemma/docs/core/model_card_4) |
  | Nemotron 3 Nano 4B | 51.8 | reasoning on | [Nemotron card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16) |
  | Qwen3-VL-4B-Thinking | 0.513 | thinking | [Ministral card](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512) |
  | Gemma 4 E2B | 44.0 | v6 | [Gemma 4 card](https://ai.google.dev/gemma/docs/core/model_card_4) |
  | R1-Distill-Llama-8B | 39.6 | thinking | [DeepSeek card](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-8B) |
  | Gemma 3 27B | 29.1 | no think, v6 | [Gemma 4 card](https://ai.google.dev/gemma/docs/core/model_card_4) |

- BenchLM lists the Gemma 4 E4B LCB v6 52.0 as "Provider exact" and ranks E4B #182 of 228 on its aggregate index (30.95/100). — [BenchLM: Gemma 4 E4B](https://benchlm.ai/models/gemma-4-e4b)
- Instruction following [V]:
  - Qwen3.5-4B IFEval 89.8 — [Qwen card](https://huggingface.co/Qwen/Qwen3.5-4B)
  - Nemotron 3 Nano 4B IFEval-Prompt 82.8 with reasoning off and 87.9 with reasoning on — [Nemotron card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16)
  - Gemma 4 and Ministral 3: no IFEval on the cards read.
- Agentic tool-use aggregates are not like-for-like:
  - Qwen3.5-4B: TAU2-Bench 79.9 — [Qwen card](https://huggingface.co/Qwen/Qwen3.5-4B)
  - Gemma 4 E4B: Tau2 average over 3 of 42.2 — [Gemma 4 card](https://ai.google.dev/gemma/docs/core/model_card_4)
  - Nemotron 3 Nano 4B: per-domain scores of 28.0 to 39.8 — [Nemotron card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16)
- Searches found no Aider or edit-format benchmark for Gemma 4 E4B against Qwen3.5. One user found Qwen ahead on coding but Gemma "more precise on structured extraction and instruction following". That comparison was of larger models (Gemma 4 26B vs Qwen3.6-35B), not the 4B class. — [search summary of MindStudio / Codersera / HN comparisons](https://www.mindstudio.ai/blog/gemma-4-vs-qwen-3-5-open-weight-comparison); [Brian Lovin HN mirror](https://brianlovin.com/hn/47960507)
- Security-repair benchmarks found evaluate large or closed models only:
  - PatchEval (Nov 2025): 1,000 CVEs across 65 CWEs; the best model repaired 53 of 98 repairable cases — [PatchEval, arXiv 2511.11019](https://arxiv.org/html/2511.11019v1)
  - Vul4Py (2026): 100 Python vulnerabilities across 60 CWEs; every LLM tested was a closed-weight model, but the harness is released for others to run — [Vul4Py, arXiv 2608.00692](https://arxiv.org/pdf/2608.00692)

### Inferences
- The LCB gaps between Qwen3.5-4B and Ministral 3 3B, Gemma 4 E4B and Nemotron 3 Nano 4B (1 to 4 points) are within the noise of mixed modes and versions. They do not predict which model wins at SEARCH/REPLACE patches with thinking off. The project's own 10-scenario dev set is a better discriminator than any published number.
- Vul4Py's released harness (Python, exploit plus functional oracles) could serve as an external check on the shortlisted models later. It has no published small-model results to compare against.

### Gaps
- No Aider polyglot, SWE-bench Verified, HumanEval+ / EvalPlus, CyberSecEval, SecCodePLT or CWE-repair results were found for any of: Qwen3.5-4B, Gemma 4 E2B/E4B, Ministral 3 3B, Nemotron 3 Nano 4B.
- No thinking-off LiveCodeBench for any candidate. Nemotron's reasoning-off table has no coding benchmark.
- The Ministral 3 Instruct variant (the one Ollama ships) has no published LiveCodeBench.

## 3. Known issues: thinking modes, strict edit formats, tool-calling templates, refusals

### Takeaway
Among the new-generation candidates, every model except Ministral 3 Instruct has a thinking mode (gemma3:4b has none), and each has a different off switch:
- **Nemotron**: thinking is on by default; turn it off by system prompt or `enable_thinking=False`.
- **Gemma 4**: thinking is opt-in via a `<|think|>` token in the system prompt.
- **DeepSeek R1 distills**: thinking-only, with no off switch.

Gemma 4 has documented chat-template and tool-call problems in 2026. Ollama re-uploaded both the Gemma 4 and Nemotron 4B tags within the last 1-3 weeks, so templates may still be changing.

### Cited Findings
- Gemma 4 turns thinking on with `<|think|>` at the start of the system prompt and off by removing it. — [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
- Nemotron 3 Nano 4B has `enable_thinking` set to True by default and turns it off by system prompt or `enable_thinking=False`. NVIDIA recommends temperature 0.6 and top_p 0.95 for tool calling. — [Nemotron HF card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16)
- Unsloth suggests temp 1.0 / top-p 1.0 for one Nemotron 3 Nano 4B mode and temp 0.6 / top-p 0.95 for another. — [Unsloth Nemotron 3 guide](https://unsloth.ai/docs/models/nemotron-3)
- Gemma 4 E4B tool-calling issues:
  - Ollama returns valid tool calls for gemma4:e4b, but some clients (OpenCode / AI SDK) mis-parse streamed tool calls. — [opencode issue 20995](https://github.com/anomalyco/opencode/issues/20995)
  - The E4B Jinja template drops reasoning on assistant turns that made tool calls, which breaks prefix caching in agent loops. — [HF gemma-4-E4B-it discussion 45](https://huggingface.co/google/gemma-4-E4B-it/discussions/45); [HF gemma-4-12B-it discussion 49](https://huggingface.co/google/gemma-4-12B-it/discussions/49)
  - Malformed tool calls and looping under long context and reasoning, reported across vLLM, llama.cpp and Ollama. — [HF forum: Gemma 4 bug fixes](https://discuss.huggingface.co/t/gemma-4-bug-fixes-and-research-request/176979)
  - An extra empty user message injected by a client broke the Gemma template. — [Kotlin Slack](https://slack-chats.kotlinlang.org/t/34147833/anyone-else-having-issues-with-tool-calling-when-using-gemma)
- Gemma 4 E4B can hit a TRITON_ATTN fallback in vLLM that drops it to about 9 tok/s on an RTX 4090. This is vLLM-only. — [search summary of vantaige.io](https://vantaige.io/fr/blog/gemma-4-rtx-4090-tokens-per-sec-vram-benchmark)
- Ollama re-uploads: the Gemma 4 Q4_K_M tags 3 weeks ago and the q8_0/bf16 tags 2 weeks ago — [Ollama gemma4 tags](https://ollama.com/library/gemma4/tags). The Nemotron 3 Nano 4B q4_K_M tag 6 days ago — [Ollama nemotron-3-nano tags](https://ollama.com/library/nemotron-3-nano/tags).
- The DeepSeek R1 distills are reasoning-distilled models trained on 800k R1-curated samples. — [Ollama deepseek-r1](https://ollama.com/library/deepseek-r1:8b)
- One user reports deepseek-r1:8b "can't do the most simple things". — [r/ollama](https://www.reddit.com/r/ollama/comments/1l703uz/8b_model_of_deepseek_cant_do_the_most_simple/)

### Inferences
- For AeroPatch's thinking-off pipeline:
  - **Nemotron** must be sent its thinking-off switch every call, by system prompt or template flag. Verify that Ollama's `think: false` maps to it, or every patch call will pay for reasoning tokens.
  - **Gemma 4** is off by default unless the system prompt contains `<|think|>`, which suits the current setup.
  - **The R1 distills** cannot be used with thinking off. Their extra tokens cost the latency budget that thinking-off was chosen to protect, and that alone rules them out as patch writers on this laptop.
- AeroPatch parses SEARCH/REPLACE text, not tool calls, so the Gemma 4 tool-call template bugs mostly do not apply to the patch writer. They would matter if a candidate were used in a tool-calling role.
- Because the Ollama tags were re-uploaded recently, pin the tag digest when benchmarking (e.g. gemma4 `e4b-it-q4_K_M` = dc35e8d9c606, `e2b-it-q4_K_M` = b37049369adf) so results are reproducible.

### Gaps
- No reports were found on any candidate's adherence to a strict SEARCH/REPLACE or diff edit format.
- No reports were found on refusals for security or exploit text for Gemma 4, Ministral 3 or Nemotron 3 Nano 4B. The acceptable-use clauses of the NVIDIA licence were not read.
- It was not verified whether Ollama 0.40.x's `think` parameter toggles Nemotron 3 Nano 4B's reasoning, or Gemma 4's `<|think|>`.

## 4. Which 2-4 to benchmark against Qwen3.5-4B, and which may suit other roles

### Takeaway
Treat this as a test order, not a verdict:
1. Run a fit check (`ollama ps` plus nvidia-smi at `num_ctx` 8192) on each candidate.
2. Run the 10-scenario dev set on the models that fit fully on the GPU.

Suggested order:
1. **Nemotron 3 Nano 4B** (2.8 GB file, hybrid architecture with small KV, thinking off available)
2. **Ministral 3 3B Instruct** (3.0 GB, Apache-2.0, no thinking tokens)
3. **Gemma 4 E2B, then E4B** (Apache-2.0; fit unknown, try the qat tags first)
4. **gemma3:4b** as a free extra row, since it is already pulled.

Drop all DeepSeek options for patch writing.

### Cited Findings
- Nemotron 3 Nano 4B: 2.8 GB Q4_K_M file — [Ollama](https://ollama.com/library/nemotron-3-nano/tags); IFEval-Prompt 82.8 with reasoning off, BFCL v3 61.1, RULER 128k 91.1 — [HF card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16)
- Ministral 3 3B Instruct: 3.0 GB Q4_K_M — [Ollama](https://ollama.com/library/ministral-3/tags); Apache 2.0 with native function calling — [HF card](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512)
- Gemma 4 E2B / E4B: Q4_K_M files 4.6 / 6.6 GB and qat files 4.3 / 6.1 GB — [Ollama](https://ollama.com/library/gemma4/tags); Apache 2.0, LCB v6 44.0 / 52.0 — [Gemma 4 card](https://ai.google.dev/gemma/docs/core/model_card_4)
- gemma3:4b: already pulled, 3.11 GiB — local `/api/tags`
- DeepSeek options:
  - V4-Flash is 284B/13B active — [Simon Willison](https://simonwillison.net/2026/apr/24/deepseek-v4)
  - Coder-V2-Lite runs at an estimated 5.5 tok/s with about 70% offload — [willitrunai](https://willitrunai.com/can-run/deepseek-coder-v2-16b-on-rtx-3050-ti-laptop-4gb)
  - The R1 distills are reasoning-only — [Ollama](https://ollama.com/library/deepseek-r1:8b)

### Inferences
- **Patch writer:**
  - Nemotron 3 Nano 4B and Ministral 3 3B are the cheapest to test, since both should fit at least as comfortably as qwen3.5:4b.
  - Gemma 4 E4B has the best vendor coding numbers of the new families but carries the most fit risk. If it needs partial offload, its speed will fall well below 46 tok/s; measure that before running the full set.
  - Gemma 4 E2B is the smaller-footprint fallback.
- **Triage or classification** (short outputs, many calls):
  - Gemma 4 E2B or gemma3:1b could act as a fast first pass, but not resident next to Qwen3.5-4B. Qwen already takes 3,043 MiB at 8k, so E2B cannot sit beside it, and gemma3:1b (0.76 GiB file) beside it would be borderline on a 4 GB laptop card. Plan on swapping models or running the small model on the CPU.
  - Nemotron's 91.1 RULER-128k suggests it could read long scanner output or whole files for triage.
  - Both are inferences from vendor long-context and size data, not from triage tests.
- **Patch judge or verifier:**
  - A different family from the writer reduces correlated errors.
  - Nemotron 3 Nano 4B or Ministral 3 3B are plausible judges next to a Qwen writer: both have reasonable vendor instruction-following, and judging tolerates lower coding skill.
  - With 4 GB VRAM, two models cannot both stay resident at 8k. A judge would mean model swapping (load time per call) or running the judge on the CPU.
- **Test writer:** no evidence favours any candidate. Run Qwen3.5-4B and the best-performing candidate on a few test-writing prompts.
- **Not worth a slot:**
  - DeepSeek-Coder-V2-Lite: an estimated 5.5 tok/s, plus it would push the 16 GB RAM machine close to the memory pressure that caused WinError 1455 before.
  - Ministral 3 8B and Nemotron Nano 9B v2: offload only, and Qwen3.5-9B (already pulled) covers the "bigger model with offload" role.

### Gaps
- No independent head-to-head among these 4B-class models on code editing exists; the local dev set is the only evidence source.
- Model-swap latency in Ollama on this laptop (for a writer plus judge pair) was not researched.
