# AI security vulnerability auto-fix products: how fixes reach users (state as of 2026-10-22)

Scope: how existing commercial and open-source AI fix tools deliver security fixes, what the user sees, how fixes are validated, how triage works, what onboarding takes, what people complain about, and which patterns a free, local, single-laptop tool can realistically copy. Vendor numbers are self-reported unless marked otherwise. "Older" marks information from before 2026.

## 1. Which products exist as of late 2026 and how does each deliver fixes?

### Takeaway
By October 2026 every large vendor has moved from one-shot "suggest a patch" to agentic fix loops that rerun a scanner or tests before showing anything: GitHub (agentic autofix, GA 2026-10-15), Snyk (agentic Agent Fix, 2026-04), OpenAI (Codex Security, research preview 2026-03-06) and Google (CodeMender, gated access). Almost all of them deliver fixes as a pull request or an IDE diff that needs a cloud account and repo connection. The only fully local, open pieces are deterministic engines (Pixee codemodder) and bring-your-own-model CLIs (Patchwork).

### Cited Findings

**GitHub Copilot Autofix / agentic autofix (CodeQL)**
- Agentic autofix went GA on 2026-10-15. When a user assigns a code scanning alert to Copilot, it "explores relevant files across your codebase", "generates a proposed fix", "validates the fix works by rerunning CodeQL", and "iterates if needed, then opens a draft pull request ready for your review". — [GitHub changelog 2026-10-15](https://github.blog/changelog/2026-10-15-agentic-autofix-for-code-scanning-alerts-general-availability/)
- Once enabled, it replaces the free **Generate Fix** button with an **Assign to Copilot** button. Users can select up to 25 alerts to fix together in one PR, or trigger it through the REST API (`assignees: ["copilot-swe-agent[bot]"]`). It works only on default-branch alerts. — [GitHub changelog 2026-10-15](https://github.blog/changelog/2026-10-15-agentic-autofix-for-code-scanning-alerts-general-availability/)
- Older (2024, from an extract): the original Copilot Autofix showed an explanation and a suggested diff in the PR, which developers could dismiss, edit or commit. It was offered free to all open-source projects from September 2024. — [GitHub blog, 2024-08-14, updated 2025-01-21](https://github.blog/news-insights/product-news/secure-code-more-than-three-times-faster-with-copilot-autofix/)

**Snyk Agent Fix (formerly DeepCode AI Fix)**
- Snyk's docs say "DeepCode AI Fix is now Snyk Agent Fix." — [Snyk Docs](https://docs.snyk.io/scan-fix-and-prevent/scan-with-snyk/snyk-code/manage-code-vulnerabilities/fix-code-vulnerabilities-automatically)
- Older (2024): fixes were delivered "in real-time, in-line, and within the IDE". Developers can "select from a variety of proposed fixes" and "preview potential changes to their code ... before the proposed fix is applied." — [Snyk blog (2024)](https://snyk.io/blog/ai-code-security-snyk-autofix-deepcode-ai/)
- 2026-04-27: a new agentic architecture. When the model's output is imperfect or insecure, the system works out why the suggestion failed, feeds that error context back to the agent, and generates a corrected version (paraphrased from an extract). — [Snyk blog 2026-04-27](https://snyk.io/blog/snyk-agent-fix-agentic-architecture/)
- Snyk Code auto-fixes code issues "inside the IDE and pull requests" (competitor's description). — [Checkmarx comparison](https://checkmarx.com/learn/appsec/best-automated-remediation-for-application-vulnerabilities-top-8-solutions-compared/)

**Semgrep (Assistant, Multimodal, Memories, Autofix)**
- Semgrep Autofix entered public beta on 2026-03-16. It combines Semgrep's static analysis with "frontier-model LLMs to provide contextual upgrade guidance, line-level breaking change analysis, and high-confidence fix suggestions" (page description). According to an extract of the post, fixes are delivered as human-readable PRs. — [Semgrep blog 2026-03-16](https://semgrep.dev/blog/2026/semgrep-autofix-public-beta/)
- Multimodal is now a separate product name, "over 95% accurate in categorizing Semgrep Code findings as false positives". Memories "allows AppSec teams and developers to tailor" triage. — [Semgrep Multimodal docs](https://docs.semgrep.dev/semgrep-multimodal/overview)
- Semgrep promotes an MCP integration for real-time feedback inside Cursor for "vibe coding". — [YouTube, "Vibe Coding, But Make it Safe"](https://www.youtube.com/watch?v=e432_8fn_3o)

**Aikido AutoFix / AutoTriage**
- Aikido creates PRs automatically "on a daily basis" for dependency updates, SAST issues, container base images and pentest issues. — [Aikido help](https://help.aikido.dev/autofix-and-remediation/automation-and-merging/automatic-creation-of-pull-requests)
- Aikido also shows AutoFix in the IDE and in PR comments. — [Aikido YouTube](https://www.youtube.com/watch?v=iNvaMvtQXmk)

**Corgea**
- Corgea is an "AI-native SAST" with fix suggestions "intended for developer review, with explanations tied to the security finding". — [Corgea (vendor) best-SAST page](https://corgea.com/learn/best-sast-tools)
- According to a Pixee competitor table, Corgea ingests SARIF from multiple scanners. — [Pixee (competitor) 2026 comparison](https://www.pixee.ai/blog/best-automated-remediation-tools-2026)

**Mobb**
- Mobb is a dedicated remediation tool that takes findings from Checkmarx, Snyk, Fortify and other scanners and offers "AI-generated fixes with IDE integration". — [Pixee (competitor) 2026 comparison](https://www.pixee.ai/blog/best-automated-remediation-tools-2026)
- Mobb markets fixing "code vulnerabilities within GitHub in seconds". — [Mobb Clean Fix](https://www.mobb.ai/clean-fix)
- "Vibe Shield" gives real-time secure-code alternatives while AI writes code. — [Mobb blog](https://www.mobb.ai/blog/vibe-shield-real-time-security-ai-code)

**Pixee (Pixeebot, codemodder)**
- Pixeebot is a GitHub App that "triages findings and delivers actual code fixes through pull requests—all on a schedule". — [GitHub Apps: pixeebot](https://github.com/apps/pixeebot)
- Codemodder is Pixee's open-source framework of deterministic codemods. `codemodder-python` uses LibCST, regex and XML transformers, installs with `pip install codemodder`, and writes a JSON report of "what changed and why". The open-source engine has "No AI, no triage, no scanner integration, no PR workflow". — [Pixee docs: Codemodder](https://docs.pixee.ai/open-source/codemodder/)
- According to an extract of Pixee's own comparison table, the commercial platform adds three-tier triage, more than 120 deterministic codemods, AI "MagicMods" and a Fix Evaluation Agent, and supports air-gapped deployment. — [Pixee 2026 comparison (vendor)](https://www.pixee.ai/blog/best-automated-remediation-tools-2026)

**Socket**
- Socket fixes dependencies, not first-party code. `socket fix` is a CLI that "helps you fix vulnerable dependencies automatically, with built-in safety guardrails". — [Socket blog](https://socket.dev/blog/introducing-socket-fix)
- Socket Fix 2.0 adds "targeted CVE remediation, smarter upgrade planning". — [Socket blog](https://socket.dev/blog/announcing-socket-fix-2-0)
- The CLI also has `socket patch` to "apply, manage, and rollback Socket security patches for vulnerable dependencies". — [Socket CLI docs](https://docs.socket.dev/docs/socket-cli)
- "sauce" ships coding-agent skills, including `socket-fix`. — [SocketDev/sauce](https://github.com/SocketDev/sauce)

**Endor Labs**
- Endor Labs opens automated upgrade PRs for dependencies. — [AppSec Santa review (secondary)](https://appsecsanta.com/endor-labs)
- Its AI SAST "emits a suggested fix diff with each finding". — [Heeler comparison (competitor)](https://www.heeler.com/heeler-vs-endor-labs)
- "AURI Agents" run inside Claude Code and similar tools (for example, an `sca-remediation` subagent copied into `.claude/agents`). Endor says they work "on your own infrastructure". — [Endor Labs blog](https://www.endorlabs.com/learn/agentic-appsec-and-agentic-remediation-is-finally-here)

**Google DeepMind CodeMender**
- CodeMender only surfaces "high-quality patches" for human review: ones that "fix the root cause of the issue, are functionally correct, cause no regressions and follow style guidelines". — [DeepMind blog](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/)
- It had upstreamed 72 security fixes (at announcement, 2025). — [AI Business (secondary)](https://aibusiness.com/agentic-ai/google-codemender-patches-code-vulnerabilities)
- As of Oct 2026 (paraphrased from an extract of the product page), CodeMender runs as a secure headless agent on the Gemini Enterprise Agent Platform and is used through a local CLI and VS Code. Patches arrive as standard diffs and PRs for the developer to approve. CodeMender with Gemini 3.8 Flash Cyber is available only to customers and governments that qualify for Google's Fairwind Program. — [Google Cloud CodeMender](https://cloud.google.com/security/codemender)

**OpenAI Aardvark → Codex Security**
- "March 6, 2026 Update: Aardvark is now Codex Security, and is available as a research preview." Aardvark "attaches a Codex-generated and Aardvark-scanned patch to each finding for human review and efficient, one-click patching." — [OpenAI](https://openai.com/index/introducing-aardvark/)
- Aardvark was tested with a limited customer group from October 2025. — [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-vulnerability-scanning-market-20260308/)
- Codex Security runs as a plugin, CLI and SDK (`npx @openai/codex-security`). Scans go through "threat modeling, discovery, validation, attack-path analysis, and reporting". It can "Fix one accepted finding with a patch, regression coverage, and verification of the original issue" (0.1.7, 2026-06-04). — [Codex Security plugin changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)

**Anthropic Claude Code security review**
- There are two ways to use it: the `/security-review` slash command for "on-demand checks in your terminal", and a GitHub Action for "automatic review of pull requests". — [Claude support](https://support.claude.com/en/articles/11932705-automated-security-reviews-in-claude-code)
- According to an extract of the README, the Action comments on the PR's specific lines with explanations, severity ratings and remediation guidance. The README does not describe applying fixes. The README's quick-start sets `comment-pr: true`. — [anthropics/claude-code-security-review](https://github.com/anthropics/claude-code-security-review)

**Amazon CodeGuru Security / Amazon Q Developer (discontinued or sunsetting)**
- CodeGuru Security is discontinued: "After November 20, 2025, you will no longer be able to access the /codeguru/security console, service resources, or documentation." — [AWS CLI reference](https://docs.aws.amazon.com/cli/latest/reference/codeguru-security/)
- Amazon Q Developer's IDE security scan gives "an accompanying suggested code fix" for some detections. — [AWS DevOps blog](https://aws.amazon.com/blogs/devops/code-security-scanning-with-amazon-q-developer/)
- Q Developer IDE plugins and paid subscriptions reach end of support on 2027-04-30. New signups were blocked from 2026-05-15. Kiro (IDE and CLI, with "custom subagents" for tasks such as security review) replaces it. — [AWS blog 2026-04-30, updated 2026-06-10](https://aws.amazon.com/blogs/devops/amazon-q-developer-end-of-support-announcement/)

**Veracode Fix / Checkmarx**
- Veracode Fix for SAST gives "AI-generated fix suggestions (applied by developers)" and "on average, covers over 70% of detected flaws in 10 supported languages". Fix for SCA produces an "evidence-rich pull request". — [Veracode Fix](https://www.veracode.com/products/fix/). A competitor table contradicts the breadth claim, describing Veracode Fix as "Early Access, limited CWEs" — [Pixee (competitor)](https://www.pixee.ai/blog/veracode-alternatives)
- Veracode Fix also offers a CLI batch mode and IDE integration. — [Checkmarx (competitor) comparison](https://checkmarx.com/learn/appsec/best-automated-remediation-for-application-vulnerabilities-top-8-solutions-compared/)
- Checkmarx Developer Assist works through the user's AI assistant: "Your AI will automatically route the request to the Checkmarx MCP ... to generate the suggested remediation." — [Checkmarx docs](https://docs.checkmarx.com/en/34965-549181-using-developer-assist-for-detection-and-remediation.html)
- Checkmarx One Triage & Remediation Assist offers "Attackability-based prioritization, review-ready fix PRs, audit trail". — [Checkmarx](https://checkmarx.com/learn/appsec/best-automated-remediation-for-application-vulnerabilities-top-8-solutions-compared/)

**Open-source and local-model options**
- Patchwork (patched-codes) is a CLI whose `AutoFix` patchflow "will first scan the code in your repository" and then fixes. It accepts any OpenAI-compatible endpoint, for example `client_base_url=http://localhost:8080/v1 openai_api_key=no_key_local_model` (llama.cpp). — [patched-codes/patchwork](https://github.com/patched-codes/patchwork); [AutoFix README](https://github.com/patched-codes/patchwork/blob/main/patchwork/patchflows/AutoFix/README.md); [Patched docs](https://docs.patched.codes/patchwork/quickstart)
- Codex Security can use non-OpenAI providers for scans: Amazon Bedrock (0.1.18), OpenRouter and Fireworks credentials (0.1.19). — [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)

**Non-technical-user platform (adjacent example)**
- According to an extract of the post, Lovable's Security Center (2026-03-24) runs four scanners: RLS analysis, database security check, code security review and dependency audit. They run automatically when files or dependencies change and before publishing. Users see severity with plain-language explanations and can apply a fix with one click ("Try to fix") or through the chat agent. — [Lovable blog 2026-03-24](https://lovable.dev/blog/a-founders-guide-to-lovable-security)

### Inferences
- The industry converged on one shape: scanner finding → agent edits → scanner or tests rerun → PR for human review. AeroPatch already uses this shape locally (finding → edit → gates → sandbox → re-scan). What it lacks is delivery to an ordinary user's own repo, not the core loop.
- No mainstream product found is local by default and free for private code. GitHub's free tier covers public repos only. Patchwork and codemodder are the closest local and open alternatives, and neither validates with exploit tests.
- Amazon has effectively left the dedicated security autofix space (CodeGuru Security gone, Q Developer sunsetting into Kiro). Treat it as a discontinued reference point.

### Gaps
- I did not read Mobb's or Corgea's primary docs on their exact delivery UI, only vendor marketing and a competitor's table.
- I found no primary source for Semgrep Guardian (product page only: [Semgrep Guardian](https://semgrep.dev/products/semgrep-guardian/)).
- I found no Ollama-specific Python vulnerability autofix tool. Searches for "Ollama autofix" returned only Ollama CVEs. Patchwork is the only confirmed local-endpoint option.
- I did not find the exact announcement day of CodeMender in a fetched source (2025).

## 2. What is the delivery surface for each, and what does the user see?

### Takeaway
The PR is the dominant surface, followed by the IDE. The strongest UX pattern is a PR or diff that carries (a) a summary of the fix, (b) why it closes the alert, and (c) the validation steps taken (GitHub agentic autofix), or a per-finding verdict with evidence (Codex Security). Plain-language explanations and one-click "Try to fix" appear mainly in products built for non-developers (Lovable).

### Cited Findings

| Product | Surface(s) | What the user sees | Source |
|-|-|-|-|
| GitHub agentic autofix (GA 2026-10-15) | Alert page "Assign to Copilot" → draft PR; Agents tab; REST API | PR with "a summary of the fix, why it closes the alert, and the validation steps Copilot took"; follow-up changes through PR comments | [GitHub changelog](https://github.blog/changelog/2026-10-15-agentic-autofix-for-code-scanning-alerts-general-availability/) |
| Copilot Autofix classic (older, 2024) | PR alert | Explanation plus suggested diff; dismiss, edit or commit | [GitHub blog 2024](https://github.blog/news-insights/product-news/secure-code-more-than-three-times-faster-with-copilot-autofix/) |
| Snyk Agent Fix | IDE (in-line), also PR | Several fix candidates, preview before applying (2024) | [Snyk blog 2024](https://snyk.io/blog/ai-code-security-snyk-autofix-deepcode-ai/); PR surface per [Checkmarx comparison](https://checkmarx.com/learn/appsec/best-automated-remediation-for-application-vulnerabilities-top-8-solutions-compared/) |
| Semgrep Autofix (beta 2026-03) | PRs | Upgrade guidance, breaking-change analysis, fix suggestions it calls high-confidence | [Semgrep blog](https://semgrep.dev/blog/2026/semgrep-autofix-public-beta/) |
| Aikido AutoFix | Daily auto-PRs, IDE, PR comments | Fix PRs with a configurable title, description, labels and branch; only medium or high confidence | [Aikido help](https://help.aikido.dev/autofix-and-remediation/automation-and-merging/automatic-creation-of-pull-requests) |
| Pixee | GitHub App PRs on a schedule; codemodder CLI with a JSON report | PR; JSON "what changed and why" | [Pixee docs](https://docs.pixee.ai/open-source/codemodder/) |
| Codex Security | Codex desktop and CLI plugin, SDK; findings workspace | Findings with "coverage, severity, confidence"; sort by confidence; "source evidence, validation details, reachability, impact, and remediation guidance in one place" (0.1.9, 2026-06-18); live progress view showing phase, elapsed time, files reviewed and token usage (0.1.17) | [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog) |
| Codex Security verify-fix | Plugin skill `$codex-security:verify-fix` | "`fixed`, `still_vulnerable`, or `inconclusive` result for each finding, with supporting evidence and validation limits" (0.1.22, 2026-08-25) | [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog) |
| Codex Security assess-patch-risk | Plugin skill | "advisory recommendation to merge, revise, or make no change"; impact, likelihood and "difficulty of recovery" assessed separately (0.1.23, 2026-09-08) | [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog) |
| Claude Code `/security-review` | Terminal slash command | "detailed explanations provided for each issue found"; the support article has a section on implementing fixes | [Claude support](https://support.claude.com/en/articles/11932705-automated-security-reviews-in-claude-code) |
| Claude Code security Action | PR line comments | Explanation, severity rating, remediation guidance; no auto-applied fix described | [GitHub repo](https://github.com/anthropics/claude-code-security-review) |
| CodeMender | Local CLI and VS Code talking to a hosted agent | Standard diffs and PRs for developer approval | [Google Cloud](https://cloud.google.com/security/codemender) |
| Veracode Fix | IDE, CLI batch mode; PRs for SCA | Fix suggestions applied by the developer; SCA PR "with rationale and supporting references" | [Veracode](https://www.veracode.com/products/fix/); [Checkmarx comparison](https://checkmarx.com/learn/appsec/best-automated-remediation-for-application-vulnerabilities-top-8-solutions-compared/) |
| Checkmarx Developer Assist | User's AI assistant through MCP (IDE) | Suggested remediation | [Checkmarx docs](https://docs.checkmarx.com/en/34965-549181-using-developer-assist-for-detection-and-remediation.html) |
| Socket | CLI `socket fix`, `socket patch`; agent skills | Dependency upgrades or patches with rollback | [Socket CLI docs](https://docs.socket.dev/docs/socket-cli) |
| Patchwork | CLI (`patchwork AutoFix`) | Fix PR on GitHub (needs a GitHub token) | [patchwork](https://github.com/patched-codes/patchwork) |
| Lovable Security Center | In-app dashboard | Severity, plain-language explanation, one-click "Try to fix", prompt to review critical issues before publishing | [Lovable blog](https://lovable.dev/blog/a-founders-guide-to-lovable-security) |

- Codex Security exports results as JSON, CSV or SARIF, including SARIF "readable rule names, remediation guidance, CWE tags, and security severity for GitHub code scanning" (0.1.21). — [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)
- Codex Security writes "source-backed vulnerability reports that separate observed behavior from unverified hypotheses", including "realistic proof-of-concept limitations" (0.1.16). Its `report.md` is the entry point to per-finding reports (0.1.11). — [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)
- Codex Security compares scans and labels each finding "new, persisting, resolved, and not-rescanned" (0.1.14). — [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)

### Inferences
- A visible "validation steps taken" block (GitHub) or a tri-state verdict with evidence (Codex) is now table stakes for trust. AeroPatch's 8 gates and sandbox results map onto this directly. A non-expert summary could read: "Fixed: the attack test no longer works, your tests still pass, the scanner no longer flags it", or "Couldn't confirm".
- Explicit confidence scores are rare in the UI. Products use confidence internally as a gate (Aikido) or a sort key (Codex) rather than showing a percentage. A coarse label such as high/medium/inconclusive seems to be the norm.
- For non-developers, the Lovable pattern (dashboard with plain-language explanation plus one "Try to fix" button plus a check before publishing) is the closest model. No PR or Git knowledge is assumed.

### Gaps
- I could not confirm whether GitHub or Semgrep show any numeric confidence to the user. No source found.
- Mobb's and Corgea's exact explanation format was not verified from primary docs.

## 3. How does each validate a fix before showing it, and what do they report about acceptance or accuracy?

### Takeaway
Validation now ranges from scanner re-runs (GitHub reruns CodeQL), to symbolic re-analysis plus internal unit-test benchmarks (Snyk), to exploit/regression verification with a tri-state verdict (Codex Security), to LLM-as-judge (CodeMender). Very few vendors publish real-world acceptance rates. Pixee says it is the only one of seven to publish a merge rate (76%, its own number). Independent benchmarks show that unvalidated LLM patches are mostly wrong, and that small open models score near 0% on exploit-validated Python repair.

### Cited Findings

**Validation methods**
- GitHub agentic autofix validates by "rerunning CodeQL" and iterates. — [GitHub changelog 2026-10-15](https://github.blog/changelog/2026-10-15-agentic-autofix-for-code-scanning-alerts-general-availability/)
- According to an extract of the docs, agentic autofix works on a best-effort basis and cannot confirm fixes for alerts from custom CodeQL queries, from the `security-extended` suite, or from third-party tools. — [GitHub Docs](https://docs.github.com/en/code-security/concepts/code-scanning/autofix-for-code-scanning)
- Snyk (2024): "all predictions are checked against our human-created rules and knowledge base (embodied in our symbolic AI)" before reaching customers. CodeReduce shrinks the context given to the model and "improved GPT-4's accuracy by up to 20%". — [Snyk blog 2024](https://snyk.io/blog/ai-code-security-snyk-autofix-deepcode-ai/); [Snyk blog](https://snyk.io/blog/find-auto-fix-prioritize-intelligently-snyks-ai-powered-code/)
- Snyk (2026, paraphrased from an extract): internal "golden tests" pair real-world vulnerable snippets with unit tests. A fix must flip the security test from FAIL to PASS while keeping the functional test passing (PASS to PASS). The suite has about 150 tests. — [Snyk blog 2026-04-27](https://snyk.io/blog/snyk-agent-fix-agentic-architecture/)
- Codex Security: patches include "regression coverage, and verification of the original issue". verify-fix returns fixed, still_vulnerable or inconclusive "with supporting evidence and validation limits", and adds "an investigation before patching and a review after patching". — [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)
- CodeMender (paraphrased from an extract) uses an LLM-as-a-judge framework to test modified code for program equivalence. — [Google Cloud](https://cloud.google.com/security/codemender)
- DeepMind lists criteria of root cause fixed, functionally correct, no regressions, and style followed. — [DeepMind blog](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/)
- A secondary source says every CodeMender patch was reviewed by a human researcher before upstreaming. — [Medium (secondary)](https://medium.com/@tahirbalarabe2/how-google-deepmind-codemender-ai-automates-code-security-400f51ba3a52)
- Veracode: "No place for hallucinations"; "inbuilt quality-gates"; does "not retain customer code". — [Veracode Fix](https://www.veracode.com/products/fix/)
- Pixee (competitor table): Checkmarx uses "Syntax + build checks" as its hallucination safeguard. Veracode's safeguard is "Not disclosed". — [Pixee Veracode-alternatives (competitor)](https://www.pixee.ai/blog/veracode-alternatives)
- Pixee: deterministic codemods plus a Fix Evaluation Agent. — [Pixee 2026 comparison (vendor)](https://www.pixee.ai/blog/best-automated-remediation-tools-2026)
- Aikido gates PR creation on AutoFix "medium or high confidence". — [Aikido help](https://help.aikido.dev/autofix-and-remediation/automation-and-merging/automatic-creation-of-pull-requests)
- The Claude Code security review Action reports findings only and does not validate fixes. — [GitHub repo](https://github.com/anthropics/claude-code-security-review)

**Published numbers (vendor self-reported unless noted)**
- GitHub (older, 2024 beta data): "the median time for developers to use Copilot Autofix to automatically commit the fix for a pull request-time alert was 28 minutes, compared to 1.5 hours" manually (3x faster). According to an extract of the same post, XSS took 22 minutes versus almost three hours (7x) and SQL injection 18 minutes versus 3.7 hours (12x). — [GitHub blog 2024-08-14](https://github.blog/news-insights/product-news/secure-code-more-than-three-times-faster-with-copilot-autofix/)
- GitHub (older, 2024; from an extract, not verified verbatim): Autofix helps developers fix more than two-thirds of supported alerts with little or no editing. — [GitHub blog 2024](https://github.blog/news-insights/product-news/found-means-fixed-introducing-code-scanning-autofix-powered-by-github-copilot-and-codeql/)
- GitHub (2026): "GitHub has not published public data on autofix acceptance rates or post-merge regression rates at enterprise scale." — [Tech Insider (secondary), Oct 2026](https://tech-insider.org/github-ai-autofix-ga-codeql-2-27-2026/)
- Snyk (2024): "80% security fix accuracy". — [LinkedIn post by Snyk exec (2024)](https://www.linkedin.com/posts/mnair1_snyk-autofix-ai-code-security-improvements-activity-7188935483618402304--xJ-)
- Snyk (2026): DeepCode AI "powers 85%-accurate security autofixes". — [Snyk DeepCode AI page](https://snyk.io/platform/deepcode-ai/)
- Snyk golden-test "functional and secure fix" rates (about 150 tests, internal, 2026-04-27; figures from an extract): Opus 4.6 + Snyk intelligence 85.4%; Sonnet 4.6 + Snyk 82.5%; Opus 4.6 alone 74.6%; Gemini 3.1 Pro 74.2%; Sonnet 4.6 alone 72.4%; StarCoder (current Snyk model) 72.4%. Adding Snyk intelligence raised pass rates by 14.48%. — [Snyk blog 2026-04-27](https://snyk.io/blog/snyk-agent-fix-agentic-architecture/)
- Pixee claims a 76% merge rate (production customer data, calendar 2024-2025), measured as whether each PR it opened was merged, which it describes as three of four fixes reaching production without modification. Its table lists merge rates for Copilot Autofix, Snyk, Mobb and Corgea as not published, and gives Veracode as "vendor claims 60-70% acceptance" (figures from an extract). The page subtitle says "only one publishes its merge rate". — [Pixee 2026 comparison (vendor)](https://www.pixee.ai/blog/best-automated-remediation-tools-2026)
- Corgea: "fix accuracy above 90% by Corgea's reporting". Corgea's own July 2026 benchmark claims 82% precision and 89% recall on 47 confirmed issues. It says Latio Tech's autofix report ranked Corgea "first of seven tools on coverage multiplied by quality". — [Corgea (vendor)](https://corgea.com/learn/best-sast-tools)
- Veracode: "covers over 70% of detected flaws in 10 supported languages" (coverage, not accuracy). — [Veracode](https://www.veracode.com/products/fix/)
- OpenAI: Codex Security "scanned 1.2 million commits", finding 792 critical and 10,561 high-severity issues (OpenAI-reported, March 2026). — [The Hacker News](https://thehackernews.com/2026/03/openai-codex-security-scanned-12.html?m=1)
- CodeMender: 72 security fixes upstreamed (2025). — [AI Business (secondary)](https://aibusiness.com/agentic-ai/google-codemender-patches-code-vulnerabilities)

**Independent and academic evaluations**
- AutoPatchBench (Meta, 2025-04-29) has 136 fuzzing-crash samples. "Gemini 1.5 Pro achieved a 61.1% patch generation success rate, yet fewer than 15% of these patches (5.3% out of total set) were found to be correct." — [Meta Engineering](https://engineering.fb.com/2025/04/29/ai-research/autopatchbench-benchmark-ai-powered-security-fixes/)
- VulnRepairEval (arXiv 2509.03331, 2025-09-03) has 23 Python CVEs across 9 categories, with Docker-isolated PoC checks. "A repair counts as success only when the original PoC no longer works after patching." The paper reports (verbatim): "the strongest model repairs 5/23 (≈21.7%), while several models repair at most one case; the average end-to-end success is about 7%. Most failures arise from incorrect localization (commonly 60–78% of attempts), followed by unusable/incorrect diffs and logically incomplete fixes." Also: "Enhanced prompting strategies and multi-agent approaches yield minimal improvements", and "the agent reduces abstentions and yields more applicable patches, yet the PoC-validated end-to-end success remains low." — [arXiv 2509.03331](https://arxiv.org/html/2509.03331v1)
- Per-model VulnRepairEval figures (from an extract of the results table, not verified verbatim): Gemini 2.5 Pro 21.7% (best), DeepSeek R1 671B 17.4%, DeepSeek V3 671B 13.0%, Qwen3 235B thinking 8.7%, GPT-4o 0%, and Qwen3 8B 0% with and without thinking. The extract also reports that SWE-agent cut detection failure for DeepSeek V3 from over 80% to 26%. — [arXiv 2509.03331](https://arxiv.org/html/2509.03331v1)
- CVE-Bench (NAACL 2025): agents repaired about 21% of CVEs; Python repair rate was 21.17%. GPT-4 scored 23%, Llama-3 15% and GPT-3.5 5%. — [ACL Anthology](https://aclanthology.org/2025.naacl-long.212.pdf)
- SAN2PATCH (USENIX Security 2025, C/sanitizer setting) reports a 79.5% patch success rate (31/39) on VulnLoc. — [USENIX appendix](https://www.usenix.org/system/files/usenixsecurity25-appendix-kim-youngjoon.pdf)

### Inferences
- The gap between "a patch was generated" and "the patch is correct" is large: 61.1% versus 5.3% in AutoPatchBench. Re-scanning alone (GitHub's method) can confirm that the alert disappeared without proving that the exploit is closed. AeroPatch's PoC-plus-regression sandbox is stricter than most commercial validation. That is a real differentiator, but only while exploit tests exist.
- VulnRepairEval's 0% for Qwen3 8B under single-shot PoC validation is a warning that a 4B local model will often fail on real code. The repair loop, deterministic codemods and the escalation path matter more than the model. "Couldn't fix, here is why" has to be a first-class, honest outcome.
- Vendor accuracy numbers come from internal benchmarks (Snyk's roughly 150 golden tests) or from merge rates the vendor measured itself (Pixee). None are independently audited, so AeroPatch's own published benchmark numbers would be comparable in kind.

### Gaps
- No independent, published acceptance or merge rate exists for GitHub agentic autofix, Snyk, Semgrep Autofix, Aikido, Mobb or Codex Security.
- The Latio Tech autofix report was not read directly; Corgea's summary is the only source.
- Semgrep Autofix's validation method is not described on its beta page.

## 4. How do they handle findings triage and false positives for the user?

### Takeaway
Triage is the most mature AI feature. Vendors claim it filters most noise before a human sees it: Semgrep handles 60% of triage with over 96% user agreement, Aikido claims 85% extra false-positive removal, and Pixee claims a 70–95% cut. The best designs remember why a finding was dismissed and re-apply that reason only while it still holds (Codex Security, Semgrep Memories). They also throttle fix volume (Aikido's PR caps) and exclude low-value categories up front (Claude Code).

### Cited Findings
- Semgrep Assistant "triages 60% of all SAST findings for customers, filtering out false positives before security teams ever see them. When users audit Assistant's triage history, they agree over 96% of the time" (2025-09-10). — [Semgrep blog](https://semgrep.dev/blog/2025/semgrep-is-confidently-handling-60-of-all-triage-for-users-without-reducing-coverage/)
- Conflict in Semgrep's own figures: the 2025-09-10 post gives users' agreement as over 96%. — [Semgrep blog](https://semgrep.dev/blog/2025/semgrep-is-confidently-handling-60-of-all-triage-for-users-without-reducing-coverage/). The Memories post and the metrics page it cites give users' agreement as "over 95%" and researchers' as "over 96%". — [Semgrep blog (Memories)](https://semgrep.dev/blog/2025/making-zero-false-positive-sast-a-reality-with-ai-powered-memory/)
- Semgrep Multimodal is "over 95% accurate in categorizing Semgrep Code findings as false positives". Memories lets teams tailor triage. — [Semgrep docs](https://docs.semgrep.dev/semgrep-multimodal/overview)
- According to an extract of the Autofix beta post, Semgrep claims to deprioritise more than 95% of false positives. — [Semgrep blog 2026-03-16](https://semgrep.dev/blog/2026/semgrep-autofix-public-beta/)
- Aikido's AutoTriage agent "removes an additional 85% of false positives" (vendor video). — [Aikido YouTube](https://www.youtube.com/watch?v=iNvaMvtQXmk)
- Aikido limits PR volume: SAST PRs are created only for medium or high confidence; at most 2 PRs per repo per daily run, each with at most 5 changed files; at most 10 open SAST AutoFix PRs per repo. The stated rationale: "When you perform SAST scanning on a repository for the first time, you will typically discover a large amount of issues." — [Aikido help](https://help.aikido.dev/autofix-and-remediation/automation-and-merging/automatic-creation-of-pull-requests)
- Pixee claims three-tier triage cuts false positives by 70-95% (from an extract). — [Pixee 2026 comparison (vendor)](https://www.pixee.ai/blog/best-automated-remediation-tools-2026)
- Pixee's merge-rate article (paraphrased from an extract) recommends: triage before fixing; matching codebase context; giving merge-confidence signals; small, focused PRs with clear explanations; building trust gradually; and matching the amount of review to the actual risk. — [Pixee blog 2026-03-17](https://www.pixee.ai/blog/merge-rate-problem-security-prs-ignored)
- Corgea has a false-positive detection feature and multi-file analysis that it says gives "up to 40% fewer" false positives. — [Corgea blog](https://corgea.com/blog/improved-multi-file-analysis-and-false-positive-reduction); [Corgea FP feature](https://corgea.com/blog/introducing-corgea-s-new-feature-detecting-false-positives)
- Codex Security lets users "Record a reason when you close a finding as a false positive". It carries reviewed decisions into later scans of the same target and suppresses a recurring finding "only when the earlier reason still applies to the current code". It removes duplicates and keeps "the strongest finding by severity, confidence, and supporting evidence" (0.1.15, 2026-07-30). — [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)
- Codex Security keeps real findings in local, internal or non-production code and uses "deployment and exposure context to calibrate severity and confidence instead of automatically suppressing the finding" (0.1.13). — [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)
- Codex Security's `SECURITY.md` policy defines "trust boundaries, security invariants, reportable findings, severity, exclusions, and accepted risk" (0.1.11, 0.1.14). Its triage of external findings (scanners, bug bounty, Jira and others) returns "an evidence-backed verdict and a prioritized action queue" (0.1.9). — [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)
- According to an extract of the README, the Claude Code security review Action filters out these false-positive categories by default: denial of service, rate limiting, memory or CPU exhaustion, generic input validation without proven impact, and open redirects. — [GitHub repo](https://github.com/anthropics/claude-code-security-review)
- Checkmarx One uses "Attackability-based prioritization". — [Checkmarx](https://checkmarx.com/learn/appsec/best-automated-remediation-for-application-vulnerabilities-top-8-solutions-compared/)

### Inferences
- For a non-expert, triage matters more than fixing. A first run of Bandit or Opengrep on real code produces a long list (Aikido's stated reason for caps). AeroPatch should rank by severity and confidence, show only a handful ("top 3 to fix now"), and hide or collapse the rest.
- Codex's "dismiss with a reason, re-check the reason later" pattern can be built locally with a plain file in the repo (a reason plus a code fingerprint). No cloud is needed.
- A default exclusion list (like Claude Code's) and a short per-repo policy file (like `SECURITY.md`) are cheap ways to cut noise that need no model capacity.

### Gaps
- No independent measurement of any vendor's triage accuracy was found; all figures are self-reported.
- I did not find how Semgrep phrases "why this is a false positive" to the user. The page fetch returned only metadata.

## 5. What onboarding does each require, and which are designed for non-experts or small teams?

### Takeaway
Most products need an account, a repo connection (GitHub App or Action plus secret), and often an admin toggle or paid licence. GitHub's sources conflict on who can use agentic autofix: the GA changelog describes GitHub Enterprise Cloud with an enterprise-admin policy, while the docs also list public repos and GitHub Team orgs. The lowest-friction entry points are Claude Code's `/security-review` (no configuration, inside a tool the user already runs) and Lovable's built-in scanner (zero setup, aimed at founders). None of the zero-setup options is local.

### Cited Findings
- GitHub agentic autofix "requires an enterprise administrator to enable access ... via the new 'Agentic autofix' policy". After that an organisation or repository admin turns it on, and "Access also requires a Copilot billing method to be defined". It "consumes AI Credits from your Code Security budget and GitHub Actions minutes". — [GitHub changelog 2026-10-15](https://github.blog/changelog/2026-10-15-agentic-autofix-for-code-scanning-alerts-general-availability/)
- According to an extract of the docs, Copilot Autofix is available for public repositories on GitHub.com, while private and internal repositories need a GitHub Code Security licence. Agentic autofix is listed for public repositories and for organisation repos on GitHub Team with Code Security enabled. It needs no Copilot licence and is not available for Enterprise Managed Users repos. — [GitHub Docs](https://docs.github.com/en/code-security/concepts/code-scanning/autofix-for-code-scanning). This partly contradicts the GA changelog, which names only "GitHub Code Security and GitHub Advanced Security customers on GitHub Enterprise Cloud" and requires "a Copilot billing method". — [GitHub changelog](https://github.blog/changelog/2026-10-15-agentic-autofix-for-code-scanning-alerts-general-availability/)
- A competitor lists Copilot Autofix pricing as "$49/committer/mo (GHAS combined)". — [Pixee (competitor)](https://www.pixee.ai/blog/best-automated-remediation-tools-2026)
- Claude Code `/security-review`: "Update Claude Code to the latest version ..., then run `/security-review` in your project directory." — [Claude support](https://support.claude.com/en/articles/11932705-automated-security-reviews-in-claude-code)
- A user reports no setup and a finding in about 1 minute (anecdotal). — [Medium, 2026-02-23](https://alirezarezvani.medium.com/how-to-set-up-claude-codes-new-security-review-the-complete-practical-guide-0f900a680eb1)
- The Claude Code GitHub Action needs a workflow YAML, `pull-requests: write` permission and a `claude-api-key` secret. — [GitHub repo](https://github.com/anthropics/claude-code-security-review)
- Aikido onboarding: go to Autofix Settings, enable "Autocreation of PRs", select repos and containers, then click **Test Autocreation**. — [Aikido help](https://help.aikido.dev/autofix-and-remediation/automation-and-merging/automatic-creation-of-pull-requests)
- Aikido's CI option is a GitHub Action with an `AIKIDO_SECRET_KEY`. — [AppSec Santa (secondary)](https://appsecsanta.com/aikido)
- Bret Fisher discusses Aikido for "smaller teams and solo #DevOps practitioners". — [LinkedIn](https://www.linkedin.com/posts/bretefisher_devops-github-activity-7285283344739627008-2e_h)
- Pixee: install the GitHub App. — [GitHub Apps](https://github.com/apps/pixeebot)
- Pixee codemodder: `pip install codemodder`, then `codemodder /path/to/project --output results.json`. — [Pixee docs](https://docs.pixee.ai/open-source/codemodder/)
- Socket: `npm install -g socket`, then `socket login` with an API token. — [Socket CLI docs](https://docs.socket.dev/docs/socket-cli)
- Patchwork: a CLI with `openai_api_key` (or a local endpoint) and a `github_api_key`. — [patchwork](https://github.com/patched-codes/patchwork)
- Codex Security can scan "Git repositories, individual folders, or codebases without Git history" (0.1.9). It installs without the optional access app (0.1.21) and has a Windows fix to use Codex's bundled Node.js. It advises on "Trusted Access for Cyber" / Daybreak access but continues the scan if the check fails (0.1.20, 0.1.24). — [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)
- Codex Security setup reports "individual readiness checks and their blocking or warning details" and keeps a scan open "while you decide how to resolve a setup issue" (0.1.23). — [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)
- CodeMender is available only to customers and governments that qualify for Google's Fairwind Program (from an extract). — [Google Cloud](https://cloud.google.com/security/codemender)
- Amazon Q Developer has blocked new signups since 2026-05-15. — [AWS blog](https://aws.amazon.com/blogs/devops/amazon-q-developer-end-of-support-announcement/)
- Lovable (built for founders) runs its scans automatically and before publish, with no setup. — [Lovable blog](https://lovable.dev/blog/a-founders-guide-to-lovable-security)
- A Reddit commenter says Lovable's "new security checker and RLS configurator works pretty well", but "for non-developers it's little far" (anecdotal). — [Reddit r/lovable](https://www.reddit.com/r/lovable/comments/1low49w/followup_on_security_in_vibecoded_apps_its_worse/)

### Inferences
- The UX bar for non-experts is "one command in a folder, no account, no Git required" (Claude Code `/security-review`, Codex scanning folders without Git). AeroPatch can meet it locally. The hard part is the one-time setup of Ollama, the model pull and Docker, which none of the cloud tools ask users to do.
- Codex Security's readiness checks (each check shown as blocking or warning, with the scan kept open while the user fixes setup) are a good model for an `aeropatch doctor` step covering Ollama running, model present, Docker running and memory headroom.

### Gaps
- No user studies of onboarding drop-off or time-to-first-fix for any product were found.
- Free-tier limits for Aikido, Corgea, Mobb and Snyk Agent Fix were not verified.

## 6. What do users and reviewers complain about?

### Takeaway
The recurring complaints are noise (developers ignore most automated security PRs), broken or superficial fixes, misplaced trust and rubber-stamp review, volume of bot PRs, cost and licensing, and sending code to the cloud. The 2026 Wiz/Snowflake incident turned "AI review said it was fine" into a public cautionary tale, although GitHub disputes Copilot's role.

### Cited Findings
- **Noise and low merge rates.** "Bot-generated pull requests get accepted at 37.38%, compared to 72.53% for human submissions" (page text). According to an extract of the same post: Dependabot security PRs reach about 13% adoption in JS open-source projects, and 85% of issues flagged by AI code review are dismissed (Arnica data). The reasons given are fixes that lack codebase context, explanations and proof of safety; false positives eroding trust; and review fatigue. — [Pixee blog 2026-03-17 (vendor, aggregating third-party studies)](https://www.pixee.ai/blog/merge-rate-problem-security-prs-ignored)
- **Trust and over-reliance (Snowflake, Aug 2026).** Wiz's autonomous Red Agent exploited a GitHub Actions script injection in Snowflake's .NET connector repo and extracted a Jira token. CSA reports (verbatim): "Copilot Autofix — listed as a co-author on the merged pull request — is described by Wiz as having reviewed the change and missed it as well, a characterization GitHub disputes, stating Copilot never reviewed the specific vulnerable lines". GitHub stated that "a human wrote the contributions that led to the vulnerability, and that Copilot Autofix neither reviewed nor contributed to them". The flaw was exploitable for about five days. CSA recommends that organisations "treat a clean AI review as one input among several rather than a sufficient control", noting that for well-known classes such as CI/CD injection "a dedicated static analysis rule or linter is likely to be more reliable than general-purpose AI review". — [CSA research note 2026-08-25](https://labs.cloudsecurityalliance.org/research/csa-research-note-wiz-red-agent-copilot-snowflake-20260825-c/); [daily.dev summary of the dispute](https://daily.dev/posts/github-disputes-wiz-s-claim-that-copilot-autofix-wrote-a-snowflake-flaw-ybruxnh95); [The Hacker News](https://thehackernews.com/2026/08/snowflake-github-actions-flaw-lets_0330881554.html?m=1)
- The Hacker News thread had 424 points and 157 comments. david_shaw called it "a natural evolution of the 'LGTM!' review", adding that "most people weren't really reviewing code assigned to them. They were effectively rubber-stamping most things." johnwils wrote: "The env + jq was there on purpose. Autofix swapped it for a string in a shell. That's the part that needed a person on the diff." As a counterpoint, kozikow criticised judging from a single incident "without giving a 'denominator'". — [Hacker News](https://news.ycombinator.com/item?id=49331423)
- **Broken or incorrect fixes.** AutoPatchBench: most "successful" generated patches were not correct (61.1% generated versus 5.3% correct). — [Meta](https://engineering.fb.com/2025/04/29/ai-research/autopatchbench-benchmark-ai-powered-security-fixes/)
- A Lovable community member advises fixing issues one at a time "instead of stacking 12 warnings and hitting 'Try to Fix All' (which often creates new problems)" (anecdotal). — [Facebook group](https://www.facebook.com/groups/lovableboost/posts/1298729689005961/)
- Another Lovable post says the AI "will try to fix it five or six times ... and never get to the root cause" (anecdotal, general bugs). — [Reddit r/vibecoding](https://www.reddit.com/r/vibecoding/comments/1t95536/most_common_breaks_i_see_in_lovablebolt_apps_and/)
- Veracode Fix: "Users report that Fix proposes dependency versions that conflict with enterprise architecture constraints." — [Pixee (competitor)](https://www.pixee.ai/blog/veracode-alternatives)
- "Interface and reporting feel dated to some users." — [Checkmarx (competitor)](https://checkmarx.com/learn/appsec/best-automated-remediation-for-application-vulnerabilities-top-8-solutions-compared/)
- **Unsolicited bot PR volume.** In March 2026 Aardvark opened 13 pull requests against NVIDIA's OpenShell repo (secondary, unverified). — [Towards AI](https://pub.towardsai.net/codex-security-openai-built-an-ai-to-find-security-bugs-b0c9fa47f673)
- **Privacy and cloud.** A Reddit thread describes a company about to ban AI coding over "sending code over the internet". — [Reddit r/ClaudeAI](https://www.reddit.com/r/ClaudeAI/comments/1qk3umy/my_company_is_about_to_ban_ai_coding_bc_security/)
- Vendors answer this concern directly: Veracode says it "does not retain customer code". Pixee lists only itself and Moderne as air-gapped capable among seven tools. — [Veracode](https://www.veracode.com/products/fix/); [Pixee](https://www.pixee.ai/blog/best-automated-remediation-tools-2026)
- **Prompt injection.** According to an extract of the README, the Claude Code security review Action is not hardened against prompt-injection attacks and should only be used on trusted PRs. — [GitHub repo](https://github.com/anthropics/claude-code-security-review)
- **Opaque results and cost.** No public acceptance or regression data exists for GitHub autofix at scale. — [Tech Insider (secondary)](https://tech-insider.org/github-ai-autofix-ga-codeql-2-27-2026/)
- Agentic autofix bills AI credits plus Actions minutes. — [GitHub changelog](https://github.blog/changelog/2026-10-15-agentic-autofix-for-code-scanning-alerts-general-availability/)
- **Vibe-coded app risk.** A May 2025 study found 170 of 1,645 sampled Lovable apps had RLS issues (secondary). — [Chiri Atlas (secondary)](https://chiri.ai/chiri-atlas/lovable)

### Inferences
- The Snowflake episode and the HN reaction show that a confident "all clear" is more dangerous than an honest "inconclusive". AeroPatch should never present a scanner-only pass as "safe". It should state exactly which checks ran.
- "Try to Fix All" on many issues at once is a known failure pattern for non-experts. Fixing one issue at a time with a verified result each time is safer and matches AeroPatch's per-finding loop.
- Local-by-default directly answers the privacy complaint. Optional escalation to a cloud model should be explicit, opt-in per finding, and say what code will be sent.

### Gaps
- No systematic user survey of AI security autofix satisfaction was found. Complaints come from vendor-aggregated statistics, one incident and anecdotes.
- The Towards AI claim about 13 NVIDIA PRs was not verified against the repo.
- Direct Reddit r/netsec complaints specific to Copilot Autofix quality were not found in this pass.

## 7. Which of these patterns are realistic for a free, local, single-laptop open-source tool?

### Takeaway
Most of the trust-building UX patterns are cheap and local: a validation summary, a tri-state verdict, confidence-gated output, small batches, dismiss-with-reason memory, default exclusions, plain-language explanations, a readiness check and SARIF export. Hosted agents, cloud dashboards, PR bots and frontier-model exploration are not realistic. Evidence suggests a 4B local model will often fail on real code, so deterministic fixes first plus an honest "couldn't fix" plus opt-in escalation is the realistic design.

### Cited Findings
- Tri-state verdict with evidence and "validation limits" (fixed / still_vulnerable / inconclusive). — [Codex Security changelog 0.1.22](https://www.codex-docs.com/en/docs/security/plugin/changelog)
- PR or report body with "a summary of the fix, why it closes the alert, and the validation steps". — [GitHub changelog 2026-10-15](https://github.blog/changelog/2026-10-15-agentic-autofix-for-code-scanning-alerts-general-availability/)
- Confidence gate and volume caps (medium or high only; 2 PRs and 5 files per day; 10 open). — [Aikido help](https://help.aikido.dev/autofix-and-remediation/automation-and-merging/automatic-creation-of-pull-requests)
- Deterministic, pip-installable Python codemods (LibCST) with a JSON "what changed and why" report. — [Pixee codemodder docs](https://docs.pixee.ai/open-source/codemodder/)
- False-positive memory: a reason is recorded and re-checked against current code. — [Codex Security changelog 0.1.15](https://www.codex-docs.com/en/docs/security/plugin/changelog)
- Default exclusion categories (DoS, rate limiting and others). — [Claude Code security review](https://github.com/anthropics/claude-code-security-review)
- Scan folders "without Git history"; readiness checks shown as blocking or warning. — [Codex Security changelog](https://www.codex-docs.com/en/docs/security/plugin/changelog)
- Plain-language explanation plus one-click "Try to fix", and a review of critical issues before publishing. — [Lovable blog](https://lovable.dev/blog/a-founders-guide-to-lovable-security)
- Local OpenAI-compatible endpoint support is proven in an open-source autofix CLI. — [patchwork](https://github.com/patched-codes/patchwork)
- On PoC-validated Python repair the average model success is "about 7%", and Qwen3 8B scored 0/23 (per-model figure from an extract). "Enhanced prompting strategies and multi-agent approaches yield minimal improvements"; the agent mainly "reduces abstentions". — [VulnRepairEval](https://arxiv.org/html/2509.03331v1)
- Fixes in the context-reduction style (narrowing to relevant code) improved GPT-4 accuracy "by up to 20%" at Snyk. — [Snyk blog](https://snyk.io/blog/find-auto-fix-prioritize-intelligently-snyks-ai-powered-code/)
- Patch risk assessed as impact, likelihood and "difficulty of recovery", with an advisory to merge, revise or make no change. — [Codex Security changelog 0.1.23](https://www.codex-docs.com/en/docs/security/plugin/changelog)

### Inferences
**Realistic to copy, mostly UX work on top of the existing pipeline:**
- **One-command entry on any folder.** `aeropatch scan .` with no Git or account needed, mirroring `/security-review` and Codex folder scans. Add a readiness check ("doctor") that reports Ollama, the model, Docker and RAM, each as blocking or warning.
- **Triage before fixing.** Rank findings by severity and confidence, apply a default exclusion list, and show the top few with a one-paragraph plain-language "what could happen" explanation. Collapse the rest.
- **Tri-state outcome per finding**, mapped onto the existing gates: Fixed (PoC blocked, tests pass, re-scan clean); Partly verified / inconclusive (re-scan clean, but no exploit test available for user code); Not fixed (attempts exhausted, with the reason). Always list which checks ran, as GitHub does.
- **Deterministic first tier.** Run pixee `codemodder-python` codemods (or equivalent rules) before the LLM for common Bandit and Opengrep patterns. This lowers dependence on a 4B model, which benchmarks suggest is weak at repair.
- **Small batches and caps.** One finding at a time by default, with an "apply" step per fix showing a diff and a one-line undo (git stash, or a backup copy for non-Git folders). Avoid a "fix all" button, given the Lovable "Try to Fix All" complaints.
- **Dismiss with a reason.** Store the reason in a local file keyed to a code fingerprint, and re-check it on rescan (the Codex and Semgrep Memories pattern).
- **SARIF and Markdown report export**, so results open in VS Code or GitHub code scanning without AeroPatch hosting anything.
- **Privacy statement as a feature.** "Your code never leaves this laptop", with escalation to Claude through the user's own subscription shown per finding as an explicit opt-in.

**Not realistic, or out of scope for a free single-laptop tool:**
- Hosted PR bots or GitHub Apps that run on a schedule (Pixeebot, Aikido daily PRs) need a server. A local Git branch or patch file is the substitute. A GitHub Action is possible only if the runner can host the model, which is unlikely on free runners.
- Multi-hour, multi-worker deep scans with frontier models (Codex's up-to-96-hour deep scans), cross-repo agentic exploration (GitHub agentic autofix), and LLM-as-judge with large models (CodeMender) do not fit a 4 GB VRAM budget.
- Enterprise dashboards, policy administration and multi-scanner ingestion across ecosystems.

**Key open design problem specific to AeroPatch:**
- On a user's own code there is no hand-written exploit test, so the strongest gate (PoC) is missing. Options are: generate a PoC test per CWE template and label it lower confidence, fall back to re-scan plus the user's existing tests and report "inconclusive" honestly, or escalate. This needs its own research. No product found solves it locally; Codex Security does it with frontier models and a validation phase.

### Gaps
- No evidence was found on how well non-experts understand any of these outputs (no usability studies). The inferences above extrapolate from product design and complaints.
- Whether codemodder-python's codemods cover the specific Bandit and Opengrep rules AeroPatch targets was not checked.
- How well 4B-class models do at generating PoC exploit tests (rather than patches) was not researched here.
