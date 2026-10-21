# Feasibility of training and inference improvements for the Qwen3.5-4B LoRA on a Kaggle T4 and a 4 GB laptop (October 2026)

Notation. "Measured (project)" means a figure from this repository or the task brief: `NOTES.md`, `training/finetune.py`, `training/kaggle/*`, `docker/*`, `docs/07-sandbox.md`. "Measured (vendor)" means a number printed in a published notebook or log. Everything under **Inferences** is an estimate derived from those numbers; the assumptions are stated each time.

Project baseline used throughout (measured, project):
- Pilot at 2,048 tokens: 9.89 GB peak; about 34 s a step after the first; the first step took 5 min 16 s compiling kernels; 3.86 ms a token — [NOTES.md D17 table](../../NOTES.md)
- Probe at 4,096 tokens: 12.99 GB peak — [NOTES.md](../../NOTES.md)
- Dataset v1: 511 train examples, 683,663 tokens (1,338 tokens an example on average); 2 epochs = 128 steps — [NOTES.md](../../NOTES.md)
- Full run (task brief): 47.5 s a step at batch 1 × accumulation 8; 13.1 GB peak; 128 steps in about 100 min (that is about 4.45 ms a token); about 2.5 h a session including 4 GGUF exports.
- LoRA: r = 16, `lora_alpha` = 16 (a scale of 1.0), targets `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`, LR 2e-4; the adapter is saved by `save_pretrained`, then exported with `save_pretrained_gguf` — [training/finetune.py L127-176](../../training/finetune.py)

## 1. Software support for Qwen3.5 (hybrid Gated DeltaNet) on a T4: Unsloth, TRL, vLLM, verl

### Takeaway
SFT works on a T4 today, and this project has measured it. GRPO is officially supported, but only through Unsloth's own HF-style generation (`fast_inference=False`). The only Qwen3.5-4B GRPO notebook is a *vision* one, and on a T4 it falls back to float32. The text-only GRPO path has had open shape-mismatch bugs. DPO, ORPO and KTO go through TRL with Unsloth's patch, but nobody has shown them on Qwen3.5 on a T4. Whether vLLM can serve Qwen3.5 on a T4 is unproven, and the sources contradict each other. Plan for no vLLM.

