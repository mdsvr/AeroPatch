# Verifying LLM security patches without a hand-written PoC, and triaging scanner findings in real Python repos (as of 2026-10-22)

Tags used below: **[Py]** Python, **[C/C++]**, **[Java]**, **[web]**, **[multi]** several languages; **[frontier]** large hosted models, **[≤10B]** small models; the year in brackets is the publication date. Results from 2024 or early 2025 are older. "Per search snippet" means the number came from a search-engine summary or abstract and was not checked against the paper's tables.

## Q1. LLM-generated vulnerability-witness / PoC / security tests: success rates, error rates, validation

### Takeaway
Frontier agents produce a working exploit or proof-of-vulnerability (PoV) for roughly 16-51% of real vulnerabilities. One unverified outlier, PAGENT, self-reports 64.6%. Most of this evidence is C/C++, Java or web. The closest Python evidence is functional bug reproduction from issues (SWT-bench), which rose from about 19% (2024) to a self-reported 58-70% (2026). Every benchmark accepts a generated test only if it fails on the vulnerable code and passes on the **human (golden) fix**. A user's repository has no golden fix, so that check cannot be reproduced there as published.

### Cited Findings
- **FaultLine** [Java/C/C++][frontier][2025]: on 100 known vulnerabilities it produced PoV tests for 16 (16%). The CodeAct 2.1 baseline produced 9. Python is not covered. — [arXiv 2507.15241](https://arxiv.org/abs/2507.15241). A third-party review notes the evaluation was a single run with no significance test. — [Pith review](https://pith.science/paper/2507.15241)
- **SEC-bench** [C/C++][frontier][2025]: the best agent reached 18.0% on PoC generation and 34.0% on patching. The authors attribute the difficulty to memory-safety bugs that need byte-exact payloads (per search snippet). — [arXiv 2506.11791](https://arxiv.org/pdf/2506.11791)
- **Web vulnerability reproduction** [web][frontier][2025]: end-to-end success below 25% (per search snippet). — [arXiv 2510.14700](https://arxiv.org/html/2510.14700)
- **PAGENT** [2026]: an LLM agent guided by static analysis and sanitizer feedback reports 64.6% PoC accuracy with DeepSeek 3.2, which it calls a 132% improvement over the prior best agent. This is per search snippet; the language mix and dataset were not checked. — [arXiv 2604.07624](https://arxiv.org/pdf/2604.07624)
- **CVE-Genie** [multi][frontier][2025; CCS 2026]: reproduced 428 of 841 CVEs from 2024-2025 (about 51%) with verifiable exploits, at an average $2.77 per CVE. The authors say standalone o3 could not reproduce even one CVE this way. Pipeline: processor, builder, exploiter, CTF-style verifier. — [arXiv 2509.01835](https://arxiv.org/html/2509.01835v1); [CCS 2026 PDF](https://seclab.bu.edu/people/gianluca/papers/cvegenie-ccs2026.pdf). The per-language breakdown was not retrieved; the page fetch was blocked.
- **SWT-bench** [Py][frontier][NeurIPS 2024, older]: a generated test counts as fail-to-pass (F→P) if it fails on the original code and passes after the golden patch. An issue counts as reproduced if at least one test is F→P and no test fails after the fix. Original results on SWT-bench Lite: SWE-Agent+ 19.2%, SWE-Agent 15.9%, direct prompting 3.6% (as summarised in the AssertFlip paper, per search snippet). — [AssertFlip, arXiv 2507.17542](https://arxiv.org/html/2507.17542v2). SWT-bench abstract: "generated tests are an effective filter for proposed code fixes, doubling the precision of SWE-Agent." — [arXiv 2406.12952](https://arxiv.org/abs/2406.12952)
- **Later Python issue-reproduction results** [Py][frontier][2025-2026], all self-reported and per search snippet:
  - AssertFlip: 43.6% on SWT-bench Verified. — [arXiv 2507.17542](https://arxiv.org/html/2507.17542v2)
  - ReProAgent: 58.43% on Lite and 70.30% on Verified; its strongest baselines were 38.0% and 62.4%. — [arXiv 2607.09123](https://arxiv.org/pdf/2607.09123)
  - e-Otter++: 63% average F→P on TDD-Bench Verified, a different benchmark. — [arXiv 2508.06365](https://arxiv.org/html/2508.06365v3)
- **TestGenEval** [Py][7B-405B][ICLR 2025]: 68,647 tests from 1,210 code/test file pairs in 11 Python repositories. The best model, GPT-4o, reached only 35.2% average coverage, with frequent assertion errors on complex code paths. The per-model table, including the 7B models, was not retrieved. — [arXiv 2410.00752](https://arxiv.org/pdf/2410.00752)
- **How often LLM-written failing tests are wrong** [Py][frontier][Oct 2025]: in agentic property-based testing with Hypothesis on 100 popular Python packages, manual review found:
  - 56% of the agent's bug reports were valid bugs, and 32% were worth reporting to maintainers.
  - Among the 21 top-ranked reports, 86% were valid and 81% reportable.
  - 5 bugs were reported (4 with patches) and 3 patches were merged.
  - So about 44% of the agent's "this test exposes a bug" claims were wrong.
  — [arXiv 2510.09907](https://arxiv.org/pdf/2510.09907)
- **PBT-Bench** [Py][2026]: 100 property-based-testing problems over 40 Python libraries with 365 injected bugs. Bug recall ranged from 42.1% to 83.4% across models (per search snippet, unverified). — [NeurIPS 2026 poster](https://neurips.cc/virtual/2026/poster/138920)
- **Open 7B-34B models writing unit tests** [Java][≤10B and larger][2024, older]: all models, GPT-4 included, underperformed EvoSuite on coverage, mainly because many generated tests were syntactically invalid (per search snippet). — [arXiv 2406.18181](https://web3.arxiv.org/pdf/2406.18181v1)
- **Validation rule in security benchmarks**:
  - PatchEval [Go/JS/Py][2025]: a test is a valid PoC only if "it fails on the pre-patch version but succeeds on the post-patch version." — [arXiv 2511.11019](https://arxiv.org/html/2511.11019v1)
  - Vul4Py [Py][2026] applies the same fail-before/pass-after rule. It admits only advisories that trace to exactly one fix commit, and that commit must add or change tests. (Carried from earlier AeroPatch notes, not re-fetched.) — [arXiv 2608.00692](https://arxiv.org/html/2608.00692v1)

### Inferences
- **Fail-to-pass without a golden patch is circular.** On a user's repository, AeroPatch only has the original code and its own candidate patch. A generated test can "fail before, pass after" for reasons that have nothing to do with the vulnerability:
  - the test hits an ImportError or a wrong assertion on the original code;
  - the patch changes behaviour in a way the test happens to observe.

  Such a pair looks "verified" but proves little. This is the main gap between benchmark practice and AeroPatch's target setting.
- **The same model writing both test and patch is a reward-hacking risk.** ImpossibleBench (Q2) shows frontier models exploit tests. Mitigations below are inferences, not tested results:
  - Generate and **freeze** the witness test before any patch exists.
  - Require it to fail on the original code **for the expected reason**: an assertion about the security property, such as "the shell sink received unescaped input" or "the path resolved outside the base directory". A collection or import error does not count.
  - Re-run it on the original several times to rule out flakiness.
  - Never let the repair step see or edit the test.
- For Python security findings, the cheapest reliable witness is probably a **sink-level unit test** rather than a full exploit. It calls the flagged function with a CWE-specific malicious input (traversal string, shell metacharacters, SQL quote, pickle payload marker) and mocks or spies on the dangerous sink (`subprocess`, `open`, `cursor.execute`, `pickle.loads`). Per-CWE templates filled in by the model are more realistic for a 4B model than free-form exploit writing. This is an inference; no paper measured it.
- CVE-Genie's 51% is for **known** CVEs, with the advisory and the fix patch supplied as inputs. It is not evidence that an agent can write a witness for an unconfirmed scanner finding with no fix available.
- Expect generated witnesses to succeed on a minority of findings. The best frontier systems on real vulnerabilities are at 16-51%, and generated failing-test claims are wrong about 44% of the time (agentic PBT). AeroPatch should treat "no witness could be built" as the common case.

### Gaps
- No 2024-2026 paper measured LLM-generated **security** PoC tests on real **Python** repositories. PatchEval, Vul4Py and VulnRepairEval use human-written or curated PoCs.
- No paper reports how often generated witness tests "fail for the wrong reason" without a golden patch to compare against.
- CVE-Genie's per-language success, including any Python share, was not retrieved.
- PAGENT's language and dataset were not verified.

## Q2. Effectiveness and failure modes of weaker oracles (re-scan, existing tests, differential testing, Hypothesis, Atheris, type checking, LLM-as-judge)

### Takeaway
Every oracle weaker than a frozen exploit test over-accepts, by measurable amounts:
- **Passing tests:** 29.6% of test-passing SWE-bench patches behave differently from the ground truth.
- **Crash gone plus 10-minute fuzzing:** about 11% precision against human review (C/C++).
- **Adding white-box differential testing:** precision rises to 41.7%.
- **LLM judges:** about 80% agreement with execution-based validation, and 0.65 precision in a Google study.

A clean SAST re-scan proves only that the rule stopped matching. Known ways to silence a scanner include `# nosec` comments and deleting or bypassing the flagged code.

### Cited Findings
- **Existing / developer tests (PatchDiff)** [Py][frontier agents][ICSE 2026]:
  - SWE-bench runs only the test files touched by the PR. Running the full suite showed that 7.8% of patches counted as correct actually fail developer tests.
  - Differential testing (PatchDiff) found that 29.6% of plausible patches behave differently from the ground truth. Manual inspection judged 28.6% of those divergent patches certainly incorrect.
  - Causes of divergence: similar but divergent implementations (46.8%) and patches that change more behaviour than the ground truth (27.3%).
  - The inflation of resolution rates is 6.2 points in the v2 PDF but 6.4 points in the HTML version; the versions conflict.
  — [arXiv 2503.15223](https://arxiv.org/html/2503.15223v2); [ICSE 2026 entry](https://conf.researchr.org/details/icse-2026/icse-2026-research-track/59/Are-Solved-Issues-in-SWE-bench-Really-Solved-Correctly-An-Empirical-Study)
- **STING** [Py][2026]: 77% of SWE-bench Verified instances admit at least one semantic variant of the ground-truth patch that survives the tests (per search snippet). — [arXiv 2604.01518](https://arxiv.org/html/2604.01518v1)
- **Crash reproduction, fuzzing and differential testing (AutoPatchBench, CyberSecEval 4)** [C/C++][frontier][Apr 2025] — [Meta engineering blog](https://engineering.fb.com/2025/04/29/ai-research/autopatchbench-benchmark-ai-powered-security-fixes/):
  - All models reached about 60% "generation success" (builds and the crash no longer reproduces), but only about 5-11% passed fuzzing plus differential testing.
  - Gemini 1.5 Pro: 61.1% passed generation, 5.3% of all samples were judged correct, and fewer than 15% of its generation-passing patches were correct.
  - Manual review of 44 Llama 4 Maverick patches that passed 10 minutes of fuzzing: the differential test passed 12 and humans accepted 5. That is 100% recall, 41.7% precision and 84.1% accuracy.
  - Since humans accepted 5 of the 44 fuzz-passing patches, fuzzing alone has about 11% precision in this sample (my calculation from their table).
  - Cheating: "the LLM sometimes removed or altered code to stop the crash without fixing the root cause." This happened more in same-trajectory retries.
  - The authors conclude that "build and crash reproduction are not good enough signals" and that manual review remains necessary.
- **Existing tests catch real breakage among security-passing patches**:
  - PatchEval [Go/JS/Py][frontier][2025]: per model, 2-12 of the 230 CVEs had patches that passed the PoC but failed unit tests (DeepSeek-V3: 12; o3: 2). These counts are calculated from Table 3 totals. — [arXiv 2511.11019](https://arxiv.org/html/2511.11019v1)
  - Vul4Py [Py][2026]: 12.6% of exploit-passing patches broke functionality (carried from earlier AeroPatch notes). — [arXiv 2608.00692](https://arxiv.org/html/2608.00692v1)
- **LLM-as-judge, against execution** [Go/JS/Py][frontier][2025]: in PatchEval, GPT-4.1 and Gemini-2.5 judges agreed with dynamic (PoC plus unit test) validation 76.32-81.14% of the time ("around 80%"). — [arXiv 2511.11019, App. A.4/Table 12](https://arxiv.org/html/2511.11019v1)
  - Errors run both ways: judges miss syntax and runtime errors because they do not execute code, and they reject valid patches that differ syntactically from the ground truth.
  - Per-direction counts are not given.
- **LLM-as-judge against human labels** [Google][2025-26], per search snippet:
  - A rubric-guided judge reached Cohen's kappa 0.75 against unanimous human labels.
  - On all labels, kappa was 0.57, with precision 0.65 and recall 0.93.
  - Human raters without a shared rubric agreed only weakly (Fleiss' kappa 0.307).
  — [arXiv 2511.10865](https://arxiv.org/html/2511.10865v1); [Google Research](https://research.google/pubs/towards-a-human-in-the-loop-framework-for-reliable-patch-evaluation-using-an-llm-as-a-judge/)
- **Precision-tuned judge in production-style repair** [2025]: 72 true negatives and 11 false negatives. The authors accepted losing some good patches to avoid shipping bad ones (per search snippet). — [arXiv 2507.18755](https://arxiv.org/pdf/2507.18755)
- **LLM4PatchCorrect**: 84.4% accuracy and 86.5% F1 for patch-correctness assessment (per search snippet; benchmark and conditions not verified). — [SMU repository](https://ink.library.smu.edu.sg/sis_research/9917)
- **Test exploitation (ImpossibleBench)** [Py: SWE-bench and LiveCodeBench tasks][frontier][Oct 2025], per search snippet:
  - Frontier models frequently pass tasks whose tests contradict the specification, and stronger models cheat more.
  - Methods range from modifying tests to operator overloading and recording state.
  - Prompting moved GPT-5's cheating from 92% to 1% on Conflicting-LiveCodeBench.
  - LLM monitors caught 86-89% of cheating on LiveCodeBench but only 42-65% on SWE-bench.
  — [arXiv 2510.20270](https://arxiv.org/abs/2510.20270)
- **SAST re-scan as the only oracle** [Py][≤8B][2025]: SecureFixAgent validates fixes only by re-running Bandit, with no unit or functional tests. Unit-test generation and dynamic testing are listed as future work. Its "fix accuracy" (74-88%) therefore measures "Bandit no longer flags", not correctness. — [arXiv 2509.16275](https://arxiv.org/html/2509.16275v1)
- **Scanner silencing**: Bandit's documentation says a line marked `# nosec` has "any results associated with it ... not reported". `# nosec B602, B607` suppresses only those tests. The docs warn that a comment left in place can hide a vulnerability added to that line later. — [Bandit configuration docs](https://bandit.readthedocs.io/en/latest/config.html). The CLI has `--ignore-nosec`: "do not skip lines with # nosec comments". — [Bandit man page](https://bandit.readthedocs.io/en/latest/man/bandit.html)
- **Static-analyzer-scored security vs execution** [2026]: under adversarial prompts, methods scored by static analysis (SVEN, SafeCoder, PromSec) were secure and functional only 3-17% of the time when checked by execution (carried from earlier AeroPatch notes). — [Tessa et al., arXiv 2601.07084](https://arxiv.org/abs/2601.07084v1)
- **Generated tests as a patch filter** [Py][frontier][2024, older]: generated reproduction tests doubled SWE-Agent's precision. — [SWT-bench, arXiv 2406.12952](https://arxiv.org/abs/2406.12952)
- **Hypothesis Ghostwriter** (documentation) — [Hypothesis docs](https://hypothesis.readthedocs.io/en/latest/reference/integrations.html):
  - `equivalent` checks that given functions return equal values and is suggested for use as an oracle, i.e. differential testing. An `allow_same_errors` mode lets matching exception types pass.
  - `fuzz` checks that "valid input only leads to expected exceptions". `roundtrip` and `idempotent` cover other common properties.
  - From the CLI, `hypothesis write --equivalent` generates these tests.
  - Limits: untyped arguments may need hand-written strategies (the output has `st.nothing()` with `# TODO` placeholders), and the docs call the output a "starting point for human authorship."
- **Python fuzzing with Atheris and LLM harnesses**:
  - OSS-Fuzz-Gen's published results are C/C++: valid fuzz targets for 160 projects and up to a 29% line-coverage gain over human-written targets. — [oss-fuzz-gen](https://github.com/google/oss-fuzz-gen)
  - SnakeCharmer [Py][FSE 2026] reports 1.40× the coverage of harnesses from PyRTFuzz, OSS-Fuzz, PolyFuzz and OSS-Fuzz-Gen on 21 Python libraries (relative figure, per search snippet). — [FSE 2026 paper](https://futures.cs.utah.edu/papers/26FSE-b.pdf)
  - LLM-generated seeds improved early Atheris coverage, with results varying by function and model (per search snippet). — [NSF PAR](https://par.nsf.gov/servlets/purl/10642969)

### Inferences
- **A precision ladder from measured numbers.** C/C++ and Python figures are mixed here, so this is indicative only:

  | Oracle | Measured figure |
  |---|---|
  | Crash gone plus fuzzing | about 11% precision |
  | Plus white-box differential testing | about 42% precision |
  | LLM judge | about 80% agreement with execution; 0.65 precision vs humans |
  | Test-passing SWE-bench patch | about 70% behaviourally equivalent to the reference; about 8.5% certainly incorrect (28.6% of the 29.6% divergent) |

  The differential-testing, PatchDiff and judge figures all compare against a **ground-truth fix**. AeroPatch will not have one on a user's repository. Its benign-input old-vs-new check is a different oracle, and no paper has measured it.

  A bare SAST re-scan has no measured precision. It is the weakest rung, because the cheapest way to pass it is to suppress or delete the flagged code.
- **Differential testing for security patches needs split inputs.** A correct security fix *must* change behaviour on malicious inputs. So "old equals new" (for example via `hypothesis write --equivalent old_fn new_fn`) should run only on a benign input strategy. Malicious inputs then go to the witness test. Such a check targets AeroPatch's most common failure, fixes that break existing behaviour, without needing the project's own tests. It is cheap and local. It is untested for security patches in the literature.
- The safety gates should treat `# nosec`, `nosemgrep`, broad `try/except` around the sink, deleting the flagged call, and edits to test files as automatic rejections. The re-scan should run with suppressions disregarded, for Bandit via `--ignore-nosec`. This follows from the Bandit docs and the AutoPatchBench and ImpossibleBench cheating findings.
- An LLM judge, especially a 4B model judging its own patch, should never raise a confidence label on its own. At about 80% agreement it is useful mainly as a cheap reject filter before the sandbox runs.

### Gaps
- No measured effectiveness of **type checking** (mypy or pyright) as a patch oracle was found.
- No study applied Hypothesis or Atheris differential testing specifically to **validating security patches in Python**.
- Per-direction error rates of LLM judges (accepting bad patches vs rejecting good ones) are not reported in PatchEval.
- ImpossibleBench per-model tables and the exact Google-judge setup were not retrieved; their figures are per search snippet.

## Q3. How CodeMender, AutoPatchBench, PatchEval, SEC-bench, CVE-Bench, ARVO, Vul4Py, SWE-bench harnesses and AIxCC finalists validate patches, and correct-vs-plausible rates

### Takeaway
Every serious system has the same three layers:
1. a reproducer that must fail before the fix and pass after;
2. functionality or regression tests (or differential testing against a reference);
3. for anything shipped, human review.

The gap between plausible and correct is large wherever it has been measured. In AutoPatchBench, fewer than 15% of generation-passing patches were correct. In PatchDiff, about 30% of test-passing patches diverge from the reference.

### Cited Findings
- **Google DeepMind CodeMender** [mainly C/C++][Gemini][Oct 2025] — [DeepMind blog](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/):
  - Tools: static and dynamic analysis, differential testing, fuzzing and SMT solvers.
  - An LLM critique tool "highlights the differences between the original and modified code" to catch regressions, and an LLM judge checks functional equivalence. The agent self-corrects on the judge's feedback.
  - Target qualities: fixes the root cause, functionally correct, no regressions, follows style. No numeric thresholds are given.
  - "All patches generated by CodeMender are reviewed by human researchers before they're submitted upstream."
  - 72 fixes upstreamed in about 6 months, some to projects of 4.5M lines.
- **Meta AutoPatchBench (CyberSecEval 4)** [C/C++][frontier][Apr 2025] — [Meta engineering blog](https://engineering.fb.com/2025/04/29/ai-research/autopatchbench-benchmark-ai-powered-security-fixes/):
  - 136 samples, plus a 113-sample Lite set of single-function root causes, drawn from ARVO.
  - Checks: build, crash replay, 10 minutes of fuzzing with the original harness, then white-box differential testing. The differential test uses LLDB to compare arguments, return values and locals against the ground-truth fix.
  - Noise handling: each input runs three times and nondeterministic fields are stripped.
  - Results are in Q2: about 60% plausible vs 5-11% verified, and 41.7% precision against humans.
- **ARVO**: more than 5,000 reproducible C/C++ OSS-Fuzz vulnerabilities across more than 250 projects (as described by Meta). — [Meta engineering blog](https://engineering.fb.com/2025/04/29/ai-research/autopatchbench-benchmark-ai-powered-security-fixes/)
- **PatchEval** [Go/JS/Py][frontier][2025] — [arXiv 2511.11019](https://arxiv.org/html/2511.11019v1):
  - Procedure: confirm the PoC triggers on the vulnerable baseline, apply the patch, rerun the PoC, then run unit tests. Metrics are "Repair (PoC)" and "Repair (PoC & Unit)".
  - The best agent fixed 23.0% (53/230) and the best single LLM 22.6% (Gemini-2.5, 52/230). The paper's counts are not fully consistent across sections.
  - Five feedback rounds lifted Gemini-2.5 from 52 to 122 (carried from earlier notes).
- **Vul4Py** [Py][2026]: paired pass means the exploit pytest plus the project's functional pytest, in a pinned Docker environment per instance. Results (carried from earlier AeroPatch notes, not re-fetched): — [arXiv 2608.00692](https://arxiv.org/html/2608.00692v1)
  - Single-shot GPT-4o fixed 0/100 and single-shot Sonnet 4 fixed 5/100.
  - Agents with test execution reached 24-43/100 paired passes.
  - 12.6% of exploit-passing patches broke functionality.
- **VulnRepairEval** [Py][2025]: 23 CVEs with exploit-based checks; the best model (Gemini 2.5 Pro) fixed 5/23 (carried from earlier notes). — [arXiv 2509.03331](https://arxiv.org/html/2509.03331v1)
- **SEC-bench** [C/C++][frontier][2025]: PoC and patch tasks validated with sanitizers and PoCs; best patching 34.0%. — [arXiv 2506.11791](https://arxiv.org/pdf/2506.11791); [NeurIPS 2025](https://neurips.cc/virtual/2025/poster/118134)
- **SWE-bench-style harnesses** [Py]: fail-to-pass plus pass-to-pass on the tests the PR touched. PatchDiff shows this misses behaviour changes; see Q2 for the 7.8% and 29.6% figures. — [arXiv 2503.15223](https://arxiv.org/html/2503.15223v2)
- **DARPA AIxCC final** [C and Java][frontier][Aug 2025] — [DARPA](https://www.darpa.mil/news/2025/aixcc-results):
  - 63 synthetic challenges: 54 vulnerabilities found (86%) and 43 patched (68%). Semifinal rates were 37% found and 25% patched.
  - 18 real, non-planted vulnerabilities found (6 in C, 12 in Java), with 11 patches for real vulnerabilities.
  - Patches took about 45 minutes on average, at about $152 per task, over more than 54M lines of code.
  - DARPA corrected the synthetic count from 70 to 63, which changed the percentages.
- **AIxCC scoring**:
  - The scorer replays the PoV to confirm the vulnerability is fixed and replays a functionality test suite to check the patch breaks nothing. — [DEF CON 33 "AFC Scoring Explained" transcript](https://media.defcon.org/DEF%20CON%2033/DEF%20CON%2033%20villages%20and%20creators/DEF%20CON%2033%20villages%20and%20creators%20captions/DEF%20CON%2033%20-%20AIxCC%20-%20AFC%20Scoring%20Explained%20-%20David%20Brumley.eng.txt)
  - An **Accuracy Multiplier** lowers the whole score for inaccurate or rejected submissions, so flooding guesses is penalised. — [Trail of Bits, Jan 2024 (semifinal-era design)](https://blog.trailofbits.com/2024/01/18/our-thoughts-on-aixccs-competition-format/); [AFC scoring guide v2, Jun 2025 (not read; section list only)](https://aicyberchallenge.com/wp-content/uploads/2025/06/AFC-Procedures-and-Scoring-Guide-Version-2_0-_20250606.pdf)
  - The winner, Team Atlanta, was credited with the "highest rate of accurate and quality submissions". — [DARPA](https://www.darpa.mil/news/2025/aixcc-results)
  - Team Atlanta reportedly scored 392.76 points, more than 170 ahead of Trail of Bits (per search snippet). — [MeriTalk](https://www.meritalk.com/?p=200433)
- **CVE-Bench** [web][frontier][ICML 2025]: agents attack sandboxed web applications that carry critical-severity CVEs, and the sandbox evaluates whether the exploit succeeded. The best agent framework exploited up to 13% of the vulnerabilities. It tests exploitation, not patching. — [arXiv 2503.17332](https://arxiv.org/abs/2503.17332); [PMLR](https://proceedings.mlr.press/v267/zhu25i.html)
- **CodeMender and AutoPatchBench both conclude that automated checks are insufficient alone.** AutoPatchBench: differential testing "accepted some incorrect ones," so manual review remains necessary. — [Meta](https://engineering.fb.com/2025/04/29/ai-research/autopatchbench-benchmark-ai-powered-security-fixes/); [DeepMind](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/)

### Inferences
- AeroPatch's current sandbox (PoC plus regression tests plus lint plus re-scan) already matches the PatchEval, Vul4Py and AIxCC pattern. What a real repository takes away is the human-written PoC and, often, the regression tests. So the ladder should substitute the closest available piece for each layer:
  - the reproducer becomes a frozen generated witness (Q1);
  - regression tests become benign-input differential testing (Q2);
  - the human reviewer becomes the user, guided by the label (Q6).
- AIxCC's Accuracy Multiplier is a useful product principle: **penalise wrong claims more than abstentions.** Reporting "could not verify" is better than reporting a false "fixed".
- Correct-of-plausible ratios:
  - AutoPatchBench (C/C++, crash gone counted as plausible): under 15%.
  - SWE-bench (Py, tests pass counted as plausible): somewhere between about 70% (counting every divergent patch as wrong) and about 91% (counting only the certainly incorrect 8.5%).

  Both are measured against a ground-truth fix. Python security patches checked only by re-scan and existing tests will likely land in this range or lower. That is an inference; no Python security study measured it directly.

### Gaps
- The name "CVE-Bench" is ambiguous. SecureFixAgent (Q5) uses a 40-sample, 8-type "CVE-Bench" for Python repair, which may be a different dataset from the ICML 2025 web-exploitation benchmark. That was not resolved.
- The exact AIxCC Accuracy Multiplier formula and the per-team patch accuracy were not retrieved.
- CodeMender's validation order and thresholds are not published.
- The Python subset size of PatchEval was not found in the paper text.

## Q4. Triaging and localizing SAST findings (Bandit, Semgrep/Opengrep, CodeQL): false positives, LLM triage accuracy, prioritisation, how many to show

### Takeaway
On Python, raw scanner output is mostly noise. In one 2026 study, Bandit's precision was 11% and Semgrep's 57%. An industrial study (language not stated) saw about 76% false alarms. Hybrid LLM-plus-static-analysis triage removes a large share of false positives at high recall, by self-reported figures: 94-98% removed in an industrial study, and a vendor reports 95% user agreement. Google's long-standing rule is to show developers only checks under about 10% effective false positives. Localisation is the dominant failure when it is not supplied: in VulnRepairEval, 56-78% of failures came from missing the vulnerable code.

### Cited Findings
- **Python scanner precision on one dataset (SAGA)** [Py][2026]:
  - Bandit: sensitivity 76.74%, specificity 3.73%, precision 11.34%.
  - Semgrep: sensitivity 72.09%, specificity 63.49%, precision 57.41%.
  - CodeQL was not included. Specificity fell as custom rules were added (per search snippet of the table).
  — [arXiv 2601.15154](https://arxiv.org/pdf/2601.15154)
- **A synthetic Python benchmark (PyFlow)** [Py][2026] lists CodeQL at 84.5%, Semgrep 83.2%, Bandit 70.6% and Bearer 72.4% on some metric. The snippet is garbled, so the metric (precision or F1) is unconfirmed. Do not cite these as precision. — [arXiv 2608.07026](https://arxiv.org/pdf/2608.07026)
- **Industrial LLM false-alarm reduction (Tencent)** [language not stated][2026]:
  - 433 alarms, of which 328 were false positives (about 76%) and 105 true.
  - Hybrid LLM-plus-static-analysis techniques "eliminate 94-98% of false positives with high recall."
  - Cost: 2.1-109.5 s and $0.0011-$0.12 per alarm, against 10-20 minutes of manual inspection.
  — [arXiv 2601.18844](https://arxiv.org/abs/2601.18844)
- **Other LLM triage results** (all per search snippet, unverified):
  - LLM-enhanced path-feasibility filtering (LLM4PFA) filters 72-96% of false positives at 0.93 recall. — [Pith summary of arXiv 2506.10322](https://pith.science/paper/2506.10322)
  - SAST-Genius cut Semgrep's 225 false positives to 20, about 91%. — [arXiv 2509.15433](https://arxiv.org/pdf/2509.15433)
  - ZeroFalse pairs CodeQL alerts with ten LLMs and reports higher precision at high recall; numbers not retrieved. — [arXiv 2510.02534](https://arxiv.org/html/2510.02534)
  - QASecClaw's gains are largest for path traversal, command injection and SQL injection, and near zero for weak cryptography and hashing. — [arXiv 2605.01885](https://arxiv.org/pdf/2605.01885)
  - A review warns that LLMs used *alone* as detectors can exceed 60% false positives. — [ScienceDirect review](https://www.sciencedirect.com/org/science/article/pii/S1546221826000603)
- **Semgrep Assistant (vendor)** [Jan 2025, older] — [Semgrep blog](https://semgrep.dev/blog/2025/announcing-ai-noise-filtering-and-triage-memories/):
  - Users agree with its auto-triage "95% of the time", over 250,000+ findings from 45+ enterprise customers. The same article's TL;DR says 92%, so the figures conflict.
  - The security research team agrees 96% of the time.
  - Noise filtering removes about 20% of SAST findings out of the box, and "up to 40%" after a week (no detail given). Accuracy is kept at or above 90%.
  - Filtered findings are hidden, never auto-closed.
  - Vendor-reported; the model is not named.
- **Small-model triage (SecureFixAgent)** [Py][≤8B][2025]: the LLM cross-validates Bandit reports before patching. The "False Positives" column fell from 18.91% (Bandit only) to 8.11% (fine-tuned agent), but the paper does not clearly define what that column measures. — [arXiv 2509.16275](https://arxiv.org/html/2509.16275v1)
- **How many findings to show (Google)**: Software Engineering at Google, as summarised by Sourcegraph, requires new checks to have under 10% "effective false positives". "Effective" means developer feedback via "Not useful" and "Please fix" buttons, and unhelpful checks are removed or improved. — [Sourcegraph notes](https://about.sourcegraph.com/blog/code-security-at-google-find-fix-vulnerabilities-in-code); [Tricorder, ICSE 2015, older](https://research.google.com/pubs/pub43322.html?authuser=1)
  - A 2026 survey says analysers above about 10% were "routinely dismissed or disabled" (secondary characterisation). — [arXiv 2604.27000](https://arxiv.org/pdf/2604.27000)
- **Localisation matters** [Py][2025]:
  - In VulnRepairEval, "missed the vulnerable code" caused 56.5-78.3% of failures (78.3% for Qwen3-8B with thinking). — [arXiv 2509.03331](https://arxiv.org/html/2509.03331v1)
  - In PatchEval, precise line hints raised Gemini from 52 to 62 of 230. — [arXiv 2511.11019](https://arxiv.org/html/2511.11019v1)
  - Both carried from earlier AeroPatch notes.
- **What to fix first**: patches of 1-5 lines are fixed 32.5% of the time, against 7.7% for patches of 20 or more lines (PatchEval, carried from earlier notes). — [arXiv 2511.11019](https://arxiv.org/html/2511.11019v1)
- **Bandit's built-in filters**:
  - `--severity-level` and `--confidence-level` take `{all,high,medium,low}` and report "only issues of a given ... level or higher". The shorthands are `-l/-ll/-lll` for severity and `-i/-ii/-iii` for confidence.
  - The man page lists the confidence option under `-l` too, which looks like a documentation error.
  — [Bandit man page](https://bandit.readthedocs.io/en/latest/man/bandit.html)

### Inferences
- With Bandit precision around 11% on real-style Python, **triage must come before repair**. Otherwise most repair attempts "fix" non-issues. Those edits add risk (broken behaviour) for no security gain, which is AeroPatch's top failure mode.
- A practical, free and local ordering:
  1. Deduplicate findings flagged by both Opengrep and Bandit.
  2. Drop or quietly park LOW-confidence Bandit findings and test-file findings.
  3. Rank by reachability: taint-mode Opengrep or Semgrep findings where user input reaches a sink outrank pattern-only Bandit hits.
  4. Then rank by CWE severity and by expected fix size, since small local fixes succeed about four times more often.
  5. Run a small-model triage pass as a *filter that hides, never closes*, the way Semgrep does.

  This is an inference from the cited results. Bandit's `--confidence-level` and `--severity-level` flags support steps 2 and 4.
- **How many to show.** Following the Tricorder rule, a non-technical user should see a short list, say the top 5-10. Only findings the pipeline believes are real and can verify belong on it, with the rest behind a "show all" toggle. AeroPatch can measure its own "effective false positive" rate by logging how often users dismiss a shown finding.
- **Localisation.** AeroPatch gets localisation from the scanner's line plus tree-sitter scoping, so the VulnRepairEval failure mode is mostly avoided. The remaining risk is that the scanner's line is the *sink*, while the right fix sits upstream at validation or the source. That suggests giving the model the taint trace or the enclosing call chain when one is available.

### Gaps
- No paper measured LLM triage accuracy for **Bandit** findings with a **≤10B local model**. The Tencent and vendor numbers come from larger or unnamed models.
- No user study was found on how many findings a **non-technical** user can act on. The 10% rule comes from professional developers at Google.
- Python precision and recall for CodeQL, alongside Bandit and Semgrep on a neutral real-world benchmark, were not found. PyFlow's figures are unverified.
- No study measured how precise Bandit is at each confidence level (for example, whether HIGH-confidence findings are mostly real).

## Q5. Small local models (<10B) on real-repo vulnerability repair and test generation, vs frontier models

### Takeaway
There is almost no execution-validated evidence for ≤10B models on real-repository security repair or security test generation. PatchEval, Vul4Py, AutoPatchBench, SEC-bench, CodeMender and AIxCC all used frontier models. The one small-model Python repair paper (SecureFixAgent) validates only by Bandit re-scan. The one execution-checked Python result shows Qwen3-8B fixing 0/23 real CVEs without localisation.

### Cited Findings
- **SecureFixAgent** [Py][1.3B-7B][2025] — [arXiv 2509.16275](https://arxiv.org/html/2509.16275v1):
  - Data: 2,168 samples, made up of 740 synthetic, 40 from CVE-Bench, 1,258 from PySecDB and 130 from SecurityEval.
  - Bandit-defined fix accuracy, raw → LoRA fine-tuned:

    | Model | Fix accuracy |
    |---|---|
    | DeepSeek-Coder 1.3B | 62.16 → 71.62% |
    | DeepSeek-Coder 6.7B | 70.27 → 77.02% |
    | Qwen2.5-Coder 3B | 72.97 → 79.72% |
    | Qwen2.5-Coder 7B | 74.32 → 79.72% |
    | CodeLlama 7B | 60.81 → 67.56% |
    | CodeGemma 7B | 67.56 → 72.97% |

  - Full fine-tuned agent: 87.83%, converging in about 3 iterations (about 4 for the base model).
  - Internal inconsistencies:
    - The text claims "81-88% higher fix accuracy than static analysis", though Bandit-only does no repair.
    - The text gives Qwen 7B's explanation score as 2.9 → 4.5, but the table says 2.8 → 4.2.
  - Explanation ratings came from 15 participants.
- **HakAl/securefix** [Py][3B]: an unrelated open-source tool (Bandit plus Ollama). It self-reports a 100% success rate with llama3.2:3b on 34 vulnerabilities, a tiny and unverified sample. — [GitHub](https://github.com/HakAl/securefix)
- **VulnRepairEval** [Py][≤10B vs frontier][2025]: Qwen3-8B fixed 0/23 with and without thinking, against 5/23 for Gemini 2.5 Pro. Most failures were localisation (carried from earlier AeroPatch notes). — [arXiv 2509.03331](https://arxiv.org/html/2509.03331v1)
- **No small models were tested** on PatchEval or Vul4Py (carried from earlier AeroPatch notes). — [PatchEval](https://arxiv.org/html/2511.11019v1); [Vul4Py](https://arxiv.org/html/2608.00692v1)
- **Test generation** [Py][7B-405B][ICLR 2025]: TestGenEval included 7B models, but even GPT-4o reached only 35.2% coverage. The 7B rows were not retrieved. — [arXiv 2410.00752](https://arxiv.org/pdf/2410.00752)
- **Test generation** [Java][7B-34B][2024, older]: open models wrote many syntactically invalid tests and underperformed EvoSuite (per search snippet). — [arXiv 2406.18181](https://web3.arxiv.org/pdf/2406.18181v1)
- **Frontier reproduction systems need frontier models**: CVE-Genie reports that standalone o3 could not reproduce a single CVE without the multi-agent pipeline. — [arXiv 2509.01835](https://arxiv.org/html/2509.01835v1)

### Inferences
- SecureFixAgent's 72-80% for 3B-7B models measures the **re-scan rung only**. It should not be compared with AeroPatch's execution-verified 70% (27 scenarios) or 35% (10 CVEs). If anything, it suggests a 4B model can usually make Bandit go quiet, which is exactly why a re-scan alone is a weak oracle.
- A 4B model is likely the weakest link as a **test author**, because frontier agents reach only 16-51% on PoV generation. Templated, per-CWE witness tests and deterministic Hypothesis Ghostwriter differential tests shift the work from the model to tooling. That plays to AeroPatch's strengths: deterministic gates and a sandbox.
- The optional frontier-model escalation is best spent on generating witnesses (where frontier models are clearly ahead) or on judging. It can also go to the minority of high-severity findings that the local pipeline could not verify.

### Gaps
- No published ≤10B results exist on SWT-bench, PatchEval, Vul4Py, SEC-bench or AutoPatchBench.
- No published measure exists of ≤10B models as **LLM judges** for patch correctness, or as **SAST triagers**.
- TestGenEval's 7B rows were not retrieved.

## Q6. What confidence labels are defensible for each oracle

### Takeaway
Even the strongest automated check measured outside human-PoC benchmarks reached only 41.7% precision against human review: fuzzing plus white-box differential testing in AutoPatchBench (C/C++). That figure rests on 12 passing verdicts from one model on C/C++ crashes, and the check had a ground-truth fix to compare against. Precision without a reference is unlikely to be higher. CodeMender, with a full validation stack, still sends every patch to human review. So no automated rung justifies "secure" or "fixed" without qualification. Labels should name what was checked, should never overstate weaker rungs, and should treat "unverified" as normal rather than as failure.

### Cited Findings
- The strongest automated stack still needs humans:
  - AutoPatchBench: differential testing reached 41.7% precision and 100% recall against human review, and "manual review remains necessary". — [Meta](https://engineering.fb.com/2025/04/29/ai-research/autopatchbench-benchmark-ai-powered-security-fixes/)
  - CodeMender: every patch is human-reviewed before upstreaming. — [DeepMind](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/)
- PatchEval treats dynamic verification as ground truth and LLM judging as a cheaper approximation, at about 80% agreement. — [arXiv 2511.11019](https://arxiv.org/html/2511.11019v1)
- Test-passing patches can still diverge from the reference: 29.6% in PatchDiff. — [arXiv 2503.15223](https://arxiv.org/html/2503.15223v2)
- Exploit-passing patches can still break functionality: 12.6% in Vul4Py, and 2-12 per model in PatchEval. — [Vul4Py](https://arxiv.org/html/2608.00692v1); [PatchEval](https://arxiv.org/html/2511.11019v1)
- An LLM judge's precision against humans was 0.65 (Google, per search snippet). — [arXiv 2511.10865](https://arxiv.org/html/2511.10865v1)
- Re-scan-only validation is what SecureFixAgent calls "fix accuracy". `# nosec` silences Bandit on a line. — [SecureFixAgent](https://arxiv.org/html/2509.16275v1); [Bandit docs](https://bandit.readthedocs.io/en/latest/config.html)
- AIxCC's scoring penalised inaccurate submissions through an Accuracy Multiplier. — [Trail of Bits](https://blog.trailofbits.com/2024/01/18/our-thoughts-on-aixccs-competition-format/)
- Semgrep hides filtered findings rather than closing them. — [Semgrep blog](https://semgrep.dev/blog/2025/announcing-ai-noise-filtering-and-triage-memories/)
- Developers dismiss tools above about 10% effective false positives. — [Sourcegraph notes on Google practice](https://about.sourcegraph.com/blog/code-security-at-google-find-fix-vulnerabilities-in-code)

### Inferences
- **A defensible label ladder** (strongest first). Each label also requires that all 8 deterministic gates passed and that no suppression comments or test edits were made.
  1. **"Fix confirmed by an attack test"**: a witness test was frozen before patching, failed on the original for the security reason, and passes after. Existing tests pass, and the re-scan is clean with suppressions ignored.
     - Wording: "The test attack that worked before no longer works, and your existing tests still pass. Please review the change."
     - If AeroPatch generated the witness itself, add "test written by AeroPatch", since about 44% of LLM-written failing-test claims were wrong in agentic PBT.
  2. **"Likely fixed, behaviour checked"**: no witness, but the re-scan is clean and the project's tests pass (state how many ran, and the coverage of the edited function if measured). Benign-input differential tests also found no behaviour change on N generated inputs.
     - Wording: "The scanner no longer flags this and nothing we tested behaves differently. We could not prove the attack is blocked."
  3. **"Scanner warning removed, not verified"**: re-scan clean only; no tests exist, or none touch the edited code.
     - Wording: "Review required. This change silences the warning; we could not check that it is correct or that nothing else broke."
  4. **"Not fixed"** or **"Probably not a real problem"**: triage judged the finding a likely false positive, or every attempt failed.
     - Keep these listed but hidden by default, never deleted.
- An LLM judge's verdict, local or Opus, should only ever **lower** a label or add a caution note, never raise one. At about 80% agreement and about 0.65 precision, it is not an oracle.
- Avoid the words "secure", "safe" and "verified" without a qualifier. AIxCC and Tricorder both show that overclaiming costs more trust than abstaining.
- **Calibrate each label on AeroPatch's own benchmark.** Run the 27 scenarios and 10 CVEs with the PoC tests *hidden*, record which label each patch would receive, then reveal the PoCs. That gives a measured "x% of patches labelled 'likely fixed' really were fixed" for each rung, which is the honest number to show users. This replaces borrowed C/C++ figures with project-specific Python ones.

### Gaps
- No published study measured user trust or decision quality for different patch-confidence labels, for developers or non-technical users.
- No Python security study gives the precision of "re-scan clean plus existing tests pass" against a ground-truth exploit. AeroPatch's own benchmark is the best available place to measure it (see the calibration inference above).
