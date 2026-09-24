# 02 — Hardware Reality Check and Environment Setup

Back to the index: [00-overall-plan.md](00-overall-plan.md)

## 1. What this machine actually has (checked 2026-09-24)

| Component | Value | Consequence |
|---|---|---|
| GPU | NVIDIA RTX 3050 Laptop, **4 GB VRAM**, driver 616.92 | Inference of ≤4B models at Q4 only; no local 3–4B training |
| RAM | ~15.7 GB | Tight for checkpoint conversion of 4B models (Unsloth advises ~32 GB) |
| CPU | Intel i5-12450H (8 cores / 12 threads) | Fine for 1–2 parallel sandbox containers |
| OS | Windows 11 Home | No Hyper-V isolation features of Pro; Docker runs via WSL2 |
| WSL | WSL2, default distro Ubuntu | Primary dev environment; CUDA works inside WSL2 |
| Docker | 29.7.2 (Docker Desktop) | Good; but no gVisor support on Desktop for Windows |
| Python | **Not installed** (only the Microsoft Store alias) | Install inside WSL2 via `uv` (below) |

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

## 4. Recommended environment layout

Work entirely inside WSL2 Ubuntu. Keep the repo on the Linux filesystem, not on `F:`.

- Path: `~/aeropatch` inside Ubuntu. From Windows you can reach it at
  `\\wsl$\Ubuntu\home\<user>\aeropatch`.
- Why not `F:\AeroPatch`? Bind mounts from NTFS into Linux containers are slow and cause
  file-permission and line-ending problems. The `docs/` folder can stay on `F:` or be copied over.
- Python: install `uv` in WSL2, then pin Python 3.12 per project with `uv python install 3.12`.
  `uv` covers venvs, lockfiles and tool installs, so no conda is needed.
- Docker: Docker Desktop with the WSL2 backend and "WSL integration" enabled for Ubuntu.
  The `docker` CLI inside WSL2 then talks to Desktop's engine.
- GPU in WSL2: the Windows NVIDIA driver provides CUDA to WSL2. Don't install a Linux NVIDIA
  driver inside WSL. Check with `nvidia-smi` inside Ubuntu.
- Local model server, two options:
  - **Ollama** (simplest). It runs on Windows or inside WSL2, exposes an HTTP API, and supports
    JSON-schema structured output.
  - **llama.cpp `llama-server`**. It gives the most control (GBNF grammars, exact quant choice,
    KV-cache settings). Qwen3.5 needs a recent build that supports the Gated DeltaNet layers;
    older builds fail to load it.

## 5. One-time setup checklist (about 1 hour)

1. Update WSL: `wsl --update` (PowerShell), then reboot WSL with `wsl --shutdown`.
2. In Ubuntu: install `git`, `build-essential`, and `curl`. Install `uv` from its official installer.
3. In Docker Desktop settings: enable the WSL2 engine and integration for Ubuntu, and set the
   resource limits (e.g. 8 GB RAM, 6 CPUs) so the sandbox can't starve the model server.
4. Check `docker run --rm hello-world` from inside Ubuntu.
5. Install Ollama (or build llama.cpp with CUDA), pull a 3–4B Q4 model, and check GPU offload
   in the logs. Before loading, VRAM should show about 3.5 GB free.
6. Create accounts (you do this yourself): Kaggle, Hugging Face, and the API consoles for your
   chosen frontier provider(s). Keep keys in an `.env` file in the repo root, listed in
   `.gitignore`, and never mounted into sandboxes.
7. Clone the scenario repos into `~/aeropatch/evaluations/dataset/` at pinned commits.

## 6. VRAM budget for local inference (approximate)

| Item | Qwen3.5-4B Q4_K_M | Qwen2.5-Coder-1.5B Q4_K_M | Qwen2.5-Coder-3B Q4_K_M |
|---|---|---|---|
| Weights | ~2.5–2.8 GB | ~1.0 GB | ~1.9 GB |
| KV/state at 8k ctx | small (hybrid layers keep most state constant-size) | ~0.2 GB | ~0.3 GB |
| CUDA/runtime overhead | ~0.3–0.5 GB | ~0.3 GB | ~0.3 GB |
| Fits in 4 GB? | Yes, with limited context | Easily | Yes |

These are estimates. Measure peak VRAM in Week 1 and record it, because it becomes a reported
metric in doc 12. Close browsers and other GPU apps during benchmark runs: Windows itself holds
some VRAM, and the desktop compositor alone can take a few hundred MB.

## 7. Throughput expectations

- A laptop 3050 decodes a 3–4B Q4 model at tens of tokens per second (measure it; don't assume).
  A 400-token edit therefore takes roughly 5–20 s, and prompt processing of a 3–6k-token
  context adds a few seconds.
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

## 9. Decision summary

- Dev environment: WSL2 Ubuntu + `uv` + Python 3.12 + Docker Desktop (WSL2 backend).
- Local inference: Ollama or llama.cpp, Q4_K_M GGUF, ≤4B parameters.
- Training: Kaggle T4 (primary), Colab T4 (backup); Unsloth + TRL; LoRA 16-bit for Qwen3.5,
  QLoRA only for Qwen2.5-Coder models.
- Evaluation: local, sequential generation, ≤2 parallel sandboxes, Python-only scenarios.
- Next doc: [03-models-local-slm.md](03-models-local-slm.md)
