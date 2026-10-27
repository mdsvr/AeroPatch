# Finding real security bugs in Python repos with free local tools (state as of 2026-10-24)

Context for the writer: AeroPatch measured 0 of 10 real Python CVEs found (85 findings, none within 3 lines of the bug) with Opengrep (22 custom rules) plus Bandit on 2026-10-24. The 10 CVEs were path traversal (mako), XSS (mistune), code injection (sqlparse), header injection (microdot), ReDoS, auth bypass, two PyJWT signature-verification bugs, and two DoS/resource-exhaustion bugs (hpack and similar). Research sessions hit a Firecrawl rate limit midway, so some sources below are search-result snippets only. Those are marked "(snippet)".

## 1. Taint and dataflow analysers for Python: what is free, local, and how well they recall real CVEs

### Takeaway
On the only public real-CVE Python SAST benchmark (108 CVEs, ICSE 2026), the best free tool, Semgrep, recalls 40.7% at 65.7% precision. CodeQL recalls 31.8% at 72.3%, Bandit 27.8% at 60.0%, and Pysa 0%. A new open-source interprocedural tool, PyFlow, reaches 48.1% recall at 71.2% precision. That benchmark covers only six injection-style CWEs, which match 3 of AeroPatch's 10 CVEs. CodeQL's licence forbids use on non-OSI-licensed (private) code, so it cannot be a default for users' own repos. Opengrep 1.30.0, already in AeroPatch's CI, has a `--taint-intrafile` flag that adds inter-procedural taint within one file for Python. AeroPatch is not using it today.

