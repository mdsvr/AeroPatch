# 16 — Sources and Verification Notes

Back to the index: [00-overall-plan.md](00-overall-plan.md)
All sources were accessed 2026-09-24. "Reported" means the figure came from a secondary source
or summarizer and should be checked against the primary source before you publish it.

## 1. Hardware facts (measured on this machine)

- `nvidia-smi`: NVIDIA GeForce RTX 3050 Laptop GPU, 4096 MiB, driver 616.92.
- System RAM ~15.7 GB; CPU Intel Core i5-12450H; Windows 11 Home; WSL2 default distro Ubuntu.
- Docker 29.7.2 present; `python` resolves only to the Microsoft Store alias (not installed).

## 2. Models and fine-tuning

- Qwen3.5-4B model card (license, context, thinking modes, LiveCodeBench v6 55.8, BFCL-V4 50.3):
  https://huggingface.co/Qwen/Qwen3.5-4B
- Qwen3.5 small series overview (0.8B/2B/4B/9B, March 2026): https://qwen.ai/blog?id=qwen3.5 ,
  https://artificialanalysis.ai/articles/qwen3-5-small-models
- Unsloth Qwen3.5 fine-tuning guide (LoRA VRAM table; "QLoRA not recommended"; ≥75% reasoning
  advice; GGUF export): https://unsloth.ai/docs/models/qwen3.5/fine-tune
- Unsloth requirements (system RAM guidance): https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements
- Unsloth 4 GB VRAM QLoRA guide PR (Llama-3.2-1B, ~1.5 GB peak, unmerged as of Sep 2026):
  https://github.com/unslothai/unsloth/pull/7605
- Qwen2.5-Coder-3B license (Qwen Research License, non-commercial):
  https://huggingface.co/Qwen/Qwen2.5-Coder-3B/blob/main/LICENSE
- Qwen2.5-Coder technical report: https://arxiv.org/pdf/2409.12186
- Qwen3-Coder-Next (80B/3B active, 70.6% SWE-bench Verified, reported): https://qwen.ai/blog?id=qwen3-coder-next
- Qwen3.6-35B-A3B: https://qwen.ai/blog?id=qwen3.6-35b-a3b
- Qwen3.8 lineup (no sub-10B dense model, reported): https://codersera.com/blog/qwen-3-8-model-lineup-2026/ ,
  https://github.com/QwenLM/Qwen3.8
- Gemma 4 model card and E2B/E4B details: https://ai.google.dev/gemma/docs/core/model_card_4 ,
  https://huggingface.co/google/gemma-4-E4B-it
- Gemma 4 fine-tuning VRAM (Unsloth): https://unsloth.ai/docs/models/gemma-4/train
- Qwen llama.cpp guide: https://qwen.readthedocs.io/en/latest/run_locally/llama.cpp.html

## 3. Frontier APIs

- Claude model IDs and prices: Anthropic model table as bundled with the Claude API skill
  (cached 2026-06-24); confirm at https://docs.anthropic.com before publishing costs.
- Gemini deprecations (2.0 Flash shutdown 2026-06-01; replacements; current Flash models):
  https://ai.google.dev/gemini-api/docs/deprecations
- Gemini pricing trackers (reported, volatile): https://pricepertoken.com/pricing-page/model/google-gemini-3.7-flash ,
  https://pricepertoken.com/pricing-page/model/google-gemini-3.5-flash , https://costgoat.com/pricing/gemini-api
- Official Gemini pricing (check here before quoting): https://ai.google.dev/gemini-api/docs/pricing

## 4. Protocols and frameworks

- MCP 2026-07-28 release notes: https://blog.modelcontextprotocol.io/posts/2026-07-28/
- MCP specification: https://modelcontextprotocol.io/specification/2026-07-28
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk ;
  v2 overview: https://pydantic.dev/articles/mcp-python-sdk-v2-beta
- FastMCP: https://github.com/PrefectHQ/fastmcp , https://gofastmcp.com/updates
- LangGraph 1.0 announcement: https://www.langchain.com/blog/langchain-langgraph-1dot0

## 5. Benchmarks and datasets

- PatchEval (repo, Verified leaderboard, Docker requirements): https://github.com/bytedance/PatchEval ;
  paper: https://arxiv.org/abs/2511.11019 ; dataset: https://huggingface.co/datasets/ByteDance/PatchEval
- Vul4Py (Python, paired exploit + functional oracles, 100 vulns): https://arxiv.org/abs/2608.00692
- CVE-Bench (Gatti, real-world CVE patching, Python): https://giovannigatti.github.io/cve-bench/
- CVE-Bench (Wang, Liu, Xiao; NAACL 2025; repair, 509 CVEs): https://aclanthology.org/2025.naacl-long.212/
- CVE-Bench (Zhu et al., UIUC; ICML 2025; exploitation, out of scope): https://arxiv.org/abs/2503.17332 ,
  https://github.com/uiuc-kang-lab/cve-bench
- SEC-bench (C/C++, sanitizer-verified): https://arxiv.org/pdf/2506.11791 , https://github.com/SEC-bench/SEC-bench
- OpenAI on SWE-bench Verified: https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- SWE-bench Pro leaderboard: https://labs.scale.com/leaderboard/swe_bench_pro
- SWE-smith: https://github.com/SWE-bench/SWE-smith , https://arxiv.org/pdf/2504.21798
- SWE-Gym: https://nlp.cs.berkeley.edu/pubs/Pan-Wang-Neubig-Jaitly-Ji-Suhr-Zhang_2025_SWEGym_paper.pdf
- MoreFixes: https://github.com/JafarAkhondali/morefixes
- MegaVul (C/C++): https://arxiv.org/pdf/2406.12415

