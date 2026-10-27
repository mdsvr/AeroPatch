# Human factors: presenting security findings and AI-generated fixes to non-expert users (as of 2026-10-22)

Legend: **[fetched]** = read on the source page itself in this pass. **[snippet]** = seen only in a search-result excerpt or a secondary write-up; verify before quoting. **[vendor]** = a commercial scanner or security vendor's own study, not peer reviewed. Older work is date-tagged.

## 1. Who the non-expert users are, and how secure their AI-built code is

### Takeaway
AI coding is near universal among developers in 2026 (83% use AI at work, 73% daily), and the "vibe-coded" app population that non-experts ship has a high, repeatedly measured rate of basic, exploitable flaws (exposed secrets, broken access control, open databases). Every source finds the same thing: these users lean on "does it work" as their security check. The data on non-developer vibe coders is mostly vendor scans, not peer-reviewed surveys.

### Cited Findings
**Who uses AI to code (2026 survey data)**
- Stack Overflow 2026 Developer Survey (results blog, 6 Oct 2026): 83% use AI at work (about flat on 2025), 73% use AI tools daily, 66% use AI agents, 63% use general chatbots, over 60% use two to five AI tools. 53% use AI tools to learn to code. Security concerns ranked second as a source of friction (no percentage given). "Vibe coding" is not mentioned. [fetched] — [Stack Overflow blog, 2026-10-06](https://stackoverflow.blog/2026/10/06/tales-from-the-2026-developer-survey-results/)
- The same survey: 48% trust AI output "when they can verify it", 7% trust it for many tasks and decisions, 79% rate source attribution as important or very important. "Plausible but wrong code" was the top AI-caused disruption, and "almost right code" the top friction. [fetched] — [Stack Overflow blog, 2026-10-06](https://stackoverflow.blog/2026/10/06/tales-from-the-2026-developer-survey-results/). Press coverage gives more than 30,000 respondents in 169 countries and 6.6% trusting AI for important decisions. [snippet] — [IT Brief UK](https://itbrief.co.uk/story/stack-overflow-survey-shows-developers-trust-ai-with-caveats)
- Older (2025 survey): 46% actively distrust AI accuracy vs 33% who trust it, only 3% "highly trust", and 66% cite "AI solutions that are almost right, but not quite". [snippet] — [LeadDev](https://leaddev.com/technical-direction/trust-in-ai-coding-tools-is-plummeting)
- "Vibe coding" (building by prompting and accepting AI output without reading the code) has a Wikipedia entry; the term dates from 2025. [not fetched] — [Wikipedia: Vibe coding](https://en.wikipedia.org/wiki/Vibe_coding)

**Security of what they ship (mostly vendor scans)**
- Escape.tech [vendor] scanned over 5,600 publicly deployed apps built on vibe-coding platforms (sourced from launch directories such as launched.lovable.dev, Shodan, Reddit and manual crawling). It found more than 2,000 vulnerabilities, 400+ exposed secrets and 175 instances of exposed PII (medical records, IBANs, phone numbers, emails). Escape's own summary page instead says "1.4K" apps, an unresolved inconsistency. [snippet] — [Escape methodology](https://escape.tech/blog/methodology-how-we-discovered-vulnerabilities-apps-built-with-vibe-coding/); [Escape summary](https://escape.tech/state-of-security-of-vibe-coded-apps)
- Tenzai [vendor] pen-tested 15 apps built with 5 AI coding tools and found 69 vulnerabilities, 6 of them critical, mostly OWASP Top 10 classics (SQL injection, broken authentication, hardcoded secrets). [snippet] — [SecurityWeek](https://www.securityweek.com/vibe-coded-apps-riddled-with-exploitable-security-flaws/); [DEV Community](https://dev.to/gabrielanhaia/69-vulnerabilities-in-15-apps-the-vibe-coding-security-reckoning-is-real-23o2)
- One aggregator reports three more studies; none was checked against its primary source. (a) An academic audit of 200 deployed vibe-coded repos: 180 (90%) vulnerable, 1,471 vulnerabilities, broken access control the top class at 36%. (b) SUSVIBES (ICML 2026): on synthetic tasks the best configuration was 57% functionally correct but only 11.8% secure. (c) Kingbird [vendor]: "91.5% of vibe-coded apps have vulnerabilities", which counts apps with at least one flaw; methodology partly undisclosed. [snippet, aggregator] — [SoftwareSeni Q1 2026 round-up](https://www.softwareseni.com/91-5-percent-of-vibe-coded-apps-have-vulnerabilities-and-what-the-q1-2026-research-actually-shows/)
- Vibe-Eval [vendor] monthly report, August 2026: 30,998 apps scanned, 57% with an open Supabase backend, "4.4x more flaws" (headline only). [snippet] — [Vibe-Eval Aug 2026](https://vibe-eval.com/updates/vibe-coding-security-monthly-aug-2026/)
- Veracode GenAI Code Security Report 2026 (released 28 Jul 2026) [vendor, model benchmark rather than a user study]: the average security pass rate across more than 100 models is 56%, "nearly unchanged from last year", so about 44% of generation tasks produced code with a known vulnerability. Syntax pass rate is close to 100%. Python is the best language at 63% and Java the worst at 30%. The best model (GPT-5.5) reaches 68% and the worst (Qwen3.7-max) 50%. Reasoning models average 56% vs 51% for non-reasoning models. [snippet] — [SD Times](https://sdtimes.com/agentic-security/veracode-finds-ai-generated-code-security-has-barely-improved-since-last-year/); [eSecurityPlanet](https://www.esecurityplanet.com/threats/veracode-finds-ai-generated-code-still-struggles-with-security/); [report landing page](https://view.ceros.com/veracode/genai-code-security-report2026)
- Secrets: a GitGuardian figure cited by the Cloud Security Alliance puts AI-assisted commits at a 3.2% secret-leak rate vs a 1.5% baseline across all public commits. 24,008 unique secrets were found in MCP configuration files, 2,117 of them valid. [snippet] — [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-coding-assistant-attack-surface-2026040/)

**What they understand about security (user studies)**
- Khalid et al., "(Don't) Trust, but (Don't) Verify" (arXiv, 17 Sep 2026; 100 participants, 88 from Upwork, 91% male, mostly 18 to 29; four C tasks; five AI suggestions per task; bonus paid for secure code). Only 22% of the 400 submissions were fully secure. 16 of 23 interviewees took no explicit security steps, citing low perceived risk, lack of knowledge, or prioritizing functionality. Participants chose the least secure suggestion as often as the most secure one (35.0% vs 37.7%, not significant) and spent about 21 s per suggestion whatever its security. "Tests pass" was the most-used selection criterion (22 interviewees, 48 survey responses). Visible edge-case handling acted as a superficial security proxy (18 interviewees, 44 survey responses). [fetched] — [arXiv 2609.21020](https://arxiv.org/html/2609.21020v1)
- The same study: 61% agreed that AI generally improves code security, and 89% intend to keep using AI. [fetched] — [arXiv 2609.21020](https://arxiv.org/html/2609.21020v1)
- Perry et al. (CCS '23, older; 47 analyzed: 33 with an AI assistant, 14 without). Secure-answer rates, AI group vs control: encryption 21% vs 43%, message signing 3% vs 21%, sandboxed directory 12% vs 29%, SQL insert 36% vs 50% (the paper's text and table disagree on the SQL figures). The AI group was less secure on 4 of 5 tasks (overall p = 0.056 after correction), yet rated its own answers as more secure on every task. Among participants without security experience, 25.3% copied AI output on the SQL task, vs 6.67% of those with security experience. [fetched] — [Perry et al., ar5iv](https://ar5iv.labs.arxiv.org/html/2211.03622); [arXiv abstract](https://arxiv.org/abs/2211.03622)
- Mousavi (arXiv 2607.11348; 44 professionals; Copilot on Java security-API tasks): Copilot improved functional correctness but not secure API usage. Developers stayed confident even though none of the implementations was fully secure. [snippet] — [arXiv 2607.11348](https://arxiv.org/html/2607.11348v1)

### Inferences
- Likely users in 2026: (a) vibe coders and solo founders shipping web apps on Lovable, Bolt, Replit or Cursor-style tools; (b) students and learners (53% of AI users learn to code with it); (c) small-business owners or hobbyists with a Python script. Most know "it runs" but not threat models. The design target is someone who judges by passing tests and readable code, the exact cues Khalid et al. found to be unreliable.
- The flaws these users ship most often (hardcoded or exposed secrets, missing access control, SQL injection) are the ones to explain first and best. Secrets matter most: they are the commonest finding and the one with a direct cost (a leaked key gets abused).
- Python is the best case in Veracode's benchmark (63%), and still more than a third of tasks fail. AeroPatch should never say or imply that AI-written code, its own fixes included, is safe by default.

### Gaps
- No peer-reviewed survey found of non-developer vibe coders as a group (how many there are, demographics, security knowledge). The numbers above are developer surveys or vendor scans.
- Platform user counts (Lovable, Replit and similar) were not retrieved.
- The aggregator studies (the 200-repo audit, SUSVIBES, Kingbird, Symbiotic Security's August 2026 figure of 42.3 vs 9.6 vulnerabilities per repo) need checking against their primary sources.

## 2. Overreliance and trust in AI code and AI security fixes; interventions that help

### Takeaway
People with AI help write less secure code and feel more sure of it (Perry 2023; Khalid 2026; Mousavi 2026). Lower trust and more editing go with better security. What helps: making the user engage (light cognitive forcing), highlighting where to look rather than showing raw model confidence, keeping each fix small and scoped, and requiring explicit review. Forcing steps work, but people dislike them, and they help high-motivation users most.

### Cited Findings
- Perry et al. (CCS '23, older): participants who trusted the AI less and engaged more with their prompts produced fewer vulnerabilities. On one task, secure-answer participants averaged 1.5 on AI trust vs 4.0 for insecure ones. The paper recommends warnings and test suggestions based on the generated code, library usage warnings in the IDE, and visible rather than hidden controls. [fetched] — [ar5iv 2211.03622](https://ar5iv.labs.arxiv.org/html/2211.03622)
- Khalid et al. (2026): participants who changed more lines ended with fewer vulnerabilities (β = −0.5, p < 0.001). Confidence was miscalibrated: low-vulnerability participants reported confidence 87.2% of the time, high-vulnerability participants still 65.1%. The authors recommend limiting each AI suggestion's scope (e.g. to one function or line), showing provenance, a spec-first workflow where the user edits a plan before code is written, and using AI to find issues for humans to triage. [fetched] — [arXiv 2609.21020](https://arxiv.org/html/2609.21020v1)
- "From Preventive to Reactive" (arXiv 2605.23130, 2026) argues that presenting a single "best" suggestion may suppress the critical evaluation a security review needs. It cites prior experiments where developers trusted insecure suggestions such as MD5 hashing. [snippet] — [arXiv 2605.23130](https://arxiv.org/html/2605.23130v2)
- A qualitative study (27 interviews, 190 Reddit posts) found complaints that assistants are "always confident" even when wrong or insecure, and that wrong suggestions are hard to recognise. [snippet] — [arXiv 2405.06371](https://arxiv.org/html/2405.06371v2)
- Buçinca, Malaya & Gajos (CSCW 2021, older; 199 participants): three cognitive forcing designs reduced overreliance more than simple explanations did. Participants rated the most effective designs least favourably. The benefit was larger for people high in Need for Cognition. [snippet] — [arXiv 2102.09692](https://arxiv.org/pdf/2102.09692); [Harvard page](https://www.eecs.harvard.edu/~kgajos/papers/2021/bucinca2021trust.shtml)
- Vasconcelos et al. (2022/2023, older): explanations can reduce overreliance without forcing functions. [snippet] (The condition usually cited, that explanations must make verification cheaper than doing the task, is from memory of the paper and was not verified in this pass.) — [arXiv 2212.06823](https://ar5iv.labs.arxiv.org/html/2212.06823)
- Vasconcelos et al., "Generation Probabilities Are Not Enough" (ACM TOCHI 2024, older; 30 programmers): highlighting the tokens predicted to be edited sped up tasks, produced more targeted edits and was preferred. Highlighting by the model's generation probability gave no benefit over no highlighting. Participants wanted highlights that are granular, informative, interpretable and not overwhelming. [snippet] — [arXiv 2302.07248](https://arxiv.org/abs/2302.07248v3)
- Steenhoek et al. (ICSE 2025; 17 Microsoft developers on their own code; 24 projects, 1.7M LOC; 170 alerts and 50 fix suggestions from an IDE vulnerability detect-and-repair tool): the authors conclude such tools are "not yet practical for real-world use" because of high false-positive rates and non-applicable fixes. Users wanted more context and customisation. The study explored confidence scores, explanations and chat. [fetched, abstract] — [arXiv 2412.14306](https://arxiv.org/abs/2412.14306).- Automated program repair surveys: about 72% of surveyed developers are willing to review auto-generated patches but would not trust them by default and want manual review. [snippet] — [arXiv 2211.12787](https://arxiv.org/pdf/2211.12787)
- GitHub Copilot Autofix (the closest shipped analogue) "presents all suggestions as proposed code changes that require explicit developer review". It states: "You must always review suggestions ... and edit changes as needed before accepting them." Suggestions that fail GitHub's internal testing (over 2,300 alerts, unit tests plus a re-scan) are not shown, and no success-rate percentage is published. [fetched] — [GitHub Docs: Responsible use of Copilot Autofix](https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts/responsible-use-autofix-code-scanning)

### Inferences
Presentation patterns for AeroPatch:
- **Never a one-click "Fix all".** Show one finding at a time, with the fix as a proposal and an explicit "Apply this change" step. That matches Autofix and the evidence that more engagement means fewer vulnerabilities.
- **Light cognitive forcing, not heavy.** Non-experts are probably lower in Need for Cognition, and forcing steps are disliked (Buçinca). Use one cheap engagement step per fix, for example "Before applying: does your app ever need to load files from outside the project folder? Yes / No / Not sure", or a two-item "try this by hand" checklist. Avoid quizzes and timed delays.
- **Highlight where to look, not how confident the model is.** Generation probabilities do not help users (Vasconcelos 2024). Instead, mark the two or three changed lines that carry the security meaning ("this line now checks the path stays inside uploads/") and the lines most likely to break behaviour.
- **Keep each fix small and scoped** (Khalid's recommendation). A smaller diff is reviewable by a non-expert; any fix touching more than one function should carry a "larger change, review carefully" label.
- **Be honest about the base rate, with its exact meaning.** Per the project context, AeroPatch's local model alone solves about 35% of a real-CVE benchmark; Steenhoek found high rates of non-applicable fixes. That 35% is a solve rate across all attempts, not the chance that a fix shown as "Checks passed" is right (that conditional rate is unmeasured, see section 4 Gaps). State it once, plainly and accurately ("On a test set of real security bugs, AeroPatch's local model produced a working fix for about a third of them. Treat every fix as a suggestion."). Pass/fail evidence is shown per fix.
- **"Tests pass" is the user's main heuristic, and it is weak.** Khalid found it was the top cue. A green "tests passed" badge feeds the very heuristic that misleads, so tests must be framed as one piece of evidence (see section 4).
- Consider showing "what the scanner saw" first and the fix second, so the user forms a view of the problem before seeing a solution (a mild form of "decide first").

### Gaps
- No study found of non-experts (as opposed to developers) reviewing AI security fixes specifically.
- No published Copilot Autofix or Snyk Agent Fix acceptance or merge rates were found.
- arXiv 2607.24601 (34 participants, explainable AI in AI code review, effect on trust) was found, but its results were not retrieved.

## 3. Explaining a vulnerability in plain language (what could happen, how likely, what to do); reading level and length

### Takeaway
Government guidance aimed at small businesses (NCSC, CISA, NIST) is built around short, actionable steps that cost little or nothing. Error-message guidance says to name the specific problem in plain words and give the remedy. This pass found no peer-reviewed study of the best reading level for vulnerability explanations, so use a three-part "what could happen / how likely for you / what to do" block, with jargon (CWE IDs, CVSS) moved to an expandable detail.

### Cited Findings
- NCSC Small Business Guide (relaunched with an Actions Guide and a Recovery Guide): accessible, actionable steps that "cost little or nothing", organised into five topic areas; "implementing the Actions Guide will significantly reduce the chance of you becoming a victim." [snippet] — [NICSC relaunch note](https://www.nicybersecuritycentre.gov.uk/articles/relaunch-ncsc-small-business-guides); [NCSC actions guide](https://www.ncsc.gov.uk/collection/small-business-guide/small-business-guide-actions)
- CISA's small and medium business page notes that cyber incidents have surged among small businesses that "often lack the resources to defend". Its Secure by Design material puts ownership of product security on technology providers. [snippet] — [CISA SMB](https://cisa.gov/topics/small-and-medium-businesses)
- NIST's Small Business Cybersecurity Corner lists CISA's Cyber Essentials toolkit, which breaks guidance into smaller actions (last updated 29 Jan 2026). [snippet] — [NIST all-purpose guides](https://nist.gov/itl/smallbusinesscyber/guidance-topic/all-purpose-guides)
- NN/g error-message guidelines (Neusesser & Sunwall, May 2023): plain language with no jargon; hide error codes unless they help diagnosis; be specific rather than generic ("An error occurred") without becoming so technical that it confuses; give constructive remedies; use a non-blaming tone and avoid "invalid" or "incorrect"; link to extra detail only when needed. [fetched] — [NN/g](https://www.nngroup.com/articles/error-message-guidelines/)
- GOV.UK Design System: explain what went wrong and how to fix it. [snippet] — [GOV.UK error message](https://design-system.service.gov.uk/components/error-message). UK Home Office: use simple language that names the cause, and give suggestions for fixing it unless that would compromise security. [snippet] — [Home Office design](https://design.homeoffice.gov.uk/accessibility/interactivity/error-messages)
- Stack Overflow 2026: 79% rate source attribution as important when judging AI-generated code or answers. [fetched] — [Stack Overflow blog](https://stackoverflow.blog/2026/10/06/tales-from-the-2026-developer-survey-results/)
- Copilot Autofix pairs every fix with "a natural language explanation of the fix". [fetched] — [GitHub Docs](https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts/responsible-use-autofix-code-scanning)

### Inferences
Suggested per-finding card (front-loaded, aiming for well under 150 words before any "Show technical details" toggle):
1. **Headline in user terms:** "Someone could read any file on your computer through your upload page" rather than "CWE-22 Path Traversal (B108)".
2. **What could happen:** one or two concrete consequences tied to their app ("they could download your .env file, which holds your Stripe key").
3. **How likely this matters for you:** conditional on context the tool can detect or ask about ("This matters if the app is on the internet. If it only runs on your laptop, the risk is low."). Use the scanner's severity, but explain it in words.
4. **What AeroPatch suggests:** one sentence on what the change does ("checks that the file name stays inside the uploads folder").
5. **What you should do:** the next action ("Review the 3 highlighted lines, then Apply. Then try the two checks below.")
6. **Behind a toggle:** rule ID, CWE link, OWASP category, scanner output, full diff and test log. This serves the 79% who want attribution and lets the user learn more.
- Attribute each claim's source ("found by Bandit rule B602"; "fix written by the local model qwen…"; "checked by: re-scan + 12 tests").
- Secrets need a special explanation, because fixing the code does not undo the exposure: "Moving the key out of the code stops future leaks, but if this code was ever pushed to GitHub or shared, rotate the key now", with a link to the provider's rotate page.

### Gaps
- Not retrieved: GOV.UK's reading-age guidance (often quoted as writing for a reading age of about 9, unverified here), Snyk Learn's lesson structure, GitHub Security Advisory field layout, OWASP's plain-language material, or any MITRE CWE "plain language" effort. These are worth checking directly before choosing a house style.
- No empirical study found comparing explanation lengths or reading levels for vulnerability explanations to non-experts.

## 4. Communicating confidence and verification status without false assurance

### Takeaway
Verbal probability words ("likely", "probably") mean very different things to different people, most of all in the 20 to 80% middle range; extreme terms are understood most consistently. Status should be stated as concrete, checkable evidence ("scanner no longer flags this line; 12 existing tests pass; 0 new tests") with an explicit statement of what was not checked, never as "secure" or "fixed". Colour is never the only signal.

### Cited Findings
- A Dutch study of verbal probability phrases (881 participants) found large variability in interpretation, even within sub-populations and among statisticians. Extreme terms ("always", "certain", "never", "impossible") were the most consistent, and disagreement was widest for phrases in the 20 to 80% range. The authors call verbal probability expressions "a risk for miscommunication". [snippet] — [arXiv 1901.09686](https://arxiv.org/pdf/1901.09686)
- Khalid et al. (2026): "tests pass" was the most-used cue for choosing code, and surface features such as edge-case blocks were taken as signs of security. [fetched] — [arXiv 2609.21020](https://arxiv.org/html/2609.21020v1)
- Vasconcelos et al. (TOCHI 2024): raw generation-probability signals did not help programmers. [snippet] — [arXiv 2302.07248](https://arxiv.org/abs/2302.07248v3)
- Copilot Autofix's limitations wording, a useful template: the system "may suggest fixes that fail to remediate the underlying vulnerability or introduce new vulnerabilities"; it "has no understanding of the programmer's intent"; users should confirm CI passes and the alert is resolved before merging. [fetched] — [GitHub Docs](https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts/responsible-use-autofix-code-scanning)
- NN/g: match presentation to severity (inline or banner for minor issues, modal only for severe blocking ones), and never rely on colour or motion alone. [fetched] — [NN/g](https://www.nngroup.com/articles/error-message-guidelines/). Home Office: do not use colour alone to identify an error. [snippet] — [Home Office](https://design.homeoffice.gov.uk/accessibility/interactivity/error-messages)

### Inferences
- **Status labels as evidence, not verdicts.** Suggested three states, each with an icon, a word and a sentence, never colour alone:
  - "Checks passed, needs your review": the scanner no longer flags it, the existing tests still pass, and the sandbox run finished.
  - "Partly checked": e.g. the re-scan is clean but there were no tests, or only AeroPatch-written tests.
  - "Not fixed": the fix failed a check; show which one and offer "keep the warning" or "ask a stronger model" (opt-in).
  - Banned words in status lines: "secure", "safe", "fixed", "verified", "guaranteed". Prefer "the scanner no longer reports this", "tests that existed before still pass".
- **Always pair "what was checked" with "what was not checked."** Example: "Checked: Bandit re-scan, 12 existing tests, ran with no network. Not checked: whether your app still behaves the way you want; other places with the same problem; the live server."
- **Differentiate test provenance.** Existing user tests passing is evidence of no regression. Model-written tests passing is weak evidence (the same model wrote both). A "failing before, passing after" exploit test is the strongest available signal, so show it as such ("we wrote a test that reads ../../.env: before the fix it succeeded, after the fix it is blocked").
- **No raw confidence percentages.** If a likelihood must be conveyed, use a numeric frequency measured for that status on AeroPatch's own benchmark ("on real bugs, fixes that passed these same checks were correct N in 10 times"), not "likely correct". Do not reuse the overall 35% solve rate for this: it answers a different question (see Gaps).
- **Calibrate the severity display to context.** Severity words should come with a reason ("High: anyone on the internet could trigger it"), because severity words alone are interpreted inconsistently.

### Gaps
- Unsourced (search-summary only, no paper mapped to a URL): that "likely" is read as anywhere from about 10% to 85%; that giving the numeric range alongside the verbal term (as the IPCC scale does) improves consistency; that lay people vary more than surgeons and read risk words systematically higher. Candidate sources appeared in results (e.g. a UCL Harris et al. PDF). Verify before using any of these.
- The number the interface actually needs is the share of fixes that are correct **per displayed status** (e.g. how often a "Checks passed" fix is truly right), for the local model and separately for opt-in frontier runs. It is not in the project context and should be measured on AeroPatch's own benchmark before any likelihood wording is shown to users.
- Browser-warning research (e.g. Felt et al. on "opinionated" SSL warning design and adherence) and studies of traffic-light labels for software risk were not retrieved.

## 5. Review and apply flows for non-experts (diffs, one-click apply with undo, backups, git branches, manual test steps)

### Takeaway
The shipped norm (GitHub Copilot Autofix) is: the fix is a proposal, explanation alongside, explicit review, edits allowed, merge only after CI passes and the alert clears. Research supports small scoped diffs and user editing (the value of a before/after view for non-experts is untested; see Gaps). This pass found no empirical study of undo, backup or branch flows for non-experts, so these are design inferences.

### Cited Findings
- Copilot Autofix: suggestions appear inline on the pull request or alert page as "proposed code changes that require explicit developer review". Users "must always review ... and edit changes as needed before accepting them", should confirm CI passes and the alert is resolved before merging, and should "always verify dependency changes before merging". Fixes may also add fabricated or insecure dependencies. [fetched] — [GitHub Docs](https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts/responsible-use-autofix-code-scanning)
- More edits to AI suggestions predicted fewer vulnerabilities (β = −0.5). Recommended: limit suggestion scope; show provenance; let users edit a plan before code. [fetched] — [Khalid et al. 2026](https://arxiv.org/html/2609.21020v1)
- About 72% of developers would review auto-generated patches but want manual review by default. [snippet] — [arXiv 2211.12787](https://arxiv.org/pdf/2211.12787)
- Perry et al. recommend giving "warnings and test suggestions based on generated code". [fetched] — [ar5iv 2211.03622](https://ar5iv.labs.arxiv.org/html/2211.03622)
- NN/g: preserve user input and offer a short list of likely fixes to pick from. [fetched] — [NN/g](https://www.nngroup.com/articles/error-message-guidelines/)

### Inferences
Suggested flow (lowest-effort version first):
1. **Safety net before any change.** If the folder is a git repo, apply fixes on a new branch (`aeropatch/fix-<date>`) and commit each fix separately, so one fix can be reverted. If it is not a git repo, copy each changed file to `.aeropatch/backup/<timestamp>/` first. Always print the one undo command or button ("Undo all AeroPatch changes"). Never touch the user's main branch or uncommitted work without asking.
2. **Per-finding review screen:** plain-language card (section 3), then a side-by-side or unified diff limited to the changed function with the security-relevant lines highlighted, then the evidence block (section 4), then **Apply / Skip / Edit first / Ask a stronger model (cloud, opt-in)**.
3. **"Try this yourself" checklist after apply:** two or three concrete manual checks in user terms ("Upload a normal photo: it should still work. Try a file named ../../secret.txt: you should see an error."). This is the light forcing function and the regression check the sandbox cannot do.
4. **Dependency changes get their own warning.** Autofix documents fabricated or insecure dependencies as a failure mode, so any added or changed package must be listed with "check this package exists and is the one you expect".
5. **End-of-run summary:** counts by status ("3 checked and applied, 1 partly checked, 2 not fixed, warnings kept"). List what still needs action first.
6. Keep the technical markdown report and raw diff as an export for anyone who wants it, or wants to hand it to a developer.

### Gaps
- No empirical evidence found on undo or backup affordances, branch-based apply flows, or side-by-side vs unified diffs for non-programmers. A good subject for AeroPatch's own think-aloud tests (section 8).
- No data found on how often non-experts run the manual test steps they are given.

## 6. Reporting errors and setup problems to non-technical users

### Takeaway
State the specific problem in plain words, keep codes and stack traces out of the main message, give a concrete fix (ideally a command or button), never blame the user, and keep their work. For AeroPatch's setup chain (Python, Docker, Ollama, a model download), each known failure deserves a pre-written, actionable message.

### Cited Findings
- NN/g (May 2023): place the message near its cause; match severity to presentation; plain language; hide error codes unless they help diagnosis; be specific, not generic; give constructive advice; positive, non-judgmental tone (avoid "invalid" or "incorrect"); no humour on repeated errors; prevent errors before they happen; preserve input; offer a short list of likely fixes; teach concisely with links to more. [fetched] — [NN/g](https://www.nngroup.com/articles/error-message-guidelines/)
- GOV.UK: say what went wrong and how to fix it. Summarise multiple errors in one list that links to each. [snippet] — [GOV.UK Design System](https://design-system.service.gov.uk/components/error-message). GOV.UK also has a "There is a problem with the service" pattern for total failures. [snippet] — [GOV.UK pattern](https://design-system.service.gov.uk/patterns/problem-with-the-service-pages)
- Home Office: name the cause in simple language, suggest a correction, don't rely on colour. [snippet] — [Home Office](https://design.homeoffice.gov.uk/accessibility/interactivity/error-messages)

### Inferences
- Map every known failure to a template: **what happened** / **why it matters** / **what to do (copy-paste command or button)** / **"Show details"** (stack trace and log path). Examples:
  - "Docker isn't running. AeroPatch needs Docker to test fixes safely, away from your files. Start Docker Desktop, wait for the whale icon to stop moving, then click Retry."
  - "The local AI model isn't downloaded yet (about 5 GB). Download now / Choose a smaller model."
  - "Your computer ran low on memory while testing this fix. Close other apps and retry, or skip this finding."
- Add a preflight "Check my setup" step that runs before scanning (Docker up, Ollama reachable, model present, enough disk and RAM) and reports all problems in one list (the GOV.UK error-summary idea). This prevents errors mid-run.
- Partial failure must not lose results: if one fix crashes, keep the other findings and say which one failed.
- Never show a raw Python traceback as the primary message. Write it to a log and offer "Copy details for a bug report".

### Gaps
- No research found specifically on error messages for developer CLIs or local-AI setup used by non-experts.

## 7. Privacy and safety expectations (code leaving the machine, secrets, cloud consent, sandboxing) and regulation

### Takeaway
Exposing sensitive data (secrets, proprietary code) is a recurring, documented worry and a documented failure of AI coding tools. Some LLM IDEs have sent environment-file contents to external services without confirmation. Local-only by default, explicit per-run consent before any cloud call, and redacting secrets before any outbound request match both user concerns and observed failures. The EU Cyber Resilience Act most likely does not apply to a non-monetised individual open-source project, but this is an inference from secondary sources.

### Cited Findings
- arXiv 2607.26390 ("Impossible to hide secret ...", 2026) on LLM-native IDEs: confidential data was sent to external services without user confirmation, e.g. Windsurf sending an environment file's contents externally. [snippet] — [arXiv 2607.26390](https://arxiv.org/pdf/2607.26390)
- The Cloud Security Alliance's note treats coding assistants as an attack surface. They read .env files, YAML configs and MCP configs. AI-assisted commits leak secrets at 3.2% vs a 1.5% baseline (GitGuardian figure). [snippet] — [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-coding-assistant-attack-surface-2026040/); [Knostic blog, vendor](https://www.knostic.ai/blog/ai-coding-assistants-leaking-secrets)
- Developer interviews: "the risk of inadvertently exposing sensitive information" was a recurring concern. One participant's leadership discouraged external AI tools because providers aren't transparent about use of the data. [snippet] — [arXiv 2405.06371](https://arxiv.org/html/2405.06371v2)
- CodeCloak (arXiv 2024, older): local models avoid sending prompts outside the network. Remote models offer freshness, performance and ease of use, so there is a trade-off. [snippet] — [arXiv 2404.09066](https://arxiv.org/pdf/2404.09066)
- Stack Overflow 2026: 79% want source attribution for AI answers, a transparency expectation. [fetched] — [Stack Overflow blog](https://stackoverflow.blog/2026/10/06/tales-from-the-2026-developer-survey-results/)
- EU Cyber Resilience Act (secondary sources only). Manufacturers' Article 14 reporting obligations (actively exploited vulnerabilities and severe incidents) apply from 11 Sep 2026; the rest, including open-source steward duties (a documented cybersecurity policy, cooperation with market-surveillance authorities), from 11 Dec 2027. [snippet] — [noze.it](https://www.noze.it/en/insights/cyber-resilience-act-sbom/); [Goodwin, Sep 2026](https://www.goodwinlaw.com/en/insights/publications/2026/09/alerts-lifesciences-technology-preparing-for-eu-cyber-resilience-act); [Checkmarx](https://checkmarx.com/zero-post/the-cyber-resilience-acts-new-reporting-obligations-are-active-what-you-should-know.md)
- A "steward" is described as a legal person that gives sustained support to FOSS intended for commercial activities. Monetised open source can make the company a "manufacturer". Stewards are reportedly exempt from administrative fines (Art. 64(10)). One vendor (Patchstack) claims stewards are affected from Sep 2026, which conflicts with the other sources. [snippet] — [OpenSSF steward one-pager](https://policy.openssf.org/CRA/stewards-one-pager.html); [HeroDevs](https://www.herodevs.com/blog-posts/cra-reporting-obligations-start-september-2026-what-eol-dependencies-mean-for-your-compliance); [Patchstack](https://patchstack.com/articles/launching-managed-cra-article-14-reporting-for-open-source-maintainers/)

### Inferences
- **Privacy defaults to state up front, on the first screen and in the README:** "Your code stays on this computer. AeroPatch uses a local model and tests fixes in a sandbox with no internet." Then show it during the run: "Model: local (Ollama). Network: off".
- **Cloud opt-in consent pattern:** per run (not a hidden global setting), naming exactly what is sent ("the 40 lines around this finding, not your whole project"), where it goes (provider name), and that it may cost money or need an API key. Show a preview of the outgoing text with secrets already redacted. Default button: "Keep local".
- **Secrets:** scan for and mask secrets before anything is written to reports, logs or prompts. Never include a secret's value in the report ("API key found on line 12 of config.py", not the key). Advise rotation (section 3).
- **Sandbox wording:** explain in one line why the user's code is run ("to check the fix doesn't break your tests") and what the sandbox prevents ("no internet, no access to files outside a copy of your project"). Running someone's own code is expected, but saying so builds calibrated trust.
- **CRA:** AeroPatch is a free, non-monetised, individually maintained portfolio project, so it is probably outside CRA manufacturer and steward obligations (individuals reportedly fall outside the steward definition, and there is no commercial placing on the market). Verify against Art. 3(14), Art. 24, Art. 64(10) and the open-source recitals in the Official Journal text. A public SECURITY.md with a way to report vulnerabilities is cheap good practice regardless.

### Gaps
- No user survey found that quantifies non-experts' expectations about code leaving their machine (e.g. the share who would refuse cloud processing).
- The CRA reading comes only from law-firm and vendor commentary; the Official Journal text was not read.
- GDPR implications of sending code containing personal data to a cloud model were not researched.

## 8. Practical usability evaluation methods for a solo developer

### Takeaway
Run small iterative think-aloud rounds: 5 users find about 85% of problems in a homogeneous group, and three rounds of 5 beat one round of 15. Add task success and the 10-item System Usability Scale (average 68 is the 50th percentile). For AeroPatch, add a calibration measure: does the user apply the good fixes and reject the bad ones?

### Cited Findings
- Nielsen (2000, older but still the standard reference): the first 5-user study found about 85% of usability problems, using N(1 − (1 − L)^n) with a typical L = 31%. Run three rounds of 5 with fixes in between rather than one round of 15. With distinct user groups, test 3 to 4 per group for two groups, and 3 per group for three or more. [fetched] — [NN/g: Why you only need to test with 5 users](https://www.nngroup.com/articles/why-you-only-need-to-test-with-5-users/)
- SUS benchmarks (MeasuringU): mean SUS across about 500 products is 68, the 50th percentile. 75 is about the 73rd percentile and 52 about the 15th. A SUS score is not a percentage. [snippet] — [MeasuringU: SUS](https://www.measuringu.com/sus/); [MeasuringU: 10 things about SUS](https://www.measuringu.com/10-things-sus)
- Khalid et al. measured security outcomes, suggestion choice, time per suggestion and self-reported confidence, and paid a bonus for secure code. A ready template for a calibration task. [fetched] — [arXiv 2609.21020](https://arxiv.org/html/2609.21020v1)
- Perry et al. measured belief that the code is secure against actual security, the overconfidence signal. [fetched] — [ar5iv 2211.03622](https://ar5iv.labs.arxiv.org/html/2211.03622)

### Inferences
A practical protocol for AeroPatch:
- **Participants:** 2 groups × 3 people (e.g. vibe coders or solo founders, and students), recruited from friends, Discord or Reddit communities, about 45 min each, remote screen share, think-aloud. Repeat after fixes (a second round of 5).
- **Seeded test project:** a small Flask app with 4 to 5 findings, where AeroPatch's output (fixed in advance for repeatability) includes at least one good fix, one plausible-but-wrong fix (e.g. passes the re-scan but breaks a feature or only partly fixes the bug), and one "not fixed".
- **Tasks:** (1) install and run the setup check; (2) scan the project; (3) for each finding, decide apply or skip and say why; (4) undo one change; (5) explain back in their own words what one finding meant.
- **Measures:** task success and time; **appropriate reliance** (applied good fixes / rejected the bad one, the key metric); self-rated confidence per decision vs correctness (calibration, as in Perry and Khalid); comprehension (can they restate the risk in one sentence?); SUS at the end (target ≥ 68, ideally ≥ 75); whether they ran the manual test steps.
- **Analysis:** list problems by severity after each round, fix the top ones, retest. A solo developer can do all of this with a spreadsheet.

### Gaps
- No MeasuringU or NN/g source was retrieved on think-aloud protocol specifics, or on average task-completion benchmarks.
- No validated questionnaire for "appropriate reliance on AI fixes" was found. The measure above is adapted from the research designs, not a standard instrument.