### Cited Findings
**Unsloth, general Qwen3.5 support**
- Qwen3.5 sizes 0.8B to 122B are supported. The bf16 LoRA VRAM table gives **4B = 10 GB** and 2B = 5 GB. QLoRA (4-bit) "is not recommended" for any Qwen3.5 model. Transformers v5 is required ("Older versions will not work"). — [Unsloth Qwen3.5 fine-tune guide](https://unsloth.ai/docs/models/qwen3.5/fine-tune)
- The custom Mamba Triton kernels make compilation "take longer than normal, especially on T4 GPUs". — [Unsloth Qwen3.5 guide](https://unsloth.ai/docs/models/qwen3.5/fine-tune). Measured (project): the first step took 5 min 16 s — [NOTES.md](../../NOTES.md).
- For multi-GPU, the guide says to add `device_map = "balanced"`, which splits the model across GPUs. — [Unsloth Qwen3.5 guide](https://unsloth.ai/docs/models/qwen3.5/fine-tune)

**Unsloth, GRPO and fast inference (the sources conflict)**
- The fine-tune guide and the RL guide both say Qwen3.5 is "not supported by vLLM": set `fast_inference=False` to use Unsloth inference. GRPO and GSPO are supported that way. The guide also says "vLLM version 0.16.0 does not support Qwen3.5". — [Unsloth Qwen3.5 guide](https://unsloth.ai/docs/models/qwen3.5/fine-tune); [Unsloth RL guide](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide)
- **Conflict:** the Unsloth changelog for 2026-09-17 lists "GRPO: Qwen3.5 and latest TRL/vLLM support" and "Qwen3.5 `fast_inference`". The changelog entries are Unsloth Studio releases (v0.1.x-beta), and none of them mention T4 or fp16. — [Unsloth changelog](https://unsloth.ai/docs/new/changelog)
- **The only Qwen3.5-4B GRPO notebook is `Qwen3_5_(4B)_Vision_GRPO`.** Its saved run on a Tesla T4 (14.563 GB usable) logs "Using float16 precision for qwen3_5 won't work! Using float32" and "Switching to float32 training since model cannot work with float16". Settings: `load_in_4bit=False` (16-bit LoRA), `fast_inference=False`, `max_seq_length=16384`, r = 16, LR 5e-6, `adamw_8bit`, batch 1, `num_generations=2`, `max_prompt_length=1024`, `max_completion_length=1024`, 60 steps, `loss_type="dr_grpo"`, `importance_sampling_level="sequence"`. **60 steps took 1:20:25 (about 80 s a step).** — measured (vendor), [Unsloth notebook Qwen3_5_(4B)_Vision_GRPO.ipynb](https://github.com/unslothai/notebooks/blob/main/nb/Qwen3_5_(4B)_Vision_GRPO.ipynb). Peak memory was not found in the part of the notebook that was read.
- Measured (project): the same "float16 precision for qwen3_5 won't work, using float32" message appears in this project's SFT. Even so, the weights report float16 and the peak at 2,048 tokens is 9.89 GB, so most of the model stays 16-bit. — [NOTES.md](../../NOTES.md)
- Open or uncertain GRPO bugs:
  - unsloth#5121: the "GRPO text-only path treats logits as hidden states for Qwen3.5 and Gemma 4, causing matmul shape mismatch" (unsloth 2026.4.6, TRL 0.24.0, transformers 5.5.0, RTX 4090). — [GitHub unsloth#5121](https://github.com/unslothai/unsloth/issues/5121)
  - A digest of 2026-09-16 reports a Qwen3.5 GRPO crash (`Sizes of tensors must match in apply_rotary_pos_emb`, #4801, TRL 0.24.0). This is a secondary aggregator source. — [agents-radar digest](https://github.com/duanyytop/agents-radar/blob/e4e0e20ce9d164a7f56b531d12094f9943f1e7c2/digests/2026-09-16/ai-infra.md)
- A T4 fp16 crash on Qwen3.5 SFT: with `use_gradient_checkpointing="unsloth"`, offloaded activations were staged in a **bf16 buffer on GPUs without bf16**, which gave "expected mat1 and mat2 to have the same dtype ... BFloat16 != Half". Reported on Kaggle T4 on 2026-07-27, reproduced at sequence length ≥ 512, and **fixed 2026-10-11 in unsloth-zoo PR #1316**. Upgrade with `pip install --upgrade --force-reinstall --no-cache-dir unsloth unsloth_zoo`. — [GitHub unsloth#7506](https://github.com/unslothai/unsloth/issues/7506)
- An earlier Unsloth Vision-RL fix: the float16 issue "only occurred on devices that do not support BF16 and instead fall back to F16 (e.g., T4 GPUs). We fixed this in Unsloth". — [Unsloth Vision RL blog](https://unsloth.ai/blog/vision-rl)
- Unsloth's GRPO memory claims (Llama 3.1 8B, 20K context, 8 generations): 54.3 GB with Unsloth against 510.8 GB for TRL + FA2. The method is a chunked linear-logits loss plus gradient checkpointing that offloads to system RAM ("only 1% slower"). — [Unsloth long-context GRPO blog](https://unsloth.ai/blog/grpo)
- RL guide rules of thumb:
  - "Wait for at least 300 steps for the reward to actually increase"; "you may need to trade for a minimum of 12 hours"; "sometimes it might be 1000 steps or more"; ≥ 500 rows of data recommended.
  - With vLLM on a 16 GB T4, expect about "300 tokens / s" (Llama 3.2 3B).
  - "LoRA 16-bit will use at minimum 4x more VRAM" than QLoRA.
  - — [Unsloth RL guide](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide)
- The text GRPO notebook for the closest equivalent, `Qwen3_(4B)-GRPO`, loads `unsloth/Qwen3-4B-Base` with `load_in_4bit=False`, `fast_inference=True` (vLLM), `gpu_memory_utilization=0.9`, `max_seq_length=2048` and `lora_rank=32` on a T4 (14.741 GB). Its GRPOConfig, peak memory and runtime were not in the part that was read. — [Unsloth notebook Qwen3_(4B)-GRPO.ipynb](https://github.com/unslothai/notebooks/blob/main/nb/Qwen3_(4B)-GRPO.ipynb)

**Unsloth and TRL, DPO / ORPO / KTO**
- Unsloth patches TRL's `DPOTrainer` (`PatchDPOTrainer`). It ships Colab notebooks for "GRPO, ORPO, DPO Zephyr, KTO and SimPO" and says "PPO, KTO Reward Modelling all work with Unsloth". Its example sets `fp16 = not is_bfloat16_supported()`. Nothing on that page mentions Qwen3.5. — [Unsloth DPO/ORPO/KTO page](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide/preference-dpo-orpo-and-kto)
- TRL `DPOConfig` defaults: `max_length=1024`; `truncation_mode="keep_start"`, which is "the only supported value"; `beta=0.1`; `learning_rate=1e-6` (the doc suggests about 1e-5 for adapters); `gradient_checkpointing=True`.
  - "`bf16`: Defaults to `True` if `fp16` is not set". **On a T4, set bf16 explicitly to False.**
  - `precompute_ref_log_probs` exists and saves memory "as the reference model does not need to be kept in memory".
  - `padding_free` is "temporarily unavailable" since the DPO refactor.
  - `loss_type` options include `sigmoid`, `ipo`, `robust`, `apo_zero`, `sigmoid_norm` (SimPO) and `sft`, and losses can be combined, for example `["sigmoid","sft"]`.
  - With PEFT and `ref_model=None`, "the trainer will automatically use the initial policy".
  - — [TRL DPO Trainer docs (main)](https://huggingface.co/docs/trl/main/en/dpo_trainer)
- TRL `GRPOConfig`:
  - `num_generations` defaults to 8, `max_completion_length` to 512, `beta` to 0.0 ("the reference model is not loaded"), and `loss_type` to `'dapo'`.
  - Reward functions get `prompts`, `completions`, `completion_ids` and the dataset columns as kwargs, and return a list of floats (or None). They may be `async def`, in which case they "are awaited concurrently".
  - `vllm_mode` is "colocate" (the default) or "server" ("runs in a separate process (and using separate GPUs) and communicates with the trainer via HTTP").
  - `rollout_func` and `environment_factory` are experimental hooks.
  - Truncated importance sampling corrects the generation-training mismatch, which "turns an otherwise on policy RL problem into an off policy one".
  - — [TRL GRPO Trainer docs (main)](https://huggingface.co/docs/trl/main/en/grpo_trainer)

**vLLM**
- vLLM supports Gated DeltaNet hybrids through FLA Triton kernels and a hybrid KV-cache manager (Qwen3-Next, 2025). — [vLLM blog](https://vllm.ai/blog/2025-09-11-qwen3-next)
- The Qwen3.5 recipe gives vLLM ≥ 0.17.0, and its hardware examples are H100/H200/MI300-class only. — [vLLM recipe Qwen3.5-122B](https://recipes.vllm.ai/Qwen/Qwen3.5-122B-A10B); [vLLM Qwen3.5 recipe](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html)
- fp16 problems on Qwen3.5 in vLLM:
  - A "dtype mismatch in DeltaNet layers during torch.compile (float != c10::Half)" (Qwen3.5-27B, a 0.16 nightly). — [vllm#35238](https://github.com/vllm-project/vllm/issues/35238)
  - `--dtype float16` "works fine on the 35B model but produces garbage on the 397B". — [vllm#35924](https://github.com/vllm-project/vllm/issues/35924)
- Weak third-party evidence that the GDN kernels run on Turing: a guide to running Qwen3.5-35B GPTQ on 4× T4 with vLLM. It was not read in full. — [67ailab guide](https://67ailab.com/posts/vllm-qwen-35b-t4-gpu-guide/)

**Ollama and llama.cpp (inference side)**
- Measured (task brief): Ollama 0.40.3 runs the project's Q4_K_M 100% on the GPU at 8k context, 46.5 tok/s.

### Inferences
- **SFT, RFT and lower-LR retrains carry no new software risk.** They reuse the measured pipeline unchanged.
- **DPO, ORPO and KTO have moderate risk.** TRL's trainer is architecture-agnostic, but the Unsloth patch plus the Qwen3.5 fp32-fallback path on a T4 is untested. That needs a 20–30 min smoke test (5 steps) before any real run. It also needs `bf16=False` and an explicit fp16 or default dtype, mirroring `finetune.py`, which asks for bf16 only where the GPU has it.
- **GRPO has high risk on a T4.** Four reasons:
  - the text path has had shape bugs (#5121, #4801), and no fix was confirmed for either;
  - the only working Qwen3.5-4B GRPO reference is the vision notebook;
  - fp32 fallback;
  - no vLLM.

  Budget a 1–2 h smoke session whose only goal is "does 3 steps of text GRPO with a custom reward run".
- **Dual T4 buys memory, not speed, for these tools.** `device_map="balanced"` splits layers. TRL's server mode would put vLLM on the second T4, but that needs vLLM to run Qwen3.5 on sm75 in fp16, which no source shows. So treat "GPU T4 x2" as one T4 plus a spare.
- **Pin and record versions.** The project's Unsloth 2026.10.3 predates the 2026-10-11 unsloth-zoo fix for #7506. The project's runs did not hit #7506 (they trained at 2,048 and 4,096), but an upgrade to get the GRPO fixes may change the dtype path. Pin, and record versions in `training/requirements.txt` as the project already does.

### Gaps
- No source shows text-only GRPO with Qwen3.5-4B on a T4 working after the fixes. Whether #5121 and #4801 are fixed was not checked.
- Whether Unsloth's new "Qwen3.5 fast_inference" (2026-09-17) runs on a T4 (sm75, fp16) is unknown. The docs page still says "not supported by vLLM".
- No measured peak VRAM for GRPO on Qwen3.5-4B or Qwen3-4B on a T4 was found. The notebooks' memory cells were not in the portions read.
- **verl:** no sources were searched. It is a Ray-based framework built around vLLM/SGLang rollouts. Its support for Qwen3.5 on 2× T4 (fp16) is unknown, and it is not a free-tier fit without evidence.
- No source confirms that DPO/ORPO/KTO run with Unsloth on Qwen3.5 on fp16 GPUs.

## 2. Memory, speed and wall-clock estimates for SFT/RFT, DPO/ORPO/KTO and GRPO on a T4

### Takeaway
Use the measured 4.45 ms a token and the 13 GB peak at 4,096 tokens as the yardsticks:
- **RFT** costs exactly what SFT costs, about 1.5–3 h of GPU a run.
- **DPO** costs about 2.5× SFT per pair. It does *not* fit at 4,096 tokens per side, so filter pairs to about 2,048 tokens per side.
- **GRPO** at a useful size (8 generations, prompts of about 1.3k tokens) is about 80–110 s a step. The 300-step minimum is about 7–9 h (one session), and 1,000 steps is about 22–31 h, which is the whole weekly quota.

### Cited Findings
- SFT measurements (project): 47.5 s a step for 8 examples at up to 4,096 tokens; 13.1 GB peak; 9.89 GB at 2,048; 3.86 ms a token (pilot); 128 steps in about 100 min; a session with 4 GGUF exports takes about 2.5 h. — [NOTES.md](../../NOTES.md) and the task brief
- Kaggle T4 usable memory: 14.563–14.741 GB (as printed by Unsloth). — [Unsloth Qwen3.5 Vision GRPO notebook](https://github.com/unslothai/notebooks/blob/main/nb/Qwen3_5_(4B)_Vision_GRPO.ipynb); [Qwen3 4B GRPO notebook](https://github.com/unslothai/notebooks/blob/main/nb/Qwen3_(4B)-GRPO.ipynb). The project uses a 14 GB budget — [NOTES.md](../../NOTES.md)
- GRPO anchor, measured (vendor): Qwen3.5-4B on a T4, G = 2, prompt ≤ 1,024 and completion ≤ 1,024 tokens, fp32 fallback, no vLLM: about 80 s a step. — [Unsloth notebook](https://github.com/unslothai/notebooks/blob/main/nb/Qwen3_5_(4B)_Vision_GRPO.ipynb)
- Step counts: GRPO needs at least 300 steps "for the reward to actually increase", sometimes 1,000 or more, and "a minimum of 12 hours". — [Unsloth RL guide](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide)
- How DPO works: each example is a prompt with a chosen and a rejected completion. The loss uses policy and reference log-probabilities of both. With PEFT, the reference is the initial policy, so there is no second weight copy. — [TRL DPO docs](https://huggingface.co/docs/trl/main/en/dpo_trainer)
- GRPO defaults: 8 generations, `beta=0` (no reference model), completion ≤ 512 tokens. — [TRL GRPO docs](https://huggingface.co/docs/trl/main/en/grpo_trainer)

### Inferences
**Memory model, fitted from the project's two points.**

| Item | Value |
|---|---|
| Peak at 2,048 tokens | 9.89 GB |
| Peak at 4,096 tokens | 12.99 GB |
| Cost per extra 1k tokens of activations | about 1.5 GB |
| Fixed part | about 6.8 GB |

Use this to size each method:
- **DPO:** a pair puts chosen and rejected through together, so 2 × 4,096 = 8,192 tokens comes to about 19 GB and **does not fit**. 2 × 2,048 comes to about 13 GB, the same as today's SFT, and fits.
- **GRPO:** must use microbatches of 1–2 completions with gradient accumulation across the group of 8. At about 1.6k tokens a completion, that is about 9–10 GB a microbatch.

**DPO truncation trap.** TRL only truncates `keep_start`, so an over-length pair loses the *end of the completion*, which is the part that differs. Drop over-length pairs; do not truncate them.

**Time per method** (4.45 ms a token, 1,338 tokens an example on average):

| Method | Basis | GPU time | Session with exports (about +50 min) |
|---|---|---|---|
| RFT, retrain from base | 511 old + ≤ 378 new examples (≤ 2 verified fixes per scenario × 189), 2 epochs | about 2.9 h | about 3.8 h |
| RFT, continue from v2 on new data only | 378 examples, 2 epochs | about 75 min | about 2.1 h |
| DPO / IPO / RPO-style (`["sigmoid","sft"]`) | about 14–15 s a pair (2 sequences × 1,338 tokens × 4.45 ms × 1.25 for the reference forward with the adapter off) | 300 pairs × 1 epoch: about 1.2 h; × 2 epochs: about 2.5 h | — |
| ORPO / SimPO-style (no reference) | about 12 s a pair | — | — |
| KTO (unpaired pass/fail labels) | about the SFT cost per sample, plus a KL-estimate forward | — | — |

`precompute_ref_log_probs` saves memory, not total time, since with PEFT there is no second model anyway.

**GRPO per step** (1 prompt × 8 completions; prompt about 1.3k tokens, completion about 300 tokens, which matches the measured 6 s an attempt at 46.5 tok/s):

| Part | Estimate | Basis |
|---|---|---|
| Generation | 20–40 s | The anchor implies about 60 s of its 80 s goes on generating about 1k tokens for 2 sequences, roughly 15–20 tok/s a sequence on a T4 without vLLM. |
| Policy forward and backward | about 57 s | 8 × 1.6k tokens × 4.45 ms |
| Rewards | 5–10 s | 8 pytest runs, parallel on CPU |
| **Total** | **about 80–110 s a step** | |

| GRPO run | Time | Fit |
|---|---|---|
| 300 steps (about 1.6 passes over 189 scenarios) | about 7–9 h | One 12 h session, using about 25–30% of a 30 h week |
| 1,000 steps | about 22–31 h | Exceeds one session and uses the whole week. It needs checkpoint/resume across about 3 sessions. |

**GRPO signal.** With a binary pass/fail reward, groups where all 8 pass or all 8 fail give zero advantage. The fraction of usable groups depends on the per-scenario pass rate of the current model, which is not measured for the 189 synthetic scenarios. Measure it in the RFT rollout pass first (it is free there).

**Dual T4.** For SFT/DPO it brings no speed-up with these tools. One could hand-roll generation on GPU 1 with HF `generate` while GPU 0 trains, which is custom code with no published recipe.

### Gaps
- No measured DPO/ORPO/KTO step time or peak memory exists for Qwen3.5-4B on a T4. The figures above are extrapolated from SFT.
- The generation speed of Unsloth/HF `generate` for Qwen3.5-4B on a T4 was not found directly. It is back-derived from one notebook's total runtime, which includes vision inputs.
- The per-scenario pass rate of the current model on the synthetic set is unknown. It determines both the number of DPO pairs and how much of GRPO's signal is usable.

## 3. Computing execution rewards on Kaggle without Docker

### Takeaway
It is feasible for this project's scenarios. All 189 synthetic scenarios are stdlib-only Python with pytest tests. The laptop's verdict is pytest-only: "resolved" means the patch applied, the PoC suite passed and the regression suite passed. ruff and bandit are recorded but do not count. That makes the same verdict reproducible on Kaggle if you reuse `docker/pytest_runner.py` and the `run.sh` flags in a subprocess with:
- a timeout and a process-group kill;
- rlimits set by an exec wrapper, not by `preexec_fn`;
- a temp copy of the repo;
- an environment stripped of secrets.

Expect it to be less isolated than the laptop's `--network none` container. Recalibrate it against the Docker results, inside the training kernel, before trusting it: Kaggle runs Python 3.13, the sandbox runs 3.12. Whether bwrap, nsjail, firejail, `prlimit` or `unshare` are available on Kaggle is unknown and needs a one-cell probe.

### Cited Findings
- Measured (project):
  - `training/synthetic/` holds 189 scenarios. Each has `repo/`, `tests_poc/`, `tests_regression/`, `reference_fix.patch`, `scenario.json` and a `requirements.lock`, and **all 189 lockfiles say "stdlib only"**.
  - Imports across the synthetic code include `subprocess` (13), `urllib` (28), `sqlite` (22), `os` (71), `hashlib`, `secrets` and `hmac`.
  - — repository scan, 2026-10-19
- The laptop sandbox:
  - It uses `python:3.12-slim` pinned by digest, with harness tools pytest 8.4.2, pytest-timeout 2.4.0, ruff 0.13.3 and bandit 1.8.6. — [docker/sandbox-base.Dockerfile](../../docker/sandbox-base.Dockerfile), [docker/harness-requirements.in](../../docker/harness-requirements.in)
  - It runs with `--network none --read-only --pids-limit 256 --memory 2g --memory-swap 2g --cpus 2`, cap-drop ALL, no-new-privileges, user 10001. — [docs/07-sandbox.md](../../docs/07-sandbox.md)
- The laptop's verdict, measured (project):
  - `run.sh` runs each suite as `timeout 240 python -I /harness/pytest_runner.py -q -p no:cacheprovider -p pytest_timeout --timeout=30 -c /dev/null --rootdir=/work --junitxml=...`, with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and `HOME=/tmp`. The tests stay at read-only image paths outside the candidate repo. `pytest_runner.py` puts the repo on `sys.path` and `PYTHONPATH` only after pytest has started. — [docker/run.sh](../../docker/run.sh), [docker/pytest_runner.py](../../docker/pytest_runner.py)
  - A suite passes only if `rc == 0`, junit `total > 0` and there are no failures. `resolved = applied and poc_passed and regressions_passed`. ruff (`lint_ok`) and bandit (`rescan_clean`) are recorded but are not part of `resolved`. — [src/aeropatch/sandbox/sandbox.py L173-218](../../src/aeropatch/sandbox/sandbox.py), [src/aeropatch/contracts.py L86-104](../../src/aeropatch/contracts.py)
- The Kaggle training image: Python 3.13, torch 2.11 (task brief).
- The project's Kaggle kernel has `"enable_internet": true` (it pip-installs at start). — [training/kaggle/kernel-metadata.json](../../training/kaggle/kernel-metadata.json), [training/kaggle/kernel.py L56](../../training/kaggle/kernel.py)
- TRL reward functions can be `async`, and several are awaited concurrently, so test runs can overlap. — [TRL GRPO docs](https://huggingface.co/docs/trl/main/en/grpo_trainer)
- Python stdlib primitives:
  - `subprocess.run(..., timeout=)` kills and waits for the child when the timeout expires. — [Python subprocess docs](https://docs.python.org/3/library/subprocess.html)
  - `resource.setrlimit` with `RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_NPROC` and `RLIMIT_FSIZE` caps memory, CPU seconds, processes and file size. — [Python resource docs](https://docs.python.org/3/library/resource.html)
  - "The preexec_fn parameter is NOT SAFE to use in the presence of threads in your application. The child process could deadlock before exec is called." — [Python subprocess docs](https://docs.python.org/3/library/subprocess.html)
  - Linux `RLIMIT_NPROC` limits the number of processes, "more precisely on Linux, threads", for the real user ID. It is not enforced for processes with `CAP_SYS_ADMIN` or `CAP_SYS_RESOURCE`, or for real UID 0. — [setrlimit(2) man page](https://man7.org/linux/man-pages/man2/setrlimit.2.html)

### Inferences
**A minimal reward runner** (stdlib, about 40 lines, mirroring `run.sh` so the verdict means the same thing):
1. Copy `repo/` to a fresh `tempfile.mkdtemp()` and apply the candidate patch. A patch that does not apply gets reward 0, as `applied=False` does on the laptop.
2. Keep the tests in a separate directory outside the repo copy.
3. For each suite, run `[sys.executable, "limits.py", "-I", "pytest_runner.py", "-q", "-p", "no:cacheprovider", "-p", "pytest_timeout", "--timeout=30", "-c", "/dev/null", "--rootdir", tmp, "--junitxml", ...]`, using a copy of `pytest_runner.py` with its hard-coded `/work/repo` replaced by the temp path. Pass:
   - `timeout=240`;
   - `start_new_session=True`, plus `os.killpg` on timeout, because the stdlib timeout kills only the direct child, and the 13 `subprocess`-using scenarios spawn grandchildren;
   - `env={"PATH":..., "HOME": tmp, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}`, which strips `KAGGLE_*`, HF tokens and any Kaggle Secrets, the real assets at risk;
   - `cwd=tmp`.
4. `limits.py` is a 5-line exec wrapper. It calls `resource.setrlimit` for `RLIMIT_AS` (about 2 GB), `RLIMIT_CPU` (about 60 s) and `RLIMIT_FSIZE` (about 50 MB), then `os.execv(sys.executable, [sys.executable] + argv)`. The limits are therefore set in a fresh single-threaded process. Do **not** use `preexec_fn`: a GRPO trainer always has threads (torch, the dataloader, async reward functions), so it can deadlock.
5. Parse the junit XML exactly as `sandbox.py` does: rc 0, total > 0, no failures. Reward 1.0 if both suites pass, 0 otherwise. A partial reward for regression-only passes is optional.

**`RLIMIT_NPROC` is best-effort only.** It counts every process *and thread* of the same real UID, so a trainer with hundreds of threads would make every `subprocess` call inside a test fail with EAGAIN. Those scenarios would then fail for the reference fix and the candidate alike, and the reward goes silently to 0. Root ignores it entirely. Leave it out, or use `prlimit --nproc` only if the probe shows a separate UID is available. Rely on the timeout and the process-group kill instead.

**Threat level.** The candidate code is the project's own model editing the project's own small stdlib repos. The risk is accidental damage (runaway loops, fork storms, deleting files in cwd, huge writes), not an adversary. Rlimits plus a temp cwd cover that.

**Network is the gap.** With `enable_internet: true`, the `urllib` (SSRF-type) scenarios could make real requests. That makes rewards noisy, not unsafe. There are two fixes:
- Build a Kaggle dataset of wheels and run the GRPO kernel with `enable_internet: false`, which is offline for the whole session.
- Wrap each test in `unshare -rn` if the probe shows unprivileged user namespaces work.

**Calibrate before training, in the training kernel.** Run the calibration with the same runner, after the model has loaded and the trainer's threads exist, so that a limit problem shows up here and not as a flat reward later. Run all 189 scenarios twice: (a) with no patch and (b) with `reference_fix.patch`. The PoC must fail on (a), and both suites must pass on (b). Diff the results against the laptop's Docker results. Drop from the reward set any scenario that disagrees, for example through 3.12/3.13 differences. This takes a few CPU-minutes.

**Probe cell** for the next kernel run: `which bwrap nsjail firejail prlimit; unshare -rn true; echo $?; nproc; free -g; id`.

**pytest-timeout** has to be pip-installed on Kaggle to match the harness, or the run relies on the subprocess timeout alone.

### Gaps
- No source on whether bwrap, nsjail, firejail or unprivileged user namespaces are available in Kaggle's 2026 image, or whether Kaggle sessions run as root. The probe cell above answers all of it.
- No source on the vCPU count of the "GPU T4 x2" shape in 2026. It limits how many tests run in parallel.
- Whether all 189 scenarios behave the same on Python 3.13 as on 3.12 is unknown until the calibration pass.

## 4. Kaggle quotas and session limits (2026)

### Takeaway
Kaggle offers about **30 GPU-hours a week** (Kaggle says "or sometimes higher depending on demand"), **12 h sessions** for GPU and CPU (9 h for TPU), a 20 GB `/kaggle/working` output and optional internet. "GPU T4 x2" appears to cost the same quota per hour as a single GPU (only a forum excerpt supports this). Realistically that means two or three 3–4 h training sessions a week, or one long GRPO session plus one export session.

### Cited Findings
- "You can use up to a quota limit per week of GPU. The quota resets weekly and is 30 hours or sometimes higher depending on demand and resources." — [Kaggle Efficient GPU Usage Tips (search excerpt)](https://www.kaggle.com/docs/efficient-gpu-usage)
- "A free weekly GPU quota, guaranteed at 30 hours and floating higher when capacity allows, with sessions capped at 12 hours for CPU and GPU and 9 hours for TPU (checked August 2026)". — [clusy.io Colab vs Kaggle 2026](https://www.clusy.io/compare/colab-vs-kaggle). This is a third-party source, but it matches Kaggle's own wording.
- On the T4 x2 launch: "there is no change to GPU quotas and both GPU ..." — [Kaggle discussion 361104 (excerpt only)](https://www.kaggle.com/discussions/product-feedback/361104)
- A 12 h runtime is reported on the Kaggle forums: "It seems the limit has been increased to 12 hours"; "30 hours per week now". — [Kaggle forum 286404](https://www.kaggle.com/general/286404); [Kaggle forum 397547](https://www.kaggle.com/discussions/general/397547)
- A 20-minute idle timeout applies to interactive sessions. This is a weak source (a video description). — [YouTube](https://www.youtube.com/watch?v=IMVjEsKX5UQ)
- Colab Pro and Pro+ add 15 or 30 extra Kaggle GPU-hours a week. Both are paid, so the free-only rule excludes them. — [Kaggle announcement 575468](https://www.kaggle.com/discussions/product-announcements/575468)
- Measured (project):
  - `/kaggle/working` "holds 20 GB and becomes the kernel's output". — [training/kaggle/kernel.py L6](../../training/kaggle/kernel.py)
  - No L4 is available to this account ("a kernel that asks for one gets no GPU").
  - The CLI shows no log while a kernel runs.
  - — [NOTES.md](../../NOTES.md)
- Kaggle's main Notebooks doc (scraped 2026-10-18) still describes "a single NVIDIA Tesla P100" and "TPU v3-8". **The page content is outdated** compared with the T4 x2 shape the project uses, so do not rely on it for limits. — [Kaggle Notebooks docs](https://www.kaggle.com/docs/notebooks)

### Inferences
**Weekly budget at 30 h:**

| Week plan | GPU hours |
|---|---|
| RFT (about 3.8 h) + DPO (about 3 h) + an export/scale session (about 1.5 h) + smoke tests (about 2 h) | about 10 h, which leaves room for one 300-step GRPO run (about 9 h) |
| 1,000 GRPO steps | about 22–31 h, the whole week |

**Session length.** The 12 h cap means long GRPO runs need `save_steps` checkpoints written to `/kaggle/working` (≤ 20 GB, about 100 MB a LoRA checkpoint) and a resume path through a Kaggle dataset.

**P100 is irrelevant here.** Unsloth's T4 notebooks and the Qwen3.5 Triton kernels target the T4. P100 support for these kernels was not checked.

### Gaps
- The account's exact current quota is shown only in the Kaggle account settings and was not checked. The official docs page could not be rendered.
- Whether CPU-only sessions have a weekly cap was not found. That matters if merges and exports are moved to CPU sessions.

## 5. Laptop throughput, memory risks, and the laptop/Kaggle split

### Takeaway
The laptop produces about **360 verified samples an hour serially**, or **about 600 an hour if generation and Docker verification overlap**. 189 scenarios × 8 samples takes about 2.5–4.5 h, which is overnight-safe if memory is capped. The laptop/Kaggle split only works as **batched off-policy rounds**, one round a day at most. That is iterated RFT or DPO, not online GRPO.

### Cited Findings
- Measured (task brief):
  - Ollama Q4_K_M on the GPU at 8k context: 46.5 tok/s, about 6 s a repair attempt.
  - A sandbox pytest run takes "a few seconds".
  - The 9B teacher runs at about 7 tok/s.
  - 16 GB RAM with a tight commit limit; heavy Python beside Ollama and Docker has caused out-of-memory failures (WinError 1455).
- Ollama: `OLLAMA_NUM_PARALLEL` defaults to 1, and "Required RAM will scale by `OLLAMA_NUM_PARALLEL` * `OLLAMA_CONTEXT_LENGTH`". The K/V cache can be quantized when Flash Attention is enabled (`OLLAMA_KV_CACHE_TYPE`, default f16). Models stay loaded for 5 min by default (`keep_alive`). — [Ollama FAQ](https://docs.ollama.com/faq)
- WSL2 (Docker Desktop's VM): `.wslconfig` `memory` defaults to "50% of total memory on Windows" (8 GB here) and `swap` to 25%. The docs' example caps it with `memory=4GB`. `autoMemoryReclaim` defaults to `dropCache`. — [Microsoft Learn, WSL config (updated 2026-10-16)](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)
- Each sandbox container is capped at `--memory 2g --memory-swap 2g --cpus 2`. — [docs/07-sandbox.md](../../docs/07-sandbox.md)
- TRL's server mode needs the trainer to reach a running vLLM server over HTTP on separate GPUs. `rollout_func` must return `prompt_ids`, `completion_ids` and `logprobs`, and is experimental. — [TRL GRPO docs](https://huggingface.co/docs/trl/main/en/grpo_trainer)

### Inferences
**Throughput:**
- Serial: about 6 s to generate plus about 3–5 s to verify, so 9–11 s a sample, or about 330–400 an hour.
- Pipelined (one generator thread, one verifier thread, which works because Docker runs on CPU while Ollama runs on the GPU): bounded by generation at about 6 s, so about 600 an hour.
- Sampling N times from the same prompt back to back lets Ollama reuse the prompt's KV prefix, so real numbers may be a little better. Measure it.

| Samples per scenario | Total | Serial | Pipelined |
|---|---|---|---|
| × 4 | 756 | about 2.1 h | about 1.3 h |
| × 8 | 1,512 | about 4.2 h | about 2.5 h |
| × 16 | 3,024 | about 8.4 h | about 5 h |

A 13-scenario dev check × 8 takes about 10–20 min.

**Parallel requests:** do not assume `OLLAMA_NUM_PARALLEL` > 1 fits in 4 GB at 8k context. Memory scales with it. Qwen3.5's few full-attention layers keep the KV cache small, so 2 might fit, but that needs measuring (check `ollama ps` for 100% GPU).

**Memory risks.** The risky combination is Ollama's runner, Docker Desktop's VM (up to 8 GB by default) and any Python job.

| Mitigation | Detail |
|---|---|
| Cap the VM | `[wsl2] memory=4GB` in `%UserProfile%\.wslconfig` (2 containers × 2 GB) |
| Few containers | Run 1–2 at a time |
| Light driver | Keep the rollout driver small (no torch import) and resumable: append JSONL per sample and skip done (scenario, seed) keys on restart |
| Isolation | Never run a merge, export or eval in Python beside the rollout run |

**The split (one "round"):**
1. Export the current policy GGUF (already part of every Kaggle session).
2. On the laptop, sample N per scenario at temperature 0.7–1.0, verify in Docker and write JSONL. Takes 1.5–4.5 h.
3. `kaggle datasets version` the JSONL. Takes minutes.
4. A Kaggle RFT or DPO session. Takes 2–4 h.
5. Download the GGUF (`fetch_output.py`) and evaluate on the laptop.

A round therefore runs about 6–10 h end to end, about one a day.

**Why GRPO cannot use the split.** GRPO changes the weights every step (about 1.5 min here). A laptop round trip (GGUF export, download, Ollama reload) takes hours. Laptop samples are therefore stale one step after they arrive, and that alone rules it out. The plumbing is also against it:
- TRL's server mode needs the trainer on Kaggle to reach a generation server on the laptop, which sits behind home NAT;
- `rollout_func` must return `prompt_ids`, `completion_ids` and `logprobs` from the same weights.

**So GRPO is Kaggle-only (rewards computed there, §3), and the laptop's role is evaluation.**

### Gaps
- The exact Docker verification time per sample (cold `docker run` against a warm container plus `docker exec`) is "a few seconds" and needs measuring.
- Whether `OLLAMA_NUM_PARALLEL=2` fits on the 3050 at 8k context with this model is not measured.
- Whether Ollama 0.40.3 can return per-token logprobs was not checked. It would not rescue on-policy GRPO anyway, because of the staleness above.

## 6. Weight interpolation, LoRA scaling and merging: exact tooling

### Takeaway
The lowest-risk route is to **scale the LoRA in PEFT before the existing Unsloth merge and GGUF export**:
- edit `lora_alpha` in `adapter_config.json` (16 → 8 halves the delta), or
- wrap the merge in `peft.helpers.rescale_adapter_scale`.

For fast A/B sweeps without re-exporting, `llama-server --lora-scaled adapter.gguf:S` on a recent llama.cpp build works. Qwen3.5 LoRA-to-GGUF conversion was only fixed on 2026-09-30. Ollama's `ADAPTER` has no scale setting.

### Cited Findings
- PEFT LoRA scaling is `lora_alpha/r`, or `lora_alpha/math.sqrt(r)` with `use_rslora=True`. — [PEFT LoRA reference](https://huggingface.co/docs/peft/package_reference/lora)
- `peft.helpers.rescale_adapter_scale(model, multiplier)` is a "Context manager to temporarily rescale the scaling of the LoRA adapter". "applying this context manager with multiplier in [0, 1] is strictly equivalent to applying wise-ft". — [PEFT helpers v0.21.0](https://huggingface.co/docs/peft/package_reference/helpers)
- `add_weighted_adapter(adapters, weights, adapter_name, combination_type=...)` supports `svd` (the default), `linear`, `cat`, `ties`, `dare_ties`, `dare_linear` and `magnitude_prune` among others. `cat` and `svd` are precise and `linear` "is a rough approximation". `svd` is not supported in fp16 or bf16. — [PEFT LoRA reference](https://huggingface.co/docs/peft/package_reference/lora)
- llama.cpp at runtime:
  - `--lora-scaled FNAME:SCALE` (default scale 1.0; values above 1 allowed).
  - `llama-server`'s `/lora-adapters` endpoint sets global scales, and a per-request `lora` array overrides them. — [simplified.guide, llama.cpp server LoRA scales](https://www.simplified.guide/llama-cpp/server-set-lora-adapter)
- llama.cpp merge: `llama-export-lora -m base.gguf --lora-scaled a.gguf:0.5 -o out.gguf`. The default output is `ggml-lora-merged-f16.gguf`. — [llama.cpp export-lora README](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/export-lora/README.md)
- The Qwen3.5 LoRA conversion crash in `convert_lora_to_gguf.py` (V-head reorder on linear-attention `out_proj`/`in_proj_*` tensors; issue #21125) was **fixed by PR #28324, merged 2026-09-30**. An earlier fix (#23969) was closed unmerged. — [llama.cpp #28324](https://github.com/ggml-org/llama.cpp/issues/28324); [llama.cpp #23969](https://github.com/ggml-org/llama.cpp/pull/23969)
- Ollama `ADAPTER`:
  - It applies a LoRA to the `FROM` base, and "If the base model is not the same ... the behaviour will be erratic".
  - Safetensors adapters are listed only for Llama, Mistral and Gemma; GGUF adapters are accepted.
  - **There is no scale parameter.**
  - This is from the v0.9.0 docs, which may be outdated. The current docs.ollama.com Modelfile page has no ADAPTER section.
  - — [Ollama modelfile.md @ v0.9.0](https://raw.githubusercontent.com/ollama/ollama/v0.9.0/docs/modelfile.md); [docs.ollama.com/modelfile](https://docs.ollama.com/modelfile)
- A Qwen3.5 caveat on Ollama: "newer GGUFs don't work in Ollama anymore. You'll have to remove the vision model". This is a 35B-A3B user report of unknown date. — [HF discussion](https://huggingface.co/unsloth/Qwen3.5-35B-A3B-GGUF/discussions/14)
- Measured (project): `lora_alpha = r = 16`. Targets are q/k/v/o/gate/up/down. The PEFT adapter is saved next to the GGUF. Unsloth writes no Ollama Modelfile for this model ("no template mapping found"). — [training/finetune.py](../../training/finetune.py); [NOTES.md](../../NOTES.md)

### Inferences
**Exact recipe for a scaled GGUF** (merged weights = base + s·ΔW, which is base-to-fine-tune interpolation):
1. Copy `adapter/`, set `"lora_alpha": 16*s` in `adapter_config.json`, keep `r=16`, and leave `use_rslora` unset.
2. Load it with Unsloth in the Kaggle session.
3. Run `save_pretrained_gguf(..., quantization_method="q4_k_m")` exactly as now.

Three scales (0.25, 0.5, 0.75) add 3 exports to one session, about 1–1.5 h of GPU, given that 4 exports plus training take about 2.5 h. No new tooling is needed, and Ollama's Modelfile stays as it is.

**Laptop-only sweep** (no Kaggle): build a recent llama.cpp (≥ 2026-09-30) and convert the PEFT adapter with `convert_lora_to_gguf.py --base <HF base dir>`. Then serve the *base* Q4_K_M with `llama-server --lora-scaled lora.gguf:0.5`, or change the scale per request through `/lora-adapters`. The eval harness would point at llama-server's OpenAI-compatible endpoint instead of Ollama. The project's adapter targets q/k/v/o/MLP; in Qwen3.5 the `q/k/v/o_proj` names exist only on the full-attention layers, and the linear-attention layers use `in_proj_*`/`out_proj`. So the V-head-reorder crash may not even trigger, but use a build with #28324 anyway. Caveat: the HF base needed for conversion is the 16-bit checkpoint (about 8–9 GB of disk). Store it on F: or D:, never C:.

**Merging two fine-tunes** (say v1 and v2, or SFT and DPO adapters): `add_weighted_adapter(..., combination_type="cat")` is exact. Use `linear` only for same-rank adapters with that caveat. Avoid `svd`, which is unsupported in fp16 on a T4. Full-weight merging tools (mergekit) were not checked for `qwen3_5` support.

### Gaps
- Whether Ollama 0.40.3 applies a GGUF LoRA (`ADAPTER x.gguf`) to a `qwen35` base at all is not documented. Treat it as unsupported and bake the scale into the merged GGUF.
- Whether `llama-export-lora` accepts a quantized (Q4_K_M) base was not stated. Assume an f16 base is needed (about 8.4 GB), which is a RAM risk on the laptop. Do it on Kaggle.
- mergekit or other model-merging support for the Qwen3.5 hybrid was not researched.

## 7. Wall-clock cost of each option on this hardware

### Takeaway
Ordered by cost:
1. LoRA scaling and lower LR, about 1–3 GPU-hours, no new risk.
2. RFT, about 3–5 laptop hours plus 2–4 GPU-hours a round.
3. DPO (reusing the RFT rollouts), plus 1.5–3 GPU-hours and a smoke test.
4. GRPO, a 1–2 h smoke test, then 7–9 h for the bare 300-step minimum, or 22–31 h (a whole week's quota) for 1,000 steps, with the highest software risk.

### Cited Findings
- SFT session cost: about 2.5 h including 4 GGUF exports; 128 steps in about 100 min. — task brief and [NOTES.md](../../NOTES.md)
- GRPO needs at least 300 steps, sometimes 1,000 or more, and "a minimum of 12 hours". — [Unsloth RL guide](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide)
- Qwen3.5-4B GRPO on a T4: about 80 s a step at G = 2, 1k + 1k tokens. — [Unsloth notebook](https://github.com/unslothai/notebooks/blob/main/nb/Qwen3_5_(4B)_Vision_GRPO.ipynb)
- Kaggle: about 30 GPU-hours a week, 12 h sessions. — [Kaggle docs excerpt](https://www.kaggle.com/docs/efficient-gpu-usage); [clusy.io](https://www.clusy.io/compare/colab-vs-kaggle)

### Inferences

| Option | Laptop hours | Kaggle GPU-hours | Software risk | Notes |
|---|---|---|---|---|
| (4a) LoRA scale 0.25 / 0.5 / 0.75, baked into GGUFs | eval only: about 0.5–1 h per scale on the dev and test sets (existing harness) | about 1–1.5 (one export session) | none | Or 0 GPU-hours with llama-server `--lora-scaled` after a recent llama.cpp build |
| (4b) Lower-LR retrain (e.g. 1e-4 or 5e-5), same data | eval about 1 h | about 2.5 | none | Same as the existing session |
| (4c) Merge v1 and v2 adapters (`cat`) | eval about 1 h | about 1 | low | PEFT only |
| (1) RFT on own verified fixes, 1 round, N = 8 | 2.5–4.5 rollouts plus about 1 eval | 2.1 (continue) to 3.8 (retrain) | none | One round a day; 2–3 rounds a week fit the quota |
| (2) DPO on pass/fail pairs (same rollouts as RFT) | 0 extra | about 0.5 smoke plus 1.5–3 | moderate (Unsloth DPO on Qwen3.5 on a T4 unshown; `bf16=False`; pairs ≤ 2,048 tokens a side) | Can run in the same session as RFT, as SFT then DPO |
| (3) GRPO with a pytest reward on Kaggle | 0 (eval only) | 1–2 smoke; 7–9 for 300 steps; 22–31 for 1,000 | high (text GRPO bugs, fp32 fallback, no vLLM, a sandbox without Docker) | Needs the §3 runner, the calibration pass, a wheels dataset for offline mode and checkpoint/resume |

### Gaps
- Every row except the existing SFT session is an extrapolation. The first real measurement of each, from a smoke test of 5–10 steps, should replace these figures before any longer run.
- The project's eval-harness runtime per model (dev 13 and test 54) was not measured here. The "eval about 1 h" entries are placeholders to swap for the project's own timing.
