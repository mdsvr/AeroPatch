# 02 — Hardware Reality Check and Environment Setup

Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. What this machine actually has (checked 2026-09-24, updated 2026-09-29)

| Component | Value | Consequence |
|---|---|---|
| GPU | NVIDIA RTX 3050 Laptop, **4 GB VRAM**, driver 616.92 | Inference of ≤4B models at Q4 only; no local 3–4B training |
| RAM | ~15.7 GB | Tight for checkpoint conversion of 4B models (Unsloth advises ~32 GB) |
| CPU | Intel i5-12450H (8 cores / 12 threads) | Fine for 1–2 parallel sandbox containers |
| OS | Windows 11 Home | No Hyper-V isolation features of Pro; Docker Desktop's VM runs on WSL2 |
| WSL | WSL2, default distro Ubuntu | Installed but **not** the dev environment (§4) |
| Docker | 29.8.0 (Docker Desktop) | Good; but no gVisor support on Desktop for Windows |
| Ollama | 0.34.4 for Windows, models on `F:\.ollama\models` | Uses the 3050 through CUDA |
| Python | `python` resolves to the Store alias, but uv 0.10.2 + uv-managed CPython 3.12.11 exist | Project uses uv's 3.12 (`.python-version`); always `uv run` |

This table should drive the plan. Every choice in the later docs is sized to fit it.

## 2. What fits where

| Workload | Local (3050, 4 GB) | Free cloud (Kaggle/Colab T4 16 GB) | Paid cloud (L4/A10/A100) |
|---|---|---|---|
| Run a 1.5–4B model at Q4 GGUF, ~8k context | Yes | Yes | Yes |
| Run a 7–9B model at Q4 | CPU offload only, slow | Yes | Yes |
| Run Qwen3.6-35B-A3B / Qwen3-Coder-Next | No | No (too big) | Yes (≥24 GB) |
| QLoRA 1–1.5B model, seq ≤2k | Probably (pilot first) | Yes | Yes |
| QLoRA/LoRA 3–4B model | No | Yes (LoRA 16-bit ~10 GB for Qwen3.5-4B) | Yes |
| Merge + GGUF convert a 4B model | Risky (RAM) | Yes | Yes |
| Sandbox containers (pytest) | Yes, 1–2 at a time | n/a | n/a |
| Full PatchEval (230 images, ~500 GB) | No | No | Maybe |

Rule of thumb: **train in the cloud, infer locally, evaluate locally**.

## 3. Free GPU options for Week 3 (reported, check current limits)

- **Kaggle Notebooks**: ~30 GPU-hours/week, T4 ×2 or P100, 12 h max per session. Reliable quota,
  which makes it the recommended primary.
- **Google Colab free**: T4 when available, session limits vary and access is not guaranteed.
  Unsloth ships free Colab notebooks for Qwen3.5 0.8B/2B/4B.
- The T4 has no native bf16. Unsloth falls back to fp16 automatically when the dtype is left
  unset. Confirm this in the pilot run.
- Budget: one 50-step pilot (~15 min), then 1–3 full runs of 1–3 hours each. That fits one
  week of Kaggle quota with room to spare.

## 4. Environment layout: as set up on 2026-09-24 (Windows-native)

This environment was originally planned inside WSL2, but it was set up **Windows-native in
`F:\AeroPatch`**, because everything the orchestrator needs already runs on Windows:
- Docker Desktop (Linux containers) works natively, and the Docker SDK talks to it over the named pipe.
- Ollama for Windows uses the RTX 3050 through CUDA.
- uv, Python 3.12, git and `gh` are all installed.

The WSL route was blocked on this machine. Ubuntu's `sudo` needs a password, WSL has no Docker
socket until Docker Desktop's WSL integration is switched on, and reaching Windows Ollama from
WSL needs extra networking. Sandboxes are Linux containers either way.
- Venv: `F:\AeroPatch\.venv` (uv); deps pinned in `uv.lock`; run everything with `uv run ...`.
- `.gitattributes` forces LF line endings, so patches applied inside Linux containers aren't
  broken by CRLF.
- Scratch copies for sandbox runs are small toy apps, so NTFS bind-mount speed is acceptable.
  Revisit this if Tier B repos get large.
- Opengrep v1.30.0 is at `.tools\opengrep.exe` (gitignored; not on PATH). Bandit comes from the venv.
- WSL2 (Ubuntu 24.04) stays available, with `nvidia-smi` working, if you ever need Linux-only tooling.
- Local model server, two options:
  - **Ollama** (simplest). It runs on Windows or inside WSL2, exposes an HTTP API, and supports
    JSON-schema structured output.
  - **llama.cpp `llama-server`**. It gives the most control (GBNF grammars, exact quant choice,
    KV-cache settings). Qwen3.5 needs a recent build that supports the Gated DeltaNet layers;
    older builds fail to load it.

## 5. One-time setup checklist (as done on Windows, about 1 hour)

1. Install `uv`, git and Docker Desktop (Linux containers). Give the Docker VM enough memory
   (e.g. 8 GB) that sandboxes can't starve the model server.