## 6. Edit formats, repair and evaluation methodology

- Aider edit formats: https://aider.chat/docs/more/edit-formats.html ; unified diffs study:
  https://aider.chat/docs/unified-diffs.html
- Diff-XYZ benchmark (diff understanding / representations): https://arxiv.org/pdf/2510.12487
- Agentless (Xia et al., 2024), a fixed localize→repair→validate pipeline (arXiv 2407.01489).
- Olausson et al., "Is Self-Repair a Silver Bullet for Code Generation?" (ICLR 2024).
- Chen et al., "Evaluating Large Language Models Trained on Code" (2021): unbiased pass@k.

## 7. Security tooling and sandboxing

- Opengrep: https://www.opengrep.dev/ ; background on the fork: https://thenewstack.io/opengrep-launches-as-free-fork-after-semgrep-license-shift/
- Semgrep vs Opengrep (vendor view): https://semgrep.dev/docs/faq/comparisons/opengrep
- gVisor Docker quick start: https://gvisor.dev/docs/user_guide/quick_start/docker/
- Docker Desktop gVisor request (unsupported on Windows): https://github.com/docker/desktop-feedback/issues/364
- Docker Desktop WSL2 backend and best practices: https://docs.docker.com/desktop/features/wsl/ ,
  https://docs.docker.com/desktop/features/wsl/best-practices/
- Enhanced Container Isolation limitations: https://docs.docker.com/enterprise/security/hardened-desktop/enhanced-container-isolation/limitations/
- Rootless Docker + gVisor for untrusted code: https://www.sitepoint.com/isolate-untrusted-code-rootless-docker-gvisor/
- Securely deploying AI agents (Claude docs): https://code.claude.com/docs/en/agent-sdk/secure-deployment

## 8. Prior art (autonomous patching systems)

- DARPA AIxCC final results: https://www.darpa.mil/news/2025/aixcc-results ,
  https://aicyberchallenge.com/finals-winners-announcement/
- Buttercup (Trail of Bits, open source): https://trailofbits.com/buttercup/
- ATLANTIS (Team Atlanta): https://arxiv.org/pdf/2509.14589
- SoK on AIxCC: https://arxiv.org/html/2602.07666v2
- Google CodeMender preview: https://www.helpnetsecurity.com/2026/07/24/google-codemender-ai-agent-code-security/
- OpenAI Aardvark: https://thehackernews.com/2025/10/openai-unveils-aardvark-gpt-5-agent.html
- GitHub Copilot Autofix responsible-use notes: https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts/responsible-use-autofix-code-scanning

## 9. Compute

- Kaggle GPU usage docs: https://www.kaggle.com/docs/efficient-gpu-usage
- Colab free-tier limits overview (reported): https://aicreditmart.com/ai-credits-providers/google-colab-free-tier-t4-gpu-access-guide-2026/

## 10. Key claim → source map (the claims that change decisions)

| Claim used in these docs | Source | Confidence |
|---|---|---|
| Machine has an RTX 3050 4 GB, 16 GB RAM, no Python | Local `nvidia-smi` / system query | Measured |
| Gemini 2.0 Flash shut down 2026-06-01 | Google deprecations page | High (primary) |
| Don't QLoRA Qwen3.5; LoRA 4B ≈ 10 GB | Unsloth Qwen3.5 guide | High (primary) |
| Qwen2.5-Coder-3B is non-commercial | HF LICENSE file | High (primary) |
| Qwen3.5-4B is Apache-2.0, 262k ctx, LCB v6 55.8 | HF model card | High (primary) |
| MCP 2026-07-28 is stateless; Sampling/Roots/Logging deprecated | MCP blog | High (primary) |
| Python SDK v2 / FastMCP support the new spec | SDK pages, third-party posts | Medium |
| Docker Desktop for Windows lacks gVisor support | Docker feedback issue | Medium-high |
| PatchEval-Verified: 230 CVEs, Docker, ~500 GB, leaderboard 80%+ | PatchEval repo README | High (primary) |
| PatchEval paper best at release ≈ 23% | arXiv paper | High (primary) |
| OpenAI stopped using SWE-bench Verified | OpenAI post | High (primary) |
| Opengrep v1.27.1 (Aug 2026), LGPL-2.1 | Third-party review | Medium |
| Kaggle ~30 GPU-h/week | Kaggle docs, forum | Medium (quotas change) |
| Claude prices | Anthropic model table (cached 2026-06-24) | High, but re-check live |
| Gemini Flash prices | Third-party trackers | Low-medium (volatile) |

Anything rated "Medium" or lower should carry a "(reported)" tag or a link wherever it appears
in the public README.

## 11. Open items to verify before publishing

- [ ] Per-language count of PatchEval-Verified cases (Python share); it isn't in the sources checked.
- [ ] Current price of `gemini-3.8-flash` and whether Google's recommended replacement has changed.
- [ ] Claude prices on the live pricing page (the skill table is cached from 2026-06-24).
- [ ] Licenses of SWE-smith, SWE-Gym, MoreFixes, and the chosen teacher model.
- [ ] Current FastMCP / MCP Python SDK version numbers at project start; pin them.
- [ ] llama.cpp/Ollama minimum version for Qwen3.5 (Gated DeltaNet) support.