### Cited Findings
- **The benchmark.** The ICSE 2026 empirical study evaluated 8 Python SAST tools: DevSkim, Dlint, Bandit, Bearer, CodeQL, Pysa, Semgrep and Snyk. They were picked from 117 candidates and run on a real-world set of 108 unique CVEs across 62 projects, plus 120 LLM-generated synthetic programs. The authors call it "the first publicly available benchmark specifically designed to evaluate Python SAST tools"; the data is at github.com/Victor725/PySASTBench. — [ICSE'26 study, ACM DL](https://dl.acm.org/doi/10.1145/3744916.3773110)
- **Weak categories in that study:**
  - About 70% of CWE-79 (XSS, 15 of 22) and CWE-89 (SQLi, 7 of 10) went undetected by every tool combined.
  - Bandit missed about 90% of CWE-22 path traversal (26 of 29).
  - Semgrep was best on CWE-77, 502 and 94, where bugs are "misuse of specific, well-known functions (eval(), os.system(), pickle.load(), cursor.execute())".
  - CodeQL and Bearer did relatively better on CWE-22. — [ICSE'26 study](https://dl.acm.org/doi/10.1145/3744916.3773110)
- **Combining tools.** Bandit+Bearer+CodeQL+Semgrep detects 38.9% more than Bandit alone and 26% more than Semgrep alone, with a "modest reduction in Precision". CodeQL had 11 unique detections and Bandit 4. 83.3% of Bandit's detections (25 of 30) were also found by CodeQL or Semgrep. Bandit and Bearer had the highest false-positive rates on real code. — [ICSE'26 study](https://dl.acm.org/doi/10.1145/3744916.3773110)
- **Per-tool numbers on the 108 real CVEs**, as re-reported by the PyFlow paper (arXiv 2608.07026, submitted 2026-08-07, Gu, Yan, Yao). A report on the patched version counts as a false positive.

  | Tool | Precision | Recall | F1 |
  |---|---|---|---|
  | DevSkim | 82.4% | 13.0% | 22.5% |
  | Dlint | 72.5% | 26.9% | 39.2% |
  | Bandit | 60.0% | 27.8% | 38.0% |
  | Bearer | 62.3% | 35.2% | 45.0% |
  | CodeQL | 72.3% | 31.8% | 44.2% |
  | Pysa | 0.0% | 0.0% | 0.0% |
  | Semgrep | 65.7% | 40.7% | 50.3% |
  | Snyk | 80.0% | 11.9% | 20.7% |
  | PyFlow | 71.2% | 48.1% | 57.5% |

  — [PyFlow, arXiv 2608.07026](https://arxiv.org/html/2608.07026v1)
- **The CWEs covered** by both benchmarks are CWE-77, 502, 94, 79, 22 and 89 only. — [PyFlow](https://arxiv.org/html/2608.07026v1)
- **PyFlow itself:**
  - Open source at github.com/ZJU-PL/pyflow.
  - On the synthetic set, aggregate precision/recall/F1 is 83.7/85.8/84.8. Its misses come from "library-code flows with incomplete stubs and dynamically-constructed attribute names (setattr)".
  - Runtime on real projects: 46.5% finished within 5 s and 81.8% within 30 s; 45 timed out and 2 failed. The machine was an i7-13700H laptop-class CPU. — [PyFlow](https://arxiv.org/html/2608.07026v1)
- **Pysa on the synthetic set:** 2.5% recall and 60.0% precision, which "reflects its sparse report set". — [PyFlow](https://arxiv.org/html/2608.07026v1)
- **How Semgrep was characterised:** "Although Semgrep supports intraprocedural taint analysis, most of its rules rely on code pattern matching for vulnerability detection." Versions tested: Semgrep 1.101.0, CodeQL CLI 2.20.0, Bandit 1.8.0, Pyre-check (Pysa) 0.9.23. — [ICSE'26 study](https://dl.acm.org/doi/10.1145/3744916.3773110)
- **What "intra-procedural only" means in practice:**
  - Semgrep moved cross-function taint and fingerprinting to its commercial platform in late 2024. Cross-file analysis is commercial only.
  - Opengrep, a January 2025 fork of Semgrep CE, restores cross-function taint via `--taint-intrafile`. One source says this tracks constructor/field assignment, inter-method flow, higher-order functions and collection methods.
  - It stays inside one file. Cross-file flows need commercial Semgrep or another tool.
  - Sources conflict on Opengrep version numbers.

  — [NHI Mgmt Group / Aikido, 2026-05-12](https://nhimg.org/articles/opengreps-first-year-shows-why-deterministic-sast-still-matters/); [appsecsanta Opengrep vs Semgrep](https://appsecsanta.com/opengrep-vs-semgrep); [Semgrep feature definitions](https://docs.semgrep.dev/references/feature-definitions)
- **Local check, 2026-10-24.** `F:\AeroPatch\.tools\opengrep.exe --version` prints 1.30.0. `opengrep scan --help` lists `--taint-intrafile`, described as "Enable intra-file inter-procedural taint analysis. Supported languages: ... Python ...". It also lists `--guarded-taint-signatures`, which attaches branch-condition guards to taint effects. — local command output (no URL)
- **CodeQL licence**, GitHub CodeQL Terms and Conditions in the codeql-cli-binaries LICENSE.md, last changed 2026-02-02:
  - "Open Source Codebase" means one "released under an OSI-approved License".
  - Permitted: "Perform analysis on the Open Source Codebase", and generating databases for automated analysis/CI/CD only "If the Open Source Codebase is hosted and maintained on GitHub.com".
  - Not permitted: use "in connection with any codebase that is not an Open Source Codebase (e.g., code in a private repo in GitHub)".
  - These restrictions lift only under a paid GitHub Advanced Security licence. — [codeql-cli-binaries LICENSE.md](https://github.com/github/codeql-cli-binaries/blob/main/LICENSE.md)
- **GitHub docs** say "The CodeQL CLI is free to use on public repositories" and available in private repositories for orgs on GitHub Team/Enterprise with Code Security (snippet). — [GitHub Docs: CodeQL CLI](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-cli)
- **Joern** documents a taint-analysis engine over code property graphs. Python coverage (pysrc2cpg) was not confirmed in this session. — [Joern docs](https://docs.joern.io/)
- **Pysa** is Pyre's taint analyser and publishes its own guidance on false positives and negatives. — [Pysa docs](https://pyre-check.org/docs/pysa-false-positives-negatives)
- **Per-commit scanning blind spot.** CrossCommitVuln-Bench collects 15 real Python CVEs that span several commits and are invisible to per-commit Semgrep/Bandit scanning (snippet). — [OpenReview PDF](https://openreview.net/attachment?id=jWVoTxGSyb&name=pdf)

### Inferences
- **The 0 of 10 fits published numbers.**
  - Only 3 of the 10 CVEs (mako CWE-22, mistune CWE-79, sqlparse CWE-94) fall inside any Python SAST benchmark's CWE set.
  - Even there, published recall is 28–48%, and CWE-79 and CWE-22 are the weakest categories for Bandit and pattern rules.
  - The other 7 (JWT verification, ReDoS, hpack DoS, header injection, auth bypass) are logic or resource bugs inside a library. They have no source-to-sink flow for a taint engine to follow.
  - So taint or dataflow tools would lift the ceiling to roughly 1–2 of these 10, not to 10.
- **Cheapest step: turn on `--taint-intrafile`.** It is already shipped in the pinned Opengrep, free and LGPL. Pair it with taint-mode rules (`mode: taint`) instead of pattern rules.
- **PyFlow** is the strongest open interprocedural Python option on paper. It is a 2026 research prototype; its stability on Windows and its licence were not checked.
- **Do not make CodeQL a default.** Running it on a user's private or unlicensed repo breaches the 2026 terms. It can only be an opt-in for OSI-licensed public code. The same applies to IRIS, which is built on CodeQL.
- **Drop Pysa for detection.** It scores 0% recall on the real benchmark and needs heavy model/stub configuration.

### Gaps
- Maintenance status in 2026 of Pysa, PyT (python-taint) and Joern's Python frontend was not verified. Searches returned no repo status.
- No measured recall was found for Opengrep's `--taint-intrafile` on real Python CVEs. The ICSE'26 study used Semgrep 1.101.0 without cross-function taint.
- PyFlow's licence, Windows support and memory use were not checked.

## 2. Community rule sets: licences, size, precision

### Takeaway
Semgrep-maintained registry rules are under the Semgrep Rules License v1.0, which allows only internal business use and forbids redistribution or offering them as a service. AeroPatch cannot bundle them. Opengrep ships no rules ("bring your own"). Its community rules repo exists, but its licence and size were not verified in this session.

### Cited Findings
- **Semgrep Rules License v1.0:** "You may use the rules only for your own internal business purposes. This license does not allow you to distribute the rules, or to make them available to others as a service." Modified copies must carry notices. — [Semgrep Rules License](https://semgrep.dev/legal/rules-license/)
- **When the change happened:** Semgrep's 2024 announcement says Semgrep-maintained rules are now under that licence, limiting them "to internal, non-competing, and non-SaaS contexts". — [Semgrep blog 2024](https://semgrep.dev/blog/2024/important-updates-to-semgrep-oss/)
- **Semgrep's own comparison:** Opengrep rules are "Bring your own", Semgrep CE uses community rules from the registry, and the paid platform adds Pro rules. — [Semgrep docs: Opengrep comparison](https://docs.semgrep.dev/faq/comparisons/opengrep)
- **The paid catalogue:** "20000+ proprietary rules across SAST, SCA, and secrets". — [semgrep GitHub README](https://github.com/semgrep/semgrep)
- **Opengrep's engine licence** is LGPL-2.1. — [appsecsanta Opengrep review](https://appsecsanta.com/opengrep)
- **The fork's motive:** "Opengrep Forks Semgrep to Liberate Rulesets After License Change". — [InfoQ, 2025-02](https://www.infoq.com/news/2025/02/semgrep-forked-opengrep/)
- **opengrep-rules repo:** the search snippet says "It is now read-only". The licence text was not read. — [opengrep-rules LICENSE](https://github.com/opengrep/opengrep-rules/blob/main/LICENSE)
- **Measured precision of rule sets**, from the ICSE'26 study with Semgrep's default rules: 65.7% precision and 40.7% recall on 108 real CVEs. Bandit's built-in plugins scored 60.0% and 27.8%. — [PyFlow table](https://arxiv.org/html/2608.07026v1)

### Inferences
- **Free rule sources AeroPatch can bundle:** Bandit's plugins (Apache-2.0, per general knowledge, not checked this session), Dlint, AeroPatch's own 22 rules, and opengrep-rules if its licence checks out as LGPL.
- **Registry rules stay with the user.** Pulling Semgrep registry rules at runtime for the user's own internal use is likely allowed for the user but not for AeroPatch to redistribute. Treat that as a legal question.
- **More pattern rules will not fix the 0 of 10.** The missed classes are not single-call misuse patterns.

### Gaps
- Licence, rule count and Python rule count of opengrep-rules were not confirmed.
- No per-rule precision study for any open Python rule set was found.

## 3. LLM-assisted detection, 2024–2026, and what happens under 10B parameters

### Takeaway
LLMs help most when a static tool tells them where to look:
- **IRIS**, where the LLM infers taint specs that CodeQL then runs, doubled CodeQL's detections on Java (27 to 55 of 120).
- **Triage papers** report large precision gains on SAST alerts.
- **Function-level scanning by LLMs is near random** on clean benchmarks (PrimeVul).
- **Small models raise recall but flood alarms.** In IRIS, 7–8B models found 41–52 of 120 at about 95% false discovery rate.

Agentic systems (Aardvark, AIxCC, Big Sleep) rely on frontier models or C/Java fuzzing and are not local. Vulnhuntr, the Python-specific LLM hunter, says open models via Ollama fail to produce structured output.

### Cited Findings
- **IRIS headline result** (ICLR 2025). On CWE-Bench-Java, CodeQL alone detects 27; IRIS with GPT-4 detects 55 (+28) and improves average false discovery rate by about 5 points. It found 4 previously unknown vulnerabilities. — [IRIS, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/582d4e27fa24168f3af1f4582655034b-Abstract-Conference.html)
- **IRIS Table 1** (detected of 120 / detection rate / average false discovery rate):

  | Method | Detected | Rate | Avg FDR |
  |---|---|---|---|
  | CodeQL | 27 | 22.50% | 90.03% |
  | IRIS + GPT-4 | 55 | 45.83% | 84.82% |
  | IRIS + GPT-3.5 | 47 | — | 90.42% |
  | IRIS + Llama 3 8B | 41 | 34.17% | 95.55% |
  | IRIS + Llama 3 70B | 54 | — | 90.96% |
  | IRIS + Qwen-2.5-Coder 32B | 47 | — | 92.38% |
  | IRIS + Gemma-2 27B | 45 | — | 91.23% |
  | IRIS + DeepSeekCoder 7B | 52 | 43.33% | 95.40% |

  The authors call FDR "an upper bound". A manual check of 50 GPT-4 alarms gave a refined FDR of 46%. — [IRIS arXiv v3](https://arxiv.org/html/2405.17238v3)
- **IRIS specs and repo:**
  - LLM-inferred sinks reach up to 87.11% recall against CodeQL's sink specs (GPT-4). Other LLMs over-approximate sinks, which the authors argue widens coverage. — [IRIS arXiv v3](https://arxiv.org/html/2405.17238v3)
  - The repo quickstart runs with `--llm qwen2.5-coder-7b`.
  - CWE-Bench-Java grew to 213 CVEs across 49 CWEs (update 2025-08-30). — [iris-sast/iris GitHub](https://github.com/iris-sast/iris)
- **PrimeVul** (ICSE 2025). A 7B model scored 68.26% F1 on BigVul but only 3.09% F1 on PrimeVul. GPT-3.5 and GPT-4 were "akin to random guessing in the most stringent settings". — [PrimeVul, arXiv 2403.18624](https://arxiv.org/abs/2403.18624)
- **CleanVul.** Models fine-tuned on CleanVul reach 54.65% accuracy and 59.59% F1 on PrimeVul (snippet). — [CleanVul, arXiv 2411.17274](https://arxiv.org/html/2411.17274v2)
- **Repository-level benchmark** (Yildiz et al., ACL 2025). "Pairwise vulnerable" errors, where the model flags both the vulnerable and the patched version, range about 40–95% for LLMs and 35–50% for ReAct agents (snippet). — [Yildiz et al. PDF](https://yebof.github.io/assets/pdf/yildiz2025acl.pdf)
- **LLM as SAST triager** (all snippets; backbone sizes not confirmed):
  - **ZeroFalse** (arXiv 2510.02534) feeds SAST output plus flow traces and CWE context to an LLM. The best of 10 LLMs reached F1 0.912 on OWASP Java Benchmark and 0.955 on OpenVuln. — [ZeroFalse](https://arxiv.org/html/2510.02534v1)
  - **SAST-Genius** (arXiv 2509.15433) pairs Semgrep with a fine-tuned LLM. Precision is 89.5%, against 35.7% for Semgrep alone and 65.5% for GPT-4, across 25 GitHub projects. — [SAST-Genius](https://arxiv.org/pdf/2509.15433v3)
  - **"Sifting the Noise"** (arXiv 2601.22952). An agent setup kept 95.5% precision identifying false positives, against 36.4% for vanilla prompting. The authors warn that aggressive filtering can suppress real vulnerabilities. — [alphaXiv 2601.22952](https://www.alphaxiv.org/abs/2601.22952.md)
  - **Tencent industrial study** (arXiv 2601.18844) cautions that open-benchmark triage results may not transfer to enterprise code. — [arXiv 2601.18844](https://arxiv.org/html/2601.18844v1)
- **Semgrep's 2026 benchmark** (commercial, vendor claim). "Semgrep Multimodal" finds 3.5x more true positives than a tuned guided prompt at similar precision. They report "models miss up to 90% of endpoints alone" without deterministic analysis telling them where to look. — [Semgrep blog 2026](https://semgrep.dev/blog/2026/3-5x-more-true-positives-how-we-benchmark-ai-powered-detection/)
- **Vulnhuntr** (Protect AI, Python only):
  - It covers 7 classes: LFI, arbitrary file overwrite, RCE, XSS, SQLi, SSRF and IDOR.
  - It uses Jedi to request extra context until "the entire call chain from user input to server processing is complete", then reports a PoC and confidence score (7 = investigate, 8+ = likely real).
  - It requires Python 3.10 exactly.
  - On Ollama: "Ollama is included as an option, however we haven't had success with the open source models structuring their output correctly." — [protectai/vulnhuntr](https://github.com/protectai/vulnhuntr)
  - It reportedly found more than a dozen zero-days in popular Python GitHub projects (secondary report). — [Dark Reading](https://www.darkreading.com/application-security/open-source-llm-tool-finds-python-zero-days)
- **AISLE, 2026-04-14:**
  - Whole-file scanning with multi-round triage and grep access.
  - GPT-OSS-20B (3.6B active parameters) detected CVE-2026-4747 in 2 of 3 runs, stayed silent on the patched code 3 of 3 times, and found AISLE-2026-8073 in 3 of 3.
  - Qwen3-32B was the only model to raise a false positive on patched code (1 of 3).
  - The authors call it "a small operational benchmark, not a comprehensive evaluation". — [AISLE blog](https://aisle.com/blog/system-over-model-zero-day-discovery-at-the-jagged-frontier)
- **OpenAI Aardvark** (GPT-5, private beta). It identified "92% of known and synthetically-introduced vulnerabilities" in "golden" repositories; 10 of its open-source finds received CVEs. No false-positive rate or repo count was published. — [OpenAI: Introducing Aardvark](https://openai.com/index/introducing-aardvark)
- **DARPA AIxCC finals** (DEF CON 33, announced 2025-08-08):
  - Team Atlanta (ATLANTIS) won $4M, Trail of Bits (Buttercup) $3M and Theori $1.5M.
  - Buttercup found 28 vulnerabilities and applied 19 patches across 48 challenges.
  - The finalist systems are open source. — [DARPA](https://darpa.mil/news/2025/aixcc-results); [Trail of Bits](https://blog.trailofbits.com/2025/08/09/trail-of-bits-buttercup-wins-2nd-place-in-aixcc-challenge/)
- **Google Big Sleep** found SQLite CVE-2025-6965, a memory corruption flaw (CVSS 7.2) that was "known only to threat actors", in July 2025. In October 2024 it found an SQLite stack buffer underflow. — [The Hacker News, 2025-07](https://thehackernews.com/2025/07/google-ai-big-sleep-stops-exploitation.html)

### Inferences
- **Vulnhuntr out of the box is not viable.** For Qwen3.5-4B Q4 on 4 GB VRAM, its own authors say open models fail its structured-output format. Its 7 classes exclude every class AeroPatch missed except XSS. Its call-chain idea (Jedi context requests) is the reusable part.
- **IRIS shows the shape that works with small models:** the LLM labels sources and sinks, the static engine finds paths, and the LLM filters paths.
  - Recall gains survive at 7–8B. DeepSeekCoder 7B got 52 of 120, almost GPT-4's 55.
  - Precision does not survive: FDR is about 95%, versus 85% for GPT-4.
  - A 4B model would likely need the static engine and a strict triage step to keep false alarms down.
  - IRIS is Java-only and CodeQL-based. On this laptop the static half would have to be Opengrep `--taint-intrafile` or PyFlow.
- **A model should not scan whole repos function by function.** PrimeVul and pairwise results suggest it cannot tell vulnerable from patched code. Use it only on pre-selected paths or alerts.
- **The AISLE "3.6B active" model does not fit.** GPT-OSS-20B is a mixture-of-experts with about 21B total parameters (general knowledge), so it does not fit 4 GB of VRAM. The result was on C code with 3 runs.
- **AIxCC and Big Sleep** show agentic plus fuzzing approaches finding real bugs, but on C/Java targets with frontier models. They do not transfer to a 4B local model on Python without heavy adaptation.

### Gaps
- Backbone model sizes in ZeroFalse, SAST-Genius and "Sifting the Noise" were not read from the full papers. No triage result specifically for models under 10B on Python was found.
- Anthropic's vulnerability-research publications: no source was retrieved this session.
- AIxCC final-round target languages: from memory they were C and Java OSS projects, not verified this session. Whether ATLANTIS or Buttercup can run with a local small model is unchecked.
- Big Sleep 2025 total find count: not found.
- Codex Security as a product name for Aardvark: not confirmed.
- No IRIS-style result on Python was found.

## 4. The bug classes the scanners missed, and specialised free checkers per class

### Takeaway
Of the missed classes, only ReDoS has mature free static checkers; regexploit is reported to have low false-positive and false-negative rates. JWT verification, header injection, DoS limits and auth bypass have no dedicated free Python checker found in this session. Practical coverage for these is AeroPatch's own targeted rules for the misuse pattern in app code, plus dependency advisories (section 5) when the bug lives in a library.

### Cited Findings
- **ReDoS checkers:**
  - A SoK cites Parolini et al.: regexploit had low false-positive and false-negative rates, while safe-regex and redos-detector had much higher false-positive rates. Syntax-heuristic tools are fast but have accuracy limits. — [SoK on ReDoS, arXiv 2406.11618](https://arxiv.org/pdf/2406.11618)
  - Parolini et al.'s RAT terminates in under 1 s on 99.47% of 74,670 regexes and reports no false negatives with a low number of false positives. The paper names Python's `re` as backtracking-vulnerable. — [Parolini et al., TASE 2022](https://www-apr.lip6.fr/~mine/publi/article-parolini-al-tase22.pdf)
  - Regulator, a dynamic fuzzer, reported 7x more true positives than prior tools. — [USENIX Security 2022](https://usenix.org/conference/usenixsecurity22/presentation/mclaughlin)
  - Five public detectors "exhibit substantial disagreement" (abstract only). — [arXiv 2609.10294](https://arxiv.org/pdf/2609.10294)
  - The original rxxr static ReDoS analysis paper. — [arXiv 1701.04045](https://arxiv.org/pdf/1701.04045)
- **JWT, the PyJWT case:**
  - CVE-2022-29217 is key confusion in PyJWT before 2.4.0, where the token submitter can choose the algorithm.
  - Exposure depends on calling `jwt.decode` with `algorithms=jwt.algorithms.get_default_algorithms()` or all algorithms enabled.
  - The mitigation is pinning the algorithm list. — [GitLab advisory](https://advisories.gitlab.com/pkg/pypi/pyjwt/CVE-2022-29217/); [Vulert](https://vulert.com/vuln-db/CVE-2022-29217)
- **Benchmark coverage of these classes:** neither real-CVE Python SAST benchmark includes JWT, ReDoS, DoS, header-injection or auth-bypass CWEs. Both cover only CWE-77, 502, 94, 79, 22 and 89. — [PyFlow](https://arxiv.org/html/2608.07026v1)

### Inferences
- **ReDoS.** Run regexploit (Python, pip-installable, CPU-only) over regex literals extracted from the repo. It needs no model and gives cheap, high-precision findings for the ReDoS CVE class.
- **JWT.** A rule for `jwt.decode(...)` with `verify_signature: False`, `verify=False`, missing `algorithms=`, or `algorithms` taken from the token header catches app-level misuse. It cannot find bugs inside PyJWT itself. Those come from pip-audit/OSV.
- **Header injection** (CWE-113, microdot). A taint rule with sources being request data and sinks being response-header setters and `\r\n` checks. `--taint-intrafile` makes this feasible within a file.
- **DoS/resource limits** (hpack style). Static detection inside a library is unrealistic. App-level rules can flag unbounded `read()`, `json.loads` on raw request bodies without size caps, and decompression without limits. Dependency advisories cover the library bug.
- **Auth bypass** is a logic bug. No pattern catches it in general. This is where scoped LLM review of route handlers and decorators, IRIS-style, has the most potential and the highest false-alarm risk.

### Gaps
- No free dedicated checker was found for JWT misuse, HTTP header injection, resource-limit DoS or auth bypass in Python. The Semgrep registry has JWT rules, but none were retrieved, and they are under the restrictive licence anyway.
- No Python-specific ReDoS benchmark of regexploit was found. Per-tool numbers in arXiv 2609.10294 were not read.

## 5. Dependency-level detection (pip-audit, OSV-Scanner) as a precise complementary source

### Takeaway
All 10 of AeroPatch's benchmark CVEs are library CVEs. Any user repo that pins a vulnerable mako, mistune, sqlparse, microdot, PyJWT or hpack would get an exact advisory match from pip-audit or OSV-Scanner, so these tools are the clearest route to real findings for this set. That is an inference; no precision study comparing them was found. Their main false-positive sources are unreachable vulnerable code and imperfect dependency resolution.

### Cited Findings
- **Resolution noise.** OSV-Scanner 2.3.5 and later enables deps.dev-based transitive resolution for requirements.txt by default. The resolved graph does not reproduce pip's interpreter, platform, index options or constraints, so apparent Python false positives often come from resolution rather than reachability (practitioner guide, July 2026). — [OneUptime blog, 2026-07-23](https://oneuptime.com/blog/post/2026-07-23-requirements-false-positives-osv/view)
- **Native-dependency errors.** A cross-ecosystem study says current scanners miss vulnerabilities in vendored native libraries and raise false positives by ignoring distro backports. It evaluated 100,000 Python packages and reports up to 97% false-positive reduction over upstream version matching (research prototype). — [arXiv 2603.18693](https://arxiv.org/abs/2603.18693v1)
- **Reachability claims.** ReachGuard (PyPI) adds call-graph reachability on top of OSV data. It claims ">80% of flagged CVEs are completely unreachable"; this is unsourced README copy. — [ReachGuard on PyPI](https://pypi.org/project/reachguard/)

### Inferences
- **Run pip-audit or OSV-Scanner first; it costs nothing.** Both are free, local after advisory download, and CPU-only.
  - A finding names an exact CVE plus a fixed version, which yields a one-line, testable patch (bump the pin).
  - Where the app actually calls the vulnerable function, a cheap reachability check (grep or import graph for the advisory's affected symbols) keeps findings honest. It can also feed the LLM a focused context.
- **Score AeroPatch's 10-CVE benchmark separately from library detection.** Finding the bug inside the library's own source is a different task from flagging it in a downstream repo. The 0 of 10 measures the former.

### Gaps
- No primary pip-audit or OSV documentation was fetched this session, and no measured precision for either on Python projects was found.
- Offline-mode support (advisory DB caching) was not verified for either tool.

## 6. How to combine these on a 4 GB laptop to keep false alarms low

### Takeaway
The evidence supports a funnel: deterministic, high-precision sources first, then taint paths, then a small LLM used only as a judge on pre-selected paths. Stage by stage:
- **Deterministic sources:** dependency advisories, ReDoS checker, targeted misuse rules.
- **Taint paths:** Opengrep `--taint-intrafile`, optionally PyFlow.
- **Small LLM as judge:** decides on those pre-selected paths, does not scan whole repos.

LLM-generated sources and sinks can widen taint coverage, but at 7–8B they push false discovery to about 95%, so they need a second filter.

### Cited Findings
- Combining SAST tools raises coverage 26–39% at "a modest reduction in Precision". — [ICSE'26 study](https://dl.acm.org/doi/10.1145/3744916.3773110)
- IRIS's design: LLM-inferred specs, then CodeQL paths, then LLM contextual filtering. Recall doubled over CodeQL, but small-model FDR was 95.4–95.55%. — [IRIS arXiv v3](https://arxiv.org/html/2405.17238v3)
- Deterministic analysis telling the model where to look gave 3.5x more true positives than a guided prompt (vendor benchmark). — [Semgrep blog 2026](https://semgrep.dev/blog/2026/3-5x-more-true-positives-how-we-benchmark-ai-powered-detection/)
- Triage agents can reach 95.5% precision on false-positive identification, but aggressive filtering can suppress true vulnerabilities (snippet). — [Sifting the Noise](https://www.alphaxiv.org/abs/2601.22952.md)
- A fine-tuned triager on Semgrep output reached 89.5% precision versus 35.7% for raw Semgrep (snippet). — [SAST-Genius](https://arxiv.org/pdf/2509.15433v3)
- Function-level LLM detection is near random on PrimeVul. — [PrimeVul](https://arxiv.org/abs/2403.18624)
- Vulnhuntr-style call-chain context gathering is the Python-specific precedent, but open models failed its output format. — [Vulnhuntr](https://github.com/protectai/vulnhuntr)

### Inferences (proposed pipeline, ordered by precision; none of it is measured on AeroPatch yet)
1. **Dependency advisories** (pip-audit/OSV), with a light import or call reachability check. This is the highest-precision source and needs no GPU.
2. **Class-specific deterministic checkers:**
   - regexploit on extracted regexes.
   - Targeted Opengrep rules for JWT decode misuse, header-setter sinks, unbounded reads and decompression, `yaml.load`, `pickle`.
   - Bandit only for plugins that measured precision supports, given its 60% precision and that 83% of its finds overlap Semgrep/CodeQL.
3. **Opengrep taint-mode rules with `--taint-intrafile`**, plus optionally PyFlow for cross-file Python paths. These produce source-to-sink paths, the only candidates sent to the LLM.
4. **Qwen3.5-4B as a triager on each path or alert.** Show it the path and the functions on it plus their callers (Vulnhuntr-style context fetch via Jedi or the AST, capped to the context budget). Ask for a strict JSON verdict with a short reason.
   - At about 46 tok/s, a 200-token verdict takes roughly 4–5 s per alert, so dozens of alerts are affordable. A whole-repo function sweep is not.
   - Use grammar- or JSON-constrained decoding in Ollama, since Vulnhuntr's failure was output structure.
   - Bias the triager toward keeping findings when the path is complete. "Sifting the Noise" warns that aggressive filtering drops real bugs.
5. **Optional, measure before shipping: IRIS-style spec inference.** The 4B model proposes extra sources and sinks per project, for example framework request accessors and custom header writers. These are written as generated Opengrep taint rules, and their output goes back through step 4. Expect more recall and many more false alarms (IRIS small-model FDR about 95%), so gate by the step-4 verdict and a confidence threshold.
6. **Keep the triager out of logic-bug hunting by default.** Auth bypass and verification logic are the only classes left uncovered. A narrow, opt-in LLM review of auth decorators and token-verification functions is the remaining lever. Report its output as "worth a look", not as findings, to protect the user's trust given the false alarms already seen on their small repos.
7. **Report the benchmark in two layers.**
   - (a) Library-source detection, the current 0 of 10. The realistic ceiling is about 1–3 of 10 with taint, plus regexploit for the ReDoS one.
   - (b) Downstream-repo detection via advisories, about 10 of 10 when vulnerable versions are pinned (inference).

### Gaps
- No published result exists for a 4B local model as SAST triager on Python. AeroPatch would have to measure precision on its own labelled set, for example the Phase 0 label-precision table.
- The memory and runtime of `--taint-intrafile` on large Python repos on a 16 GB laptop were not measured.