2. `uv sync` in `F:\AeroPatch`; put `opengrep.exe` in `.tools\`.
3. Install Ollama for Windows; `ollama pull qwen3.5:4b` and
   `ollama pull qwen2.5-coder:3b-instruct-q4_K_M`. Before loading, ~3.9 GB of VRAM is free.
4. `uv run aeropatch build-base`, `uv run aeropatch validate --all`, `uv run pytest -q`.
   These prove Docker, the sandbox hardening and the scanners work on this machine.
5. Frontier access: either an Anthropic API key in `.env` (gitignored, never mounted into
   sandboxes), or Claude Code logged in on a subscription (`claude` on PATH; doc 04 §3).
6. Accounts you create yourself for Week 3: Kaggle and Hugging Face.
7. Tier B repos (Week 2) are cloned at pinned commits under `evaluations/`.
8. In a git worktree, set `AEROPATCH_OPENGREP=F:\AeroPatch\.tools\opengrep.exe`: `.tools\` is
   gitignored, so worktrees don't get a copy.

## 6. VRAM budget for local inference (approximate)

| Item | Qwen3.5-4B Q4_K_M | Qwen2.5-Coder-1.5B Q4_K_M | Qwen2.5-Coder-3B Q4_K_M |
|---|---|---|---|
| Weights | ~2.5–2.8 GB | ~1.0 GB | ~1.9 GB |
| KV/state at 8k ctx | small (hybrid layers keep most state constant-size) | ~0.2 GB | ~0.3 GB |
| CUDA/runtime overhead | ~0.3–0.5 GB | ~0.3 GB | ~0.3 GB |
| Fits in 4 GB? | Yes, with limited context | Easily | Yes |

**Measured 2026-09-29** (Ollama, 8k context, all layers on GPU, D6 dev run): Qwen3.5-4B peaks
at **3,787 MiB** total (3,643 MiB above the ~145 MiB idle), leaving ~300 MiB on the card.
Qwen2.5-Coder-3B peaks at 2,440 MiB. Qwen3.5-4B fits, but a larger context needs re-measuring.
Close browsers and other GPU apps during benchmark runs: the desktop compositor holds VRAM too.

## 7. Throughput expectations

- Measured 2026-09-29: Qwen3.5-4B decodes at **48 tok/s** and Qwen2.5-Coder-3B at 75 tok/s,
  with p50 latencies of 4.4 s and 1.4 s per single-attempt edit. A sandbox run takes ~1.5–2 s.
  With Ollama's default layer estimate, Qwen3.5-4B ran 54% on CPU at 9 tok/s; `num_gpu: 99`
  fixed that (doc 03 §9).
- A 40-scenario run with up to 3 repair turns means ≈120 generations and ≈120 sandbox runs.
  Plan on 1–2 hours of wall time per configuration, and run overnight where you can.
- Use sequential generation and at most two parallel sandboxes. The GPU is the bottleneck,
  so async concurrency at generation time buys nothing on this hardware.

## 8. Sandbox isolation on this OS (summary; detail in doc 07)

- Docker Desktop on Windows has no supported way to add gVisor (`runsc`). Enhanced Container
  Isolation is a paid Business-tier feature.
- Realistic baseline: hardened runc containers inside the Docker Desktop VM. Use
  `--network none`, `--cap-drop ALL`, a read-only root filesystem, `no-new-privileges`,
  pids/memory/CPU limits, and a non-root user.
- Everything already runs inside a utility VM, which adds a layer between your host and the
  container, though it isn't designed as a security boundary.
- Stronger option, if needed later: install native Docker Engine inside the WSL2 distro
  (not Desktop) and register gVisor there. Document this as a hardening upgrade, not a Week 1 task.

## 9. Troubleshooting (Windows + Docker Desktop + laptop GPU)

The first four rows were hit and fixed in Week 1.

| Symptom | Likely cause | Fix |
|---|---|---|
| Qwen3.5-4B at ~9 tok/s, half on CPU | Ollama's own offload estimate is conservative | `num_gpu: 99` (in `config.py`); all layers fit at 8k |
| No patch applies on Windows | Patch piped through text-mode stdin became CRLF | Write the patch to an LF file and apply that (`git_ops.py`) |
| `docker build` output crash (`None`) | cp1252 decoding of BuildKit output | Decode as UTF-8 (`sandbox.py`) |
| `TemporaryDirectory` cleanup error after `claude -p` | `claude.exe` still holds the dir briefly | `ignore_cleanup_errors=True` |
| Model loads but runs on CPU | GPU offload failed, VRAM full | Close GPU apps; lower the context; check `ollama ps` for "100% GPU" |
| Ollama/llama.cpp can't load Qwen3.5 | Build predates Gated DeltaNet support | Upgrade to a current release; pin the version once it works |
| Containers killed randomly | Docker VM memory limit too low | Raise the Desktop memory limit (`.wslconfig` `memory=`); keep sandboxes at 2 GB each |
| `pip install` fails in the sandbox | Run phase has no network (by design) | Install in the build phase (doc 07) |
| Laptop throttles during long runs | Thermal limits | Run on AC power, use a cooling pad, and record tok/s per attempt to spot throttling |
| Line-ending diffs in patches | Windows editors writing CRLF | `.gitattributes` forces LF; don't disable it |

Keep the machine as quiet as possible during benchmark runs: no browser tabs with video,
no games, no other GPU apps. The latency and VRAM numbers go into the README, so they
should come from a clean machine.

## 10. Decision summary

- Dev environment: Windows-native `F:\AeroPatch` + `uv` + Python 3.12 + Docker Desktop.
- Local inference: Ollama (used in Week 1) or llama.cpp, Q4_K_M GGUF, ≤4B parameters, all layers on GPU.
- Training: Kaggle T4 (primary), Colab T4 (backup); Unsloth + TRL; LoRA 16-bit for Qwen3.5,
  QLoRA only for Qwen2.5-Coder models.
- Evaluation: local, sequential generation, ≤2 parallel sandboxes, Python-only scenarios.
- Next doc: [03-models-local-slm.md](03-models-local-slm.md)
